import logging
import time
from urllib.parse import quote
import json
from urllib import parse, request

from backend.config import (
    BLOCKED_ALERT_COOLDOWN_SECONDS,
    EXECUTOR_BALANCE_FAIL_COOLDOWN_SECONDS,
    EXECUTOR_MARKET_MIN_BUY_USDC,
    EXECUTOR_MIN_SOURCE_NOTIONAL_USDC,
    EXECUTOR_MODE,
    EXECUTOR_OPEN_ORDER_CANCEL_AFTER_SECONDS,
    EXECUTOR_POLL_SECONDS,
)
from backend.db import get_conn
from backend.notifier import send_telegram_message
from backend.repositories.orders import (
    consume_follower_budget,
    create_execution_record,
    create_mirror_order,
    has_filled_buy_for_pair_token,
    has_recent_balance_or_allowance_failure,
    list_queued_mirror_orders,
    list_stale_sent_mirror_orders,
    mark_mirror_order_status,
    set_mirror_order_executor_ref,
)
from backend.repositories.runtime import heartbeat
from backend.repositories.signals import list_unmirrored_signals
from worker.executor import build_executor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
EXECUTOR = build_executor()
LOCAL_PAIR_COOLDOWN_UNTIL: dict[int, int] = {}
LOCAL_BLOCKED_ALERT_STATE: dict[tuple[int, str], tuple[int, int]] = {}
MARKET_META_CACHE: dict[str, tuple[int, dict | None]] = {}


def _notify_failed_execution(
    order_id: int,
    pair_id: int,
    follower_wallet_id: int,
    side: str,
    outcome: str | None,
    notional: float,
    fail_reason: str,
    source_tx_hash: str | None = None,
    market_slug: str | None = None,
) -> None:
    message = (
        "ProjectK 복제 실패\n"
        f"페어 ID: {pair_id}\n"
        f"주문 ID: {order_id}\n"
        f"팔로워 지갑 ID: {follower_wallet_id}\n"
        f"방향: {side}\n"
        f"결과(outcome): {outcome or '-'}\n"
        f"주문금액(USDC): {notional:.4f}\n"
        f"실패사유: {fail_reason}"
    )
    tx_link = _source_tx_link(source_tx_hash)
    market_link = _market_link(market_slug)
    if tx_link:
        message += f"\n소스 트랜잭션: {tx_link}"
    if market_link:
        message += f"\n마켓 바로가기: {market_link}"
    sent = send_telegram_message(message)
    if not sent:
        logging.warning("telegram_alert_skipped_or_failed order_id=%s reason=%s", order_id, fail_reason)


def _notify_blocked_order(
    pair_id: int,
    trade_signal_id: int,
    requested_notional: float,
    blocked_reason: str,
) -> None:
    now = int(time.time())
    noisy_reasons = {
        "insufficient_budget_for_market_min_order",
        "insufficient_budget_for_one_share",
    }
    suppressed = 0
    if blocked_reason in noisy_reasons and BLOCKED_ALERT_COOLDOWN_SECONDS > 0:
        key = (pair_id, blocked_reason)
        prev_sent_at, prev_suppressed = LOCAL_BLOCKED_ALERT_STATE.get(key, (0, 0))
        if prev_sent_at > 0 and now - prev_sent_at < BLOCKED_ALERT_COOLDOWN_SECONDS:
            LOCAL_BLOCKED_ALERT_STATE[key] = (prev_sent_at, prev_suppressed + 1)
            return
        suppressed = prev_suppressed
        LOCAL_BLOCKED_ALERT_STATE[key] = (now, 0)

    message = (
        "ProjectK 주문 차단\n"
        f"페어 ID: {pair_id}\n"
        f"시그널 ID: {trade_signal_id}\n"
        f"요청금액(USDC): {requested_notional:.4f}\n"
        f"차단사유: {blocked_reason}"
    )
    if suppressed > 0:
        message += f"\nsuppressed_since_last: {suppressed}"
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
    source_tx_hash: str | None = None,
    market_slug: str | None = None,
) -> None:
    message = (
        "ProjectK 복제 체결 완료\n"
        f"페어 ID: {pair_id}\n"
        f"주문 ID: {order_id}\n"
        f"팔로워 지갑 ID: {follower_wallet_id}\n"
        f"방향: {side}\n"
        f"결과(outcome): {outcome or '-'}\n"
        f"체결금액(USDC): {notional:.4f}\n"
        f"팔로워 체결 tx: {chain_tx_hash or '-'}"
    )
    tx_link = _source_tx_link(source_tx_hash)
    market_link = _market_link(market_slug)
    if tx_link:
        message += f"\n소스 트랜잭션: {tx_link}"
    if market_link:
        message += f"\n마켓 바로가기: {market_link}"
    sent = send_telegram_message(message)
    if not sent:
        logging.warning("telegram_alert_skipped_or_failed order_id=%s reason=filled", order_id)


