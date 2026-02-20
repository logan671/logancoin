import time
import uuid
from typing import Any

from ..db import get_conn


def _get_source_wallet_id(address: str) -> int | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM source_wallets WHERE address=?",
            (address.lower(),),
        ).fetchone()
    return int(row["id"]) if row else None


def create_mock_signal(
    source_address: str,
    side: str,
    source_notional_usdc: float,
    source_price: float | None,
    market_slug: str | None,
    token_id: str | None,
    outcome: str | None,
) -> int:
    source_wallet_id = _get_source_wallet_id(source_address)
    if source_wallet_id is None:
        raise ValueError("source_wallet_not_found")

    now = int(time.time())
    tx_hash = f"mock-{uuid.uuid4().hex}"
    idempotency_key = f"mock:{source_wallet_id}:{tx_hash}:-1"
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO trade_signals(
              source_wallet_id, chain_id, tx_hash, log_index, block_number,
              market_slug, token_id, outcome, side,
              source_notional_usdc, source_price, idempotency_key,
              observed_at, created_at
            ) VALUES (?, 137, ?, -1, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_wallet_id,
                tx_hash,
                market_slug,
                token_id,
                outcome,
                side,
                source_notional_usdc,
                source_price,
                idempotency_key,
                now,
                now,
            ),
        )
    return int(cur.lastrowid)


def list_active_source_wallet_addresses() -> list[str]:
    query = """
    SELECT DISTINCT s.address
    FROM source_wallets s
    JOIN wallet_pairs p ON p.source_wallet_id = s.id
    WHERE p.active = 1
    """
    with get_conn() as conn:
        rows = conn.execute(query).fetchall()
    return [str(row["address"]).lower() for row in rows]


def create_chain_signal(
    source_address: str,
    tx_hash: str,
    log_index: int,
    block_number: int,
    side: str,
    source_notional_usdc: float,
    source_price: float | None,
    token_id: str | None,
    outcome: str | None = None,
    market_slug: str | None = None,
    chain_id: int = 137,
) -> int | None:
    source_wallet_id = _get_source_wallet_id(source_address)
    if source_wallet_id is None:
        return None

    now = int(time.time())
    idem = f"chain:{chain_id}:{source_wallet_id}:{tx_hash}:{log_index}"
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO trade_signals(
              source_wallet_id, chain_id, tx_hash, log_index, block_number,
              market_slug, token_id, outcome, side,
              source_notional_usdc, source_price, idempotency_key,
              observed_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_wallet_id,
                chain_id,
                tx_hash,
                log_index,
                block_number,
                market_slug,
                token_id,
                outcome,
                side.lower(),
                source_notional_usdc,
                source_price,
                idem,
                now,
                now,
            ),
        )
    inserted_id = int(cur.lastrowid or 0)
    return inserted_id if inserted_id > 0 else None


def list_recent_signals(limit: int = 20) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT
              t.id,
              s.address AS source_address,
              t.side,
              t.source_notional_usdc,
              t.source_price,
              t.market_slug,
              t.created_at
            FROM trade_signals t
            JOIN source_wallets s ON s.id = t.source_wallet_id
            ORDER BY t.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def list_unmirrored_signals(limit: int = 50) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT
              t.id AS trade_signal_id,
              t.source_wallet_id,
              t.side,
              t.token_id,
              t.source_notional_usdc,
              t.source_price,
              p.id AS pair_id,
              s.source_portfolio_usdc,
              p.min_order_usdc,
              p.max_order_usdc,
              f.budget_usdc
            FROM trade_signals t
            JOIN source_wallets s
              ON s.id = t.source_wallet_id
            JOIN wallet_pairs p
              ON p.source_wallet_id = t.source_wallet_id
             AND p.active = 1
            JOIN follower_wallets f
              ON f.id = p.follower_wallet_id
            LEFT JOIN mirror_orders m
              ON m.trade_signal_id = t.id
             AND m.pair_id = p.id
            WHERE m.id IS NULL
              AND t.created_at >= p.created_at
            ORDER BY t.id ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]
