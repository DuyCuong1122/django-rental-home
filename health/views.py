from __future__ import annotations

import asyncio

from django.http import JsonResponse
from sqlalchemy import text

from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.core.redis import get_redis


async def live(request):
    return JsonResponse({"status": "alive"})


async def ready(request):
    db_ok = True
    cache_ok = True
    celery_ok = True

    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    try:
        redis = await get_redis()
        await redis.ping()
    except Exception:
        cache_ok = False

    try:
        replies = await asyncio.to_thread(lambda: celery_app.control.ping(timeout=1.0))
        celery_ok = bool(replies)
    except Exception:
        celery_ok = False

    status_code = 200 if (db_ok and cache_ok and celery_ok) else 503
    return JsonResponse(
        {
            "database": "ok" if db_ok else "error",
            "cache": "ok" if cache_ok else "error",
            "celery": "ok" if celery_ok else "error",
            "status": "ready" if (db_ok and cache_ok and celery_ok) else "not_ready",
        },
        status=status_code,
    )
