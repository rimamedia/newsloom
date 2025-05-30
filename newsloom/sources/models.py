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
    link = models.URLField(unique=True, max_length=1000)
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
        return f'{self.title}'


class Doc(models.Model):
    STATUS_CHOICES = [
        ("new", "New"),
        ("edit", "Edit"),
        ("publish", "Publish"),
        ("failed", "Failed"),
    ]

    media = models.ForeignKey(
        "mediamanager.Media", on_delete=models.CASCADE, related_name="docs"
    )
    link = models.URLField(unique=True)
    google_doc_link = models.URLField(blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    text = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="new")
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Meta configuration for Doc model."""

        ordering = ["-published_at"]
        verbose_name = "Doc"
        verbose_name_plural = "Docs"
        indexes = [
            models.Index(fields=["-published_at"]),
            models.Index(fields=["link"]),
        ]

    def __str__(self):
        return self.title
