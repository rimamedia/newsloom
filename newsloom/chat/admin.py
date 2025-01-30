from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import Chat, ChatMessage, ChatMessageDetail


class ChatMessageDetailInline(admin.TabularInline):
    model = ChatMessageDetail
    extra = 0
    readonly_fields = ("timestamp", "sequence_number")
    fields = ("role", "content_type", "content", "tool_name", "tool_id", "timestamp")
    can_delete = False
    max_num = 0  # Prevents adding new details through admin
    ordering = ("sequence_number",)


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ("timestamp",)
    fields = ("message", "response", "timestamp")
    can_delete = False
    max_num = 0  # Prevents adding new messages through admin


@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "user",
        "created_at",
        "updated_at",
        "message_count",
        "view_details",
    )
    list_filter = ("user", "created_at", "updated_at")
    search_fields = ("title", "user__username", "messages__message")
    readonly_fields = ("created_at", "updated_at")
    inlines = [ChatMessageInline]
    ordering = ("-updated_at",)

    def message_count(self, obj):
        return obj.messages.count()

    message_count.short_description = "Messages"

    def view_details(self, obj):
        return format_html(
            '<a class="button" href="{}">View Details</a>',
            reverse("chat:chat_details_admin", args=[obj.id]),
        )

    view_details.short_description = "Chat Details"


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("short_message", "chat", "user", "has_response", "timestamp")
    list_filter = ("chat", "user", "timestamp")
    search_fields = ("message", "response", "user__username")
    readonly_fields = ("timestamp",)
    ordering = ("-timestamp",)
    raw_id_fields = ("chat",)
    inlines = [ChatMessageDetailInline]

    def short_message(self, obj):
        return obj.message[:50] + "..." if len(obj.message) > 50 else obj.message

    short_message.short_description = "Message"

    def has_response(self, obj):
        return bool(obj.response)

    has_response.boolean = True
    has_response.short_description = "Has Response"


@admin.register(ChatMessageDetail)
class ChatMessageDetailAdmin(admin.ModelAdmin):
    list_display = (
        "chat",
        "chat_message",
        "sequence_number",
        "role",
        "content_type",
        "tool_name",
        "timestamp",
    )
    list_filter = ("chat", "role", "content_type", "timestamp")
    search_fields = (
        "chat__title",
        "chat_message__message",
        "tool_name",
        "tool_id",
        "content",
    )
    readonly_fields = ("timestamp",)
    ordering = ("chat_message", "sequence_number")
    raw_id_fields = ("chat_message",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("chat_message")