def _notify_canceled_order(
    order_id: int,
    pair_id: int,
    follower_wallet_id: int,
    side: str,
    reason: str,
) -> None:
    message = (
        "ProjectK 주문 취소\n"
        f"페어 ID: {pair_id}\n"
        f"주문 ID: {order_id}\n"
        f"팔로워 지갑 ID: {follower_wallet_id}\n"
        f"방향: {side}\n"
        f"사유: {reason}"
    )
    sent = send_telegram_message(message)
    if not sent:
        logging.warning("telegram_alert_skipped_or_failed order_id=%s reason=canceled", order_id)


def _notify_sent_order(
    order_id: int,
    pair_id: int,
    follower_wallet_id: int,
    side: str,
    outcome: str | None,
    notional: float,
    source_tx_hash: str | None = None,
    market_slug: str | None = None,
) -> None:
    message = (
        "ProjectK 주문 접수됨(체결 대기)\n"
        f"페어 ID: {pair_id}\n"
        f"주문 ID: {order_id}\n"
        f"팔로워 지갑 ID: {follower_wallet_id}\n"
        f"방향: {side}\n"
        f"결과(outcome): {outcome or '-'}\n"
        f"주문금액(USDC): {notional:.4f}"
    )
    tx_link = _source_tx_link(source_tx_hash)
    market_link = _market_link(market_slug)
    if tx_link:
        message += f"\n소스 트랜잭션: {tx_link}"
    if market_link:
        message += f"\n마켓 바로가기: {market_link}"
    sent = send_telegram_message(message)
    if not sent:
        logging.warning("telegram_alert_skipped_or_failed order_id=%s reason=sent", order_id)


def active_pair_count() -> int:
    with get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) AS cnt FROM wallet_pairs WHERE active=1").fetchone()
    return int(row["cnt"])


def _calc_adjusted_notional(
    source_notional: float,
    source_portfolio_usdc: float | None,
    min_order_usdc: float,
    max_order_usdc: float | None,
    follower_budget_usdc: float,
    source_price: float | None,
) -> float:
    requested = float(source_notional)
    if source_portfolio_usdc is not None and float(source_portfolio_usdc) > 0:
        # Proportional sizing: source bet ratio * follower portfolio proxy(budget).
        ratio = requested / float(source_portfolio_usdc)
        requested = follower_budget_usdc * ratio

    # Enforce market absolute minimum ($1) even when pair min_order is configured lower.
    min_floor_usdc = max(float(min_order_usdc), float(EXECUTOR_MARKET_MIN_BUY_USDC))
    adjusted = max(requested, min_floor_usdc)
    if max_order_usdc is not None:
        adjusted = min(adjusted, max_order_usdc)
    if follower_budget_usdc >= adjusted:
        return adjusted

    # Fallback: if budget is short, try buying at least one share.
    if source_price is not None and source_price > 0 and follower_budget_usdc >= source_price:
        return source_price

    # If one share is not affordable, use remaining budget (or 0 => blocked).
    return max(min(adjusted, follower_budget_usdc), 0.0)


