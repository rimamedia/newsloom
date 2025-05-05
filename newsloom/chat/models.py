from django.contrib.auth.models import User
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models


class Chat(models.Model):
    """
    Represents a chat instance associated with a user.

    Attributes:
        user (ForeignKey): Reference to the user who owns the chat.
        created_at (DateTimeField): Timestamp when the chat was created.
        updated_at (DateTimeField): Timestamp when the chat was last updated.
        title (CharField): Title of the chat, can be blank.

    Meta:
        ordering (list): Orders the chat instances by the updated_at field in descending order.

    Methods:
        __str__(): Returns a string representation of the chat instance.
        save(*args, **kwargs): Custom save method to set the chat title based
        on the first message or a default value.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    title = models.CharField(max_length=200, blank=True)
    slack_channel_id = models.CharField(max_length=100, null=True, blank=True)
    slack_thread_ts = models.CharField(max_length=100, null=True, blank=True)
    telegram_chat_id = models.CharField(max_length=100, null=True, blank=True)
    telegram_message_id = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        """
        Meta class to define model options.

        Attributes:
            ordering (list): Specifies the default ordering for the model's objects,
                             in this case, by the 'updated_at' field in descending order.
        """

        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.user.username}'s chat - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    def save(self, *args, **kwargs):
        if not self.title:
            if self.pk:  # Only try to get messages if the instance exists in DB
                first_message = self.messages.first()
                if first_message:
                    self.title = first_message.message[:50]
                    return super().save(*args, **kwargs)
            # Default title for new chats
            created_at_str = (
                self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else ""
            )
            self.title = f"Chat {created_at_str}"
        super().save(*args, **kwargs)


class ChatMessage(models.Model):
    """
    Model representing a chat message.

    Attributes:
        chat (ForeignKey): Reference to the associated Chat object. No longer nullable.
        user (ForeignKey): Reference to the User who sent the message.
        message (TextField): The content of the chat message.
        response (TextField): The response to the chat message, can be null or blank.
        timestamp (DateTimeField): The timestamp when the message was created,
        automatically set on creation.

    Meta:
        ordering (list): Orders the chat messages by timestamp in ascending order.

    Methods:
        __str__(): Returns a string representation of the chat message,
        showing the username and the first 50 characters of the message.
    """

    chat = models.ForeignKey(
        Chat, related_name="messages", on_delete=models.CASCADE
    )  # No longer nullable
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    message_uid = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    response = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    slack_ts = models.CharField(max_length=100, null=True, blank=True)
    telegram_message_id = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        """
        Meta class to define model options.

        Attributes:
            ordering (list): Specifies the default ordering for the model's
            objects based on the 'timestamp' field.
        """

        ordering = ["timestamp"]

    def __str__(self):
        return f"{self.user.username}: {self.message[:50]}"


class ChatMessageDetail(models.Model):
    """
    Model for storing detailed message flow including tool calls and their outputs.

    Attributes:
        chat_message (ForeignKey): Reference to the parent ChatMessage
        sequence_number (IntegerField): Order of the message in the conversation flow
        role (CharField): Role of the message sender (user/assistant)
        content_type (CharField): Type of content (text/tool_call/tool_result)
        content (JSONField): The actual content of the message
        tool_name (CharField): Name of the tool if content_type is tool_call
        tool_id (CharField): ID of the tool call for linking calls with results
        timestamp (DateTimeField): When this detail was created
    """

    ROLE_CHOICES = [
        ("user", "User"),
        ("assistant", "Assistant"),
    ]

    CONTENT_TYPE_CHOICES = [
        ("text", "Text"),
        ("tool_call", "Tool Call"),
        ("tool_result", "Tool Result"),
    ]

    chat_message = models.ForeignKey(
        ChatMessage, related_name="details", on_delete=models.CASCADE
    )
    chat = models.ForeignKey(
        Chat,
        related_name="message_details",
        on_delete=models.CASCADE,
        null=True,  # Temporarily allow null for migration
    )
    sequence_number = models.IntegerField()
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES)
    content = models.JSONField(encoder=DjangoJSONEncoder)
    tool_name = models.CharField(max_length=100, null=True, blank=True)
    tool_id = models.CharField(max_length=100, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        """
        Meta class to define model options.

        Attributes:
            ordering (list): Specifies the default ordering for the model's objects
            based on the 'chat_message' and 'sequence_number' fields.
            unique_together (list): Ensures that the combination of 'chat_message' and
            'sequence_number' is unique.
            indexes (list): Specifies the indexes to be created for the model.
        """

        ordering = ["chat_message", "sequence_number"]
        unique_together = ["chat_message", "sequence_number"]
        indexes = [
            models.Index(fields=["chat", "timestamp"]),
            models.Index(fields=["chat_message", "sequence_number"]),
        ]

    def __str__(self):
        return f"{self.chat_message.user.username} - {self.content_type} ({self.sequence_number})"

    def save(self, *args, **kwargs):
        if not self.chat_id and self.chat_message_id:
            self.chat = self.chat_message.chat
        super().save(*args, **kwargs)


class CallAIServiceLog(models.Model):
    model = models.CharField(max_length=255)
    max_tokens = models.IntegerField()
    temperature = models.IntegerField()
    system = models.TextField()
    tools = models.JSONField(encoder=DjangoJSONEncoder)
    messages = models.JSONField(encoder=DjangoJSONEncoder)
    chat_id = models.IntegerField()
    message = models.TextField()
    message_uid = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    response = models.TextField(null=True, blank=True)
    error = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
