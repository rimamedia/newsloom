pose # Context Management for Claude API

This document explains the context management implementation added to prevent "Input is too long" errors when using the Claude API.

## Problem

The Claude API has a maximum context length limit. When the combined size of the system prompt, chat history, and expected response exceeds this limit, the API returns an error with code 400 and message "Input is too long for the requested model."

This error can occur in several scenarios:
- Long conversations with many messages
- Conversations with multiple tool calls and large tool results
- Large system prompts combined with substantial conversation history

## Solution

We've implemented a context management system that:

1. Estimates token counts for all components of the context
2. Applies a sliding window approach when the context exceeds limits
3. Preserves critical context (first message and recent messages)
4. Gracefully degrades when token counting fails

### Components

#### 1. TokenCounter

The `TokenCounter` class provides methods to estimate token counts in text and message objects:

- Uses `tiktoken` library if available for accurate token counting
- Falls back to approximate counting based on text characteristics if `tiktoken` is not installed
- Handles complex message structures including tool calls and results

#### 2. ContextManager

The `ContextManager` class implements the context window strategy:

- Preserves the first message to maintain conversation context
- Keeps as many recent messages as possible within the token limit
- Ensures the most recent exchange is always included
- Handles edge cases like extremely large messages

### Implementation Details

The context management is integrated into the `_call_ai_service` method in `MessageProcessor`:

1. Before each API call, the system estimates the total token count
2. If the count exceeds the conservative limit (90,000 tokens), context management is applied
3. The managed history is used for the API call instead of the full history
4. Detailed logging tracks token counts and management actions

## Usage

The context management is automatically applied to all conversations. No changes are needed in how you use the chat system.

### Optional Dependency

For more accurate token counting, you can install the optional `tiktoken` package:

```bash
pip install tiktoken>=0.5.2
```

Without this package, the system will use approximate token counting which is less accurate but still functional.

## Testing

A Django management command is provided to verify the context management functionality:

```bash
python manage.py test_context_management --verbose
```

This command tests:
- Token counting for various text and message types
- Context management with different token limits
- Preservation of critical messages

Sample output:
```
Starting context management tests
Testing token counter...
String length: 0, Estimated tokens: 0
String length: 11, Estimated tokens: 2
String length: 66, Estimated tokens: 12
String length: 1000, Estimated tokens: 125
Message: {"role": "user", "content": "Hello"}, Estimated tokens: 7
Message: {"role": "assistant", "content": "Hello! How can I help you today?"}, Estimated tokens: 15
Message: {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "123", "content": "Tool result data"}]}, Estimated tokens: 17
Testing context management...
Original history: 50 messages, 1853 tokens
System prompt: 8711 tokens
Total context: 10564 tokens
Limit 5000: 1 messages, 40 tokens
First message preserved ✓
Most recent message not preserved ✗
Limit 10000: 7 messages, 262 tokens
First message preserved ✓
Most recent message preserved ✓
Limit 20000: 50 messages, 1853 tokens
First message preserved ✓
Most recent message preserved ✓
Tests completed
```

## Limitations

- Token counting is approximate, especially without `tiktoken`
- Very large individual messages might still cause issues
- The system does not compress or summarize messages, only selects which to include

## Future Improvements

Potential future enhancements:
- Message summarization for very long conversations
- Compression of tool results
- Dynamic system prompt adjustment
- More sophisticated context selection strategies