def _source_tx_link(tx_hash: str | None) -> str | None:
    if not tx_hash:
        return None
    raw = str(tx_hash).strip()
    if not raw or raw.startswith("mock-"):
        return None
    return f"https://polygonscan.com/tx/{raw}"


def _market_link(market_slug: str | None) -> str | None:
    if not market_slug:
        return None
    slug = quote(str(market_slug).strip(), safe="-_")
    if not slug:
        return None
    return f"https://polymarket.com/event/{slug}"


def _fetch_market_meta(token_id: str) -> dict | None:
    now = int(time.time())
    cached = MARKET_META_CACHE.get(token_id)
    if cached and cached[0] > now:
        return cached[1]
    q = parse.urlencode({"clob_token_ids": token_id})
    url = f"https://gamma-api.polymarket.com/markets?{q}"
    req = request.Request(
        url,
        headers={"User-Agent": "ProjectK-Worker/1.0", "Accept": "application/json"},
        method="GET",
    )
    try:
        with request.urlopen(req, timeout=6) as resp:
            rows = json.loads(resp.read().decode("utf-8"))
        market = rows[0] if rows and isinstance(rows[0], dict) else None
        MARKET_META_CACHE[token_id] = (now + 600, market)
        return market
    except Exception:
        MARKET_META_CACHE[token_id] = (now + 120, None)
        return None


def _market_policy_block_reason(token_id: str | None, market_slug: str | None) -> str | None:
    if not token_id:
        return None
    market = _fetch_market_meta(str(token_id))
    if not market:
        return None

    category = str(market.get("category") or "").lower()
    question = str(market.get("question") or "")
    slug = str(market.get("slug") or market_slug or "")
    text = f"{question} {slug}".lower()

    # Rule 1: block sports event markets.
    if "sport" in category:
        return "market_policy_filtered:sports_event"

    # Rule 2: block short-term crypto price prediction markets.
    crypto_tokens = [
        "bitcoin", "btc", "ethereum", "eth", "solana", "sol", "xrp", "doge", "bnb", "ada", "stx",
    ]
    price_words = [
        "price", "priced", "trading", "above", "below", "over", "under", "reach", "hit", "close at", "$", "usd",
        "가격", "달러",
    ]
    time_words = [
        "today", "tomorrow", "tonight", "this week", "next week", "by ", "before ", "in the next",
        "5m", "15m", "1h", "24h", "오늘", "내일", "이번 주", "몇시", "시간 내",
    ]

    has_crypto = ("crypto" in category) or any(k in text for k in crypto_tokens)
    has_price = any(k in text for k in price_words)
    has_time = any(k in text for k in time_words)
    if has_crypto and has_price and has_time:
        return "market_policy_filtered:crypto_short_term_price"

    return None


def _is_balance_or_allowance_failure(fail_reason: str | None) -> bool:
    if not fail_reason:
        return False
    normalized = fail_reason.lower()
    return (
        "not enough balance / allowance" in normalized
        or "insufficient_balance" in normalized
    )


def _is_market_min_size_failure(fail_reason: str | None) -> bool:
    if not fail_reason:
        return False
    normalized = fail_reason.lower()
    return "min size: $1" in normalized and "invalid amount for a marketable buy order" in normalized


def _is_reprice_after_timeout_reason(reason: str | None) -> bool:
    if not reason:
        return False
    return "reprice_after_timeout" in str(reason)


