from __future__ import annotations

import requests

from .config import Settings


class InfluxWriter:
    def __init__(self, settings: Settings) -> None:
        self._enabled = settings.influx_enabled
        self._app_name = settings.app_name.replace(" ", "-")
        self._app_env = settings.app_env
        self._url = f"{settings.influx_url.rstrip('/')}/api/v2/write"
        self._params = {
            "org": settings.influx_org,
            "bucket": settings.influx_bucket,
            "precision": "s",
        }
        self._headers = {
            "Authorization": f"Token {settings.influx_token}",
            "Content-Type": "text/plain; charset=utf-8",
        }
        self._session = requests.Session()

    @property
    def enabled(self) -> bool:
        return self._enabled

    def write_stats(self, stats: dict[str, int]) -> bool:
        if not self._enabled:
            return True

        line = (
            f"app_metrics,app={self._app_name},env={self._app_env} "
            f"users_total={stats['users_total']}i,"
            f"tickets_total={stats['tickets_total']}i,"
            f"tickets_open={stats['tickets_open']}i,"
            f"tickets_closed={stats['tickets_closed']}i,"
            f"tickets_overdue={stats['tickets_overdue']}i"
        )

        try:
            response = self._session.post(
                self._url,
                params=self._params,
                data=line.encode("utf-8"),
                headers=self._headers,
                timeout=5,
            )
            response.raise_for_status()
        except requests.RequestException:
            return False
        return True
