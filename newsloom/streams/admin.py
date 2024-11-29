import json

from django.contrib import admin
from django.utils.html import format_html

from .models import LuigiTaskLog, Stream, TelegramPublishLog
from .schemas import STREAM_CONFIG_SCHEMAS
from .tasks import get_task_class


@admin.register(Stream)
class StreamAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "stream_type",
        "source",
        "frequency",
        "status",
        "last_run",
        "next_run",
    )
    list_filter = ("stream_type", "status", "frequency")
    search_fields = ("name", "source__name")
    readonly_fields = ("last_run", "next_run", "created_at", "updated_at")

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "stream_type",
                    "source",
                    "media",
                    "frequency",
                    "status",
                )
            },
        ),
        (
            "Configuration",
            {
                "fields": ("configuration",),
                "classes": ("collapse",),
                "description": "Stream-specific configuration in JSON format",
            },
        ),
        (
            "Timing Information",
            {
                "fields": ("last_run", "next_run", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.readonly_fields + ("stream_type",)
        return self.readonly_fields

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if "configuration" in form.base_fields:
            stream_type = None
            if obj:
                stream_type = obj.stream_type
            elif request.method == "POST":
                stream_type = request.POST.get("stream_type")
            elif request.method == "GET":
                stream_type = request.GET.get("stream_type")

            if stream_type:
                schema = STREAM_CONFIG_SCHEMAS.get(stream_type)
                if schema:
                    task_class = get_task_class(stream_type)
                    example = task_class.get_config_example() if task_class else {}

                    help_text = format_html(
                        "Example configuration for {}:<br><pre>{}</pre>",
                        stream_type,
                        json.dumps(example, indent=2),
                    )
                    form.base_fields["configuration"].help_text = help_text

        return form

    def formfield_for_dbfield(self, db_field, **kwargs):
        field = super().formfield_for_dbfield(db_field, **kwargs)
        if db_field.name == "configuration":
            field.widget.attrs["rows"] = 10
        return field

    def get_urls(self):
        from django.urls import path

        urls = super().get_urls()
        custom_urls = [
            path(
                "<path:object_id>/copy/",
                self.admin_site.admin_view(self.copy_stream),
                name="stream-copy",
            ),
        ]
        return custom_urls + urls

    def copy_stream(self, request, object_id):
        from django.contrib import messages
        from django.shortcuts import get_object_or_404, redirect

        stream = get_object_or_404(Stream, id=object_id)
        new_stream = Stream.objects.create(
            name=f"Copy of {stream.name}",
            stream_type=stream.stream_type,
            source=stream.source,
            frequency=stream.frequency,
            configuration=stream.configuration,
            status="inactive",  # Set as inactive by default
        )

        messages.success(request, f'Stream "{stream.name}" was successfully copied.')
        return redirect("admin:streams_stream_change", new_stream.id)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["show_copy_button"] = True
        return super().change_view(request, object_id, form_url, extra_context)

    def response_change(self, request, obj):
        if "_copy_stream" in request.POST:
            return self.copy_stream(request, obj.id)
        return super().response_change(request, obj)


@admin.register(LuigiTaskLog)
class LuigiTaskLogAdmin(admin.ModelAdmin):
    list_display = ["stream", "task_id", "status", "started_at", "completed_at"]
    list_filter = ["status", "started_at", "completed_at"]
    search_fields = ["stream__name", "task_id", "error_message"]
    readonly_fields = ["started_at", "completed_at"]


@admin.register(TelegramPublishLog)
class TelegramPublishLogAdmin(admin.ModelAdmin):
    list_display = ["news", "media", "published_at"]
    list_filter = ["media", "published_at"]
    search_fields = ["news__title", "media__name"]
    readonly_fields = ["published_at"]

    def has_add_permission(self, request):
        return False  # Prevent manual creation of publish logs
