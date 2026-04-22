from __future__ import annotations

import logging
import time
from uuid import uuid4

from flask import Flask, Response, g, jsonify, request

from .config import Settings
from .db import (
    close_ticket,
    create_ticket,
    create_user,
    get_app_stats,
    init_db,
    list_tickets,
    list_users,
    ping_db,
    reopen_ticket,
    seed_demo_data,
)
from .influx import InfluxWriter
from .metrics import (
    observe_request,
    record_business_event,
    record_influx_export,
    render_metrics,
    update_runtime_metrics,
)
from .observability import configure_logging, setup_tracing


def _parse_limit(raw_value: str | None, *, default: int = 50) -> int:
    if raw_value is None:
        return default
    limit = int(raw_value)
    return max(1, min(limit, 100))


def _read_payload() -> dict[str, object]:
    return request.get_json(silent=True) or {}


def _refresh_metrics(settings: Settings) -> tuple[bool, dict[str, int] | None]:
    db_ok = ping_db(settings.db_path)
    stats = None
    if db_ok:
        stats = get_app_stats(
            settings.db_path,
            overdue_after_hours=settings.overdue_after_hours,
        )
    update_runtime_metrics(stats=stats, db_ok=db_ok)
    return db_ok, stats


def create_app(settings: Settings | None = None) -> Flask:
    settings = settings or Settings.from_env()
    configure_logging(settings.log_level, json_logs=settings.json_logs)

    app = Flask(__name__)
    app.config["SETTINGS"] = settings
    app.logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    setup_tracing(app, settings)

    init_db(settings.db_path)
    influx_writer = InfluxWriter(settings)
    _refresh_metrics(settings)

    @app.before_request
    def before_request() -> None:
        request._start_time = time.perf_counter()
        g.request_id = request.headers.get(settings.request_id_header) or str(uuid4())

    @app.after_request
    def after_request(response: Response) -> Response:
        endpoint = request.url_rule.rule if request.url_rule else request.path
        latency = time.perf_counter() - getattr(request, "_start_time", time.perf_counter())
        observe_request(
            method=request.method,
            endpoint=endpoint,
            http_status=response.status_code,
            latency_seconds=latency,
        )

        db_ok, stats = _refresh_metrics(settings)
        if request.method == "POST" and stats:
            record_influx_export(influx_writer.write_stats(stats))
        elif request.method == "POST" and not db_ok:
            record_influx_export(False)

        app.logger.info(
            "request request_id=%s method=%s endpoint=%s status=%s duration_ms=%.2f",
            g.request_id,
            request.method,
            endpoint,
            response.status_code,
            latency * 1000,
        )
        response.headers[settings.request_id_header] = g.request_id
        return response

    @app.get("/")
    def index():
        return jsonify(
            {
                "app": settings.app_name,
                "environment": settings.app_env,
                "message": "Monitoring stack demo is running.",
                "endpoints": {
                    "health": "/health",
                    "metrics": "/metrics",
                    "users": "/users",
                    "tickets": "/tickets",
                    "seed": "/demo/seed",
                    "error_demo": "/demo/error",
                    "slow_demo": "/demo/slow?delay_ms=1200",
                },
            }
        )

    @app.get("/health")
    def health():
        db_ok, stats = _refresh_metrics(settings)
        status_code = 200 if db_ok else 503
        return (
            jsonify(
                {
                    "status": "ok" if db_ok else "error",
                    "database": "ok" if db_ok else "unavailable",
                    "influx_export": "enabled" if influx_writer.enabled else "disabled",
                    "stats": stats or {},
                    "overdue_after_hours": settings.overdue_after_hours,
                }
            ),
            status_code,
        )

    @app.get("/users")
    def users():
        limit = _parse_limit(request.args.get("limit"))
        return jsonify({"items": list_users(settings.db_path, limit=limit)})

    @app.route("/users", methods=["POST"])
    @app.route("/users/create", methods=["POST"])
    def users_create():
        payload = _read_payload()
        name = str(payload.get("name") or request.args.get("name") or "User").strip()
        if not name:
            return jsonify({"error": "Field 'name' is required."}), 400

        user = create_user(settings.db_path, name=name)
        record_business_event("user_created")
        return jsonify({"status": "ok", "user": user}), 201

    @app.get("/tickets")
    def tickets():
        limit = _parse_limit(request.args.get("limit"))
        status = request.args.get("status")
        return jsonify(
            {
                "items": list_tickets(
                    settings.db_path,
                    overdue_after_hours=settings.overdue_after_hours,
                    status=status,
                    limit=limit,
                )
            }
        )

    @app.route("/tickets", methods=["POST"])
    @app.route("/tickets/create", methods=["POST"])
    def tickets_create():
        payload = _read_payload()
        title = str(payload.get("title") or request.args.get("title") or "Test ticket").strip()
        age_hours = int(payload.get("age_hours") or request.args.get("age_hours") or 0)
        if not title:
            return jsonify({"error": "Field 'title' is required."}), 400

        ticket = create_ticket(settings.db_path, title=title, age_hours=age_hours)
        record_business_event("ticket_created")
        return jsonify({"status": "ok", "ticket": ticket}), 201

    @app.route("/tickets/<int:ticket_id>/close", methods=["POST"])
    @app.route("/tickets/close/<int:ticket_id>", methods=["POST"])
    def tickets_close(ticket_id: int):
        ticket = close_ticket(settings.db_path, ticket_id=ticket_id)
        if not ticket:
            return jsonify({"error": "Ticket not found."}), 404
        record_business_event("ticket_closed")
        return jsonify({"status": "ok", "ticket": ticket})

    @app.route("/tickets/<int:ticket_id>/reopen", methods=["POST"])
    def tickets_reopen(ticket_id: int):
        ticket = reopen_ticket(settings.db_path, ticket_id=ticket_id)
        if not ticket:
            return jsonify({"error": "Ticket not found."}), 404
        record_business_event("ticket_reopened")
        return jsonify({"status": "ok", "ticket": ticket})

    @app.route("/demo/seed", methods=["POST"])
    def demo_seed():
        stats = seed_demo_data(settings.db_path)
        record_business_event("seed_run")
        return jsonify({"status": "ok", "stats": stats})

    @app.get("/demo/error")
    def demo_error():
        return jsonify({"status": "error", "message": "Synthetic 503 for alert demo."}), 503

    @app.get("/demo/slow")
    def demo_slow():
        delay_ms = max(50, min(int(request.args.get("delay_ms", 1200)), 5000))
        time.sleep(delay_ms / 1000)
        return jsonify({"status": "ok", "delay_ms": delay_ms})

    @app.get("/metrics")
    def metrics():
        payload, content_type = render_metrics()
        return Response(payload, mimetype=content_type)

    return app
