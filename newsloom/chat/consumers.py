"""
WebSocket consumer for chat functionality with Anthropic Claude AI.

This module provides WebSocket-based chat functionality using Django Channels and
Anthropic's Claude AI. It handles real-time communication between clients and the
AI service, manages chat history, and provides tool execution capabilities.

Note: This file now re-exports classes from more specialized modules for backward
compatibility. For new code, it's recommended to import directly from the specific modules.
"""

# Re-export classes for backward compatibility
from .chat_consumer import ChatConsumer
from .constants import (
    MODEL_NAME,
    API_TIMEOUT,
    MAX_TOKENS,
    API_TEMPERATURE,
    WS_CLOSE_NORMAL,
    WS_CLOSE_GENERAL_ERROR,
    WS_CLOSE_UNAUTHORIZED,
    WS_CLOSE_BEDROCK_INIT_FAILED,
)
from .message_processor import MessageProcessor
from .message_storage import MessageStorage

__all__ = [
    "ChatConsumer",
    "MODEL_NAME",
    "API_TIMEOUT",
    "MAX_TOKENS",
    "API_TEMPERATURE",
    "WS_CLOSE_NORMAL",
    "WS_CLOSE_GENERAL_ERROR",
    "WS_CLOSE_UNAUTHORIZED",
    "WS_CLOSE_BEDROCK_INIT_FAILED",
    "MessageProcessor",
    "MessageStorage",
]
