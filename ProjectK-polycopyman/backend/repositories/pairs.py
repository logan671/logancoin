import sqlite3
import time
from typing import Any

from ..db import get_conn
from .vault import key_ref_exists


def list_pairs() -> list[dict[str, Any]]:
    query = """
    SELECT
      p.id,
      p.mode,
      p.active,
      p.max_slippage_bps,
      p.max_consecutive_failures,
      s.address AS source_address,
      s.alias AS source_alias,
      f.address AS follower_address,
      f.label AS follower_label,
      f.budget_usdc,
      f.initial_matic,
      f.min_matic_alert,
      COALESCE((
        SELECT SUM(t.source_notional_usdc)
        FROM trade_signals t
        WHERE t.source_wallet_id = p.source_wallet_id
      ), 0) AS cumulative_source_volume_usdc
    FROM wallet_pairs p
    JOIN source_wallets s ON s.id = p.source_wallet_id
    JOIN follower_wallets f ON f.id = p.follower_wallet_id
    ORDER BY p.id ASC
    """
    with get_conn() as conn:
        rows = conn.execute(query).fetchall()
    return [dict(row) for row in rows]


def get_pair(pair_id: int) -> dict[str, Any] | None:
    query = """
    SELECT
      p.id,
      p.mode,
      p.active,
      p.max_slippage_bps,
      p.max_consecutive_failures,
      s.address AS source_address,
      s.alias AS source_alias,
      f.address AS follower_address,
      f.label AS follower_label,
      f.budget_usdc,
      f.initial_matic,
      f.min_matic_alert,
      COALESCE((
        SELECT SUM(t.source_notional_usdc)
        FROM trade_signals t
        WHERE t.source_wallet_id = p.source_wallet_id
      ), 0) AS cumulative_source_volume_usdc
    FROM wallet_pairs p
    JOIN source_wallets s ON s.id = p.source_wallet_id
    JOIN follower_wallets f ON f.id = p.follower_wallet_id
    WHERE p.id = ?
    """
    with get_conn() as conn:
        row = conn.execute(query, (pair_id,)).fetchone()
    return dict(row) if row else None


def _ensure_source_wallet(conn: sqlite3.Connection, address: str, alias: str | None) -> int:
    now = int(time.time())
    row = conn.execute("SELECT id FROM source_wallets WHERE address=?", (address,)).fetchone()
    if row:
        source_id = int(row["id"])
        if alias:
            conn.execute(
                "UPDATE source_wallets SET alias=?, updated_at=? WHERE id=?",
                (alias, now, source_id),
            )
        return source_id
    cur = conn.execute(
        """
        INSERT INTO source_wallets(address, alias, status, created_at, updated_at)
        VALUES(?, ?, 'active', ?, ?)
        """,
        (address, alias, now, now),
    )
    return int(cur.lastrowid)


def _ensure_follower_wallet(
    conn: sqlite3.Connection,
    address: str,
    label: str | None,
    budget_usdc: float,
    initial_matic: float,
    min_matic_alert: float,
    key_ref: str,
) -> int:
    now = int(time.time())
    if not key_ref_exists(key_ref):
        raise ValueError(f"key_ref not found in vault: {key_ref}")
    row = conn.execute("SELECT id FROM follower_wallets WHERE address=?", (address,)).fetchone()
    if row:
        follower_id = int(row["id"])
        conn.execute(
            """
            UPDATE follower_wallets
            SET label=?, budget_usdc=?, initial_matic=?, min_matic_alert=?, key_ref=?, updated_at=?
            WHERE id=?
            """,
            (label, budget_usdc, initial_matic, min_matic_alert, key_ref, now, follower_id),
        )
        return follower_id
    cur = conn.execute(
        """
        INSERT INTO follower_wallets(
          address, label, budget_usdc, initial_matic, min_matic_alert, key_ref, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?)
        """,
        (address, label, budget_usdc, initial_matic, min_matic_alert, key_ref, now, now),
    )
    return int(cur.lastrowid)


def create_pair(
    source_address: str,
    follower_address: str,
    source_alias: str | None,
    follower_label: str | None,
    budget_usdc: float,
    key_ref: str,
    mode: str,
    active: int,
    min_order_usdc: float,
    max_order_usdc: float | None,
    max_slippage_bps: int,
    max_consecutive_failures: int,
    rpc_error_threshold: int,
    initial_matic: float = 3.0,
    min_matic_alert: float = 0.5,
) -> int:
    now = int(time.time())
    with get_conn() as conn:
        source_id = _ensure_source_wallet(conn, source_address, source_alias)
        follower_id = _ensure_follower_wallet(
            conn=conn,
            address=follower_address,
            label=follower_label,
            budget_usdc=budget_usdc,
            initial_matic=initial_matic,
            min_matic_alert=min_matic_alert,
            key_ref=key_ref,
        )
        cur = conn.execute(
            """
            INSERT INTO wallet_pairs(
              source_wallet_id, follower_wallet_id, mode, active, sizing_policy,
              min_order_usdc, max_order_usdc, max_slippage_bps,
              max_consecutive_failures, rpc_error_threshold, created_at, updated_at
            ) VALUES (?, ?, ?, ?, 'proportional', ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_id,
                follower_id,
                mode,
                active,
                min_order_usdc,
                max_order_usdc,
                max_slippage_bps,
                max_consecutive_failures,
                rpc_error_threshold,
                now,
                now,
            ),
        )
        return int(cur.lastrowid)


def delete_pair(pair_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM wallet_pairs WHERE id=?", (pair_id,))
    return int(cur.rowcount or 0) > 0
