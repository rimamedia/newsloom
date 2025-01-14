import asyncio
import json
import logging
import os
import traceback
from datetime import datetime

from anthropic import AnthropicBedrock
from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from . import tool_functions
from .models import Chat, ChatMessage
from .system_prompt import SYSTEM_PROMPT
from .tools import TOOLS

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    HEARTBEAT_INTERVAL = 30  # Send heartbeat every 30 seconds
    CONNECTION_TIMEOUT = 300  # Close connection after 5 minutes of inactivity

    async def connect(self):
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

            # Initialize Anthropic Bedrock client with credentials from environment
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
                await self.close(code=4002)
                return

            try:
                self.client = AnthropicBedrock(
                    aws_access_key=aws_access_key,
                    aws_secret_key=aws_secret_key,
                    aws_region=aws_region,
                )

                # Test the connection with a minimal request
                await sync_to_async(self.client.messages.create)(
                    model="anthropic.claude-3-5-sonnet-20241022-v2:0",
                    max_tokens=1,
                    messages=[{"role": "user", "content": "test"}],
                )
                logger.info("Successfully tested Bedrock connection")

            except Exception as e:
                error_msg = f"Failed to initialize Bedrock client: {str(e)}"
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                await self.send(text_data=json.dumps({"error": error_msg}))
                await self.close(code=4002)
                return

            # Initialize chat history
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
            await self.close(code=4000)

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection.

        Close codes:
        - 4000: General error
        - 4001: Unauthorized
        - 4002: Bedrock initialization failed
        """
        try:
            logger.info(f"WebSocket disconnecting with code: {close_code}")

            # Clean up tasks
            self.is_connected = False
            if hasattr(self, "heartbeat_task"):
                self.heartbeat_task.cancel()
                try:
                    await self.heartbeat_task
                except asyncio.CancelledError:
                    pass

            if hasattr(self, "timeout_task"):
                self.timeout_task.cancel()
                try:
                    await self.timeout_task
                except asyncio.CancelledError:
                    pass

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
                return

            # Handle chat rename
            if message_type == "rename_chat":
                chat_id = text_data_json.get("chat_id")
                new_title = text_data_json.get("new_title")

                # Update chat title
                success = await self.rename_chat(chat_id, new_title)
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
                return

            # Handle regular chat messages
            message = text_data_json.get("message")
            if not message:
                await self.send(text_data=json.dumps({"error": "Message is required"}))
                return

            chat_id = text_data_json.get("chat_id")

            # Get or create chat and load history
            if chat_id:
                self.chat = await self.get_chat(chat_id)
                if self.chat:
                    await self.load_chat_history(self.chat)
            if not self.chat:
                self.chat = await self.create_chat()

            # Add new user message to history
            self.chat_history.append({"role": "user", "content": message})

            try:
                # Create a task for processing
                self.processing_task = asyncio.create_task(
                    self.process_message(message)
                )
                await self.processing_task

            except asyncio.CancelledError:
                logger.info("Message processing cancelled by user")
                # Don't send completion message here since it's already sent in stop handler
                return

            except asyncio.TimeoutError:
                logger.error("Timeout waiting for Claude response")
                await self.send(
                    text_data=json.dumps(
                        {"error": "Request timed out. Please try again."}
                    )
                )

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({"error": "Invalid JSON format"}))
        except Exception as e:
            logger.error(f"Error in receive: {str(e)}")
            logger.error(traceback.format_exc())
            await self.send(text_data=json.dumps({"error": str(e)}))

    async def process_message(self, message):
        """Process a message and handle all status updates."""
        try:
            # Initial status update
            await self.send(
                text_data=json.dumps(
                    {"type": "status", "message": "Analyzing your request..."}
                )
            )

            try:
                # Get response from Claude with periodic status updates
                response = await self.get_claude_response()

                # Only save and send response if not cancelled
                if response:
                    try:
                        # Save the message and response to the database
                        await self.save_message(message, response)

                        # Send final response
                        # Get the saved message with timestamp
                        chat_message = await self.get_last_message()
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
                        await self.send(
                            text_data=json.dumps({"type": "process_complete"})
                        )
                    except Exception as e:
                        logger.error(f"Error saving/sending response: {str(e)}")
                        raise

            except asyncio.CancelledError:
                logger.info("Process message cancelled")
                # Don't save partial responses or send completion message
                # The stop handler will send the appropriate messages
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

    async def get_claude_response(self):
        """Get response from Claude with status updates."""
        try:
            logger.info(
                f"Current chat history: {json.dumps(self.chat_history, indent=2)}"
            )

            while True:
                # Update status before API call
                await self.send(
                    text_data=json.dumps(
                        {"type": "status", "message": "Generating response..."}
                    )
                )

                # Create a task for the API call that can be cancelled
                api_task = asyncio.create_task(
                    sync_to_async(self.client.messages.create)(
                        model="anthropic.claude-3-5-sonnet-20241022-v2:0",
                        max_tokens=8192,
                        temperature=0,
                        system=SYSTEM_PROMPT,
                        tools=TOOLS,
                        messages=self.chat_history,
                    )
                )

                try:
                    # Wait for the API call with timeout
                    response = await asyncio.wait_for(api_task, timeout=60.0)
                except asyncio.TimeoutError:
                    # Cancel the API task if it times out
                    api_task.cancel()
                    try:
                        await api_task
                    except asyncio.CancelledError:
                        pass
                    raise
                except asyncio.CancelledError:
                    # Cancel the API task if the parent task is cancelled
                    api_task.cancel()
                    try:
                        await api_task
                    except asyncio.CancelledError:
                        pass
                    raise

                logger.info(
                    f"API Response: {json.dumps(response.model_dump(), indent=2)}"
                )

                # Check if response contains tool calls
                if response.stop_reason == "tool_use":
                    logger.info("Tool use detected in response")

                    # Add assistant's response to history
                    self.chat_history.append(
                        {
                            "role": "assistant",
                            "content": [
                                content.model_dump() for content in response.content
                            ],
                        }
                    )

                    for content in response.content:
                        if content.type == "tool_use":
                            # Extract tool details
                            tool_name = content.name
                            tool_input = content.input
                            tool_id = content.id

                            # Update status for tool execution
                            await self.send(
                                text_data=json.dumps(
                                    {
                                        "type": "status",
                                        "message": f"Executing {tool_name}...",
                                    }
                                )
                            )

                            logger.info(f"Executing tool: {tool_name}")
                            logger.info(f"Tool input: {tool_input}")
                            logger.info(f"Tool ID: {tool_id}")

                            # Execute the tool asynchronously
                            try:
                                tool_func = getattr(tool_functions, tool_name)
                                # Wrap tool execution in shield to ensure it can be cancelled
                                tool_result = await asyncio.shield(
                                    sync_to_async(tool_func)(**tool_input)
                                )
                                logger.info(
                                    f"Tool execution successful. Result: {tool_result}"
                                )

                                # Add tool result to history with role: user
                                self.chat_history.append(
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
                                # Add error result to history with role: user
                                self.chat_history.append(
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

                    logger.info("Continuing conversation with tool results")
                    continue  # Continue the conversation with tool results

                # If no tool calls, add response to history and return
                logger.info("No tool calls in response, returning final text")
                final_response = response.content[0].text
                self.chat_history.append(
                    {"role": "assistant", "content": final_response}
                )
                return final_response

        except asyncio.CancelledError:
            logger.info("Claude response generation cancelled")
            raise

        except Exception as e:
            logger.error(f"Error in get_claude_response: {str(e)}", exc_info=True)
            return f"Error getting response: {str(e)}"

    @database_sync_to_async
    def create_chat(self):
        return Chat.objects.create(user=self.scope["user"])

    @database_sync_to_async
    def get_chat(self, chat_id):
        try:
            return Chat.objects.get(id=chat_id, user=self.scope["user"])
        except Chat.DoesNotExist:
            return None

    @database_sync_to_async
    def load_chat_history(self, chat):
        messages = ChatMessage.objects.filter(chat=chat).order_by("timestamp")
        for msg in messages:
            self.chat_history.append({"role": "user", "content": msg.message})
            if msg.response:
                self.chat_history.append({"role": "assistant", "content": msg.response})

    @database_sync_to_async
    def save_message(self, message, response):
        ChatMessage.objects.create(
            chat=self.chat, user=self.scope["user"], message=message, response=response
        )

    @database_sync_to_async
    def rename_chat(self, chat_id, new_title):
        """Rename a chat if it belongs to the current user."""
        try:
            chat = Chat.objects.get(id=chat_id, user=self.scope["user"])
            chat.title = new_title
            chat.save()
            return True
        except Chat.DoesNotExist:
            return False

    @database_sync_to_async
    def get_last_message(self):
        """Get the most recent message for the current chat."""
        try:
            return ChatMessage.objects.filter(chat=self.chat).latest("timestamp")
        except ChatMessage.DoesNotExist:
            return None