def process_once() -> int:
    pending = list_unmirrored_signals(limit=100)
    created = 0
    for row in pending:
        requested = float(row["source_notional_usdc"])
        source_portfolio = row.get("source_portfolio_usdc")
        source_portfolio_val = float(source_portfolio) if source_portfolio is not None else None
        min_order = float(row["min_order_usdc"] or 1.0)
        budget = float(row["budget_usdc"] or 0.0)
        side = str(row["side"]).lower()
        token_id = str(row["token_id"]) if row.get("token_id") is not None else None
        source_price = float(row["source_price"]) if row["source_price"] is not None else None
        max_order = row["max_order_usdc"]
        max_order_val = float(max_order) if max_order is not None else None
        pair_id = int(row["pair_id"])
        trade_signal_id = int(row["trade_signal_id"])
        market_slug = row.get("market_slug")

        policy_reason = _market_policy_block_reason(token_id=token_id, market_slug=market_slug if isinstance(market_slug, str) else None)
        if policy_reason:
            create_mirror_order(
                pair_id=pair_id,
                trade_signal_id=trade_signal_id,
                requested_notional_usdc=requested,
                adjusted_notional_usdc=0.0,
                status="blocked",
                blocked_reason=policy_reason,
            )
            # Policy-filtered markets are intentionally suppressed from telegram alerts.
            continue

        if requested < EXECUTOR_MIN_SOURCE_NOTIONAL_USDC:
            create_mirror_order(
                pair_id=pair_id,
                trade_signal_id=trade_signal_id,
                requested_notional_usdc=requested,
                adjusted_notional_usdc=0.0,
                status="blocked",
                blocked_reason=f"source_notional_below_threshold:{EXECUTOR_MIN_SOURCE_NOTIONAL_USDC:.2f}",
            )
            # Dummy/noise trades are intentionally suppressed from telegram alerts.
            continue

        if has_recent_balance_or_allowance_failure(
            pair_id=pair_id,
            within_seconds=EXECUTOR_BALANCE_FAIL_COOLDOWN_SECONDS,
        ):
            create_mirror_order(
                pair_id=pair_id,
                trade_signal_id=trade_signal_id,
                requested_notional_usdc=requested,
                adjusted_notional_usdc=0.0,
                status="blocked",
                blocked_reason="recent_balance_or_allowance_failure_cooldown",
            )
            continue

        if side == "sell" and not has_filled_buy_for_pair_token(pair_id=pair_id, token_id=token_id):
            blocked_reason = "no_prior_buy_inventory_for_sell"
            create_mirror_order(
                pair_id=pair_id,
                trade_signal_id=trade_signal_id,
                requested_notional_usdc=requested,
                adjusted_notional_usdc=0.0,
                status="blocked",
                blocked_reason=blocked_reason,
            )
            continue

        adjusted = _calc_adjusted_notional(
            source_notional=requested,
            source_portfolio_usdc=source_portfolio_val,
            min_order_usdc=min_order,
            max_order_usdc=max_order_val,
            follower_budget_usdc=budget,
            source_price=source_price,
        )
        if adjusted > 0 and adjusted < max(min_order, EXECUTOR_MARKET_MIN_BUY_USDC):
            blocked_reason = "insufficient_budget_for_market_min_order"
            create_mirror_order(
                pair_id=pair_id,
                trade_signal_id=trade_signal_id,
                requested_notional_usdc=requested,
                adjusted_notional_usdc=0.0,
                status="blocked",
                blocked_reason=blocked_reason,
            )
            _notify_blocked_order(
                pair_id=pair_id,
                trade_signal_id=trade_signal_id,
                requested_notional=requested,
                blocked_reason=blocked_reason,
            )
            continue
        if adjusted <= 0:
            blocked_reason = "insufficient_budget_for_one_share"
            create_mirror_order(
                pair_id=pair_id,
                trade_signal_id=trade_signal_id,
                requested_notional_usdc=requested,
                adjusted_notional_usdc=0.0,
                status="blocked",
                blocked_reason=blocked_reason,
            )
            _notify_blocked_order(
                pair_id=pair_id,
                trade_signal_id=trade_signal_id,
                requested_notional=requested,
                blocked_reason=blocked_reason,
            )
            continue
        create_mirror_order(
            pair_id=pair_id,
            trade_signal_id=trade_signal_id,
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
        source_tx_hash = row.get("source_tx_hash")
        market_slug = row.get("market_slug")
        now = int(time.time())

        local_cooldown_until = LOCAL_PAIR_COOLDOWN_UNTIL.get(pair_id, 0)
        if local_cooldown_until > now:
            mark_mirror_order_status(order_id, "blocked", "pair_local_balance_failure_cooldown")
            continue

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
                source_tx_hash=source_tx_hash if isinstance(source_tx_hash, str) else None,
                market_slug=market_slug if isinstance(market_slug, str) else None,
            )
            filled += 1
        elif result.status == "sent":
            mark_mirror_order_status(order_id, "sent", None)
            _notify_sent_order(
                order_id=order_id,
                pair_id=pair_id,
                follower_wallet_id=follower_wallet_id,
                side=side,
                outcome=outcome,
                notional=notional,
                source_tx_hash=source_tx_hash if isinstance(source_tx_hash, str) else None,
                market_slug=market_slug if isinstance(market_slug, str) else None,
            )
        else:
            fail_reason = result.fail_reason or "executor_failed"
            if _is_market_min_size_failure(fail_reason):
                mark_mirror_order_status(order_id, "blocked", "market_min_order_size")
            else:
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
            if _is_balance_or_allowance_failure(fail_reason):
                LOCAL_PAIR_COOLDOWN_UNTIL[pair_id] = now + EXECUTOR_BALANCE_FAIL_COOLDOWN_SECONDS

            if not _is_market_min_size_failure(fail_reason):
                _notify_failed_execution(
                    order_id=order_id,
                    pair_id=pair_id,
                    follower_wallet_id=follower_wallet_id,
                    side=side,
                    outcome=outcome,
                    notional=notional,
                    fail_reason=fail_reason,
                    source_tx_hash=source_tx_hash if isinstance(source_tx_hash, str) else None,
                    market_slug=market_slug if isinstance(market_slug, str) else None,
                )
            failed += 1
    return filled, failed


