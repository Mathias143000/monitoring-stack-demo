from __future__ import annotations

from pathlib import Path

import pytest

from monitoring_demo import create_app
from monitoring_demo.config import Settings


@pytest.fixture()
def client(tmp_path: Path):
    settings = Settings(
        app_name="monitoring-stack-demo-test",
        app_env="test",
        db_path=tmp_path / "test.db",
        overdue_after_hours=24,
        influx_enabled=False,
        influx_url="http://influxdb:8086",
        influx_token="token",
        influx_org="org",
        influx_bucket="bucket",
        log_level="INFO",
    )
    app = create_app(settings)
    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client


def test_health_endpoint_reports_database_status(client):
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["database"] == "ok"
    assert payload["influx_export"] == "disabled"


def test_seed_endpoint_is_idempotent_and_populates_stats(client):
    first = client.post("/demo/seed")
    second = client.post("/demo/seed")

    assert first.status_code == 200
    assert second.status_code == 200

    payload = client.get("/health").get_json()
    assert payload["stats"]["users_total"] == 3
    assert payload["stats"]["tickets_total"] == 4
    assert payload["stats"]["tickets_overdue"] >= 1


def test_ticket_lifecycle_and_listing(client):
    created = client.post("/tickets", json={"title": "Observe me", "age_hours": 30})
    assert created.status_code == 201
    ticket_id = created.get_json()["ticket"]["id"]

    tickets = client.get("/tickets").get_json()["items"]
    assert any(ticket["title"] == "Observe me" and ticket["is_overdue"] for ticket in tickets)

    closed = client.post(f"/tickets/{ticket_id}/close")
    assert closed.status_code == 200
    assert closed.get_json()["ticket"]["status"] == "closed"

    reopened = client.post(f"/tickets/{ticket_id}/reopen")
    assert reopened.status_code == 200
    assert reopened.get_json()["ticket"]["status"] == "open"


def test_metrics_endpoint_exposes_custom_metrics(client):
    client.post("/users", json={"name": "alice"})
    client.post("/tickets", json={"title": "Synthetic issue"})

    response = client.get("/metrics")
    payload = response.data.decode("utf-8")

    assert response.status_code == 200
    assert "app_users_total" in payload
    assert "app_tickets_total" in payload
    assert "app_users_created_total" in payload
    assert "app_http_requests_total" in payload


def test_demo_error_endpoint_returns_503(client):
    response = client.get("/demo/error")

    assert response.status_code == 503
    assert response.get_json()["status"] == "error"
