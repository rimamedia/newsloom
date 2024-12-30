import json

from anthropic import AnthropicBedrock
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .models import Chat, ChatMessage


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Accept the WebSocket connection
        await self.accept()

        # Initialize Anthropic Bedrock client
        self.client = AnthropicBedrock()

        # Create a new chat for this connection
        self.chat = await self.create_chat()

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message = text_data_json["message"]

            # Get response from Claude
            response = self.get_claude_response(message)

            # Save the message and response to the database
            await self.save_message(message, response)

            # Send message and response back to WebSocket
            await self.send(
                text_data=json.dumps({"message": message, "response": response})
            )
        except Exception as e:
            await self.send(text_data=json.dumps({"error": str(e)}))

    def get_claude_response(self, message):
        try:
            response = self.client.messages.create(
                model="anthropic.claude-3-5-sonnet-20241022-v2:0",
                max_tokens=1000,
                messages=[{"role": "user", "content": message}],
            )
            return response.content[0].text
        except Exception as e:
            return f"Error getting response: {str(e)}"

    @database_sync_to_async
    def create_chat(self):
        return Chat.objects.create(user=self.scope["user"])

    @database_sync_to_async
    def save_message(self, message, response):
        ChatMessage.objects.create(
            chat=self.chat, user=self.scope["user"], message=message, response=response
        )
