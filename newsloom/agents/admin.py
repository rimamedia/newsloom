from django.contrib import admin

from .models import Agent


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ("name", "provider", "is_active", "created_at", "updated_at")
    list_filter = ("provider", "is_active", "created_at")
    search_fields = ("name", "description")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("name", "description", "provider", "is_active")}),
        (
            "Prompts",
            {
                "fields": ("system_prompt", "user_prompt_template"),
                "description": "Configure the prompts that define the agent's behavior",
            },
        ),
        (
            "Metadata",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )
