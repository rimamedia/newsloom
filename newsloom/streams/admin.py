from django.contrib import admin
from django.utils.html import format_html
from .models import Stream
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
            'fields': ('name', 'stream_type', 'source', 'frequency', 'status')
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
            # Add help text with example configuration
            stream_type = obj.stream_type if obj else None
            if stream_type:
                schema = STREAM_CONFIG_SCHEMAS.get(stream_type)
                if schema:
                    # Create an example with default values
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
                        'telegram_channel': {
                            'channel_name': '@example',
                            'limit': 50,
                            'include_media': True
                        }
                    }.get(stream_type, {})
                    
                    form.base_fields['configuration'].help_text = (
                        f'Example configuration:<br/>'
                        f'<pre>{json.dumps(example, indent=2)}</pre>'
                    )
        return form

    def formfield_for_dbfield(self, db_field, **kwargs):
        field = super().formfield_for_dbfield(db_field, **kwargs)
        if db_field.name == 'configuration':
            field.widget.attrs['rows'] = 10
        return field
