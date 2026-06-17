import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")

import sentry_sdk
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import path
from sentry_sdk.integrations.django import DjangoIntegration

from app.core.config import settings
from app.core.metrics import init_metrics
from app.websocket.consumers import ChatConsumer
from app.websocket.middleware import JWTAuthMiddlewareStack

sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    send_default_pii=settings.SENTRY_SEND_DEFAULT_PII,
    traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
    integrations=[DjangoIntegration()],
)

init_metrics()

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": JWTAuthMiddlewareStack(
        URLRouter([
            path("ws/chat/<uuid:chat_room_id>/", ChatConsumer.as_asgi()),
            path("ws/chat/<uuid:room_id>/", ChatConsumer.as_asgi()),
        ])
    ),
})
