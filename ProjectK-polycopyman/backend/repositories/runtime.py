import json
import os
import time
from typing import Any

from ..config import DB_PATH
from ..db import get_conn


def _ensure_table() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS service_runtime (
                component TEXT PRIMARY KEY,
                pid INTEGER NOT NULL,
                db_path TEXT NOT NULL,
                updated_at INTEGER NOT NULL,
                extra_json TEXT
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_service_runtime_updated ON service_runtime (updated_at DESC)")


def heartbeat(component: str, extra: dict[str, Any] | None = None) -> None:
    _ensure_table()
    now = int(time.time())
    payload = json.dumps(extra, ensure_ascii=True, separators=(",", ":")) if extra else None
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO service_runtime(component, pid, db_path, updated_at, extra_json)
            VALUES(?, ?, ?, ?, ?)
            ON CONFLICT(component) DO UPDATE SET
              pid=excluded.pid,
              db_path=excluded.db_path,
              updated_at=excluded.updated_at,
              extra_json=excluded.extra_json
            """,
            (component, os.getpid(), DB_PATH, now, payload),
        )


def list_runtime_services() -> list[dict[str, Any]]:
    _ensure_table()
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT component, pid, db_path, updated_at, extra_json
            FROM service_runtime
            ORDER BY component ASC
            """
        ).fetchall()
    return [dict(row) for row in rows]
