from django.urls import include, path
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

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
    # API endpoints
    path("", include(router.urls)),
    path("auth/", include("rest_framework.urls")),
    path(
        "register/", views.RegisterView.as_view(), name="api_register"
    ),  # User registration endpoint
    path(
        "token/", views.LoginView.as_view(), name="api_token_login"
    ),  # Token generation endpoint
    path("logout/", views.LogoutView.as_view(), name="api_logout"),  # Token revocation endpoint
    # Swagger UI
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
