from __future__ import annotations

import sqlite3
from pathlib import Path
from datetime import datetime

from .compat import UTC, dataclass


@dataclass(slots=True)
class Observation:
    ts: datetime
    coin: str
    odds: float | None
    price: float | None
    momentum_5m: float | None
    would_trade: bool
    actual_result: str | None = None


def _normalize_ts(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC)


def init_db(db_path: str) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                coin TEXT NOT NULL,
                odds REAL,
                price REAL,
                momentum_5m REAL,
                would_trade INTEGER NOT NULL,
                actual_result TEXT
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_observations_ts ON observations(ts)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_observations_coin ON observations(coin)"
        )


def log_observation(db_path: str, obs: Observation) -> None:
    normalized_ts = _normalize_ts(obs.ts).isoformat()
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO observations
                (ts, coin, odds, price, momentum_5m, would_trade, actual_result)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                normalized_ts,
                obs.coin.upper(),
                obs.odds,
                obs.price,
                obs.momentum_5m,
                1 if obs.would_trade else 0,
                obs.actual_result,
            ),
        )
