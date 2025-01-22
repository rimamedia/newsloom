from chat.models import Chat, ChatMessage
from django.contrib.auth.models import User
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from streams.models import (
    Stream,
    StreamExecutionStats,
    StreamLog,
    TelegramDocPublishLog,
    TelegramPublishLog,
)

from .serializers import (
    ChatMessageSerializer,
    ChatSerializer,
    StreamExecutionStatsSerializer,
    StreamLogSerializer,
    StreamSerializer,
    TelegramDocPublishLogSerializer,
    TelegramPublishLogSerializer,
    UserSerializer,
)


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]


class ChatViewSet(viewsets.ModelViewSet):
    serializer_class = ChatSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Chat.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ChatMessageViewSet(viewsets.ModelViewSet):
    serializer_class = ChatMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ChatMessage.objects.filter(chat__user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class StreamViewSet(viewsets.ModelViewSet):
    queryset = Stream.objects.all()
    serializer_class = StreamSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=["post"])
    def execute(self, request, pk=None):
        stream = self.get_object()
        result = stream.execute_task()
        return Response({"status": "success", "result": result})


class StreamLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StreamLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = StreamLog.objects.all()
        stream_id = self.request.query_params.get("stream", None)
        if stream_id is not None:
            queryset = queryset.filter(stream_id=stream_id)
        return queryset


class StreamExecutionStatsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StreamExecutionStats.objects.all()
    serializer_class = StreamExecutionStatsSerializer
    permission_classes = [permissions.IsAuthenticated]


class TelegramPublishLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TelegramPublishLog.objects.all()
    serializer_class = TelegramPublishLogSerializer
    permission_classes = [permissions.IsAuthenticated]


class TelegramDocPublishLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TelegramDocPublishLog.objects.all()
    serializer_class = TelegramDocPublishLogSerializer
    permission_classes = [permissions.IsAuthenticated]
