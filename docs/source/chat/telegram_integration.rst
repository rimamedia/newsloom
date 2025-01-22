Telegram Integration
===================

The Telegram integration allows you to interact with Claude through a Telegram bot in group chats.

Setup
-----

1. Create a Telegram Bot
~~~~~~~~~~~~~~~~~~~~~~~

1. Open Telegram and search for ``@BotFather``
2. Start a chat with BotFather and use the ``/newbot`` command
3. Follow the prompts to:
   - Set a name for your bot
   - Set a username for your bot (must end in 'bot')
4. BotFather will provide you with a token. Save this token as you'll need it for configuration.

2. Configure Environment Variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add the following to your ``.env`` file:

.. code-block:: bash

    TELEGRAM_BOT_TOKEN=your_bot_token_here

3. Add Bot to Group
~~~~~~~~~~~~~~~~~~

1. Create a new Telegram group or use an existing one
2. Add your bot to the group by:
   - Click group name to open group info
   - Click "Add members"
   - Search for your bot's username and add it
3. (Optional) Make the bot an admin if you want it to see all messages

Usage
-----

There are two ways to interact with the bot in a group:

1. Mention the bot
~~~~~~~~~~~~~~~~~

Mention the bot using its username to start a new conversation:

.. code-block:: text

    @your_bot_name Hello, can you help me with something?

2. Reply to bot's messages
~~~~~~~~~~~~~~~~~~~~~~~~~

Reply directly to any of the bot's previous messages to continue the conversation in that thread.

Features
--------

- Thread-based conversations
- Persistent chat history
- Tool execution support
- Error handling and logging
- User management (automatic mapping between Telegram and Django users)

Management Command
----------------

The Telegram bot runs as a Django management command:

.. code-block:: bash

    python manage.py run_telegram_listener

In production, this command is managed by supervisord and starts automatically with the application.

Troubleshooting
--------------

1. Bot not responding to messages:
   - Ensure the bot is added to the group
   - Check if the bot token is correctly set in environment variables
   - Verify the bot has necessary permissions in the group
   - Check application logs for errors

2. Database errors:
   - Ensure migrations are applied: ``python manage.py migrate``
   - Check database connectivity
   - Verify Django user permissions

3. Common error messages:
   - "Bot not found": Check if bot token is valid
   - "Not enough rights": Bot needs admin rights in group
   - "Database error": Check Django database configuration
