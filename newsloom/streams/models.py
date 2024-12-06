import json
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from mediamanager.models import Media
from pydantic import ValidationError as PydanticValidationError
from sources.models import Source

from .schemas import STREAM_CONFIG_SCHEMAS


class Stream(models.Model):
    TYPE_CHOICES = [
        ("sitemap_news", "Sitemap News Parser"),
        ("sitemap_blog", "Sitemap Blog Parser"),
        ("playwright_link_extractor", "Playwright Link Extractor"),
        ("rss_feed", "RSS Feed Parser"),
        ("web_article", "Web Article Scraper"),
        ("telegram_channel", "Telegram Channel Monitor"),
        ("telegram_publish", "Telegram Links Publisher"),
        ("telegram_test", "Telegram Test Publisher"),
        ("article_searcher", "Article Content Searcher"),
        ("bing_search", "Bing Search"),
        ("telegram_bulk_parser", "Telegram Bulk Parser"),
    ]

    FREQUENCY_CHOICES = [
        ("5min", "Every 5 minutes"),
        ("15min", "Every 15 minutes"),
        ("30min", "Every 30 minutes"),
        ("1hour", "Every hour"),
        ("6hours", "Every 6 hours"),
        ("12hours", "Every 12 hours"),
        ("daily", "Daily"),
    ]

    STATUS_CHOICES = [
        ("active", "Active"),
        ("paused", "Paused"),
        ("failed", "Failed"),
    ]

    name = models.CharField(max_length=255)
    stream_type = models.CharField(
        max_length=50, choices=TYPE_CHOICES
    )  # Changed from task_type
    source = models.ForeignKey(
        Source, on_delete=models.CASCADE, related_name="streams", null=True, blank=True
    )
    media = models.ForeignKey(
        Media, on_delete=models.CASCADE, related_name="streams", null=True, blank=True
    )
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    configuration = models.JSONField(
        help_text="Stream-specific configuration parameters in JSON format."
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Meta configuration for Stream model."""

        ordering = ["-created_at"]
        verbose_name = "Stream"
        verbose_name_plural = "Streams"
        indexes = [
            models.Index(fields=["stream_type"]),
            models.Index(fields=["status"]),
            models.Index(fields=["next_run"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_stream_type_display()})"

    def clean(self):
        """Validate the stream configuration against its schema."""
        try:
            # Get the appropriate schema for this stream type
            config_schema = STREAM_CONFIG_SCHEMAS.get(self.stream_type)
            if not config_schema:
                raise ValidationError(_(f"Unknown stream type: {self.stream_type}"))

            # Handle empty configuration
            if not self.configuration:
                raise ValidationError(_("Configuration cannot be empty"))

            # Parse and validate configuration
            if isinstance(self.configuration, str):
                try:
                    config = json.loads(self.configuration)
                except json.JSONDecodeError:
                    raise ValidationError(_("Invalid JSON configuration"))
            else:
                config = self.configuration

            # Validate configuration without modifying it
            try:
                # Use parse_obj instead of model_validate
                config_schema.parse_obj(config)
            except PydanticValidationError as e:
                errors = []
                for error in e.errors():
                    field = ".".join(str(x) for x in error["loc"])
                    message = error["msg"]
                    errors.append(f"{field}: {message}")
                raise ValidationError(
                    _(f"Configuration validation failed: {'; '.join(errors)}")
                )

        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(str(e))

    def save(self, *args, **kwargs):
        """Save the stream instance."""
        skip_validation = kwargs.pop("skip_validation", False)
        update_fields = kwargs.get("update_fields")

        # Skip validation if we're only updating specific fields or if skip_validation is True
        if not skip_validation and not update_fields:
            # Store current configuration
            current_config = self.configuration
            try:
                self.clean()
            except Exception as e:
                # Restore original configuration if validation fails
                self.configuration = current_config
                raise e

        super().save(*args, **kwargs)

    def get_next_run_time(self):
        """Calculate the next run time based on frequency."""
        if not self.last_run:
            return timezone.now()

        frequency_mapping = {
            "5min": timedelta(minutes=5),
            "15min": timedelta(minutes=15),
            "30min": timedelta(minutes=30),
            "1hour": timedelta(hours=1),
            "6hours": timedelta(hours=6),
            "12hours": timedelta(hours=12),
            "daily": timedelta(days=1),
        }

        next_run = self.last_run + frequency_mapping[self.frequency]
        if timezone.is_naive(next_run):
            next_run = timezone.make_aware(next_run)
        return next_run

    def execute_task(self):
        """Execute the stream task directly."""
        import logging

        from django.db import transaction
        from django.utils import timezone

        from .tasks import get_task_function
        from .tasks.bing_search import _local

        logger = logging.getLogger(__name__)

        try:
            with transaction.atomic():
                # Refresh from database to ensure we have the latest state
                self.refresh_from_db()

                # Cancel any existing task for this stream
                if hasattr(_local, "cancelled"):
                    _local.cancelled = True

                task_log = StreamLog.objects.create(stream=self)

                task_function = get_task_function(self.stream_type)
                if not task_function:
                    raise ValueError(f"No task function found for {self.stream_type}")

                # Execute task
                result = task_function(stream_id=self.id, **self.configuration)

                # Update stream status and log within the same transaction
                Stream.objects.filter(id=self.id).update(
                    last_run=timezone.now(),
                    next_run=self.get_next_run_time(),
                    status="active",
                )

                # Update log with success
                task_log.status = "success"
                task_log.completed_at = timezone.now()
                task_log.result = result
                task_log.save()

                return result

        except Exception as e:
            logger.exception(f"Task execution failed for stream {self.id}")

            try:
                # Handle failure in a new transaction
                with transaction.atomic():
                    Stream.objects.filter(id=self.id).update(status="failed")

                    if "task_log" in locals():
                        task_log.status = "failed"
                        task_log.completed_at = timezone.now()
                        task_log.error_message = str(e)
                        task_log.save()
            except Exception as inner_e:
                logger.error(f"Failed to update error status: {inner_e}")

            raise


class TelegramPublishLog(models.Model):
    """Tracks which news items have been published to which Telegram channels."""

    news = models.ForeignKey("sources.News", on_delete=models.CASCADE)
    media = models.ForeignKey("mediamanager.Media", on_delete=models.CASCADE)
    published_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Meta configuration for TelegramPublishLog model."""

        indexes = [models.Index(fields=["media", "published_at"])]
        unique_together = [("news", "media")]


class StreamLog(models.Model):
    """Logs for stream task executions."""

    STATUS_CHOICES = [
        ("success", "Success"),
        ("failed", "Failed"),
        ("running", "Running"),
    ]

    stream = models.ForeignKey(Stream, on_delete=models.CASCADE, related_name="logs")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="running")
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    result = models.JSONField(
        null=True, blank=True, help_text="Task execution results in JSON format"
    )

    class Meta:
        """Meta configuration for StreamLog model."""

        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["stream", "status"]),
            models.Index(fields=["started_at"]),
        ]

    def __str__(self):
        return f"{self.stream.name} - {self.started_at}"
