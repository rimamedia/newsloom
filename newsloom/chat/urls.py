from django.urls import path

from . import views

app_name = "chat"

urlpatterns = [
    path("", views.chat_room, name="room"),
    path("<int:chat_id>/", views.chat_room, name="room_with_id"),
]
