import os
import django

# Set DJANGO_SETTINGS_MODULE first before importing other modules
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "newsloom.settings")
django.setup()

# Now import other modules after Django is set up
from django.core.asgi import get_asgi_application  # noqa: E402
from channels.auth import AuthMiddlewareStack  # noqa: E402
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from chat.routing import websocket_urlpatterns  # noqa: E402

# The Django setup has been moved before imports to avoid circular references

# Define allowed origins for WebSocket connections
ALLOWED_ORIGINS = [
    "test.newsloom.io",  # Allow connections from this origin
    "http://test.newsloom.io",  # Both HTTP and HTTPS should be allowed
]

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
    }
)
