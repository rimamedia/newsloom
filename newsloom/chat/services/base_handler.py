import logging
import os
from typing import List, Optional, Dict, Any

from anthropic import AnthropicBedrock
from django.contrib.auth.models import User

from ..models import Chat, ChatMessage
from ..system_prompt import SYSTEM_PROMPT
from ..tools import tool_functions
from ..tools.tools_descriptions import TOOLS

logger = logging.getLogger(__name__)


class ChatConfig:
    """
    Centralized configuration management for chat functionality.

    Attributes:
        aws_access_key (str): AWS access key for Bedrock
        aws_secret_key (str): AWS secret key for Bedrock
        aws_region (str): AWS region for Bedrock
        model_name (str): Claude model name to use
    """

    def __init__(self):
        self.aws_access_key = os.environ.get("BEDROCK_AWS_ACCESS_KEY_ID")
        self.aws_secret_key = os.environ.get("BEDROCK_AWS_SECRET_ACCESS_KEY")
        self.aws_region = os.environ.get("BEDROCK_AWS_REGION", "us-west-2")
        self.model_name = "anthropic.claude-3-5-sonnet-20241022-v2:0"

        if not self.aws_access_key or not self.aws_secret_key:
            raise ValueError("Missing required AWS credentials")


class ChatMessageProcessor:
    """
    Handles core message processing logic including Claude API interaction and tool execution.

    Attributes:
        client (AnthropicBedrock): Initialized Bedrock client
        config (ChatConfig): Chat configuration
    """

    def __init__(self, config: ChatConfig):
        self.config = config
        self.client = self._initialize_bedrock_client()

    def _initialize_bedrock_client(self) -> AnthropicBedrock:
        """Create and return an initialized Anthropic Bedrock client instance."""
        return AnthropicBedrock(
            aws_access_key=self.config.aws_access_key,
            aws_secret_key=self.config.aws_secret_key,
            aws_region=self.config.aws_region,
        )

    async def process_message(self, chat_history: List[Dict[str, Any]]) -> str:
        """
        Process a message using the Claude API and handle any tool usage.

        Args:
            chat_history: List of message dictionaries in Claude format

        Returns:
            str: Final response from Claude
        """
        try:
            while True:
                response = self.client.messages.create(
                    model=self.config.model_name,
                    max_tokens=8192,
                    temperature=0,
                    system=SYSTEM_PROMPT,
                    tools=TOOLS,
                    messages=chat_history,
                )

                if response.stop_reason == "tool_use":
                    logger.info("Tool use detected in response")

                    chat_history.append(
                        {
                            "role": "assistant",
                            "content": [
                                content.model_dump() for content in response.content
                            ],
                        }
                    )

                    for content in response.content:
                        if content.type == "tool_use":
                            tool_name = content.name
                            tool_input = content.input
                            tool_id = content.id

                            logger.info(f"Executing tool: {tool_name}")
                            logger.info(f"Tool input: {tool_input}")

                            try:
                                tool_func = tool_functions.get(tool_name)
                                if tool_func is None:
                                    raise ValueError(f"Unknown tool: {tool_name}")

                                tool_result = tool_func(**tool_input)
                                logger.info(
                                    f"Tool execution successful. Result: {tool_result}"
                                )

                                chat_history.append(
                                    {
                                        "role": "user",
                                        "content": [
                                            {
                                                "type": "tool_result",
                                                "tool_use_id": tool_id,
                                                "content": str(tool_result),
                                            }
                                        ],
                                    }
                                )

                            except Exception as e:
                                logger.error(f"Tool execution failed: {str(e)}")
                                chat_history.append(
                                    {
                                        "role": "user",
                                        "content": [
                                            {
                                                "type": "tool_result",
                                                "tool_use_id": tool_id,
                                                "content": str(e),
                                                "is_error": True,
                                            }
                                        ],
                                    }
                                )

                    continue

                final_response = response.content[0].text
                chat_history.append({"role": "assistant", "content": final_response})
                return final_response

        except Exception as e:
            logger.error(f"Error in message processing: {str(e)}", exc_info=True)
            raise


