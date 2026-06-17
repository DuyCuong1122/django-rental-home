import time

import redis.asyncio as redis
from prometheus_client import Counter, Histogram, Gauge

from app.core.config import settings

REDIS_COMMAND_TOTAL = Counter(
    "redis_commands_total",
    "Total Redis commands executed.",
    labelnames=("command",),
)
REDIS_COMMAND_ERRORS_TOTAL = Counter(
    "redis_command_errors_total",
    "Total Redis command errors.",
    labelnames=("command",),
)
REDIS_COMMAND_INFLIGHT = Gauge(
    "redis_commands_inflight",
    "Number of Redis commands currently in-flight.",
)
REDIS_COMMAND_LATENCY_SECONDS = Histogram(
    "redis_command_latency_seconds",
    "Redis command latency in seconds.",
    labelnames=("command",),
)

redis_client = redis.from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True
)

REDIS_POOL_MAX_CONNECTIONS = Gauge(
    "redis_pool_max_connections",
    "Redis client connection pool max_connections (if available).",
)
REDIS_POOL_IN_USE = Gauge(
    "redis_pool_in_use_connections",
    "Redis client connection pool in-use connections (best-effort).",
)
REDIS_POOL_AVAILABLE = Gauge(
    "redis_pool_available_connections",
    "Redis client connection pool available connections (best-effort).",
)

pool = getattr(redis_client, "connection_pool", None)
if pool:
    REDIS_POOL_MAX_CONNECTIONS.set_function(lambda: int(getattr(pool, "max_connections", 0) or 0))
    REDIS_POOL_IN_USE.set_function(lambda: int(len(getattr(pool, "_in_use_connections", []))))
    REDIS_POOL_AVAILABLE.set_function(lambda: int(len(getattr(pool, "_available_connections", []))))

if not getattr(redis_client, "_prom_wrapped", False):
    _orig_execute_command = redis_client.execute_command

    async def _execute_command_with_metrics(*args, **kwargs):
        cmd = "unknown"
        if args:
            cmd = str(args[0]).lower()
        start = time.monotonic()
        REDIS_COMMAND_INFLIGHT.inc()
        try:
            return await _orig_execute_command(*args, **kwargs)
        except Exception:
            REDIS_COMMAND_ERRORS_TOTAL.labels(command=cmd).inc()
            raise
        finally:
            REDIS_COMMAND_TOTAL.labels(command=cmd).inc()
            REDIS_COMMAND_LATENCY_SECONDS.labels(command=cmd).observe(time.monotonic() - start)
            REDIS_COMMAND_INFLIGHT.dec()

    redis_client.execute_command = _execute_command_with_metrics
    redis_client._prom_wrapped = True

async def get_redis():
    return redis_client
