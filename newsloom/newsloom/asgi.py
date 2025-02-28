import os
import django
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "newsloom.settings")
django.setup()

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import OriginValidator
from chat.routing import websocket_urlpatterns  # noqa E402

# Define allowed origins for WebSocket connections
ALLOWED_ORIGINS = [
    "test.newsloom.io",  # Allow connections from this origin
    "http://test.newsloom.io",  # Both HTTP and HTTPS should be allowed
]

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        # WebSocket with OriginValidator to restrict connections to allowed origins
        "websocket": OriginValidator(
            AuthMiddlewareStack(
                URLRouter(websocket_urlpatterns)  # This will route WebSocket connections
            ),
            ALLOWED_ORIGINS,  # Validate that the WebSocket origin is allowed
        ),
    }
)
