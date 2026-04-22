from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def env_bool(name: str, default: bool = False) -> bool:
    raw_value = os.getenv(name, "1" if default else "0")
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_env: str
    db_path: Path
    overdue_after_hours: int
    influx_enabled: bool
    influx_url: str
    influx_token: str
    influx_org: str
    influx_bucket: str
    log_level: str
    json_logs: bool
    tracing_enabled: bool
    otel_service_name: str
    otel_exporter_otlp_endpoint: str
    request_id_header: str

    @classmethod
    def from_env(cls) -> "Settings":
        base_dir = Path(__file__).resolve().parent.parent
        default_db_path = base_dir / "data" / "app.db"

        return cls(
            app_name=os.getenv("APP_NAME", "monitoring-stack-demo"),
            app_env=os.getenv("APP_ENV", "dev"),
            db_path=Path(os.getenv("APP_DB_PATH", str(default_db_path))),
            overdue_after_hours=int(os.getenv("TICKET_OVERDUE_AFTER_HOURS", "24")),
            influx_enabled=env_bool("INFLUX_ENABLED", True),
            influx_url=os.getenv("INFLUX_URL", "http://influxdb:8086"),
            influx_token=os.getenv("INFLUX_TOKEN", "supersecrettoken"),
            influx_org=os.getenv("INFLUX_ORG", "my-org"),
            influx_bucket=os.getenv("INFLUX_BUCKET", "app"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            json_logs=env_bool("JSON_LOGS", True),
            tracing_enabled=env_bool("OTEL_TRACING_ENABLED", True),
            otel_service_name=os.getenv("OTEL_SERVICE_NAME", "monitoring-stack-demo"),
            otel_exporter_otlp_endpoint=os.getenv(
                "OTEL_EXPORTER_OTLP_ENDPOINT",
                "http://otel-collector:4318",
            ),
            request_id_header=os.getenv("REQUEST_ID_HEADER", "X-Request-ID"),
        )
