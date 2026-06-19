# Monitoring & Performance Testing Setup

## What’s Included

- Django application metrics via Prometheus at `GET /metrics`
- Health endpoints:
  - `GET /health/live`
  - `GET /health/ready`
- Structured JSON logging (stdout) with `X-Request-ID` correlation
- PostgreSQL monitoring via `pg_stat_statements` + postgres_exporter
- Redis monitoring via redis_exporter
- Host/server monitoring via node-exporter
- Celery task monitoring (Prometheus metrics + Flower UI)
- Prometheus + Grafana via docker-compose
- k6 load/stress scripts under `performance-tests/`

## Run Monitoring Stack (Docker)

1. Start everything:

```bash
docker compose up --build
```

2. URLs:

- Django API (through nginx): `http://localhost/`
- Django metrics: `http://localhost:8000/metrics` (direct) or `http://localhost/metrics` (through nginx)
- Flower (Celery UI): `http://localhost:5555`
- Prometheus UI: `http://localhost:9090`
- Grafana UI: `http://localhost:3000`
- Node Exporter metrics: `http://localhost:9100/metrics`

3. Grafana credentials:

- Username: `admin`
- Password: `admin`

You can override via env:

- `GRAFANA_ADMIN_USER`
- `GRAFANA_ADMIN_PASSWORD`

## Metrics: Django (`/metrics`)

Metrics include request counts, status codes, and latency histograms from `django-prometheus`. The `/metrics` output also includes default process/runtime metrics (CPU seconds, memory, GC, etc.) exposed by the Prometheus Python client.

Custom metrics added for this repo:

- SQLAlchemy DB query count/latency:
  - `sqlalchemy_db_queries_total`
  - `sqlalchemy_db_query_latency_seconds`
  - `sqlalchemy_db_query_errors_total`
  - `sqlalchemy_db_slow_queries_total`
  - `sqlalchemy_db_pool_size`
  - `sqlalchemy_db_pool_checked_out`
  - `sqlalchemy_db_pool_overflow`
- Redis command count/latency:
  - `redis_commands_total`
  - `redis_command_latency_seconds`
  - `redis_command_errors_total`
  - `redis_commands_inflight`

Celery worker metrics are exposed separately by the worker process (scraped by Prometheus):

- `http://celery_worker:8001/metrics` (inside docker network)
- Task metrics:
  - `celery_task_runtime_seconds`
  - `celery_task_success_total`
  - `celery_task_failure_total`
  - `celery_task_retry_total`
  - `celery_task_inflight`
  - `celery_queue_length`

Node Exporter is scraped separately by Prometheus at `node-exporter:9100` and provides host-level metrics such as:

- CPU usage (`node_cpu_seconds_total`)
- Memory usage (`node_memory_*`)
- Disk usage / filesystem (`node_filesystem_*`)
- Disk IO (`node_disk_*`)
- Network traffic (`node_network_*`)
- System load (`node_load1`, `node_load5`, `node_load15`)
- Uptime (`node_boot_time_seconds`)

## Health Checks

- Liveness:

```bash
curl -s http://localhost/health/live
```

- Readiness (checks PostgreSQL + Redis + Celery worker):

```bash
curl -s -i http://localhost/health/ready
```

`/health/ready` returns `200` when dependencies are reachable, otherwise `503`.

## Structured Logging

Logs are JSON formatted and include:

- `request_id` (from `X-Request-ID` header or generated per request)
- `path`, `method`, `status_code`, `duration_ms`
- exception stack traces for failures

Example:

```json
{
  "levelname": "INFO",
  "name": "http",
  "message": "request_completed",
  "request_id": "f5a7b2f5-2edb-4a10-9b8c-7f94f30b8e7c",
  "path": "/api/v1/appointments/",
  "method": "POST",
  "status_code": 201,
  "duration_ms": 54
}
```

## PostgreSQL Monitoring: pg_stat_statements

### Enablement

This setup enables `pg_stat_statements` in `docker-compose.yml` and attempts to create the extension on first initialization.

If your Postgres volume already existed before enabling it, run:

```sql
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
```

### Example Queries

1) Slowest queries by mean time:

```sql
SELECT
  query,
  calls,
  mean_exec_time,
  max_exec_time,
  rows
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

2) Most expensive queries by total time:

```sql
SELECT
  query,
  calls,
  total_exec_time,
  mean_exec_time
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 10;
```

3) Active connections:

```sql
SELECT
  state,
  COUNT(*) AS connections
FROM pg_stat_activity
GROUP BY state
ORDER BY connections DESC;
```

4) Lock inspection (blocked vs blocking):

```sql
SELECT
  blocked.pid     AS blocked_pid,
  blocked.query   AS blocked_query,
  blocking.pid    AS blocking_pid,
  blocking.query  AS blocking_query
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked ON blocked.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks
  ON blocking_locks.locktype = blocked_locks.locktype
  AND blocking_locks.database IS NOT DISTINCT FROM blocked_locks.database
  AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
  AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
  AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
  AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
  AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
  AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
  AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
  AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
  AND blocking_locks.pid != blocked_locks.pid
JOIN pg_catalog.pg_stat_activity blocking ON blocking.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;
```

## k6 Performance Testing

### Prerequisites

Install k6 locally, or run it via Docker:

```bash
docker run --rm -i grafana/k6 run - < performance-tests/load_test.js
```

### Load test (100 VUs / 1 minute)

```bash
k6 run performance-tests/load_test.js \
  -e BASE_URL=http://localhost \
  -e TENANT_EMAIL=tenant@example.com \
  -e TENANT_PASSWORD=yourpassword \
  -e ROOM_ID=00000000-0000-0000-0000-000000000000
```

### Stress test (100 → 1000 VUs)

```bash
k6 run performance-tests/stress_test.js \
  -e BASE_URL=http://localhost \
  -e TENANT_EMAIL=tenant@example.com \
  -e TENANT_PASSWORD=yourpassword \
  -e ROOM_ID=00000000-0000-0000-0000-000000000000
```

### How to interpret results

- Throughput: requests per second achieved under load.
- p95/p99 latency: 95% / 99% of requests are faster than this value.
- Error rate: ratio of failed requests (timeouts, 5xx, or failed checks).

## Debugging Bottlenecks (Practical Workflow)

1. Confirm symptoms in Grafana:
   - latency p95/p99 rising
   - 5xx error rate increasing
   - DB latency spikes
2. Use logs with `request_id` to find slow endpoints and correlate errors.
3. Check DB hotspots:
   - top queries in `pg_stat_statements`
   - high connection counts or blocked locks
4. Common Django/DB bottlenecks:
   - N+1 queries (missing `select_related` / `prefetch_related`)
   - missing indexes on filter/join columns
   - heavy serialization / large response payloads
   - long transactions holding locks
   - too-small DB connection pool under load
