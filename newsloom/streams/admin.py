import json

from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.utils.html import format_html

from .models import Stream, StreamLog, TelegramPublishLog
from .schemas import STREAM_CONFIG_SCHEMAS
from .tasks import TASK_CONFIG_EXAMPLES


class StreamAdminForm(forms.ModelForm):
    """Form class for Stream model in admin interface."""

    class Meta:
        """Metaclass defining model and fields for StreamAdminForm."""

        model = Stream
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        # Skip validation if it's a new stream
        if not self.instance.pk:
            return cleaned_data
        return cleaned_data


@admin.register(Stream)
class StreamAdmin(admin.ModelAdmin):
    """Admin interface configuration for Stream model."""

    list_display = (
        "name",
        "stream_type",
        "source",
        "media",
        "status",
        "last_run",
        "next_run",
    )
    list_filter = ("stream_type", "status", "frequency")
    search_fields = ("name", "source__name")
    readonly_fields = ("last_run", "next_run", "created_at", "updated_at", "version")

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
                "fields": (
                    "last_run",
                    "next_run",
                    "created_at",
                    "updated_at",
                    "version",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    form = StreamAdminForm

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
                    example = TASK_CONFIG_EXAMPLES.get(stream_type, {})

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

    def save_model(self, request, obj, form, change):
        """Override save_model to handle validation and locking."""
        try:
            if not change:  # Only for new streams
                # Get the schema
                config_schema = STREAM_CONFIG_SCHEMAS.get(obj.stream_type)
                if config_schema:
                    try:
                        # Validate configuration directly
                        if isinstance(obj.configuration, str):
                            config = json.loads(obj.configuration)
                        else:
                            config = obj.configuration

                        # Create schema instance without validation
                        schema = config_schema.construct()
                        # Validate the config
                        schema.validate(config)

                    except Exception as e:
                        raise ValidationError(
                            f"Configuration validation failed: {str(e)}"
                        )

            super().save_model(request, obj, form, change)

        except ValidationError as e:
            if "Stream was modified" in str(e):
                self.message_user(
                    request,
                    (
                        "The stream was modified by another user or process. "
                        "Please refresh and try again."
                    ),
                    level="ERROR",
                )
            elif "Stream is currently locked" in str(e):
                self.message_user(
                    request,
                    (
                        "The stream is currently running. "
                        "Please wait for it to complete and try again."
                    ),
                    level="ERROR",
                )
            else:
                self.message_user(request, str(e), level="ERROR")
            raise


@admin.register(StreamLog)
class StreamLogAdmin(admin.ModelAdmin):
    list_display = [
        "stream",
        "status",
        "started_at",
        "completed_at",
        "execution_time",
        "has_errors",
    ]
    list_filter = ["status", "started_at", "stream__stream_type"]
    search_fields = ["stream__name", "error_message"]
    readonly_fields = [
        "stream",
        "status",
        "started_at",
        "completed_at",
        "error_message",
        "result",
        "execution_time",
    ]

    def has_errors(self, obj):
        return bool(obj.error_message)

    has_errors.boolean = True
    has_errors.short_description = "Has Errors"

    def execution_time(self, obj):
        if obj.completed_at and obj.started_at:
            duration = obj.completed_at - obj.started_at
            return f"{duration.total_seconds():.2f}s"
        return "-"

    execution_time.short_description = "Duration"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(TelegramPublishLog)
class TelegramPublishLogAdmin(admin.ModelAdmin):
    list_display = ["news", "media", "published_at"]
    list_filter = ["media", "published_at"]
    search_fields = ["news__title", "media__name"]
    readonly_fields = ["published_at"]

    def has_add_permission(self, request):
        return False
