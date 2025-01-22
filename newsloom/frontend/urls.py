from django.urls import include, path
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

urlpatterns = [
    path("api/", include(router.urls)),
    path("api-auth/", include("rest_framework.urls")),
]
