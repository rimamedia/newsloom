from django.core.exceptions import ValidationError
from django.db import models


class Agent(models.Model):
    """Agent model represents an LLM-powered agent that can process news sources.

    This model defines an agent that can process news sources and generate documents
    based on prompts.
    """

    PROVIDER_CHOICES = [
        ("openai", "OpenAI"),
        ("anthropic", "Anthropic"),
        ("google", "Google"),
        ("bedrock", "Bedrock"),
    ]

    name = models.CharField(max_length=255, help_text="Name of the agent")
    description = models.TextField(
        blank=True, help_text="Description of what this agent does"
    )
    provider = models.CharField(
        max_length=50, choices=PROVIDER_CHOICES, help_text="The LLM provider to use"
    )
    system_prompt = models.TextField(
        help_text="The system prompt that defines the agent's behavior"
    )
    user_prompt_template = models.TextField(
        help_text="Template for the user prompt. Use {news} for news content placeholder"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this agent is active and can be used by streams",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        """Validate that the prompt template contains required placeholders."""
        if "{news}" not in self.user_prompt_template:
            raise ValidationError(
                {
                    "user_prompt_template": "Prompt template must contain {news} placeholder"
                }
            )

    def __str__(self):
        return self.name

    class Meta:
        """Meta configuration for Agent model."""

        ordering = ["-created_at"]
        verbose_name = "Agent"
        verbose_name_plural = "Agents"
