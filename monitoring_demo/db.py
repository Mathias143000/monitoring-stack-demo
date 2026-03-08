from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def utcnow_iso() -> str:
    return utcnow().isoformat(timespec="seconds")


def _connect(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def _ensure_column(
    connection: sqlite3.Connection,
    table_name: str,
    column_name: str,
    ddl: str,
) -> None:
    existing_columns = {
        row["name"] for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    if column_name not in existing_columns:
        connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {ddl}")


def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with _connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT ''
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT ''
            )
            """
        )

        _ensure_column(connection, "users", "created_at", "created_at TEXT NOT NULL DEFAULT ''")
        _ensure_column(connection, "tickets", "created_at", "created_at TEXT NOT NULL DEFAULT ''")
        _ensure_column(connection, "tickets", "updated_at", "updated_at TEXT NOT NULL DEFAULT ''")

        now = utcnow_iso()
        connection.execute("UPDATE users SET created_at = ? WHERE created_at = ''", (now,))
        connection.execute(
            (
                "UPDATE tickets SET created_at = ?, updated_at = ? "
                "WHERE created_at = '' OR updated_at = ''"
            ),
            (now, now),
        )


def ping_db(db_path: Path) -> bool:
    try:
        with _connect(db_path) as connection:
            connection.execute("SELECT 1").fetchone()
    except sqlite3.Error:
        return False
    return True


def create_user(db_path: Path, *, name: str) -> dict[str, object]:
    created_at = utcnow_iso()
    with _connect(db_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO users (name, created_at)
            VALUES (?, ?)
            ON CONFLICT(name) DO UPDATE SET name = excluded.name
            RETURNING id, name, created_at
            """,
            (name, created_at),
        )
        row = cursor.fetchone()
    return dict(row)


def list_users(db_path: Path, *, limit: int = 50) -> list[dict[str, object]]:
    with _connect(db_path) as connection:
        rows = connection.execute(
            "SELECT id, name, created_at FROM users ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def create_ticket(db_path: Path, *, title: str, age_hours: int = 0) -> dict[str, object]:
    created_at = (utcnow() - timedelta(hours=age_hours)).isoformat(timespec="seconds")
    with _connect(db_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO tickets (title, status, created_at, updated_at)
            VALUES (?, 'open', ?, ?)
            RETURNING id, title, status, created_at, updated_at
            """,
            (title, created_at, created_at),
        )
        row = cursor.fetchone()
    return dict(row)


def _update_ticket_status(
    db_path: Path,
    *,
    ticket_id: int,
    status: str,
) -> dict[str, object] | None:
    updated_at = utcnow_iso()
    with _connect(db_path) as connection:
        cursor = connection.execute(
            """
            UPDATE tickets
            SET status = ?, updated_at = ?
            WHERE id = ?
            RETURNING id, title, status, created_at, updated_at
            """,
            (status, updated_at, ticket_id),
        )
        row = cursor.fetchone()
    return dict(row) if row else None


def close_ticket(db_path: Path, *, ticket_id: int) -> dict[str, object] | None:
    return _update_ticket_status(db_path, ticket_id=ticket_id, status="closed")


def reopen_ticket(db_path: Path, *, ticket_id: int) -> dict[str, object] | None:
    return _update_ticket_status(db_path, ticket_id=ticket_id, status="open")


def list_tickets(
    db_path: Path,
    *,
    overdue_after_hours: int,
    status: str | None = None,
    limit: int = 50,
) -> list[dict[str, object]]:
    query = """
        SELECT id, title, status, created_at, updated_at
        FROM tickets
    """
    parameters: list[object] = []
    if status:
        query += " WHERE status = ?"
        parameters.append(status)
    query += " ORDER BY created_at DESC LIMIT ?"
    parameters.append(limit)

    threshold = utcnow() - timedelta(hours=overdue_after_hours)
    with _connect(db_path) as connection:
        rows = connection.execute(query, parameters).fetchall()

    items: list[dict[str, object]] = []
    for row in rows:
        item = dict(row)
        item["is_overdue"] = (
            item["status"] == "open"
            and datetime.fromisoformat(item["created_at"]) < threshold
        )
        items.append(item)
    return items


def get_app_stats(db_path: Path, *, overdue_after_hours: int) -> dict[str, int]:
    threshold = (utcnow() - timedelta(hours=overdue_after_hours)).isoformat(timespec="seconds")

    with _connect(db_path) as connection:
        users_total = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        tickets_total = connection.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
        tickets_open = connection.execute(
            "SELECT COUNT(*) FROM tickets WHERE status = 'open'"
        ).fetchone()[0]
        tickets_closed = connection.execute(
            "SELECT COUNT(*) FROM tickets WHERE status = 'closed'"
        ).fetchone()[0]
        tickets_overdue = connection.execute(
            """
            SELECT COUNT(*)
            FROM tickets
            WHERE status = 'open' AND created_at < ?
            """,
            (threshold,),
        ).fetchone()[0]

    return {
        "users_total": users_total,
        "tickets_total": tickets_total,
        "tickets_open": tickets_open,
        "tickets_closed": tickets_closed,
        "tickets_overdue": tickets_overdue,
    }


def seed_demo_data(db_path: Path) -> dict[str, int]:
    for username in ("alex", "maria", "support"):
        create_user(db_path, name=username)

    demo_tickets = [
        ("VPN access is not working", 6, "open"),
        ("Grafana dashboard review", 2, "open"),
        ("Production incident retrospective", 36, "open"),
        ("Printer issue on floor 2", 48, "closed"),
    ]

    with _connect(db_path) as connection:
        for title, age_hours, status in demo_tickets:
            existing = connection.execute(
                "SELECT id FROM tickets WHERE title = ?",
                (title,),
            ).fetchone()
            if existing:
                continue

            created_at = (utcnow() - timedelta(hours=age_hours)).isoformat(timespec="seconds")
            connection.execute(
                """
                INSERT INTO tickets (title, status, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (title, status, created_at, created_at),
            )

    return get_app_stats(db_path, overdue_after_hours=24)
