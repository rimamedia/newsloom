import logging
import django_filters as filters
from agents.models import Agent
from anthropic import AnthropicBedrock
from chat.consumers import ChatConsumer
from chat.models import Chat, ChatMessage
from django.contrib.auth.models import User
from mediamanager.models import Examples, Media
from rest_framework import permissions, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
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
from asgiref.sync import async_to_sync
from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import generics

from .serializers import (
    AgentSerializer,
    ChatMessageSerializer,
    ChatMessageRequestSerializer,
    ChatMessageResponseSerializer,
    ChatSerializer,
    DocSerializer,
    ExamplesSerializer,
    LoginSerializer,
    MediaSerializer,
    NewsSerializer,
    NewsCreateSerializer,
    RegisterSerializer,
    SourceIdSerializer,
    SourceSerializer,
    StatusResponseSerializer,
    StatusWithResultResponseSerializer,
    StreamExecutionStatsSerializer,
    StreamLogSerializer,
    StreamSerializer,
    TelegramDocPublishLogSerializer,
    TelegramPublishLogSerializer,
    UserSerializer,
)
from streams.tasks import TASK_CONFIG_EXAMPLES

# Initialize loggers
logger = logging.getLogger(__name__)
message_logger = logging.getLogger("chat.message_processing")


class RegisterView(generics.GenericAPIView):
    permission_classes = (AllowAny,)

    @extend_schema(request=RegisterSerializer)
    def post(self, request, *args, **kwargs):
        """
        Register a new user
        """
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


class LoginView(generics.GenericAPIView):
    permission_classes = (AllowAny,)

    @extend_schema(request=LoginSerializer)
    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data
            token, created = Token.objects.get_or_create(user=user)
            return Response(
                {"token": token.key, "user_id": user.pk, "username": user.username}
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        """Invalidate the user's auth token."""
        try:
            # Delete the user's token to invalidate it
            request.user.auth_token.delete()
            return Response(
                {"detail": "Successfully logged out"}, status=status.HTTP_200_OK
            )
        except Exception:
            return Response(
                {"detail": "Error during logout"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


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

    @extend_schema(request=ChatMessageRequestSerializer, responses=ChatMessageResponseSerializer)
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
        serializer = ChatMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        chat_id = serializer.validated_data.get("chat_id")
        message = serializer.validated_data.get("message")

        try:
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

            client = AnthropicBedrock(
                aws_access_key=settings.BEDROCK_AWS_ACCESS_KEY_ID,
                aws_secret_key=settings.BEDROCK_AWS_SECRET_ACCESS_KEY,
                aws_region=settings.BEDROCK_AWS_REGION,
            )

            message_logger.info(f"Processing message for chat {chat.id}")

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

                response_data = {
                    "message": message,
                    "response": response,
                    "chat_id": chat.id,
                    "timestamp": None
                }

                if chat_message is not None:
                    response_data["timestamp"] = chat_message.timestamp.isoformat()

                response_serializer = ChatMessageResponseSerializer(response_data)

                return Response(response_serializer.data)
            except Exception as e:
                message_logger.error(
                    f"Failed to process message for chat {chat.id}: {str(e)}"
                )
                raise

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class StreamViewSet(viewsets.ModelViewSet):
    queryset = Stream.objects.prefetch_related('source', 'media', 'media__sources', 'media__examples').all()
    serializer_class = StreamSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses=StatusWithResultResponseSerializer)
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

    def get_serializer_class(self):
        if self.action == "create":
            return NewsCreateSerializer
        return super().get_serializer_class()


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

    @extend_schema(request=SourceIdSerializer, responses=StatusResponseSerializer)
    @action(detail=True, methods=["post"])
    def remove_source(self, request, pk=None):
        """Remove one or more sources from a media entry.
        
        Args:
            request: The HTTP request
            pk: Primary key of the media object
            
        Returns:
            JSON response confirming removal
            
        Raises:
            Http404: If media with given pk doesn't exist
            Source.DoesNotExist: If any source with given id doesn't exist
        """
        media = self.get_object()
        serializer = SourceIdSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        media.sources.remove(*serializer.validated_data["source_ids"])
        return Response({"status": "source removed"})


class ExamplesViewSet(viewsets.ModelViewSet):
    queryset = Examples.objects.prefetch_related('media').all()
    serializer_class = ExamplesSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ('media', )
