# Grafana Dashboard Checklist For k6 Runs

Open these dashboards before starting `load`, `stress`, or `soak`.

## 1. Backend Overview

- Requests/sec
- Error %
- P50 latency
- P95 latency
- P99 latency
- SQLAlchemy DB query latency
- SQLAlchemy slow query count
- Redis command latency
- Redis command error count

## 2. Node Exporter Full

- CPU usage
- Memory usage
- Disk usage
- Disk IO
- Network throughput
- System load
- Uptime

## 3. Container Monitoring

- Container CPU for `api`, `postgres`, `redis`, `grafana`, `prometheus`
- Container Memory for `api`, `postgres`, `redis`
- Container Network RX/TX
- Container Filesystem
- Container Restart Count (24h)

## 4. Logging Overview / Explore

- Backend Logs
- Postgres Logs
- Redis Logs
- Prometheus Logs
- Grafana Logs
- Loki Explore query: `{service=~"api|postgres|redis|prometheus|grafana"}`

## 5. Prometheus Targets

- `django = up`
- `postgres = up`
- `redis = up`
- `node-exporter = up`
- `cadvisor = up`
- `celery = up`

## 6. Spot Checks During Test

- Prometheus expression: `rate(django_http_requests_total_by_method_total[1m])`
- Prometheus expression: `histogram_quantile(0.95, sum(rate(django_http_requests_latency_seconds_by_view_method_bucket[5m])) by (le))`
- Prometheus expression: `rate(sqlalchemy_db_queries_total[1m])`
- Prometheus expression: `histogram_quantile(0.95, sum(rate(sqlalchemy_db_query_latency_seconds_bucket[5m])) by (le))`
- Prometheus expression: `rate(redis_commands_total[1m])`
- Prometheus expression: `histogram_quantile(0.95, sum(rate(redis_command_latency_seconds_bucket[5m])) by (le))`
