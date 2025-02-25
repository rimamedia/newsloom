"""
WebSocket consumer for chat functionality with Anthropic Claude AI.

This module provides WebSocket-based chat functionality using Django Channels and
Anthropic's Claude AI. It handles real-time communication between clients and the
AI service, manages chat history, and provides tool execution capabilities.

The module is structured with three main classes:
- MessageStorage: Handles database operations for chat messages
- MessageProcessor: Processes messages and interacts with the AI service
- ChatConsumer: Manages WebSocket connections and client communication
"""

import asyncio
import json
import logging
import os
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from anthropic import AnthropicBedrock
from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .models import Chat, ChatMessage, ChatMessageDetail
from .system_prompt import SYSTEM_PROMPT
from .tools import tool_functions
from .tools.tools_descriptions import TOOLS

logger = logging.getLogger(__name__)

# Constants
MODEL_NAME = "anthropic.claude-3-5-sonnet-20241022-v2:0"
API_TIMEOUT = 60.0  # seconds
MAX_TOKENS = 8192
API_TEMPERATURE = 0

# WebSocket close codes
WS_CLOSE_NORMAL = 1000
WS_CLOSE_GENERAL_ERROR = 4000
WS_CLOSE_UNAUTHORIZED = 4001
WS_CLOSE_BEDROCK_INIT_FAILED = 4002


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


