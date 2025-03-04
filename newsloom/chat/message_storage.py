"""
Message storage functionality for chat.

This module provides database operations for chat messages and history,
encapsulating all database interactions related to chat data.
"""

import logging
from typing import Any, Dict, List, Optional

from channels.db import database_sync_to_async

from .models import Chat, ChatMessage, ChatMessageDetail

logger = logging.getLogger(__name__)


class MessageStorage:
    """
    Handles database operations for chat messages and history.

    This class encapsulates all database interactions related to chat messages,
    providing a clean interface for saving, loading, and managing chat data.
    """

    @staticmethod
    @database_sync_to_async
    def create_chat(user) -> Chat:
        """
        Create a new chat for the given user.

        Parameters:
            user: The user to create the chat for

        Returns:
            Chat: The newly created chat object
        """
        return Chat.objects.create(user=user)

    @staticmethod
    @database_sync_to_async
    def get_chat(chat_id, user) -> Optional[Chat]:
        """
        Get a chat by ID if it belongs to the user.

        Parameters:
            chat_id: The ID of the chat to retrieve
            user: The user who should own the chat

        Returns:
            Chat or None: The chat object if found, None otherwise
        """
        try:
            return Chat.objects.get(id=chat_id, user=user)
        except Chat.DoesNotExist:
            return None

    @staticmethod
    @database_sync_to_async
    def load_chat_history(chat) -> List[Dict[str, Any]]:
        """
        Load chat history from the database.

        Parameters:
            chat: The chat to load history for

        Returns:
            list: The chat history as a list of message dictionaries
        """
        chat_history = []
        messages = ChatMessage.objects.filter(chat=chat).order_by("timestamp")
        for msg in messages:
            chat_history.append({"role": "user", "content": msg.message})
            if msg.response:
                chat_history.append({"role": "assistant", "content": msg.response})
        return chat_history

    @staticmethod
    @database_sync_to_async
    def rename_chat(chat_id, user, new_title) -> bool:
        """
        Rename a chat if it belongs to the user.

        Parameters:
            chat_id: The ID of the chat to rename
            user: The user who should own the chat
            new_title: The new title for the chat

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            chat = Chat.objects.get(id=chat_id, user=user)
            chat.title = new_title
            chat.save()
            return True
        except Chat.DoesNotExist:
            return False

    @staticmethod
    @database_sync_to_async
    def get_last_message(chat) -> Optional[ChatMessage]:
        """
        Get the most recent message for a chat.

        Parameters:
            chat: The chat to get the last message for

        Returns:
            ChatMessage or None: The most recent message if any
        """
        try:
            return ChatMessage.objects.filter(chat=chat).latest("timestamp")
        except ChatMessage.DoesNotExist:
            return None

    @staticmethod
    @database_sync_to_async
    def save_message(chat, user, message, response) -> ChatMessage:
        """
        Save a message and its response to the database.

        Parameters:
            chat: The chat the message belongs to
            user: The user who sent the message
            message: The message text
            response: The AI response text

        Returns:
            ChatMessage: The created message object
        """
        return ChatMessage.objects.create(
            chat=chat, user=user, message=message, response=response
        )

    @staticmethod
    @database_sync_to_async
    def save_message_detail(
        chat_message,
        chat,
        sequence_number,
        role,
        content_type,
        content,
        tool_name=None,
        tool_id=None,
    ) -> ChatMessageDetail:
        """
        Save a detailed message entry to the database.

        Parameters:
            chat_message: The parent message
            chat: The chat the message belongs to
            sequence_number: The order of this detail in the conversation
            role: 'user' or 'assistant'
            content_type: The type of content (text, tool_call, tool_result)
            content: The content data
            tool_name: Optional tool name for tool calls
            tool_id: Optional tool ID for tool calls/results

        Returns:
            ChatMessageDetail: The created detail object
        """
        return ChatMessageDetail.objects.create(
            chat_message=chat_message,
            chat=chat,
            sequence_number=sequence_number,
            role=role,
            content_type=content_type,
            content=content,
            tool_name=tool_name,
            tool_id=tool_id,
        )

    @classmethod
    async def save_message_details(cls, chat_message, chat, chat_history) -> None:
        """
        Save detailed message flow to database.

        Parameters:
            chat_message: The parent message
            chat: The chat the message belongs to
            chat_history: The full conversation history
        """
        sequence = 0

        # Save user's initial message
        await cls.save_message_detail(
            chat_message=chat_message,
            chat=chat,
            sequence_number=sequence,
            role="user",
            content_type="text",
            content={"text": chat_history[0]["content"]},
        )
        sequence += 1

        # Save all intermediate messages from chat_history
        for msg in chat_history[
            1:
        ]:  # Skip first message as it's the user's initial message
            if msg["role"] == "assistant":
                if isinstance(msg["content"], list):
                    # Handle tool calls
                    for content in msg["content"]:
                        if content["type"] == "tool_use":
                            await cls.save_message_detail(
                                chat_message=chat_message,
                                chat=chat,
                                sequence_number=sequence,
                                role="assistant",
                                content_type="tool_call",
                                content=content,
                                tool_name=content["name"],
                                tool_id=content["id"],
                            )
                            sequence += 1
                else:
                    # Handle text response
                    await cls.save_message_detail(
                        chat_message=chat_message,
                        chat=chat,
                        sequence_number=sequence,
                        role="assistant",
                        content_type="text",
                        content={"text": msg["content"]},
                    )
                    sequence += 1
            elif msg["role"] == "user" and isinstance(msg["content"], list):
                # Handle tool results
                for content in msg["content"]:
                    if content["type"] == "tool_result":
                        await cls.save_message_detail(
                            chat_message=chat_message,
                            chat=chat,
                            sequence_number=sequence,
                            role="user",
                            content_type="tool_result",
                            content=content,
                            tool_id=content["tool_use_id"],
                        )
                        sequence += 1
