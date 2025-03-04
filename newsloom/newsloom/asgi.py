import os
import django
from django.core.asgi import get_asgi_application

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa E402

from chat.middleware import AuthMiddleware
from chat.routing import websocket_urlpatterns  # noqa E402

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "newsloom.settings")
django.setup()

# Define allowed origins for WebSocket connections
ALLOWED_ORIGINS = [
    "test.newsloom.io",  # Allow connections from this origin
    "http://test.newsloom.io",  # Both HTTP and HTTPS should be allowed
]

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": AuthMiddleware(URLRouter(websocket_urlpatterns)),
    }
)
