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
    pnl: float | None = None
    filled: bool | None = None
    fill_price: float | None = None
    market_slug: str | None = None
    condition_id: str | None = None
    token_id: str | None = None
    side: str | None = None
    entry_odds: float | None = None
    bet_size: float | None = None
    reason: str | None = None


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
                actual_result TEXT,
                pnl REAL,
                filled INTEGER,
                fill_price REAL,
                market_slug TEXT,
                condition_id TEXT,
                token_id TEXT,
                side TEXT,
                entry_odds REAL,
                bet_size REAL,
                reason TEXT
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_observations_ts ON observations(ts)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_observations_coin ON observations(coin)"
        )
        _ensure_columns(conn)


def _ensure_columns(conn: sqlite3.Connection) -> None:
    existing = {row[1] for row in conn.execute("PRAGMA table_info(observations)")}
    wanted = {
        "actual_result": "TEXT",
        "pnl": "REAL",
        "filled": "INTEGER",
        "fill_price": "REAL",
        "market_slug": "TEXT",
        "condition_id": "TEXT",
        "token_id": "TEXT",
        "side": "TEXT",
        "entry_odds": "REAL",
        "bet_size": "REAL",
        "reason": "TEXT",
    }
    for column, col_type in wanted.items():
        if column not in existing:
            conn.execute(f"ALTER TABLE observations ADD COLUMN {column} {col_type}")


def log_observation(db_path: str, obs: Observation) -> None:
    normalized_ts = _normalize_ts(obs.ts).isoformat()
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO observations
                (ts, coin, odds, price, momentum_5m, would_trade, actual_result, pnl,
                 filled, fill_price, market_slug, condition_id, token_id, side, entry_odds,
                 bet_size, reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                normalized_ts,
                obs.coin.upper(),
                obs.odds,
                obs.price,
                obs.momentum_5m,
                1 if obs.would_trade else 0,
                obs.actual_result,
                obs.pnl,
                None if obs.filled is None else (1 if obs.filled else 0),
                obs.fill_price,
                obs.market_slug,
                obs.condition_id,
                obs.token_id,
                obs.side,
                obs.entry_odds,
                obs.bet_size,
                obs.reason,
            ),
        )
