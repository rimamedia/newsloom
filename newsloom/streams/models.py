from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from sources.models import Source
from .schemas import STREAM_CONFIG_SCHEMAS
import json
from datetime import timedelta
from pydantic import ValidationError as PydanticValidationError
from django.utils import timezone
from mediamanager.models import Media

class Stream(models.Model):
    TYPE_CHOICES = [
        ('sitemap_news', 'Sitemap News Parser'),
        ('sitemap_blog', 'Sitemap Blog Parser'),
        ('playwright_link_extractor', 'Playwright Link Extractor'),
        ('rss_feed', 'RSS Feed Parser'),
        ('web_article', 'Web Article Scraper'),
        ('telegram_channel', 'Telegram Channel Monitor'),
        ('telegram_publish', 'Telegram Publisher'),
    ]

    FREQUENCY_CHOICES = [
        ('5min', 'Every 5 minutes'),
        ('15min', 'Every 15 minutes'),
        ('30min', 'Every 30 minutes'),
        ('1hour', 'Every hour'),
        ('6hours', 'Every 6 hours'),
        ('12hours', 'Every 12 hours'),
        ('daily', 'Daily'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('failed', 'Failed'),
    ]

    name = models.CharField(max_length=255)
    stream_type = models.CharField(max_length=50, choices=TYPE_CHOICES)  # Changed from task_type
    source = models.ForeignKey(
        Source, 
        on_delete=models.CASCADE, 
        related_name='streams',
        null=True,
        blank=True
    )
    media = models.ForeignKey(
        Media,
        on_delete=models.CASCADE,
        related_name='streams',
        null=True,
        blank=True
    )
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    configuration = models.JSONField(
        help_text='Stream-specific configuration parameters in JSON format'  # Updated help text
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES,
        default='active'
    )
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Stream'  # Changed from Task
        verbose_name_plural = 'Streams'  # Changed from Tasks
        indexes = [
            models.Index(fields=['stream_type']),  # Changed from task_type
            models.Index(fields=['status']),
            models.Index(fields=['next_run']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_stream_type_display()})"  # Changed from task_type

    def clean(self):
        """Validate the configuration JSON based on stream_type using Pydantic schemas"""
        try:
            # Get the appropriate schema for this stream type
            config_schema = STREAM_CONFIG_SCHEMAS.get(self.stream_type)
            if not config_schema:
                raise ValidationError(_(f"Unknown stream type: {self.stream_type}"))
            
            # Handle empty configuration
            if not self.configuration:
                raise ValidationError(_("Configuration cannot be empty"))
            
            # Parse and validate configuration
            config = self.configuration if isinstance(self.configuration, dict) else json.loads(self.configuration)
            validated_config = config_schema(**config)
            
            # Convert to dict and use primitive types
            self.configuration = json.loads(validated_config.model_dump_json())
            
        except json.JSONDecodeError:
            raise ValidationError(_("Invalid JSON configuration"))
        except PydanticValidationError as e:
            # Convert Pydantic validation errors to Django validation errors
            errors = []
            for error in e.errors():
                field = '.'.join(str(x) for x in error['loc'])
                message = error['msg']
                errors.append(f"{field}: {message}")
            raise ValidationError(_(f"Configuration validation failed: {'; '.join(errors)}"))

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
        # Remove direct task scheduling from save

    def get_next_run_time(self):
        """Calculate the next run time based on frequency"""
        if not self.last_run:
            return timezone.now()

        frequency_mapping = {
            '5min': timedelta(minutes=5),
            '15min': timedelta(minutes=15),
            '30min': timedelta(minutes=30),
            '1hour': timedelta(hours=1),
            '6hours': timedelta(hours=6),
            '12hours': timedelta(hours=12),
            'daily': timedelta(days=1),
        }
        
        next_run = self.last_run + frequency_mapping[self.frequency]
        if timezone.is_naive(next_run):
            next_run = timezone.make_aware(next_run)
        return next_run

    def schedule_luigi_task(self):
        """Schedule or update the Luigi task based on the configuration"""
        from .tasks import get_task_class
        import logging
        
        logger = logging.getLogger(__name__)
        
        task_class = get_task_class(self.stream_type)
        if not task_class:
            logger.error(f"No task class found for stream_type: {self.stream_type}")
            return

        next_run = self.get_next_run_time()
        if timezone.is_naive(next_run):
            next_run = timezone.make_aware(next_run)

        task_params = {
            'stream_id': self.id,
            'scheduled_time': next_run.isoformat(),
        }
        
        task_params.update(self.configuration)
        logger.info(f"Scheduling task with params: {task_params}")
        
        try:
            # Create the task instance without building it
            task_instance = task_class(**task_params)
            
            # Update stream status and next run time
            Stream.objects.filter(id=self.id).update(
                status='active',
                next_run=next_run
            )
            
            return task_instance
            
        except Exception as e:
            Stream.objects.filter(id=self.id).update(
                status='failed',
                last_run=timezone.now()
            )
            raise e

class LuigiTaskLog(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('FAILED', 'Failed'),
        ('COMPLETED', 'Completed'),
    ]

    stream = models.ForeignKey('Stream', on_delete=models.CASCADE, related_name='luigi_logs')
    task_id = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-started_at']

class TelegramPublishLog(models.Model):
    """Tracks which news items have been published to which Telegram channels"""
    news = models.ForeignKey('sources.News', on_delete=models.CASCADE)
    media = models.ForeignKey('mediamanager.Media', on_delete=models.CASCADE)
    published_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('news', 'media')
        indexes = [
            models.Index(fields=['media', 'published_at']),
        ]