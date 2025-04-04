"""
WebSocket consumer for chat functionality.

This module handles WebSocket connections for real-time chat, including
connection management, message processing, and client communication.
"""

import asyncio
import json
import logging
import traceback
from datetime import datetime
from typing import Any, Dict

from anthropic import AnthropicBedrock
from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings

from .constants import (
    MODEL_NAME,
    WS_CLOSE_GENERAL_ERROR,
    WS_CLOSE_UNAUTHORIZED,
    WS_CLOSE_BEDROCK_INIT_FAILED,
)
from .message_processor import MessageProcessor
from .message_storage import MessageStorage

logger = logging.getLogger(__name__)


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

        # Log credential status (without exposing actual values)
        logger.info(f"AWS Region: {settings.BEDROCK_AWS_REGION}")
        logger.info(f"AWS Access Key present: {bool(settings.BEDROCK_AWS_ACCESS_KEY_ID)}")
        logger.info(f"AWS Secret Key present: {bool( settings.BEDROCK_AWS_SECRET_ACCESS_KEY)}")

        if not settings.BEDROCK_AWS_ACCESS_KEY_ID or not  settings.BEDROCK_AWS_SECRET_ACCESS_KEY:
            error_msg = "Missing AWS credentials for Bedrock"
            logger.error(error_msg)
            await self.send(text_data=json.dumps({"error": error_msg}))
            await self.close(code=WS_CLOSE_BEDROCK_INIT_FAILED)
            return

        try:
            self.client = AnthropicBedrock(
                aws_access_key=settings.BEDROCK_AWS_ACCESS_KEY_ID,
                aws_secret_key=settings.BEDROCK_AWS_SECRET_ACCESS_KEY,
                aws_region=settings.BEDROCK_AWS_REGION,
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
