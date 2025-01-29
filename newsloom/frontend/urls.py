from django.urls import include, path
from rest_framework.decorators import permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"users", views.UserViewSet)
router.register(r"chats", views.ChatViewSet, basename="chat")
router.register(r"messages", views.ChatMessageViewSet, basename="chatmessage")
router.register(r"streams", views.StreamViewSet)
router.register(r"stream-logs", views.StreamLogViewSet, basename="streamlog")
router.register(r"stream-stats", views.StreamExecutionStatsViewSet)
router.register(r"telegram-logs", views.TelegramPublishLogViewSet)
router.register(r"telegram-doc-logs", views.TelegramDocPublishLogViewSet)
router.register(r"sources", views.SourceViewSet)
router.register(r"news", views.NewsViewSet)
router.register(r"docs", views.DocViewSet)
router.register(r"agents", views.AgentViewSet)
router.register(r"media", views.MediaViewSet)
router.register(r"examples", views.ExamplesViewSet)

urlpatterns = [
    path("api/", include(router.urls)),
    path("api-auth/", include("rest_framework.urls")),
    path("api/login/", permission_classes([AllowAny])(views.login_view), name="login"),
]
