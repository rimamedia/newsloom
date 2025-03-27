from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from newsloom.contrib.router import NewsloomRouter
from . import views

router = NewsloomRouter()
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
    path("acc/", include([
        path('login/', views.LoginView.as_view(), name='login'),
        path('logout/', views.LogoutView.as_view(), name='logout'),
        path("register/", views.RegisterView.as_view(), name="register"),

    ])),
    # Swagger UI
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
