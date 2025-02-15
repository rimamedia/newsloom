Slack Integration
===============

The Newsloom chat interface can be accessed through Slack, allowing you to interact with the system directly from your Slack workspace.

Setup
-----

1. Create a Slack App
~~~~~~~~~~~~~~~~~~~

First, you need to create a Slack app and configure it:

1. Go to https://api.slack.com/apps
2. Click "Create New App"
3. Choose "From scratch"
4. Name your app (e.g., "Newsloom") and select your workspace
5. Click "Create App"

2. Configure App Permissions
~~~~~~~~~~~~~~~~~~~~~~~~~

Configure the necessary OAuth scopes:

1. Go to "OAuth & Permissions" in your app settings
2. Under "Bot Token Scopes", add these scopes:
   - ``app_mentions:read`` - To receive mention events
   - ``chat:write`` - To send messages
   - ``users:read`` - To get user information
   - ``users:read.email`` - To get user email addresses

3. Enable Socket Mode
~~~~~~~~~~~~~~~~~~~

Socket Mode is required for receiving events:

1. Go to "Socket Mode" in your app settings
2. Enable Socket Mode
3. Create an app-level token with ``connections:write`` scope
4. Save the app-level token - you'll need it later

4. Enable Events
~~~~~~~~~~~~~~

Configure event subscriptions:

1. Go to "Event Subscriptions"
2. Enable events
3. Subscribe to bot events:
   - ``app_mention`` - For receiving @mentions
   - ``message.channels`` - For receiving channel messages

5. Install the App
~~~~~~~~~~~~~~~~

1. Go to "Install App" in your app settings
2. Click "Install to Workspace"
3. Authorize the app

6. Configure Environment Variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add these variables to your ``.env`` file:

.. code-block:: bash

    SLACK_BOT_TOKEN=xoxb-your-bot-token
    SLACK_APP_TOKEN=xapp-your-app-token

Usage
-----

Starting the Bot
~~~~~~~~~~~~~~

Run the Slack listener management command:

.. code-block:: bash

    python manage.py run_slack_listener

This will start the Socket Mode client and begin listening for Slack events.

Interacting with the Bot
~~~~~~~~~~~~~~~~~~~~~~

There are two ways to interact with the bot:

1. Direct Mentions
   - Mention the bot using @BotName in any channel it's invited to
   - The bot will create a new thread for the conversation
   - Example: "@Newsloom what's the latest news?"

2. Thread Replies
   - Once a thread is started, you can reply in the thread without mentioning the bot
   - The bot will maintain conversation context within the thread
   - All messages and responses in the thread are saved and used for context

How It Works
-----------

Architecture
~~~~~~~~~~~

The Slack integration uses these components:

1. Socket Mode Client
   - Connects to Slack's WebSocket API
   - Receives real-time events
   - Handles authentication and reconnection

2. Event Handlers
   - ``app_mention`` - Handles direct mentions of the bot
   - ``message`` - Handles thread replies in existing conversations

3. Database Integration
   - Each Slack thread becomes a Chat instance
   - Messages and responses are saved as ChatMessage instances
   - Thread history is maintained for context

Message Flow
~~~~~~~~~~

1. Initial Mention:
   - User mentions bot
   - New Chat is created with slack_channel_id and slack_thread_ts
   - Bot processes message and responds in thread

2. Thread Reply:
   - User replies in thread
   - Existing Chat is found using thread_ts
   - Previous messages provide context
   - Bot responds in same thread

Data Model
~~~~~~~~~

Chat Model Extensions:
   - ``slack_channel_id``: ID of the Slack channel
   - ``slack_thread_ts``: Timestamp of the thread's parent message
   - ``title``: Auto-generated chat title based on first message

ChatMessage Model Extensions:
   - ``slack_ts``: Timestamp of the individual message
   - ``chat``: Reference to the parent Chat instance
   - ``response``: Bot's response to the message

ChatMessageDetail Model:
   - ``chat_message``: Reference to the parent ChatMessage
   - ``chat``: Reference to the parent Chat (for efficient querying)
   - ``sequence_number``: Order of the message in conversation flow
   - ``role``: Message sender role (user/assistant)
   - ``content_type``: Type of content (text/tool_call/tool_result)
   - ``content``: Actual message content (JSON)
   - ``tool_name``: Name of the tool if content_type is tool_call
   - ``tool_id``: ID of the tool call for linking calls with results
   - ``timestamp``: When this detail was created

Message Flow Details:
   1. User Message Processing:
      - Creates ChatMessage record
      - Generates ChatMessageDetail records for:
        * Initial user message
        * Tool calls and results
        * Final assistant response

   2. Thread Context:
      - All ChatMessageDetails are ordered by sequence_number
      - Tool calls and results are linked by tool_id
      - Complete conversation flow is preserved

Security
-------

The integration includes several security features:

1. User Management
   - Slack users are mapped to Django users
   - Email addresses are used for user matching
   - New users are created as needed

2. Authentication
   - Bot token for API operations
   - App-level token for Socket Mode
   - Tokens are kept secure in environment variables

3. Access Control
   - Bot only responds in channels it's invited to
   - Thread history is isolated per conversation
   - User permissions are respected

Troubleshooting
-------------

Common Issues:

1. Bot Not Responding
   - Check if the run_slack_listener command is running
   - Verify bot and app tokens in .env
   - Ensure bot is invited to the channel

2. Missing Messages
   - Check database for Chat and ChatMessage entries
   - Verify thread_ts values match
   - Look for error messages in logs

3. Context Loss
   - Ensure thread_ts is being passed correctly
   - Check if Chat exists for the thread
   - Verify message history is loading

Monitoring
---------

The integration includes detailed logging:

1. Event Logging
   - Incoming events
   - Message processing
   - Response generation

2. Error Tracking
   - Connection issues
   - Message processing failures
   - Database errors

3. Performance Metrics
   - Message counts
   - Response times
   - Thread activity
