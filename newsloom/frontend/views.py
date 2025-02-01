from agents.models import Agent
from chat.models import Chat, ChatMessage
from django.contrib.auth.models import User
from mediamanager.models import Examples, Media
from rest_framework import permissions, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from sources.models import Doc, News, Source
from streams.models import (
    Stream,
    StreamExecutionStats,
    StreamLog,
    TelegramDocPublishLog,
    TelegramPublishLog,
)

from .serializers import (
    AgentSerializer,
    ChatMessageSerializer,
    ChatSerializer,
    DocSerializer,
    ExamplesSerializer,
    LoginSerializer,
    MediaSerializer,
    NewsSerializer,
    SourceSerializer,
    StreamExecutionStatsSerializer,
    StreamLogSerializer,
    StreamSerializer,
    TelegramDocPublishLogSerializer,
    TelegramPublishLogSerializer,
    UserSerializer,
)


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data
        token, created = Token.objects.get_or_create(user=user)
        return Response(
            {"token": token.key, "user_id": user.pk, "username": user.username}
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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


class SourceViewSet(viewsets.ModelViewSet):
    queryset = Source.objects.all()
    serializer_class = SourceSerializer
    permission_classes = [permissions.IsAuthenticated]


class NewsViewSet(viewsets.ModelViewSet):
    queryset = News.objects.all()
    serializer_class = NewsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        source = Source.objects.get(pk=self.request.data.get("source"))
        serializer.save(source=source)


class DocViewSet(viewsets.ModelViewSet):
    queryset = Doc.objects.all()
    serializer_class = DocSerializer
    permission_classes = [permissions.IsAuthenticated]


class AgentViewSet(viewsets.ModelViewSet):
    queryset = Agent.objects.all()
    serializer_class = AgentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Agent.objects.all()
        if self.request.query_params.get("active_only"):
            queryset = queryset.filter(is_active=True)
        return queryset


class MediaViewSet(viewsets.ModelViewSet):
    queryset = Media.objects.all()
    serializer_class = MediaSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=["post"])
    def add_source(self, request, pk=None):
        media = self.get_object()
        source = Source.objects.get(pk=request.data.get("source_id"))
        media.sources.add(source)
        return Response({"status": "source added"})

    @action(detail=True, methods=["post"])
    def remove_source(self, request, pk=None):
        media = self.get_object()
        source = Source.objects.get(pk=request.data.get("source_id"))
        media.sources.remove(source)
        return Response({"status": "source removed"})


class ExamplesViewSet(viewsets.ModelViewSet):
    queryset = Examples.objects.all()
    serializer_class = ExamplesSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Examples.objects.all()
        media_id = self.request.query_params.get("media", None)
        if media_id is not None:
            queryset = queryset.filter(media_id=media_id)
        return queryset
