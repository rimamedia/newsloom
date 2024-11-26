from django.db import models
from sources.models import Source

class Media(models.Model):
    name = models.CharField(max_length=255)
    sources = models.ManyToManyField(Source, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Media'
        verbose_name_plural = 'Media'

    def __str__(self):
        return self.name 