from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from .models import Chat


@login_required
def chat_room(request, chat_id=None):
    # Get user's chats ordered by most recent
    user_chats = Chat.objects.filter(user=request.user).order_by("-updated_at")

    # If chat_id is provided, get that specific chat
    current_chat = None
    if chat_id:
        current_chat = get_object_or_404(Chat, id=chat_id, user=request.user)
    # For base chat URL without ID, always start fresh chat session
    else:
        current_chat = None

    # Get messages for current chat if it exists
    messages = []
    if current_chat:
        messages = current_chat.messages.all()

    context = {
        "user_chats": user_chats,
        "current_chat": current_chat,
        "messages": messages,
    }

    return render(request, "chat/room.html", context)