class MessageProcessor:
    """
    Processes messages and interacts with the AI service.

    This class handles the core logic of processing messages, including
    sending requests to the AI service, handling tool calls, and managing
    the conversation flow.
    """

    @staticmethod
    async def process_message_core(
        message: str,
        chat: Chat,
        chat_history: List[Dict[str, Any]],
        client: AnthropicBedrock,
        user,
    ) -> Tuple[str, ChatMessage]:
        """
        Core message processing logic that can be used by both WebSocket and REST endpoints.

        Parameters:
            message: The user message to process
            chat: The chat object
            chat_history: The current chat history
            client: The Anthropic client
            user: The user who sent the message

        Returns:
            tuple: (final_response, chat_message)
        """
        try:
            # Add new user message to history
            chat_history.append({"role": "user", "content": message})

            while True:
                # Process the message with the AI service
                response = await MessageProcessor._call_ai_service(client, chat_history)

                # Check if response contains tool calls
                if response.stop_reason == "tool_use":
                    logger.info("Tool use detected in response")

                    # Add assistant's response to history
                    chat_history.append(
                        {
                            "role": "assistant",
                            "content": [
                                content.model_dump() for content in response.content
                            ],
                        }
                    )

                    # Process tool calls
                    await MessageProcessor._process_tool_calls(
                        response.content, chat_history
                    )

                    logger.info("Continuing conversation with tool results")
                    continue  # Continue the conversation with tool results

                # If no tool calls, add response to history and return
                logger.info("No tool calls in response, returning final text")
                final_response = response.content[0].text
                chat_history.append({"role": "assistant", "content": final_response})

                # Save the message and response
                chat_message = await MessageStorage.save_message(
                    chat=chat, user=user, message=message, response=final_response
                )

                # Save detailed message flow
                await MessageStorage.save_message_details(
                    chat_message, chat, chat_history
                )

                return final_response, chat_message

        except Exception as e:
            logger.error(f"Error in process_message_core: {str(e)}", exc_info=True)
            raise

    @staticmethod
    async def _call_ai_service(
        client: AnthropicBedrock, chat_history: List[Dict[str, Any]]
    ):
        """
        Call the AI service with the current chat history.

        Parameters:
            client: The Anthropic client
            chat_history: The current chat history

        Returns:
            response: The AI service response
        """
        # Create a task for the API call that can be cancelled
        api_task = asyncio.create_task(
            sync_to_async(client.messages.create)(
                model=MODEL_NAME,
                max_tokens=MAX_TOKENS,
                temperature=API_TEMPERATURE,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=chat_history,
            )
        )

        try:
            # Wait for the API call with timeout
            response = await asyncio.wait_for(api_task, timeout=API_TIMEOUT)
            logger.info(f"API Response: {json.dumps(response.model_dump(), indent=2)}")
            return response
        except asyncio.TimeoutError:
            api_task.cancel()
            try:
                await api_task
            except asyncio.CancelledError:
                pass
            raise
        except asyncio.CancelledError:
            api_task.cancel()
            try:
                await api_task
            except asyncio.CancelledError:
                pass
            raise

    @staticmethod
    async def _process_tool_calls(content_list, chat_history: List[Dict[str, Any]]):
        """
        Process tool calls from the AI response.

        Parameters:
            content_list: The content list from the AI response
            chat_history: The current chat history to append tool results to
        """
        for content in content_list:
            if content.type == "tool_use":
                # Extract tool details
                tool_name = content.name
                tool_input = content.input
                tool_id = content.id

                logger.info(f"Executing tool: {tool_name}")
                logger.info(f"Tool input: {tool_input}")
                logger.info(f"Tool ID: {tool_id}")

                # Execute the tool asynchronously
                try:
                    # Get tool function from dictionary
                    tool_func = tool_functions.get(tool_name)
                    if tool_func is None:
                        raise ValueError(f"Unknown tool: {tool_name}")

                    # Wrap tool execution in shield to ensure it can be cancelled
                    tool_result = await asyncio.shield(
                        sync_to_async(tool_func)(**tool_input)
                    )
                    logger.info(f"Tool execution successful. Result: {tool_result}")

                    # Add tool result to history with role: user
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

                except asyncio.CancelledError:
                    logger.info(f"Tool execution cancelled: {tool_name}")
                    raise
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


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for chat functionality.

    This class handles WebSocket connections for real-time chat, including
    connection management, message processing, and client communication.
    """

    # Class constants
    HEARTBEAT_INTERVAL = 30  # Send heartbeat every 30 seconds
    CONNECTION_TIMEOUT = 300  # Close connection after 5 minutes of inactivity

    async def connect(self) -> None:
        """
        Handle WebSocket connection establishment.

        Authenticates the user, initializes the Bedrock client, and sets up
        connection monitoring.
        """
        try:
            # Get user from scope
            if not self.scope.get("user") or not self.scope["user"].is_authenticated:
                logger.error("Unauthorized WebSocket connection attempt")
                await self.close(code=WS_CLOSE_UNAUTHORIZED)
                return

            # Accept the WebSocket connection
            await self.accept()
            logger.info(
                f"WebSocket connection established for user {self.scope['user'].username}"
            )

            # Initialize Anthropic Bedrock client
            await self._initialize_bedrock_client()

            # Initialize chat state
            self.chat_history = []
            self.chat = None
            self.last_activity = datetime.now()
            self.is_connected = True

            # Start heartbeat and timeout monitoring
            self.heartbeat_task = asyncio.create_task(self.send_heartbeat())
            self.timeout_task = asyncio.create_task(self.monitor_timeout())

        except Exception as e:
            logger.error(f"Error in connect: {str(e)}")
            logger.error(traceback.format_exc())
            await self.close(code=WS_CLOSE_GENERAL_ERROR)

    async def _initialize_bedrock_client(self) -> None:
        """Initialize the Anthropic Bedrock client with credentials from environment."""
        # Get credentials from environment
        aws_access_key = os.environ.get("BEDROCK_AWS_ACCESS_KEY_ID")
        aws_secret_key = os.environ.get("BEDROCK_AWS_SECRET_ACCESS_KEY")
        aws_region = os.environ.get("BEDROCK_AWS_REGION", "us-west-2")

        # Log credential status (without exposing actual values)
        logger.info(f"AWS Region: {aws_region}")
        logger.info(f"AWS Access Key present: {bool(aws_access_key)}")
        logger.info(f"AWS Secret Key present: {bool(aws_secret_key)}")

        if not aws_access_key or not aws_secret_key:
            error_msg = "Missing AWS credentials for Bedrock"
            logger.error(error_msg)
            await self.send(text_data=json.dumps({"error": error_msg}))
            await self.close(code=WS_CLOSE_BEDROCK_INIT_FAILED)
            return

        try:
            self.client = AnthropicBedrock(
                aws_access_key=aws_access_key,
                aws_secret_key=aws_secret_key,
                aws_region=aws_region,
            )

            # Test the connection with a minimal request
            await sync_to_async(self.client.messages.create)(
                model=MODEL_NAME,
                max_tokens=1,
                messages=[{"role": "user", "content": "test"}],
            )
            logger.info("Successfully tested Bedrock connection")

        except Exception as e:
            error_msg = f"Failed to initialize Bedrock client: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            await self.send(text_data=json.dumps({"error": error_msg}))
            await self.close(code=WS_CLOSE_BEDROCK_INIT_FAILED)

    async def disconnect(self, close_code: int) -> None:
        """
        Handle WebSocket disconnection.

        Close codes:
        - 1000: Normal closure
        - 4000: General error
        - 4001: Unauthorized
        - 4002: Bedrock initialization failed

        Parameters:
            close_code: The WebSocket close code
        """
        try:
            logger.info(f"WebSocket disconnecting with code: {close_code}")

            # Clean up tasks
            self.is_connected = False
            await self._cancel_task("heartbeat_task")
            await self._cancel_task("timeout_task")
            await self._cancel_task("processing_task")

            # Clean up resources
            self.client = None
            self.chat_history = None
            self.chat = None

            logger.info(
                f"Successfully cleaned up resources for user {self.scope['user'].username}"
            )

        except Exception as e:
            logger.error(f"Error in disconnect: {str(e)}")
            logger.error(traceback.format_exc())

    async def _cancel_task(self, task_name: str) -> None:
        """
        Cancel an asyncio task if it exists.

        Parameters:
            task_name: The name of the task attribute to cancel
        """
        if hasattr(self, task_name):
            task = getattr(self, task_name)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def send_heartbeat(self) -> None:
        """Send periodic heartbeat to keep connection alive."""
        try:
            while self.is_connected:
                await self.send(text_data=json.dumps({"type": "heartbeat"}))
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in heartbeat: {str(e)}")
            await self.close()

    async def monitor_timeout(self) -> None:
        """Monitor for connection timeout due to inactivity."""
        try:
            while self.is_connected:
                if (
                    datetime.now() - self.last_activity
                ).seconds > self.CONNECTION_TIMEOUT:
                    logger.warning("Connection timed out due to inactivity")
                    await self.close()
                    break
                await asyncio.sleep(10)  # Check every 10 seconds
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in timeout monitor: {str(e)}")
            await self.close()

    async def receive(self, text_data: str) -> None:
        """
        Handle incoming WebSocket messages.

        This method processes different types of messages:
        - heartbeat_response: Client response to heartbeat
        - stop_processing: Request to stop ongoing processing
        - rename_chat: Request to rename a chat
        - Regular chat messages: User messages to process

        Parameters:
            text_data: The raw text data received from the WebSocket
        """
        try:
            # Update last activity timestamp
            self.last_activity = datetime.now()

            text_data_json = json.loads(text_data)
            message_type = text_data_json.get("type")

            # Handle heartbeat response
            if message_type == "heartbeat_response":
                return

            # Handle stop processing request
            if message_type == "stop_processing":
                await self._handle_stop_processing()
                return

            # Handle chat rename
            if message_type == "rename_chat":
                await self._handle_chat_rename(text_data_json)
                return

            # Handle regular chat messages
            await self._handle_chat_message(text_data_json)

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({"error": "Invalid JSON format"}))
        except Exception as e:
            logger.error(f"Error in receive: {str(e)}")
            logger.error(traceback.format_exc())
            await self.send(text_data=json.dumps({"error": str(e)}))

    async def _handle_stop_processing(self) -> None:
        """Handle a request to stop ongoing message processing."""
        logger.info("Received stop processing request")
        if hasattr(self, "processing_task"):
            # Send status update that we're stopping
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "status",
                        "message": "Stopping conversation...",
                    }
                )
            )

            # Cancel the processing task and wait for it to complete
            logger.info("Cancelling processing task")
            self.processing_task.cancel()

            try:
                # Wait for task to be cancelled with timeout
                await asyncio.wait_for(self.processing_task, timeout=5.0)
                logger.info("Processing task cancelled successfully")
            except asyncio.TimeoutError:
                logger.error("Timeout waiting for task cancellation")
            except asyncio.CancelledError:
                logger.info("Processing task cancelled successfully")
            except Exception as e:
                logger.error(f"Error cancelling task: {str(e)}")
                logger.error(traceback.format_exc())
            finally:
                # Reset processing state
                self.processing_task = None

                # Send completion message
                await self.send(
                    text_data=json.dumps(
                        {
                            "type": "process_complete",
                            "message": "Processing stopped by user",
                        }
                    )
                )
                logger.info("Stop processing complete")
        else:
            logger.warning("Stop request received but no processing task found")

    async def _handle_chat_rename(self, data: Dict[str, Any]) -> None:
        """Handle a request to rename a chat.

        Parameters:
            data: The parsed message data containing chat_id and new_title
        """
        chat_id = data.get("chat_id")
        new_title = data.get("new_title")

        # Update chat title
        success = await MessageStorage.rename_chat(
            chat_id, self.scope["user"], new_title
        )
        if success:
            # Send confirmation back to WebSocket
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "chat_renamed",
                        "chat_id": chat_id,
                        "new_title": new_title,
                    }
                )
            )

    async def _handle_chat_message(self, data: Dict[str, Any]) -> None:
        """Handle a regular chat message from the user.

        Parameters:
            data: The parsed message data containing the message and optional chat_id
        """
        message = data.get("message")
        if not message:
            await self.send(text_data=json.dumps({"error": "Message is required"}))
            return

        chat_id = data.get("chat_id")

        # Get or create chat and load history
        if chat_id:
            self.chat = await MessageStorage.get_chat(chat_id, self.scope["user"])
            if self.chat:
                self.chat_history = await MessageStorage.load_chat_history(self.chat)
        if not self.chat:
            self.chat = await MessageStorage.create_chat(self.scope["user"])

        try:
            # Create a task for processing
            self.processing_task = asyncio.create_task(self.process_message(message))
            await self.processing_task

        except asyncio.CancelledError:
            logger.info("Message processing cancelled by user")
            # Don't send completion message here since it's already sent in stop handler
            return

        except asyncio.TimeoutError:
            logger.error("Timeout waiting for Claude response")
            await self.send(
                text_data=json.dumps({"error": "Request timed out. Please try again."})
            )

    async def process_message(self, message: str) -> None:
        """Process a message and handle all status updates.

        Parameters:
            message: The user message to process
        """
        try:
            # Initial status update
            await self.send(
                text_data=json.dumps(
                    {"type": "status", "message": "Analyzing your request..."}
                )
            )

            try:
                # Process message using MessageProcessor
                response, chat_message = await MessageProcessor.process_message_core(
                    message,
                    self.chat,
                    self.chat_history,
                    self.client,
                    self.scope["user"],
                )

                # Send final response
                await self.send(
                    text_data=json.dumps(
                        {
                            "type": "chat_message",
                            "message": message,
                            "response": response,
                            "chat_id": self.chat.id,
                            "timestamp": (
                                chat_message.timestamp.isoformat()
                                if chat_message
                                else None
                            ),
                        }
                    )
                )

                # Send completion status
                await self.send(text_data=json.dumps({"type": "process_complete"}))

            except asyncio.CancelledError:
                logger.info("Process message cancelled")
                raise
            except Exception as e:
                logger.error(f"Error in process_message: {str(e)}")
                await self.send(text_data=json.dumps({"error": str(e)}))
                raise

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Error in process_message: {str(e)}", exc_info=True)
            await self.send(text_data=json.dumps({"error": str(e)}))
