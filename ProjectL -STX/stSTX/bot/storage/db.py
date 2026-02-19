from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class BotDB:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def init_schema(self) -> None:
        schema_path = Path(__file__).with_name("schema.sql")
        sql = schema_path.read_text(encoding="utf-8")
        with self.connect() as conn:
            conn.executescript(sql)
            conn.commit()

    def insert_signal(
        self,
        *,
        event_time_utc: str,
        pool_id: str,
        market_stx_per_ststx: float,
        intrinsic_stx_per_ststx: float,
        edge_pct: float,
        abs_edge_pct: float,
        slippage_pct: float,
        net_edge_pct: float,
        action: str,
        should_enter: bool,
        reason: str,
        order_usd: float,
    ) -> int:
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO signals (
                  event_time_utc, pool_id, market_stx_per_ststx, intrinsic_stx_per_ststx,
                  edge_pct, abs_edge_pct, slippage_pct, net_edge_pct,
                  action, should_enter, reason, order_usd
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_time_utc,
                    pool_id,
                    market_stx_per_ststx,
                    intrinsic_stx_per_ststx,
                    edge_pct,
                    abs_edge_pct,
                    slippage_pct,
                    net_edge_pct,
                    action,
                    1 if should_enter else 0,
                    reason,
                    order_usd,
                ),
            )
            conn.commit()
            return int(cur.lastrowid)

    def insert_order(
        self,
        *,
        event_time_utc: str,
        side: str,
        pool_id: str,
        order_size_usd: float,
        status: str,
        signal_id: Optional[int] = None,
        order_id: Optional[str] = None,
        reason: Optional[str] = None,
        txid: Optional[str] = None,
    ) -> int:
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO orders (
                  signal_id, event_time_utc, order_id, side, pool_id,
                  order_size_usd, status, reason, txid
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id,
                    event_time_utc,
                    order_id,
                    side,
                    pool_id,
                    order_size_usd,
                    status,
                    reason,
                    txid,
                ),
            )
            conn.commit()
            return int(cur.lastrowid)

    def update_order_status(self, order_pk: int, *, status: str, txid: Optional[str], reason: Optional[str]) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE orders
                SET status = ?, txid = COALESCE(?, txid), reason = COALESCE(?, reason)
                WHERE id = ?
                """,
                (status, txid, reason, order_pk),
            )
            conn.commit()

    def insert_fill(
        self,
        *,
        order_pk: int,
        event_time_utc: str,
        filled_stx: Optional[float],
        filled_ststx: Optional[float],
        avg_fill_price_stx_per_ststx: Optional[float],
        fee_stx: float,
        slippage_pct: Optional[float],
        trade_pnl_stx: Optional[float],
        running_pnl_stx: Optional[float],
    ) -> int:
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO fills (
                  order_id, event_time_utc, filled_stx, filled_ststx,
                  avg_fill_price_stx_per_ststx, fee_stx, slippage_pct,
                  trade_pnl_stx, running_pnl_stx
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    order_pk,
                    event_time_utc,
                    filled_stx,
                    filled_ststx,
                    avg_fill_price_stx_per_ststx,
                    fee_stx,
                    slippage_pct,
                    trade_pnl_stx,
                    running_pnl_stx,
                ),
            )
            conn.commit()
            return int(cur.lastrowid)

    def upsert_daily_pnl(
        self,
        *,
        day_utc: str,
        start_equity_stx: float,
        running_pnl_stx: float,
        trade_count: int,
        win_count: int,
        loss_count: int,
        end_equity_stx: Optional[float] = None,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO pnl_daily (
                  day_utc, start_equity_stx, end_equity_stx, running_pnl_stx,
                  trade_count, win_count, loss_count, updated_at_utc
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(day_utc) DO UPDATE SET
                  start_equity_stx = excluded.start_equity_stx,
                  end_equity_stx = excluded.end_equity_stx,
                  running_pnl_stx = excluded.running_pnl_stx,
                  trade_count = excluded.trade_count,
                  win_count = excluded.win_count,
                  loss_count = excluded.loss_count,
                  updated_at_utc = excluded.updated_at_utc
                """,
                (
                    day_utc,
                    start_equity_stx,
                    end_equity_stx,
                    running_pnl_stx,
                    trade_count,
                    win_count,
                    loss_count,
                    utc_now_iso(),
                ),
            )
            conn.commit()

    def fetch_daily_pnl(self, day_utc: str) -> Optional[sqlite3.Row]:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT day_utc, start_equity_stx, end_equity_stx, running_pnl_stx,
                       trade_count, win_count, loss_count, updated_at_utc
                FROM pnl_daily
                WHERE day_utc = ?
                LIMIT 1
                """,
                (day_utc,),
            ).fetchone()
            return row

    def insert_alert(
        self,
        *,
        event_time_utc: str,
        event_type: str,
        payload: Any,
        status: str,
        error_message: Optional[str] = None,
    ) -> int:
        payload_json = _to_json(payload)
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO alerts (event_time_utc, event_type, payload_json, status, error_message)
                VALUES (?, ?, ?, ?, ?)
                """,
                (event_time_utc, event_type, payload_json, status, error_message),
            )
            conn.commit()
            return int(cur.lastrowid)

    def fetch_latest_running_pnl_stx(self) -> float:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT running_pnl_stx
                FROM fills
                WHERE running_pnl_stx IS NOT NULL
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
            return float(row["running_pnl_stx"]) if row else 0.0

    def count_orders_by_reason_prefix_for_day(self, day_utc: str, reason_prefix: str) -> int:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM orders
                WHERE event_time_utc LIKE ?
                  AND reason LIKE ?
                """,
                (f"{day_utc}%", f"{reason_prefix}%"),
            ).fetchone()
            return int(row["c"]) if row else 0

    def fetch_latest_order_time_by_reason_prefix(self, reason_prefix: str) -> Optional[str]:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT event_time_utc
                FROM orders
                WHERE reason LIKE ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (f"{reason_prefix}%",),
            ).fetchone()
            return str(row["event_time_utc"]) if row else None


def _to_json(payload: Any) -> str:
    if is_dataclass(payload):
        obj: Dict[str, Any] = asdict(payload)
    elif isinstance(payload, dict):
        obj = payload
    else:
        obj = {"value": str(payload)}
    return json.dumps(obj, ensure_ascii=True, separators=(",", ":"))
