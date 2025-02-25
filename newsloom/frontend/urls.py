from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework.routers import DefaultRouter

from . import views

schema_view = get_schema_view(
    openapi.Info(
        title="Newsloom API",
        default_version="v1",
        description="API for managing news streams, sources, documents and chat interactions",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

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
        "register/", views.register_view, name="api_register"
    ),  # User registration endpoint
    path(
        "token/", views.login_view, name="api_token_login"
    ),  # Token generation endpoint
    path("logout/", views.logout_view, name="api_logout"),  # Token revocation endpoint
    # Swagger UI
    path(
        "swagger<format>/", schema_view.without_ui(cache_timeout=0), name="schema-json"
    ),
    path(
        "swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
]
