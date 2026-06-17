from __future__ import annotations

import logging
from contextvars import ContextVar


request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
trace_id_var: ContextVar[str | None] = ContextVar("trace_id", default=None)
span_id_var: ContextVar[str | None] = ContextVar("span_id", default=None)


def set_request_id(request_id: str | None) -> None:
    request_id_var.set(request_id)


def get_request_id() -> str | None:
    return request_id_var.get()

def set_trace_context(*, trace_id: str | None, span_id: str | None) -> None:
    trace_id_var.set(trace_id)
    span_id_var.set(span_id)


def get_trace_id() -> str | None:
    return trace_id_var.get()


def get_span_id() -> str | None:
    return span_id_var.get()



class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = get_trace_id()
        record.span_id = get_span_id()
        record.request_id = get_request_id()
