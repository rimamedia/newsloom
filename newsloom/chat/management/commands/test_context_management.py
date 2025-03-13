"""
Management command to test context management functionality.

This command tests the token counting and context management functionality
to ensure it correctly handles large conversations.
"""

import json
import logging
from typing import Dict, List, Any

from django.core.management.base import BaseCommand

from chat.message_processor import TokenCounter, ContextManager
from chat.system_prompt import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def generate_test_messages(count: int, message_size: int = 100) -> List[Dict[str, Any]]:
    """
    Generate test messages for context management testing.

    Parameters:
        count: Number of messages to generate
        message_size: Approximate size of each message in characters

    Returns:
        List of message dictionaries
    """
    messages = []

    # First message is special - we want to make sure it's preserved
    messages.append(
        {
            "role": "user",
            "content": f"This is the first message that should always be preserved in context management. It contains important context for the conversation. {'X' * (message_size - 120)}",  # noqa: E501
        }
    )

    # Generate alternating user/assistant messages
    for i in range(1, count):
        role = "user" if i % 2 == 0 else "assistant"
        messages.append({"role": role, "content": f"Message {i}: {'X' * message_size}"})

    return messages


class Command(BaseCommand):
    """Django management command to test context management functionality."""

    help = "Test context management functionality for chat"

    def add_arguments(self, parser):
        """Add command line arguments."""
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Increase output verbosity",
        )

    def handle(self, *args, **options):
        """Execute the command."""
        # Configure verbosity
        verbosity = 2 if options["verbose"] else 1

        self.stdout.write(self.style.SUCCESS("Starting context management tests"))

        # Test token counter
        self.test_token_counter(verbosity)

        # Test context management
        self.test_context_management(verbosity)

        self.stdout.write(self.style.SUCCESS("Tests completed"))

    def test_token_counter(self, verbosity):
        """Test the token counting functionality."""
        self.stdout.write("Testing token counter...")

        # Test simple strings
        test_strings = [
            "",
            "Hello world",
            "This is a longer message with multiple words and some punctuation!",
            "X" * 1000,  # 1000 character string
        ]

        for s in test_strings:
            tokens = TokenCounter.count_tokens(s)
            if verbosity > 1:
                self.stdout.write(
                    f"String length: {len(s)}, Estimated tokens: {tokens}"
                )

        # Test message objects
        test_messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hello! How can I help you today?"},
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "123",
                        "content": "Tool result data",
                    }
                ],
            },
        ]

        for msg in test_messages:
            tokens = TokenCounter.count_message_tokens(msg)
            if verbosity > 1:
                self.stdout.write(
                    f"Message: {json.dumps(msg)}, Estimated tokens: {tokens}"
                )

    def test_context_management(self, verbosity):
        """Test the context management functionality."""
        self.stdout.write("Testing context management...")

        # Generate a large conversation history
        history = generate_test_messages(50, 200)

        # Count tokens in the original history
        total_tokens = sum(TokenCounter.count_message_tokens(msg) for msg in history)
        system_tokens = TokenCounter.count_tokens(SYSTEM_PROMPT)

        self.stdout.write(
            f"Original history: {len(history)} messages, {total_tokens} tokens"
        )
        self.stdout.write(f"System prompt: {system_tokens} tokens")
        self.stdout.write(f"Total context: {total_tokens + system_tokens} tokens")

        # Apply context management with different limits
        for limit in [5000, 10000, 20000]:
            managed_history = ContextManager.manage_context(
                history,
                SYSTEM_PROMPT,
                max_context_tokens=limit,
                max_response_tokens=1000,
            )

            managed_tokens = sum(
                TokenCounter.count_message_tokens(msg) for msg in managed_history
            )

            self.stdout.write(
                f"Limit {limit}: {len(managed_history)} messages, {managed_tokens} tokens"
            )

            # Verify first message is preserved
            if managed_history and managed_history[0] == history[0]:
                self.stdout.write(self.style.SUCCESS("First message preserved ✓"))
            else:
                self.stdout.write(self.style.WARNING("First message not preserved ✗"))

            # Verify most recent messages are preserved
            if managed_history and managed_history[-1] == history[-1]:
                self.stdout.write(self.style.SUCCESS("Most recent message preserved ✓"))
            else:
                self.stdout.write(
                    self.style.WARNING("Most recent message not preserved ✗")
                )
