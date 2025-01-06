from django.contrib import admin

from .models import Chat, ChatMessage


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ("timestamp",)
    fields = ("message", "response", "timestamp")
    can_delete = False
    max_num = 0  # Prevents adding new messages through admin


@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "created_at", "updated_at", "message_count")
    list_filter = ("user", "created_at", "updated_at")
    search_fields = ("title", "user__username", "messages__message")
    readonly_fields = ("created_at", "updated_at")
    inlines = [ChatMessageInline]
    ordering = ("-updated_at",)

    def message_count(self, obj):
        return obj.messages.count()

    message_count.short_description = "Messages"


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("short_message", "chat", "user", "has_response", "timestamp")
    list_filter = ("chat", "user", "timestamp")
    search_fields = ("message", "response", "user__username")
    readonly_fields = ("timestamp",)
    ordering = ("-timestamp",)
    raw_id_fields = ("chat",)

    def short_message(self, obj):
        return obj.message[:50] + "..." if len(obj.message) > 50 else obj.message

    short_message.short_description = "Message"

    def has_response(self, obj):
        return bool(obj.response)

    has_response.boolean = True
    has_response.short_description = "Has Response"
