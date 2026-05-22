import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'solace_backend.settings')
django.setup()

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from notification_app.middleware import JWTAuthMiddleware
from notification_app.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': JWTAuthMiddleware(
        URLRouter(websocket_urlpatterns)
    ),
})
