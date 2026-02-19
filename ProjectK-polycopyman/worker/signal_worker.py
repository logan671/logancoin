import logging
import time

from backend.config import EXECUTOR_MODE, EXECUTOR_POLL_SECONDS
from backend.db import get_conn
from backend.notifier import send_telegram_message
from backend.repositories.orders import (
    consume_follower_budget,
    create_execution_record,
    create_mirror_order,
    list_queued_mirror_orders,
    mark_mirror_order_status,
    set_mirror_order_executor_ref,
)
from backend.repositories.runtime import heartbeat
from backend.repositories.signals import list_unmirrored_signals
from worker.executor import build_executor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
EXECUTOR = build_executor()


def _notify_failed_execution(
    order_id: int,
    pair_id: int,
    follower_wallet_id: int,
    side: str,
    outcome: str | None,
    notional: float,
    fail_reason: str,
) -> None:
    message = (
        "ProjectK execution failed\n"
        f"pair_id: {pair_id}\n"
        f"order_id: {order_id}\n"
        f"follower_wallet_id: {follower_wallet_id}\n"
        f"side: {side}\n"
        f"outcome: {outcome or '-'}\n"
        f"notional_usdc: {notional:.4f}\n"
        f"fail_reason: {fail_reason}"
    )
    sent = send_telegram_message(message)
    if not sent:
        logging.warning("telegram_alert_skipped_or_failed order_id=%s reason=%s", order_id, fail_reason)


def _notify_blocked_order(
    pair_id: int,
    trade_signal_id: int,
    requested_notional: float,
    blocked_reason: str,
) -> None:
    message = (
        "ProjectK order blocked\n"
        f"pair_id: {pair_id}\n"
        f"trade_signal_id: {trade_signal_id}\n"
        f"requested_notional_usdc: {requested_notional:.4f}\n"
        f"blocked_reason: {blocked_reason}"
    )
    sent = send_telegram_message(message)
    if not sent:
        logging.warning("telegram_alert_skipped_or_failed pair_id=%s reason=%s", pair_id, blocked_reason)


def _notify_filled_execution(
    order_id: int,
    pair_id: int,
    follower_wallet_id: int,
    side: str,
    outcome: str | None,
    notional: float,
    chain_tx_hash: str | None,
) -> None:
    message = (
        "ProjectK execution filled\n"
        f"pair_id: {pair_id}\n"
        f"order_id: {order_id}\n"
        f"follower_wallet_id: {follower_wallet_id}\n"
        f"side: {side}\n"
        f"outcome: {outcome or '-'}\n"
        f"notional_usdc: {notional:.4f}\n"
        f"tx_hash: {chain_tx_hash or '-'}"
    )
    sent = send_telegram_message(message)
    if not sent:
        logging.warning("telegram_alert_skipped_or_failed order_id=%s reason=filled", order_id)


def active_pair_count() -> int:
    with get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) AS cnt FROM wallet_pairs WHERE active=1").fetchone()
    return int(row["cnt"])


def _calc_adjusted_notional(
    source_notional: float,
    min_order_usdc: float,
    max_order_usdc: float | None,
    follower_budget_usdc: float,
    source_price: float | None,
) -> float:
    adjusted = max(source_notional, min_order_usdc)
    if max_order_usdc is not None:
        adjusted = min(adjusted, max_order_usdc)
    if follower_budget_usdc >= adjusted:
        return adjusted

    # Fallback: if budget is short, try buying at least one share.
    if source_price is not None and source_price > 0 and follower_budget_usdc >= source_price:
        return source_price

    # If one share is not affordable, use remaining budget (or 0 => blocked).
    return max(min(adjusted, follower_budget_usdc), 0.0)


