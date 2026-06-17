from __future__ import annotations

import time
import uuid
import logging
from inspect import iscoroutinefunction

from django.utils.decorators import sync_and_async_middleware

from app.core.request_context import set_request_id, set_trace_context


logger = logging.getLogger("http")

def _parse_traceparent(value: str | None) -> tuple[str | None, str | None]:
    if not value:
        return None, None
    parts = value.split("-")
    if len(parts) < 4:
        return None, None
    trace_id = parts[1] if len(parts[1]) == 32 else None
    span_id = parts[2] if len(parts[2]) == 16 else None
    return trace_id, span_id


@sync_and_async_middleware
def request_logging_middleware(get_response):
    if iscoroutinefunction(get_response):

        async def middleware(request):
            rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
            set_request_id(rid)
            trace_id, span_id = _parse_traceparent(request.headers.get("traceparent"))
            set_trace_context(trace_id=trace_id, span_id=span_id)
            start = time.monotonic()
            try:
                response = await get_response(request)
            except Exception:
                duration_ms = int((time.monotonic() - start) * 1000)
                logger.exception(
                    "request_failed",
                    extra={"path": request.path, "method": request.method, "duration_ms": duration_ms},
                )
                raise

            duration_ms = int((time.monotonic() - start) * 1000)
            response["X-Request-ID"] = rid
            logger.info(
                "request_completed",
                extra={
                    "path": request.path,
                    "method": request.method,
                    "status_code": getattr(response, "status_code", None),
                    "duration_ms": duration_ms,
                },
            )
            return response

        return middleware

    def middleware(request):
        rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        set_request_id(rid)
        trace_id, span_id = _parse_traceparent(request.headers.get("traceparent"))
        set_trace_context(trace_id=trace_id, span_id=span_id)
        start = time.monotonic()
        try:
            response = get_response(request)
        except Exception:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.exception(
                "request_failed",
                extra={"path": request.path, "method": request.method, "duration_ms": duration_ms},
            )
            raise

        duration_ms = int((time.monotonic() - start) * 1000)
        response["X-Request-ID"] = rid
        logger.info(
            "request_completed",
            extra={
                "path": request.path,
                "method": request.method,
                "status_code": getattr(response, "status_code", None),
                "duration_ms": duration_ms,
            },
        )
        return response

    return middleware
