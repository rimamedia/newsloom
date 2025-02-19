import asyncio
import json
import logging
import traceback
from datetime import datetime

from channels.generic.websocket import AsyncWebsocketConsumer

from .services.base_handler import BaseChatHandler

logger = logging.getLogger(__name__)


class WebSocketChatHandler(BaseChatHandler):
    """WebSocket-specific implementation of the chat handler."""

    def __init__(self, scope):
        super().__init__()
        self.scope = scope
        self.chat = None
        self.chat_history = []


class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for chat functionality."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.HEARTBEAT_INTERVAL = 30  # Send heartbeat every 30 seconds
        self.CONNECTION_TIMEOUT = 300  # Close connection after 5 minutes of inactivity
        self.handler = None
        self.last_activity = None
        self.is_connected = False
        self.heartbeat_task = None
        self.timeout_task = None

    async def connect(self):
        """Handle WebSocket connection."""
        try:
            # Get user from scope
            if not self.scope.get("user") or not self.scope["user"].is_authenticated:
                logger.error("Unauthorized WebSocket connection attempt")
                await self.close(code=4001)
                return

            # Accept the WebSocket connection
            await self.accept()
            logger.info(
                f"WebSocket connection established for user {self.scope['user'].username}"
            )

            # Initialize handler
            self.handler = WebSocketChatHandler(self.scope)

            # Initialize state
            self.last_activity = datetime.now()
            self.is_connected = True

            # Start heartbeat and timeout monitoring
            self.heartbeat_task = asyncio.create_task(self.send_heartbeat())
            self.timeout_task = asyncio.create_task(self.monitor_timeout())

        except Exception as e:
            logger.error(f"Error in connect: {str(e)}")
            logger.error(traceback.format_exc())
            await self.close(code=4000)

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        try:
            logger.info(f"WebSocket disconnecting with code: {close_code}")

            # Clean up tasks
            self.is_connected = False
            if self.heartbeat_task:
                self.heartbeat_task.cancel()
                try:
                    await self.heartbeat_task
                except asyncio.CancelledError:
                    pass

            if self.timeout_task:
                self.timeout_task.cancel()
                try:
                    await self.timeout_task
                except asyncio.CancelledError:
                    pass

            # Clean up handler
            self.handler = None

            logger.info(
                f"Successfully cleaned up resources for user {self.scope['user'].username}"
            )

        except Exception as e:
            logger.error(f"Error in disconnect: {str(e)}")
            logger.error(traceback.format_exc())

    async def send_heartbeat(self):
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

    async def monitor_timeout(self):
        """Monitor for connection timeout."""
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

    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
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

    async def _handle_stop_processing(self):
        """Handle stop processing request."""
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

    async def _handle_chat_rename(self, data):
        """Handle chat rename request."""
        chat_id = data.get("chat_id")
        new_title = data.get("new_title")

        # Update chat title
        chat = await self.handler.user_service.get_chat(chat_id, self.scope["user"])
        if chat:
            chat.title = new_title
            await self.handler.user_service.save_chat(chat)

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

    async def _handle_chat_message(self, data):
        """Handle regular chat messages."""
        message = data.get("message")
        if not message:
            await self.send(text_data=json.dumps({"error": "Message is required"}))
            return

        chat_id = data.get("chat_id")

        try:
            # Get or create chat
            if chat_id:
                self.handler.chat = await self.handler.user_service.get_chat(
                    chat_id, self.scope["user"]
                )
            if not self.handler.chat:
                self.handler.chat = await self.handler.user_service.create_chat(
                    self.scope["user"]
                )

            # Load chat history
            self.handler.chat_history = await self.handler.load_chat_history(
                self.handler.chat
            )
            self.handler.chat_history.append({"role": "user", "content": message})

            # Initial status update
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "status",
                        "message": "Analyzing your request...",
                    }
                )
            )

            # Process message
            try:
                # Create a task for processing
                self.processing_task = asyncio.create_task(
                    self.handler.message_processor.process_message(
                        self.handler.chat_history
                    )
                )
                response = await self.processing_task

                if response:
                    # Save message and response
                    chat_message = await self.handler.save_message(
                        chat=self.handler.chat,
                        user=self.scope["user"],
                        message=message,
                        response=response,
                        platform_data={},
                    )

                    # Send final response
                    await self.send(
                        text_data=json.dumps(
                            {
                                "type": "chat_message",
                                "message": message,
                                "response": response,
                                "chat_id": self.handler.chat.id,
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
                else:
                    logger.error("No response received from Claude")
                    await self.send(
                        text_data=json.dumps({"error": "No response received"})
                    )

            except asyncio.CancelledError:
                logger.info("Message processing cancelled by user")
                raise
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")
                await self.send(text_data=json.dumps({"error": str(e)}))
                raise

        except Exception as e:
            logger.error(f"Error handling chat message: {str(e)}")
            logger.error(traceback.format_exc())
            await self.send(text_data=json.dumps({"error": str(e)}))
