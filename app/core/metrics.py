from __future__ import annotations

import os
import time

from prometheus_client import Counter, Histogram, Gauge
from sqlalchemy import event

from app.core.database import engine


_initialized = False
SLOW_QUERY_THRESHOLD_MS = int(os.environ.get("SLOW_QUERY_THRESHOLD_MS", "500"))

DB_QUERY_TOTAL = Counter(
    "sqlalchemy_db_queries_total",
    "Total SQLAlchemy DB queries executed.",
    labelnames=("operation",),
)
DB_QUERY_LATENCY_SECONDS = Histogram(
    "sqlalchemy_db_query_latency_seconds",
    "SQLAlchemy DB query latency in seconds.",
    labelnames=("operation",),
)
DB_QUERY_ERRORS_TOTAL = Counter(
    "sqlalchemy_db_query_errors_total",
    "Total SQLAlchemy DB query errors.",
    labelnames=("operation",),
)
DB_SLOW_QUERY_TOTAL = Counter(
    "sqlalchemy_db_slow_queries_total",
    "Total SQLAlchemy DB queries slower than threshold.",
    labelnames=("operation",),
)

DB_POOL_SIZE = Gauge("sqlalchemy_db_pool_size", "SQLAlchemy connection pool size.")
DB_POOL_CHECKED_OUT = Gauge("sqlalchemy_db_pool_checked_out", "SQLAlchemy connections currently checked out.")
DB_POOL_OVERFLOW = Gauge("sqlalchemy_db_pool_overflow", "SQLAlchemy pool overflow.")


def _op_from_statement(statement: str | None) -> str:
    if not statement:
        return "unknown"
    op = statement.lstrip().split(None, 1)[0].lower() if statement.strip() else "unknown"
    if op in {"select", "insert", "update", "delete"}:
        return op
    return "other"


def init_metrics() -> None:
    global _initialized
    if _initialized:
        return
    _initialized = True

    sync_engine = engine.sync_engine
    pool = getattr(sync_engine, "pool", None)
    if pool:
        DB_POOL_SIZE.set_function(lambda: int(getattr(pool, "size", lambda: 0)()))
        DB_POOL_CHECKED_OUT.set_function(lambda: int(getattr(pool, "checkedout", lambda: 0)()))
        DB_POOL_OVERFLOW.set_function(lambda: int(getattr(pool, "overflow", lambda: 0)()))

    @event.listens_for(sync_engine, "before_cursor_execute")
    def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        context._prom_start_time = time.monotonic()
        DB_QUERY_TOTAL.labels(operation=_op_from_statement(statement)).inc()

    @event.listens_for(sync_engine, "after_cursor_execute")
    def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        start = getattr(context, "_prom_start_time", None)
        if start is None:
            return
        duration_s = time.monotonic() - start
        op = _op_from_statement(statement)
        DB_QUERY_LATENCY_SECONDS.labels(operation=op).observe(duration_s)
        if duration_s * 1000 >= SLOW_QUERY_THRESHOLD_MS:
            DB_SLOW_QUERY_TOTAL.labels(operation=op).inc()

    @event.listens_for(sync_engine, "handle_error")
    def _handle_error(exception_context):
        DB_QUERY_ERRORS_TOTAL.labels(operation=_op_from_statement(exception_context.statement)).inc()
