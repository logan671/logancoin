import time
from typing import Any

from ..db import get_conn


def create_mirror_order(
    pair_id: int,
    trade_signal_id: int,
    requested_notional_usdc: float,
    adjusted_notional_usdc: float,
    status: str,
    blocked_reason: str | None = None,
) -> int:
    now = int(time.time())
    idempotency_key = f"pair:{pair_id}:signal:{trade_signal_id}"
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO mirror_orders(
              pair_id, trade_signal_id, requested_notional_usdc,
              min_order_size_usdc, adjusted_notional_usdc, expected_slippage_bps,
              status, blocked_reason, executor_ref, idempotency_key,
              created_at, updated_at
            ) VALUES (?, ?, ?, NULL, ?, NULL, ?, ?, NULL, ?, ?, ?)
            """,
            (
                pair_id,
                trade_signal_id,
                requested_notional_usdc,
                adjusted_notional_usdc,
                status,
                blocked_reason,
                idempotency_key,
                now,
                now,
            ),
        )
    return int(cur.lastrowid)


def list_recent_mirror_orders(limit: int = 20) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT
              id,
              pair_id,
              trade_signal_id,
              requested_notional_usdc,
              adjusted_notional_usdc,
              status,
              blocked_reason,
              created_at
            FROM mirror_orders
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def list_queued_mirror_orders(limit: int = 50) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT
              m.id,
              m.pair_id,
              m.trade_signal_id,
              m.adjusted_notional_usdc,
              m.blocked_reason,
              t.tx_hash AS source_tx_hash,
              t.side,
              t.outcome,
              t.market_slug,
              t.token_id,
              t.source_price,
              p.follower_wallet_id,
              p.max_slippage_bps,
              s.address AS source_address,
              f.address AS follower_address,
              f.key_ref,
              f.budget_usdc
            FROM mirror_orders m
            JOIN trade_signals t ON t.id = m.trade_signal_id
            JOIN wallet_pairs p ON p.id = m.pair_id
            JOIN source_wallets s ON s.id = t.source_wallet_id
            JOIN follower_wallets f ON f.id = p.follower_wallet_id
            WHERE m.status = 'queued'
            ORDER BY m.id ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def list_stale_sent_mirror_orders(max_age_seconds: int, limit: int = 100) -> list[dict[str, Any]]:
    cutoff = int(time.time()) - max(max_age_seconds, 0)
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT
              m.id,
              m.pair_id,
              m.trade_signal_id,
              m.blocked_reason,
              m.executor_ref,
              t.side,
              t.outcome,
              p.follower_wallet_id,
              f.address AS follower_address,
              f.key_ref,
              m.updated_at
            FROM mirror_orders m
            JOIN trade_signals t ON t.id = m.trade_signal_id
            JOIN wallet_pairs p ON p.id = m.pair_id
            JOIN follower_wallets f ON f.id = p.follower_wallet_id
            WHERE m.status = 'sent'
              AND m.executor_ref IS NOT NULL
              AND m.updated_at <= ?
            ORDER BY m.id ASC
            LIMIT ?
            """,
            (cutoff, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def mark_mirror_order_status(order_id: int, status: str, blocked_reason: str | None = None) -> None:
    now = int(time.time())
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE mirror_orders
            SET status=?, blocked_reason=?, updated_at=?
            WHERE id=?
            """,
            (status, blocked_reason, now, order_id),
        )


def set_mirror_order_executor_ref(order_id: int, executor_ref: str) -> None:
    now = int(time.time())
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE mirror_orders
            SET executor_ref=?, updated_at=?
            WHERE id=?
            """,
            (executor_ref, now, order_id),
        )


def create_execution_record(
    mirror_order_id: int,
    pair_id: int,
    follower_wallet_id: int,
    executed_side: str,
    executed_outcome: str | None,
    executed_price: float | None,
    executed_notional_usdc: float | None,
    status: str,
    chain_tx_hash: str | None = None,
    fail_reason: str | None = None,
) -> int:
    now = int(time.time())
    tx_hash = chain_tx_hash
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO executions(
              mirror_order_id, pair_id, follower_wallet_id, chain_tx_hash,
              executed_side, executed_outcome, executed_price, executed_notional_usdc,
              fee_usdc, pnl_realized_usdc, status, fail_reason, executed_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?, ?, ?)
            """,
            (
                mirror_order_id,
                pair_id,
                follower_wallet_id,
                tx_hash,
                executed_side,
                executed_outcome,
                executed_price,
                executed_notional_usdc,
                status,
                fail_reason,
                now,
                now,
            ),
        )
    return int(cur.lastrowid)


def consume_follower_budget(follower_wallet_id: int, amount_usdc: float) -> None:
    now = int(time.time())
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE follower_wallets
            SET budget_usdc = CASE
              WHEN budget_usdc - ? < 0 THEN 0
              ELSE budget_usdc - ?
            END,
            updated_at = ?
            WHERE id = ?
            """,
            (amount_usdc, amount_usdc, now, follower_wallet_id),
        )


def list_recent_executions(limit: int = 20) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT
              id,
              mirror_order_id,
              pair_id,
              follower_wallet_id,
              chain_tx_hash,
              executed_side,
              executed_outcome,
              executed_price,
              executed_notional_usdc,
              status,
              fail_reason,
              executed_at
            FROM executions
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def has_recent_balance_or_allowance_failure(pair_id: int, within_seconds: int) -> bool:
    cutoff = int(time.time()) - max(within_seconds, 0)
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT 1
            FROM executions
            WHERE pair_id = ?
              AND status = 'failed'
              AND COALESCE(executed_at, created_at) >= ?
              AND (
                lower(COALESCE(fail_reason, '')) LIKE '%not enough balance / allowance%'
                OR lower(COALESCE(fail_reason, '')) LIKE '%insufficient_balance%'
              )
            ORDER BY id DESC
            LIMIT 1
            """,
            (pair_id, cutoff),
        ).fetchone()
    return row is not None


def has_filled_buy_for_pair_token(pair_id: int, token_id: str | None) -> bool:
    if not token_id:
        return False
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT 1
            FROM executions e
            JOIN mirror_orders m ON m.id = e.mirror_order_id
            JOIN trade_signals t ON t.id = m.trade_signal_id
            WHERE e.pair_id = ?
              AND e.status = 'filled'
              AND lower(COALESCE(e.executed_side, '')) = 'buy'
              AND t.token_id = ?
            ORDER BY e.id DESC
            LIMIT 1
            """,
            (pair_id, token_id),
        ).fetchone()
    return row is not None
