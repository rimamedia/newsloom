from django.db import models


class Source(models.Model):
    TYPE_CHOICES = [
        ("web", "Web"),
        ("telegram", "Telegram"),
        ("search", "Search"),
        ("rss", "RSS Feed"),
        ("twitter", "Twitter"),
        ("facebook", "Facebook"),
        ("linkedin", "LinkedIn"),
    ]

    name = models.CharField(max_length=255)
    link = models.URLField(help_text="Main website URL (e.g., https://techcrunch.com)")
    type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Meta configuration for Source model."""

        ordering = ["-created_at"]
        verbose_name = "Source"
        verbose_name_plural = "Sources"

    def __str__(self):
        return self.name


class News(models.Model):
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name="news")
    link = models.URLField(unique=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    text = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Meta configuration for News model."""

        ordering = ["-published_at"]
        verbose_name = "News"
        verbose_name_plural = "News"
        indexes = [
            models.Index(fields=["-published_at"]),
            models.Index(fields=["link"]),
        ]

    def __str__(self):
        return self.title