class UserChatService:
    """Handles user and chat management across different platforms."""

    async def get_or_create_user(
        self, platform: str, user_data: Dict[str, Any]
    ) -> Optional[User]:
        """
        Get or create a Django user based on platform-specific user data.

        Args:
            platform: Platform identifier (e.g., 'slack', 'telegram')
            user_data: Platform-specific user data

        Returns:
            Optional[User]: Created or retrieved user, None if creation fails
        """
        try:
            username = f"{platform}_{user_data['id']}"
            email = user_data.get("email", f"{user_data['id']}@{platform}.user")
            name = user_data.get("name", str(user_data["id"]))

            try:
                return User.objects.get(username=username)
            except User.DoesNotExist:
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    first_name=name.split()[0] if " " in name else name,
                    last_name=name.split()[-1] if " " in name else "",
                )
                return user

        except Exception as e:
            logger.error(f"Error getting/creating user: {str(e)}")
            return None

    async def get_or_create_chat(
        self, platform: str, user: User, chat_data: Dict[str, Any]
    ) -> Optional[Chat]:
        """
        Get or create a chat based on platform-specific data.

        Args:
            platform: Platform identifier
            user: Django user
            chat_data: Platform-specific chat data

        Returns:
            Optional[Chat]: Created or retrieved chat, None if creation fails
        """
        try:
            platform_id_field = f"{platform}_chat_id"
            platform_message_field = f"{platform}_message_id"

            filter_kwargs = {
                platform_id_field: str(chat_data["chat_id"]),
                platform_message_field: str(chat_data["message_id"]),
            }

            chat = Chat.objects.filter(**filter_kwargs).first()

            if not chat:
                create_kwargs = {
                    "user": user,
                    platform_id_field: str(chat_data["chat_id"]),
                    platform_message_field: str(chat_data["message_id"]),
                }
                chat = Chat.objects.create(**create_kwargs)
                logger.info(f"Created new chat with ID: {chat.id}")
            else:
                logger.info(f"Found existing chat with ID: {chat.id}")

            return chat

        except Exception as e:
            logger.error(f"Error getting/creating chat: {str(e)}")
            raise


class BaseChatHandler:
    """
    Base class for platform-specific chat handlers.

    Attributes:
        config (ChatConfig): Chat configuration
        message_processor (ChatMessageProcessor): Message processing service
        user_service (UserChatService): User and chat management service
    """

    def __init__(self):
        self.config = ChatConfig()
        self.message_processor = ChatMessageProcessor(self.config)
        self.user_service = UserChatService()

    async def load_chat_history(self, chat: Chat) -> List[Dict[str, Any]]:
        """
        Load chat history for a given chat.

        Args:
            chat: Chat instance to load history for

        Returns:
            List[Dict[str, Any]]: Chat history in Claude format
        """
        chat_history = []
        messages = ChatMessage.objects.filter(chat=chat).order_by("timestamp")

        for msg in messages:
            chat_history.append({"role": "user", "content": msg.message})
            if msg.response:
                chat_history.append({"role": "assistant", "content": msg.response})

        return chat_history

    async def save_message(
        self,
        chat: Chat,
        user: User,
        message: str,
        response: str,
        platform_data: Dict[str, Any],
    ) -> ChatMessage:
        """
        Save a message and its response.

        Args:
            chat: Associated chat
            user: Message sender
            message: User's message
            response: Assistant's response
            platform_data: Platform-specific message data

        Returns:
            ChatMessage: Created message instance
        """
        platform_field = next(
            (k for k in platform_data.keys() if k.endswith("_message_id")), None
        )

        create_kwargs = {
            "chat": chat,
            "user": user,
            "message": message,
            "response": response,
        }

        if platform_field:
            create_kwargs[platform_field] = str(platform_data[platform_field])

        return ChatMessage.objects.create(**create_kwargs)
