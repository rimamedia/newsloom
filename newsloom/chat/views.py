from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def chat_room(request):
    return render(request, "chat/room.html")
