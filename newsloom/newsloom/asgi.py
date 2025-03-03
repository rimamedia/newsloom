"""
ASGI config for newsloom project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os
import django
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "newsloom.settings")
django.setup()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa E402

from chat.middleware import AuthMiddleware
from chat.routing import websocket_urlpatterns  # noqa E402

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": AuthMiddleware(URLRouter(websocket_urlpatterns)),
    }
)
