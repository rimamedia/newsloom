from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, render

from .models import Chat, ChatMessageDetail


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


@user_passes_test(lambda u: u.is_staff)
def chat_details_admin(request, chat_id):
    """Admin view to display all ChatMessageDetail records for a specific chat."""
    chat = get_object_or_404(Chat, id=chat_id)
    chat_details = ChatMessageDetail.objects.filter(chat=chat).order_by(
        "sequence_number"
    )

    context = {
        "chat": chat,
        "chat_details": chat_details,
    }

    return render(request, "chat/chat_details.html", context)
