"""
Message processor for chat functionality.

This module handles the core logic of processing messages, including
sending requests to the AI service, handling tool calls, and managing
the conversation flow.
"""

import asyncio
import json
import logging
import re
import uuid
from typing import Any, Dict, List, Tuple

from anthropic import AnthropicBedrock
from asgiref.sync import sync_to_async

from .constants import MODEL_NAME, MAX_TOKENS, API_TEMPERATURE, API_TIMEOUT
from .message_storage import MessageStorage
from .models import Chat, ChatMessage, CallAIServiceLog
from .system_prompt import SYSTEM_PROMPT
from .tools import tool_functions
from .tools.tools_descriptions import TOOLS

logger = logging.getLogger(__name__)

# Try to import tiktoken for better token counting
try:
    import tiktoken

    TIKTOKEN_AVAILABLE = True
    logger.info("tiktoken is available for accurate token counting")
except ImportError:
    TIKTOKEN_AVAILABLE = False
    logger.warning("tiktoken not available, falling back to approximate token counting")


class TokenCounter:
    """
    Utility class for estimating token counts in messages.

    This class provides methods to estimate the number of tokens in text and
    message objects, using tiktoken if available or falling back to approximate
    counting methods.
    """

    @staticmethod
    def count_tokens(text: str) -> int:
        """
        Count tokens in a string using tiktoken if available, or approximate if not.

        Parameters:
            text: The text to count tokens for

        Returns:
            int: Estimated token count
        """
        if not text:
            return 0

        if TIKTOKEN_AVAILABLE:
            # Use cl100k_base encoding (similar to Claude's tokenization)
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        else:
            # Approximate token count based on whitespace and punctuation
            # This is a rough approximation that works reasonably well for English text
            text = text.strip()
            if not text:
                return 0

            # Split on whitespace and punctuation
            words = re.findall(r"\w+|[^\w\s]", text)
            # Estimate: most words are 1-2 tokens, punctuation is usually its own token
            return max(1, sum(max(1, len(word) // 4) for word in words))

    @staticmethod
    def count_message_tokens(message: Dict[str, Any]) -> int:
        """
        Count tokens in a message object.

        Parameters:
            message: The message to count tokens for

        Returns:
            int: Estimated token count
        """
        if not message:
            return 0

        total = 0

        # Count role tokens
        total += TokenCounter.count_tokens(message.get("role", ""))

        # Count content tokens
        content = message.get("content", "")
        if isinstance(content, str):
            total += TokenCounter.count_tokens(content)
        elif isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    # Count each field in the dictionary
                    for key, value in item.items():
                        total += TokenCounter.count_tokens(
                            str(key)
                        ) + TokenCounter.count_tokens(str(value))
                else:
                    total += TokenCounter.count_tokens(str(item))

        # Add overhead for message formatting
        total += 5

        return total


class ContextManager:
    """
    Manages context size for AI service calls.

    This class provides methods to ensure that the context size stays within
    the model's limits by applying various strategies to reduce the size of
    the chat history when needed.
    """

    @staticmethod
    def manage_context(
        chat_history: List[Dict[str, Any]],
        system_prompt: str,
        max_context_tokens: int = 90000,
        max_response_tokens: int = 8192,
    ) -> List[Dict[str, Any]]:
        """
        Manage context size using a fixed window strategy that preserves critical context.

        Parameters:
            chat_history: The full chat history
            system_prompt: The system prompt
            max_context_tokens: Maximum tokens for the entire context
            max_response_tokens: Maximum tokens reserved for the response

        Returns:
            List: Managed chat history
        """
        if not chat_history:
            return []

        # Calculate available tokens for chat history
        system_tokens = TokenCounter.count_tokens(system_prompt)
        available_tokens = max_context_tokens - system_tokens - max_response_tokens

        # Always keep the first user message for context
        first_message = chat_history[0] if chat_history else None
        first_message_tokens = (
            TokenCounter.count_message_tokens(first_message) if first_message else 0
        )

        # Always keep the most recent messages
        # Start with most recent and work backwards
        managed_history = []
        current_tokens = 0

        # Process messages from newest to oldest
        for message in reversed(chat_history):
            message_tokens = TokenCounter.count_message_tokens(message)

            # If this is the first message, skip it for now (we'll add it later)
            if message == first_message:
                continue

            # If adding this message would exceed our limit, stop
            if (
                current_tokens + message_tokens
                > available_tokens - first_message_tokens
            ):
                break

            # Otherwise, add the message
            managed_history.insert(0, message)
            current_tokens += message_tokens

        # Add the first message at the beginning if it's not already included
        if first_message and first_message not in managed_history:
            # If we can't fit the first message, we need to remove some recent messages
            while (
                current_tokens + first_message_tokens > available_tokens
                and managed_history
            ):
                # Remove second-to-last message to preserve the most recent exchange
                if len(managed_history) > 1:
                    removed_message = managed_history.pop(-2)
                else:
                    removed_message = managed_history.pop(0)
                current_tokens -= TokenCounter.count_message_tokens(removed_message)

            managed_history.insert(0, first_message)

        return managed_history


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
            message_uid = uuid.uuid4().hex

            # Counter to track the number of tool usage iterations
            tool_usage_count = 0

            while True:
                # Process the message with the AI service
                response = await MessageProcessor._call_ai_service(client, chat_history, chat.id, message, message_uid)

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
                        client, chat_history, chat.id, message, message_uid
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
                    chat=chat, user=user, message=message, response=final_response, message_uid=message_uid
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
        client: AnthropicBedrock, chat_history: List[Dict[str, Any]], chat_id: int, init_message: str, message_uid: str
    ):
        """
        Call the AI service with the current chat history, managing context size.

        Parameters:
            client: The Anthropic client
            chat_history: The current chat history

        Returns:
            response: The AI service response
        """
        # Set limits
        max_context_tokens = 90000  # Conservative limit for Claude's context window
        max_response_tokens = MAX_TOKENS

        # Manage context size
        managed_history = chat_history

        try:
            # Count tokens in current history
            total_tokens = sum(
                TokenCounter.count_message_tokens(msg) for msg in chat_history
            )
            system_tokens = TokenCounter.count_tokens(SYSTEM_PROMPT)

            logger.info(
                f"Estimated tokens - System: {system_tokens}, History: {total_tokens}, "
                f"Total: {system_tokens + total_tokens}"
            )

            # Apply context management if needed
            if total_tokens + system_tokens + max_response_tokens > max_context_tokens:
                logger.warning("Context size exceeds limit, applying management")
                managed_history = ContextManager.manage_context(
                    chat_history, SYSTEM_PROMPT, max_context_tokens, max_response_tokens
                )

                # Log the reduction
                managed_tokens = sum(
                    TokenCounter.count_message_tokens(msg) for msg in managed_history
                )
                logger.info(
                    f"Reduced history from {total_tokens} to {managed_tokens} tokens"
                )

                # Add a system message to inform about truncation
                if managed_history != chat_history:
                    logger.info("Added context truncation notice")
        except Exception as e:
            # If token counting fails, still try to proceed with original history
            logger.error(f"Error in context management: {str(e)}", exc_info=True)

        # Create a task for the API call that can be cancelled
        log = await create_ai_log(managed_history, chat_id, init_message, message_uid)
        api_task = asyncio.create_task(
            sync_to_async(client.messages.create)(
                model=MODEL_NAME,
                max_tokens=MAX_TOKENS,
                temperature=API_TEMPERATURE,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=managed_history,
            )
        )

        try:
            # Wait for the API call with timeout
            response = await asyncio.wait_for(api_task, timeout=API_TIMEOUT)

            logger.info(f"API Response: {json.dumps(response.model_dump(), indent=2)}")
            log.response = response.content
            await save_ai_log(log)
            return response
        except asyncio.TimeoutError as e:
            log.error = f'{e}'
            await save_ai_log(log)
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


@sync_to_async
def create_ai_log(managed_history, chat_id, init_message, message_uid) -> CallAIServiceLog:
    return CallAIServiceLog.objects.create(
        model=MODEL_NAME,
        max_tokens=MAX_TOKENS,
        temperature=API_TEMPERATURE,
        system=SYSTEM_PROMPT,
        tools=TOOLS,
        messages=managed_history,
        chat_id=chat_id,
        message=init_message,
        message_uid=message_uid,
    )

@sync_to_async
def save_ai_log(log:CallAIServiceLog) -> CallAIServiceLog:
    log.save()
    return log