import logging
import os
import django_filters as filters
from agents.models import Agent
from anthropic import AnthropicBedrock
from chat.consumers import ChatConsumer
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
from streams.tasks import TASK_CONFIG_EXAMPLES

from .serializers import (
    AgentSerializer,
    ChatMessageSerializer,
    ChatSerializer,
    DocSerializer,
    ExamplesSerializer,
    LoginSerializer,
    MediaSerializer,
    NewsSerializer,
    RegisterSerializer,
    SourceSerializer,
    StreamExecutionStatsSerializer,
    StreamLogSerializer,
    StreamSerializer,
    TelegramDocPublishLogSerializer,
    TelegramPublishLogSerializer,
    UserSerializer,
)

# Initialize loggers
logger = logging.getLogger(__name__)
message_logger = logging.getLogger("chat.message_processing")


@api_view(["POST"])
@permission_classes([AllowAny])
def register_view(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        token, created = Token.objects.get_or_create(user=user)
        return Response(
            {
                "token": token.key,
                "user_id": user.pk,
                "username": user.username,
                "email": user.email,
            }
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
    queryset = Chat.objects.prefetch_related('users', 'messages', 'messages__user', 'messages__chat').all()
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

    @action(detail=False, methods=["post"])
    def process_message(self, request):
        """
        Process a message using Claude AI and return the response.

        This endpoint uses the same processing logic as WebSocket connections to ensure
        consistent behavior across both interfaces.

        Request Body:
            {
                "message": "string",     # Required. The message to process
                "chat_id": "integer"     # Optional. ID of existing chat to continue
            }

        Returns:
            {
                "message": "string",      # The original message
                "response": "string",     # Claude's response
                "chat_id": "integer",     # ID of the chat (existing or newly created)
                "timestamp": "string"     # ISO format timestamp of the message
            }

        Raises:
            400 Bad Request: If message is missing
            404 Not Found: If specified chat_id doesn't exist
            500 Internal Server Error: For processing errors or missing credentials
        """
        try:
            message = request.data.get("message")
            chat_id = request.data.get("chat_id")

            if not message:
                return Response(
                    {"error": "Message is required"}, status=status.HTTP_400_BAD_REQUEST
                )

            # Initialize AWS Bedrock client
            aws_access_key = os.environ.get("BEDROCK_AWS_ACCESS_KEY_ID")
            aws_secret_key = os.environ.get("BEDROCK_AWS_SECRET_ACCESS_KEY")
            aws_region = os.environ.get("BEDROCK_AWS_REGION", "us-west-2")

            if not aws_access_key or not aws_secret_key:
                return Response(
                    {"error": "Missing AWS credentials for Bedrock"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            client = AnthropicBedrock(
                aws_access_key=aws_access_key,
                aws_secret_key=aws_secret_key,
                aws_region=aws_region,
            )

            # Get or create chat
            chat = None
            chat_history = []

            if chat_id:
                try:
                    chat = Chat.objects.get(id=chat_id, user=request.user)
                    # Load chat history
                    messages = list(
                        ChatMessage.objects.filter(chat=chat).order_by("timestamp")
                    )
                    for msg in messages:
                        chat_history.append({"role": "user", "content": msg.message})
                        if msg.response:
                            chat_history.append(
                                {"role": "assistant", "content": msg.response}
                            )
                except Chat.DoesNotExist:
                    return Response(
                        {"error": "Chat not found"}, status=status.HTTP_404_NOT_FOUND
                    )

            if not chat:
                chat = Chat.objects.create(user=request.user)

            # Process message using ChatConsumer's core logic
            message_logger.info(f"Processing message for chat {chat.id}")
            from asgiref.sync import async_to_sync

            try:
                response, chat_message = async_to_sync(
                    ChatConsumer.process_message_core
                )(
                    message=message,
                    chat=chat,
                    chat_history=chat_history,
                    client=client,
                    user=request.user,
                )
                message_logger.info(
                    f"Successfully processed message for chat {chat.id}"
                )
            except Exception as e:
                message_logger.error(
                    f"Failed to process message for chat {chat.id}: {str(e)}"
                )
                raise

            return Response(
                {
                    "message": message,
                    "response": response,
                    "chat_id": chat.id,
                    "timestamp": (
                        chat_message.timestamp.isoformat() if chat_message else None
                    ),
                }
            )

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class StreamViewSet(viewsets.ModelViewSet):
    queryset = Stream.objects.prefetch_related('source', 'media', 'media__sources', 'media__examples').all()
    serializer_class = StreamSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=["post"])
    def execute(self, request, pk=None):
        stream = self.get_object()
        result = stream.execute_task()
        return Response({"status": "success", "result": result})


class StreamLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StreamLog.objects.prefetch_related('stream').all()
    serializer_class = StreamLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ('stream', )


class StreamExecutionStatsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StreamExecutionStats.objects.all()
    serializer_class = StreamExecutionStatsSerializer
    permission_classes = [permissions.IsAuthenticated]


class TelegramPublishLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TelegramPublishLog.objects.prefetch_related('news', 'media').all()
    serializer_class = TelegramPublishLogSerializer
    permission_classes = [permissions.IsAuthenticated]


class TelegramDocPublishLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TelegramDocPublishLog.objects.prefetch_related("doc", "media")
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
    class Filter(filters.FilterSet):
        active_only = filters.BooleanFilter(field_name='is_active')

    queryset = Agent.objects.all()
    serializer_class = AgentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_class = Filter


class MediaViewSet(viewsets.ModelViewSet):
    queryset = Media.objects.all()
    serializer_class = MediaSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=["post"])
    def add_source(self, request, pk=None):
        media = self.get_object()
        source_ids = request.data.get("source_id")

        # Handle both single ID and list of IDs
        if isinstance(source_ids, list):
            sources = Source.objects.filter(pk__in=source_ids)
            media.sources.add(*sources)
            return Response({"status": f"{len(sources)} sources added"})
        else:
            source = Source.objects.get(pk=source_ids)
            media.sources.add(source)
            return Response({"status": "source added"})

    @action(detail=True, methods=["post"])
    def remove_source(self, request, pk=None):
        media = self.get_object()
        source = Source.objects.get(pk=request.data.get("source_id"))
        media.sources.remove(source)
        return Response({"status": "source removed"})


class ExamplesViewSet(viewsets.ModelViewSet):
    queryset = Examples.objects.prefetch_related('media').all()
    serializer_class = ExamplesSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ('media', )
