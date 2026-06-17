from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram


APPOINTMENTS_CREATED_TOTAL = Counter(
    "business_appointments_created_total",
    "Total appointments created.",
    labelnames=("status",),
)

CHAT_MESSAGES_CREATED_TOTAL = Counter(
    "business_chat_messages_created_total",
    "Total chat messages created.",
    labelnames=("message_type",),
)

AUTH_REGISTER_TOTAL = Counter(
    "business_auth_register_total",
    "Total user registrations.",
    labelnames=("result", "role"),
)

AUTH_LOGIN_TOTAL = Counter(
    "business_auth_login_total",
    "Total login attempts.",
    labelnames=("result", "role", "reason"),
)

ROOMS_CREATED_TOTAL = Counter(
    "business_rooms_created_total",
    "Total rooms created.",
    labelnames=("result", "status"),
)

ROOM_LIST_TOTAL = Counter(
    "business_room_list_total",
    "Total room list requests by kind.",
    labelnames=("kind", "cache"),
)

ROOM_DETAIL_VIEWS_TOTAL = Counter(
    "business_room_detail_views_total",
    "Total room detail views.",
)

PUSH_SEND_TOTAL = Counter(
    "business_push_send_total",
    "Total push notification sends.",
    labelnames=("provider", "result", "kind"),
)

PUSH_SEND_LATENCY_SECONDS = Histogram(
    "business_push_send_latency_seconds",
    "Push notification send latency in seconds.",
    labelnames=("provider", "kind"),
)

WEBSOCKET_ACTIVE_CONNECTIONS = Gauge(
    "websocket_active_connections",
    "Current active WebSocket connections.",
    labelnames=("namespace",),
)

WEBSOCKET_MESSAGES_TOTAL = Counter(
    "websocket_messages_total",
    "Total WebSocket messages received by type.",
    labelnames=("namespace", "type"),
)

WEBSOCKET_ERRORS_TOTAL = Counter(
    "websocket_errors_total",
    "Total WebSocket errors.",
    labelnames=("namespace", "type"),
)
