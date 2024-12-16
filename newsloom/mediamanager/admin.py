from django.contrib import admin

from .models import Examples, Media


@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at", "updated_at")
    filter_horizontal = ("sources",)
    search_fields = ("name",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(Examples)
class ExamplesAdmin(admin.ModelAdmin):
    list_display = ("media", "text", "created_at", "updated_at")
    search_fields = ("text", "media__name")
    readonly_fields = ("created_at", "updated_at")
