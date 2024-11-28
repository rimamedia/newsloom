from django.contrib import admin

from .models import News, Source


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "link", "created_at", "updated_at")
    list_filter = ("type",)
    search_fields = ("name", "link")


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ("title", "source", "published_at", "created_at", "updated_at")
    list_filter = ("source", "published_at")
    search_fields = ("title", "text")
    date_hierarchy = "published_at"
