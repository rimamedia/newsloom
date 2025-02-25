"""
Constants for chat functionality.

This module defines constants used throughout the chat functionality,
including model configuration, API settings, and WebSocket close codes.
"""

# Model and API constants
MODEL_NAME = "anthropic.claude-3-5-sonnet-20241022-v2:0"
API_TIMEOUT = 60.0  # seconds
MAX_TOKENS = 8192
API_TEMPERATURE = 0

# WebSocket close codes
WS_CLOSE_NORMAL = 1000
WS_CLOSE_GENERAL_ERROR = 4000
WS_CLOSE_UNAUTHORIZED = 4001
WS_CLOSE_BEDROCK_INIT_FAILED = 4002