def process_once() -> int:
    pending = list_unmirrored_signals(limit=100)
    created = 0
    for row in pending:
        requested = float(row["source_notional_usdc"])
        min_order = float(row["min_order_usdc"] or 1.0)
        budget = float(row["budget_usdc"] or 0.0)
        source_price = float(row["source_price"]) if row["source_price"] is not None else None
        max_order = row["max_order_usdc"]
        max_order_val = float(max_order) if max_order is not None else None
        adjusted = _calc_adjusted_notional(
            source_notional=requested,
            min_order_usdc=min_order,
            max_order_usdc=max_order_val,
            follower_budget_usdc=budget,
            source_price=source_price,
        )
        if adjusted <= 0:
            blocked_reason = "insufficient_budget_for_one_share"
            create_mirror_order(
                pair_id=int(row["pair_id"]),
                trade_signal_id=int(row["trade_signal_id"]),
                requested_notional_usdc=requested,
                adjusted_notional_usdc=0.0,
                status="blocked",
                blocked_reason=blocked_reason,
            )
            _notify_blocked_order(
                pair_id=int(row["pair_id"]),
                trade_signal_id=int(row["trade_signal_id"]),
                requested_notional=requested,
                blocked_reason=blocked_reason,
            )
            continue
        create_mirror_order(
            pair_id=int(row["pair_id"]),
            trade_signal_id=int(row["trade_signal_id"]),
            requested_notional_usdc=requested,
            adjusted_notional_usdc=adjusted,
            status="queued",
        )
        created += 1
    return created


def process_executor_once() -> tuple[int, int]:
    queued = list_queued_mirror_orders(limit=100)
    filled = 0
    failed = 0
    for row in queued:
        order_id = int(row["id"])
        pair_id = int(row["pair_id"])
        follower_wallet_id = int(row["follower_wallet_id"])
        side = str(row["side"])
        outcome = row["outcome"]
        price = row["source_price"]
        notional = float(row["adjusted_notional_usdc"])

        mark_mirror_order_status(order_id, "sent", None)
        result = EXECUTOR.execute(row)
        if result.executor_ref:
            set_mirror_order_executor_ref(order_id=order_id, executor_ref=result.executor_ref)

        if result.status == "filled":
            mark_mirror_order_status(order_id, "filled", None)
            create_execution_record(
                mirror_order_id=order_id,
                pair_id=pair_id,
                follower_wallet_id=follower_wallet_id,
                executed_side=side,
                executed_outcome=outcome,
                executed_price=result.executed_price if result.executed_price is not None else (float(price) if price is not None else None),
                executed_notional_usdc=notional,
                status="filled",
                chain_tx_hash=result.chain_tx_hash,
                fail_reason=None,
            )
            consume_follower_budget(follower_wallet_id, notional)
            _notify_filled_execution(
                order_id=order_id,
                pair_id=pair_id,
                follower_wallet_id=follower_wallet_id,
                side=side,
                outcome=outcome,
                notional=notional,
                chain_tx_hash=result.chain_tx_hash,
            )
            filled += 1
        else:
            fail_reason = result.fail_reason or "executor_failed"
            mark_mirror_order_status(order_id, "failed", fail_reason)
            create_execution_record(
                mirror_order_id=order_id,
                pair_id=pair_id,
                follower_wallet_id=follower_wallet_id,
                executed_side=side,
                executed_outcome=outcome,
                executed_price=float(price) if price is not None else None,
                executed_notional_usdc=notional,
                status="failed",
                fail_reason=fail_reason,
            )
            _notify_failed_execution(
                order_id=order_id,
                pair_id=pair_id,
                follower_wallet_id=follower_wallet_id,
                side=side,
                outcome=outcome,
                notional=notional,
                fail_reason=fail_reason,
            )
            failed += 1
    return filled, failed


def run(poll_seconds: int = 10) -> None:
    while True:
        heartbeat("worker")
        cnt = active_pair_count()
        created = process_once()
        filled, failed = process_executor_once()
        logging.info(
            "worker_tick mode=%s active_pairs=%s queued_orders=%s filled=%s failed=%s",
            EXECUTOR_MODE,
            cnt,
            created,
            filled,
            failed,
        )
        time.sleep(poll_seconds)


if __name__ == "__main__":
    run(poll_seconds=EXECUTOR_POLL_SECONDS)
