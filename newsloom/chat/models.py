from django.contrib.auth.models import User
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
    response = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

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
