from __future__ import annotations

from monitoring_demo.config import Settings
from monitoring_demo.influx import InfluxWriter


def write_app_metrics(
    *,
    users_total: int,
    tickets_open: int,
    tickets_total: int,
    tickets_closed: int = 0,
    tickets_overdue: int = 0,
) -> bool:
    writer = InfluxWriter(Settings.from_env())
    return writer.write_stats(
        {
            "users_total": users_total,
            "tickets_total": tickets_total,
            "tickets_open": tickets_open,
            "tickets_closed": tickets_closed,
            "tickets_overdue": tickets_overdue,
        }
    )
