"""
Message processor for chat functionality.

This module handles the core logic of processing messages, including
sending requests to the AI service, handling tool calls, and managing
the conversation flow.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Tuple

from anthropic import AnthropicBedrock
from asgiref.sync import sync_to_async

from .constants import MODEL_NAME, MAX_TOKENS, API_TEMPERATURE, API_TIMEOUT
from .message_storage import MessageStorage
from .models import Chat, ChatMessage
from .system_prompt import SYSTEM_PROMPT
from .tools import tool_functions
from .tools.tools_descriptions import TOOLS

logger = logging.getLogger(__name__)


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

            # Counter to track the number of tool usage iterations
            tool_usage_count = 0

            while True:
                # Process the message with the AI service
                response = await MessageProcessor._call_ai_service(client, chat_history)

                # Check if response contains tool calls
                if response.stop_reason == "tool_use":
                    logger.info("Tool use detected in response")

                    # Increment the tool usage counter
                    tool_usage_count += 1

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

                # If no tool calls, process the final response
                logger.info("No tool calls in response, processing final text")
                final_response = response.content[0].text

                # If there were multiple tool usages, generate a summary
                if tool_usage_count > 1:
                    logger.info(
                        f"Multiple tool usages detected ({tool_usage_count}), generating summary"  # noqa E501
                    )

                    # Add a message requesting a summary
                    summary_request = "Please provide a concise summary of all the actions and steps taken in this conversation."  # noqa E501
                    chat_history.append({"role": "user", "content": summary_request})

                    # Get summary from AI
                    summary_response = await MessageProcessor._call_ai_service(
                        client, chat_history
                    )
                    summary = summary_response.content[0].text

                    # Use the summary as the final response
                    final_response = summary

                    # Remove the summary request from history
                    chat_history.pop()

                # Add final response to history
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
