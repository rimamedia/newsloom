WebSocket API
============

NewLoom provides real-time updates through WebSocket connections using Django Channels. This section documents the available WebSocket endpoints and their usage.

Authentication
------------

WebSocket connections require authentication. Authentication is handled through URL parameters:

- Token Authentication: ``?token=<your-token>``
- Session Authentication: Uses Django session cookie (for browser-based access)

Connection URLs
-------------

Chat WebSocket
~~~~~~~~~~~~

.. code-block:: text

    ws://localhost:8000/ws/chat/?token=<your-token>

Features:
    - Real-time chat messages
    - Message status updates
    - Typing indicators
    - Error notifications

Message Formats:

1. Send Message:

.. code-block:: json

    {
        "type": "message",
        "content": "Your message here",
        "chat_id": 123
    }

2. Receive Message:

.. code-block:: json

    {
        "type": "message",
        "message": {
            "id": 456,
            "content": "Message content",
            "user": "username",
            "timestamp": "2024-02-05T12:00:00Z",
            "chat_id": 123
        }
    }

3. Typing Indicator:

.. code-block:: json

    {
        "type": "typing",
        "chat_id": 123,
        "user": "username",
        "is_typing": true
    }

Stream Status WebSocket
~~~~~~~~~~~~~~~~~~~

.. code-block:: text

    ws://localhost:8000/ws/streams/?token=<your-token>

Features:
    - Real-time stream status updates
    - Execution statistics
    - Error notifications

Message Formats:

1. Stream Status Update:

.. code-block:: json

    {
        "type": "status_update",
        "stream_id": 123,
        "status": "running",
        "timestamp": "2024-02-05T12:00:00Z"
    }

2. Execution Statistics:

.. code-block:: json

    {
        "type": "execution_stats",
        "stream_id": 123,
        "stats": {
            "processed_count": 50,
            "failed_count": 2,
            "total_count": 52,
            "execution_time": "00:05:23"
        }
    }

3. Error Notification:

.. code-block:: json

    {
        "type": "error",
        "stream_id": 123,
        "error": {
            "message": "Error description",
            "code": "ERROR_CODE",
            "timestamp": "2024-02-05T12:00:00Z"
        }
    }

Error Handling
------------

1. Connection Errors:

.. code-block:: json

    {
        "type": "error",
        "code": "connection_error",
        "message": "Authentication failed"
    }

2. Message Format Errors:

.. code-block:: json

    {
        "type": "error",
        "code": "invalid_format",
        "message": "Invalid message format"
    }

3. Permission Errors:

.. code-block:: json

    {
        "type": "error",
        "code": "permission_denied",
        "message": "Not authorized for this chat"
    }

Connection Management
------------------

1. Heartbeat
~~~~~~~~~~

Send periodic heartbeat to keep connection alive:

.. code-block:: json

    {
        "type": "heartbeat"
    }

2. Disconnection
~~~~~~~~~~~~~

Clean disconnection message:

.. code-block:: json

    {
        "type": "disconnect"
    }

Best Practices
------------

1. Connection Management:
    - Implement exponential backoff for reconnection attempts
    - Handle connection errors gracefully
    - Send periodic heartbeats

2. Message Handling:
    - Validate message format before sending
    - Handle all message types appropriately
    - Implement error handling for failed messages

3. Performance:
    - Limit subscription to necessary channels
    - Implement message batching for bulk updates
    - Handle reconnection efficiently

Example Usage
-----------

JavaScript WebSocket Client:

.. code-block:: javascript

    const chatSocket = new WebSocket(
        'ws://'
        + window.location.host
        + '/ws/chat/?token='
        + yourAuthToken
    );

    chatSocket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        switch(data.type) {
            case 'message':
                handleNewMessage(data.message);
                break;
            case 'typing':
                handleTypingIndicator(data);
                break;
            case 'error':
                handleError(data);
                break;
        }
    };

    chatSocket.onclose = function(e) {
        console.error('Chat socket closed unexpectedly');
    };

    // Send a message
    chatSocket.send(JSON.stringify({
        'type': 'message',
        'content': 'Hello, World!',
        'chat_id': 123
    }));

Security Considerations
--------------------

1. Authentication:
    - Always use secure tokens
    - Implement token expiration
    - Validate user permissions

2. Data Validation:
    - Validate all incoming messages
    - Sanitize user input
    - Implement rate limiting

3. Connection Security:
    - Use WSS (WebSocket Secure) in production
    - Implement proper error handling
    - Monitor for suspicious activity
