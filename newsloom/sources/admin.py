from django.contrib import admin

from .models import Doc, News, Source


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


@admin.register(Doc)
class DocAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "media",
        "status",
        "published_at",
        "created_at",
        "updated_at",
    )
    list_filter = ("media", "status", "published_at")
    search_fields = ("title", "text")
    date_hierarchy = "published_at"
    actions = ["set_status_new"]

    def set_status_new(self, request, queryset):
        count = 0
        for doc in queryset:
            doc.status = "new"
            doc.save()  # This will trigger auto_now for updated_at
            count += 1
        self.message_user(request, f"{count} documents were set to 'new' status.")

    set_status_new.short_description = "Set selected docs to 'new' status"