def cancel_stale_sent_orders_once() -> tuple[int, int]:
    stale = list_stale_sent_mirror_orders(max_age_seconds=EXECUTOR_OPEN_ORDER_CANCEL_AFTER_SECONDS, limit=100)
    canceled = 0
    failed = 0
    for row in stale:
        order_id = int(row["id"])
        pair_id = int(row["pair_id"])
        follower_wallet_id = int(row["follower_wallet_id"])
        side = str(row["side"])
        blocked_reason = str(row.get("blocked_reason") or "")
        result = EXECUTOR.cancel(row)
        if result.status == "canceled":
            if side.lower() == "buy" and not _is_reprice_after_timeout_reason(blocked_reason):
                # One-time retry: requeue with aggressive price (+0.1) in executor.
                set_mirror_order_executor_ref(order_id=order_id, executor_ref="")
                mark_mirror_order_status(order_id, "queued", "reprice_after_timeout")
            else:
                mark_mirror_order_status(order_id, "canceled", "open_order_timeout")
                _notify_canceled_order(
                    order_id=order_id,
                    pair_id=pair_id,
                    follower_wallet_id=follower_wallet_id,
                    side=side,
                    reason=f"open_order_timeout>{EXECUTOR_OPEN_ORDER_CANCEL_AFTER_SECONDS}s",
                )
                canceled += 1
        else:
            reason = result.fail_reason or "cancel_failed"
            mark_mirror_order_status(order_id, "failed", reason)
            _notify_failed_execution(
                order_id=order_id,
                pair_id=pair_id,
                follower_wallet_id=follower_wallet_id,
                side=side,
                outcome=row.get("outcome"),
                notional=0.0,
                fail_reason=f"cancel_failed:{reason}",
            )
            failed += 1
    return canceled, failed


def run(poll_seconds: int = 10) -> None:
    while True:
        heartbeat("worker")
        cnt = active_pair_count()
        created = process_once()
        canceled, cancel_failed = cancel_stale_sent_orders_once()
        filled, failed = process_executor_once()
        logging.info(
            "worker_tick mode=%s active_pairs=%s queued_orders=%s canceled=%s cancel_failed=%s filled=%s failed=%s",
            EXECUTOR_MODE,
            cnt,
            created,
            canceled,
            cancel_failed,
            filled,
            failed,
        )
        time.sleep(poll_seconds)


if __name__ == "__main__":
    run(poll_seconds=EXECUTOR_POLL_SECONDS)
