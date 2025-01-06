import json
import logging

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
    async def connect(self):
        # Accept the WebSocket connection
        await self.accept()

        # Initialize Anthropic Bedrock client
        self.client = AnthropicBedrock()

        # Create a new chat for this connection
        self.chat = await self.create_chat()

        # Initialize chat history
        self.chat_history = []

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message = text_data_json["message"]

            # Add user message to history
            self.chat_history.append({"role": "user", "content": message})

            # Get response from Claude
            response = await self.get_claude_response()

            # Save the message and response to the database
            await self.save_message(message, response)

            # Send message and response back to WebSocket
            await self.send(
                text_data=json.dumps({"message": message, "response": response})
            )
        except Exception as e:
            await self.send(text_data=json.dumps({"error": str(e)}))

    async def get_claude_response(self):
        try:
            logger.info(
                f"Current chat history: {json.dumps(self.chat_history, indent=2)}"
            )

            while True:
                response = await sync_to_async(self.client.messages.create)(
                    model="anthropic.claude-3-5-sonnet-20241022-v2:0",
                    max_tokens=8192,
                    temperature=0,
                    system=SYSTEM_PROMPT,
                    tools=TOOLS,
                    messages=self.chat_history,
                )

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

                            logger.info(f"Executing tool: {tool_name}")
                            logger.info(f"Tool input: {tool_input}")
                            logger.info(f"Tool ID: {tool_id}")

                            # Execute the tool asynchronously
                            try:
                                tool_func = getattr(tool_functions, tool_name)
                                tool_result = await sync_to_async(tool_func)(
                                    **tool_input
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

        except Exception as e:
            logger.error(f"Error in get_claude_response: {str(e)}", exc_info=True)
            return f"Error getting response: {str(e)}"

    @database_sync_to_async
    def create_chat(self):
        return Chat.objects.create(user=self.scope["user"])

    @database_sync_to_async
    def save_message(self, message, response):
        ChatMessage.objects.create(
            chat=self.chat, user=self.scope["user"], message=message, response=response
        )
