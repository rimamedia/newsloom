from django.db import models
from sources.models import Source


class Media(models.Model):
    name = models.CharField(max_length=255)
    sources = models.ManyToManyField(Source, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Meta configuration for Media model."""

        ordering = ["name"]
        verbose_name = "Media"
        verbose_name_plural = "Media"

    def __str__(self):
        return self.name


class Examples(models.Model):
    media = models.ForeignKey(Media, on_delete=models.CASCADE, related_name="examples")
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Meta configuration for Examples model."""

        verbose_name = "Example"
        verbose_name_plural = "Examples"

    def __str__(self):
        return f"Example for {self.media.name}"
