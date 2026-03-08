from __future__ import annotations

import time

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

REQUESTS_TOTAL = Counter(
    "app_http_requests_total",
    "Total HTTP requests served by the monitoring demo application.",
    ["method", "endpoint", "http_status"],
)
ERRORS_TOTAL = Counter(
    "app_http_errors_total",
    "Total HTTP error responses served by the monitoring demo application.",
    ["endpoint", "http_status"],
)
REQUEST_DURATION = Histogram(
    "app_http_request_duration_seconds",
    "HTTP request duration in seconds.",
    ["endpoint"],
)
USERS_TOTAL = Gauge("app_users_total", "Current number of users stored in SQLite.")
TICKETS_TOTAL = Gauge("app_tickets_total", "Current number of tickets stored in SQLite.")
TICKETS_OPEN = Gauge("app_tickets_open", "Current number of open tickets.")
TICKETS_CLOSED = Gauge("app_tickets_closed_current", "Current number of closed tickets.")
TICKETS_OVERDUE = Gauge(
    "app_tickets_overdue",
    "Current number of open tickets older than the configured overdue threshold.",
)
APP_UP = Gauge("app_up", "Whether the Flask application process is able to serve traffic.")
DB_UP = Gauge("app_db_up", "Whether the SQLite database is reachable.")
USERS_CREATED_TOTAL = Counter(
    "app_users_created_total",
    "Total users created through the demo API.",
)
TICKETS_CREATED_TOTAL = Counter(
    "app_tickets_created_total",
    "Total tickets created through the demo API.",
)
TICKETS_CLOSED_TOTAL = Counter(
    "app_tickets_closed_total",
    "Total ticket close operations performed through the demo API.",
)
TICKETS_REOPENED_TOTAL = Counter(
    "app_tickets_reopened_total",
    "Total ticket reopen operations performed through the demo API.",
)
SEED_RUNS_TOTAL = Counter(
    "app_demo_seed_runs_total",
    "Total demo seed operations executed through the API.",
)
INFLUX_WRITE_FAILURES_TOTAL = Counter(
    "app_influx_write_failures_total",
    "Total failed attempts to export business metrics to InfluxDB.",
)
INFLUX_LAST_EXPORT_SUCCESS = Gauge(
    "app_influx_last_export_success",
    "Whether the last attempt to export business metrics to InfluxDB succeeded.",
)
INFLUX_LAST_EXPORT_UNIX = Gauge(
    "app_influx_last_export_timestamp_seconds",
    "Unix timestamp of the last successful InfluxDB export.",
)


def observe_request(
    *,
    method: str,
    endpoint: str,
    http_status: int,
    latency_seconds: float,
) -> None:
    REQUESTS_TOTAL.labels(
        method=method,
        endpoint=endpoint,
        http_status=str(http_status),
    ).inc()
    REQUEST_DURATION.labels(endpoint=endpoint).observe(latency_seconds)
    if http_status >= 400:
        ERRORS_TOTAL.labels(endpoint=endpoint, http_status=str(http_status)).inc()


def update_runtime_metrics(*, stats: dict[str, int] | None, db_ok: bool) -> None:
    APP_UP.set(1)
    DB_UP.set(1 if db_ok else 0)

    if not stats:
        return

    USERS_TOTAL.set(stats["users_total"])
    TICKETS_TOTAL.set(stats["tickets_total"])
    TICKETS_OPEN.set(stats["tickets_open"])
    TICKETS_CLOSED.set(stats["tickets_closed"])
    TICKETS_OVERDUE.set(stats["tickets_overdue"])


def record_business_event(event_name: str) -> None:
    counters = {
        "user_created": USERS_CREATED_TOTAL,
        "ticket_created": TICKETS_CREATED_TOTAL,
        "ticket_closed": TICKETS_CLOSED_TOTAL,
        "ticket_reopened": TICKETS_REOPENED_TOTAL,
        "seed_run": SEED_RUNS_TOTAL,
    }
    counters[event_name].inc()


def record_influx_export(success: bool) -> None:
    INFLUX_LAST_EXPORT_SUCCESS.set(1 if success else 0)
    if success:
        INFLUX_LAST_EXPORT_UNIX.set(time.time())
        return
    INFLUX_WRITE_FAILURES_TOTAL.inc()


def render_metrics() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
