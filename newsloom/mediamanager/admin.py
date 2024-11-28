from django.contrib import admin

from .models import Media


@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at", "updated_at")
    filter_horizontal = ("sources",)
    search_fields = ("name",)
    readonly_fields = ("created_at", "updated_at")
