from django.contrib import admin
from django.utils.html import format_html
from .models import Stream, LuigiTaskLog, TelegramPublishLog
from .schemas import STREAM_CONFIG_SCHEMAS
import json

@admin.register(Stream)
class StreamAdmin(admin.ModelAdmin):
    list_display = ('name', 'stream_type', 'source', 'frequency', 'status', 'last_run', 'next_run')
    list_filter = ('stream_type', 'status', 'frequency')
    search_fields = ('name', 'source__name')
    readonly_fields = ('last_run', 'next_run', 'created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'fields': ('name', 'stream_type', 'source', 'media', 'frequency', 'status')
        }),
        ('Configuration', {
            'fields': ('configuration',),
            'classes': ('collapse',),
            'description': 'Stream-specific configuration in JSON format'
        }),
        ('Timing Information', {
            'fields': ('last_run', 'next_run', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.readonly_fields + ('stream_type',)
        return self.readonly_fields

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'configuration' in form.base_fields:
            # Get stream_type either from existing object or from request
            stream_type = None
            if obj:
                stream_type = obj.stream_type
            elif request.method == 'POST':
                stream_type = request.POST.get('stream_type')
            elif request.method == 'GET':
                stream_type = request.GET.get('stream_type')

            if stream_type:
                schema = STREAM_CONFIG_SCHEMAS.get(stream_type)

                if schema:
                    example = {
                        'sitemap_news': {
                            'sitemap_url': 'https://example.com/sitemap.xml',
                            'max_links': 100,
                            'follow_next': False
                        },
                        'sitemap_blog': {
                            'sitemap_url': 'https://example.com/sitemap.xml',
                            'max_links': 100,
                            'follow_next': False
                        },
                        'rss_feed': {
                            'feed_url': 'https://example.com/feed.xml',
                            'max_items': 50,
                            'include_summary': True
                        },
                        'web_article': {
                            'base_url': 'https://example.com',
                            'selectors': {
                                'title': 'h1',
                                'content': 'article'
                            }
                        },
                        'telegram_publish': {
                            'channel_id': '-100123456789',
                            'bot_token': '1234567890:ABCdefGHIjklMNOpqrsTUVwxyz',
                            'batch_size': 10,
                            'time_window_minutes': 10
                        }
                    }.get(stream_type, {})
                    
                    print(f"Example for {stream_type}: {example}")  # Debug print
                    
                    help_text = format_html(
                        'Example configuration for {}:<br><pre>{}</pre>',
                        stream_type,
                        json.dumps(example, indent=2)
                    )
                    
                    form.base_fields['configuration'].help_text = help_text

        return form

    def formfield_for_dbfield(self, db_field, **kwargs):
        field = super().formfield_for_dbfield(db_field, **kwargs)
        if db_field.name == 'configuration':
            field.widget.attrs['rows'] = 10
        return field

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                '<path:object_id>/copy/',
                self.admin_site.admin_view(self.copy_stream),
                name='stream-copy',
            ),
        ]
        return custom_urls + urls

    def copy_stream(self, request, object_id):
        from django.shortcuts import get_object_or_404, redirect
        from django.contrib import messages
        
        stream = get_object_or_404(Stream, id=object_id)
        new_stream = Stream.objects.create(
            name=f"Copy of {stream.name}",
            stream_type=stream.stream_type,
            source=stream.source,
            frequency=stream.frequency,
            configuration=stream.configuration,
            status='inactive'  # Set as inactive by default
        )
        
        messages.success(request, f'Stream "{stream.name}" was successfully copied.')
        return redirect('admin:streams_stream_change', new_stream.id)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_copy_button'] = True
        return super().change_view(request, object_id, form_url, extra_context)

    def response_change(self, request, obj):
        if "_copy_stream" in request.POST:
            return self.copy_stream(request, obj.id)
        return super().response_change(request, obj)

@admin.register(LuigiTaskLog)
class LuigiTaskLogAdmin(admin.ModelAdmin):
    list_display = ['stream', 'task_id', 'status', 'started_at', 'completed_at']
    list_filter = ['status', 'started_at', 'completed_at']
    search_fields = ['stream__name', 'task_id', 'error_message']
    readonly_fields = ['started_at', 'completed_at']

@admin.register(TelegramPublishLog)
class TelegramPublishLogAdmin(admin.ModelAdmin):
    list_display = ['news', 'media', 'published_at']
    list_filter = ['media', 'published_at']
    search_fields = ['news__title', 'media__name']
    readonly_fields = ['published_at']

    def has_add_permission(self, request):
        return False  # Prevent manual creation of publish logs
