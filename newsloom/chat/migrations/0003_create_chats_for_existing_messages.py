from django.db import migrations, models
from django.db.models import Min

def create_chats_for_messages(apps, schema_editor):
    Chat = apps.get_model('chat', 'Chat')
    ChatMessage = apps.get_model('chat', 'ChatMessage')
    
    # Get all messages without a chat, grouped by user
    messages_by_user = {}
    for message in ChatMessage.objects.filter(chat__isnull=True):
        if message.user_id not in messages_by_user:
            messages_by_user[message.user_id] = []
        messages_by_user[message.user_id].append(message)
    
    # Create a chat for each user's messages
    for user_id, messages in messages_by_user.items():
        # Get the timestamp of the first message for the chat title
        first_message = min(messages, key=lambda m: m.timestamp)
        
        # Create a new chat
        chat = Chat.objects.create(
            user_id=user_id,
            title=f"Chat from {first_message.timestamp.strftime('%Y-%m-%d %H:%M')}"
        )
        
        # Link all messages to this chat
        for message in messages:
            message.chat = chat
            message.save()

def remove_chats(apps, schema_editor):
    Chat = apps.get_model('chat', 'Chat')
    Chat.objects.all().delete()

class Migration(migrations.Migration):
    dependencies = [
        ('chat', '0002_chat_chatmessage_chat'),
    ]

    operations = [
        migrations.RunPython(create_chats_for_messages, remove_chats),
        migrations.AlterField(
            model_name='chatmessage',
            name='chat',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='messages', to='chat.chat'),
        ),
    ]
