from __future__ import annotations

import argparse
import logging
import time
from dataclasses import replace
from datetime import datetime, timezone

from bot.config import Settings, load_settings
from bot.data.bitflow_client import BitflowClient
from bot.data.coingecko_client import CoinGeckoClient
from bot.data.hiro_client import CycleStatus, HiroClient
from bot.execution.executor import ExecutionRequest, Executor
from bot.execution.fee_policy import compute_final_fee_stx
from bot.notify.telegram_notifier import BotEventPayload, TelegramNotifier
from bot.risk.guard import RiskLimits, RiskState, check_pre_trade
from bot.storage.db import BotDB, utc_now_iso
from bot.strategy.rebalance import RebalanceDecision, RebalanceInput, build_rebalance_decision
from bot.strategy.signal import SignalAction, SignalDecision, SignalInput, build_signal


def setup_logger(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
    )


def utc_day() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def estimate_trade_pnl_stx(
    *,
    order_usd: float,
    ststx_usd: float,
    intrinsic_stx_per_ststx: float,
    net_edge_pct: float,
) -> float:
    if order_usd <= 0 or ststx_usd <= 0 or intrinsic_stx_per_ststx <= 0 or net_edge_pct <= 0:
        return 0.0
    qty_ststx = order_usd / ststx_usd
    net_diff_stx_per_ststx = intrinsic_stx_per_ststx * (net_edge_pct / 100.0)
    return qty_ststx * net_diff_stx_per_ststx


def realized_trade_pnl_stx(
    *,
    action: SignalAction,
    filled_stx: float | None,
    filled_ststx: float | None,
    intrinsic_stx_per_ststx: float,
    network_fee_stx: float,
) -> float | None:
    if (
        filled_stx is None
        or filled_ststx is None
        or filled_stx <= 0
        or filled_ststx <= 0
        or intrinsic_stx_per_ststx <= 0
    ):
        return None

    intrinsic_value_stx = filled_ststx * intrinsic_stx_per_ststx
    if action == SignalAction.BUY_STSTX:
        return intrinsic_value_stx - filled_stx - network_fee_stx
    return filled_stx - intrinsic_value_stx - network_fee_stx


def _parse_iso_utc(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _build_rebalance_or_none(
    *,
    settings: Settings,
    db: BotDB,
    hiro: HiroClient,
    prices_stx_usd: float,
    prices_ststx_usd: float,
    liquidity_usd: float,
    abs_edge_pct: float,
    signal_action: SignalAction,
    now: str,
) -> RebalanceDecision | None:
    if not settings.rebalance_enabled or not settings.trading_address:
        return None

    last_rebalance = db.fetch_latest_order_time_by_reason_prefix("rebalance_")
    last_dt = _parse_iso_utc(last_rebalance)
    now_dt = _parse_iso_utc(now)
    if last_dt and now_dt:
        elapsed = (now_dt - last_dt).total_seconds()
        if elapsed < settings.rebalance_check_interval_sec:
            return None

    daily_count = db.count_orders_by_reason_prefix_for_day(utc_day(), "rebalance_")
    balances = hiro.fetch_wallet_balances(settings.trading_address, settings.ststx_token_contract)
    return build_rebalance_decision(
        RebalanceInput(
            balances=balances,
            stx_usd=prices_stx_usd,
            ststx_usd=prices_ststx_usd,
            liquidity_usd=liquidity_usd,
            target_stx_weight=settings.rebalance_target_stx_weight,
            drift_pct=settings.rebalance_drift_pct,
            min_order_usd=settings.rebalance_min_order_usd,
            max_order_usd=settings.rebalance_max_order_usd,
            dex_fee_pct=settings.dex_fee_pct,
            buffer_pct=settings.rebalance_buffer_pct,
            abs_edge_pct=abs_edge_pct,
            signal_action=signal_action,
            daily_count=daily_count,
            max_per_day=settings.rebalance_max_per_day,
        )
    )


def _cap_order_usd_by_wallet_capacity(
    *,
    settings: Settings,
    hiro: HiroClient,
    action: SignalAction,
    order_usd: float,
    stx_usd: float,
    ststx_usd: float,
    fee_stx: float,
) -> tuple[float, str]:
    if order_usd <= 0:
        return 0.0, "invalid_order_size"
    if stx_usd <= 0 or ststx_usd <= 0:
        return 0.0, "invalid_price_for_balance_check"
    if not settings.trading_address:
        return order_usd, "balance_check_skipped_no_trading_address"

    try:
        balances = hiro.fetch_wallet_balances(settings.trading_address, settings.ststx_token_contract)
    except Exception as exc:
        return 0.0, f"balance_check_error:{exc.__class__.__name__}"

    # Small safety margin for quote movement between decision and execution.
    margin = 1.005
    if action == SignalAction.BUY_STSTX:
        usable_stx = max(0.0, balances.stx_balance - max(0.0, fee_stx))
        affordable_usd = (usable_stx / margin) * stx_usd
        capped_order_usd = min(order_usd, max(0.0, affordable_usd))
        if capped_order_usd <= 0:
            required_stx = (order_usd / stx_usd) * margin + max(0.0, fee_stx)
            return (
                0.0,
                f"insufficient_stx_balance:need={required_stx:.6f},have={balances.stx_balance:.6f}",
            )
        if capped_order_usd + 1e-9 < order_usd:
            return (
                capped_order_usd,
                (
                    "order_capped_by_stx_balance:"
                    f"requested_usd={order_usd:.2f},capped_usd={capped_order_usd:.2f},"
                    f"stx={balances.stx_balance:.6f},fee={fee_stx:.6f}"
                ),
            )
        return order_usd, "balance_ok"

    affordable_usd = (balances.ststx_balance / margin) * ststx_usd
    capped_order_usd = min(order_usd, max(0.0, affordable_usd))
    if capped_order_usd <= 0:
        required_ststx = (order_usd / ststx_usd) * margin
        return (
            0.0,
            f"insufficient_ststx_balance:need={required_ststx:.6f},have={balances.ststx_balance:.6f}",
        )
    if capped_order_usd + 1e-9 < order_usd:
        return (
            capped_order_usd,
            (
                "order_capped_by_ststx_balance:"
                f"requested_usd={order_usd:.2f},capped_usd={capped_order_usd:.2f},"
                f"ststx={balances.ststx_balance:.6f}"
            ),
        )
    return order_usd, "balance_ok"


def _evaluate_failed_trade_cooldown(
    *,
    settings: Settings,
    event_time_utc: str,
    now: str,
    reason: str,
    txid: str,
) -> tuple[bool, str]:
    event_time = _parse_iso_utc(event_time_utc)
    now_dt = _parse_iso_utc(now)
    if event_time and now_dt:
        elapsed_sec = max(0, int((now_dt - event_time).total_seconds()))
        if elapsed_sec >= settings.prev_fail_retry_cooldown_sec:
            return (
                True,
                (
                    "previous_trade_failed_but_cooldown_passed:"
                    f"elapsed={elapsed_sec}s,cooldown={settings.prev_fail_retry_cooldown_sec}s"
                ),
            )
        remain = settings.prev_fail_retry_cooldown_sec - elapsed_sec
        return (
            False,
            (
                "previous_trade_failed_cooldown:"
                f"remain={remain}s,last_reason={reason},txid={txid}"
            ),
        )
    return False, f"previous_trade_not_success:status=failed,reason={reason},txid={txid}"


def _try_reconcile_submitted_trade(
    *,
    settings: Settings,
    db: BotDB,
    hiro: HiroClient,
    last_trade,
    now: str,
) -> tuple[bool, str] | None:
    order_pk = int(last_trade["id"])
    event_time_utc = str(last_trade["event_time_utc"] or "")
    side = str(last_trade["side"] or "").strip()
    txid = str(last_trade["txid"] or "").strip()

    if not txid or not settings.trading_address:
        return None
    if side not in {SignalAction.BUY_STSTX.value, SignalAction.SELL_STSTX.value}:
        return None

    try:
        outcome = hiro.wait_for_tx_outcome(
            txid,
            trading_address=settings.trading_address,
            action=side,
            ststx_contract=settings.ststx_token_contract,
            timeout_sec=2,
            poll_interval_sec=1,
        )
    except Exception as exc:
        logging.warning("previous trade reconcile failed txid=%s error=%s", txid, exc.__class__.__name__)
        return None

    tx_status = str(outcome.tx_status or "").strip().lower()
    resolved_txid = str(outcome.txid or txid).strip()
    if tx_status == "success":
        db.update_order_status(
            order_pk,
            status="filled",
            txid=resolved_txid,
            reason="onchain_success_reconciled",
        )
        logging.info("previous trade reconciled to filled txid=%s", resolved_txid)
        return True, f"previous_trade_reconciled_success:txid={resolved_txid}"

    if tx_status and (
        tx_status.startswith("abort")
        or tx_status.startswith("drop")
        or tx_status.startswith("bad_")
        or tx_status == "failed"
    ):
        failed_reason = f"onchain_{tx_status}"
        db.update_order_status(
            order_pk,
            status="failed",
            txid=resolved_txid,
            reason=failed_reason,
        )
        logging.warning("previous trade reconciled to failed txid=%s status=%s", resolved_txid, tx_status)
        return _evaluate_failed_trade_cooldown(
            settings=settings,
            event_time_utc=event_time_utc,
            now=now,
            reason=failed_reason,
            txid=resolved_txid,
        )

    return None


def _check_previous_trade_gate(settings: Settings, db: BotDB, hiro: HiroClient, now: str) -> tuple[bool, str]:
    last_trade = db.fetch_latest_trade_order()
    if last_trade is None:
        return True, "no_previous_trade"

    status = str(last_trade["status"] or "").strip().lower()
    reason = str(last_trade["reason"] or "").strip()
    txid = str(last_trade["txid"] or "").strip()
    event_time_utc = str(last_trade["event_time_utc"] or "")
    if status == "filled":
        return True, "previous_trade_success"
    if status == "submitted":
        reconciled = _try_reconcile_submitted_trade(
            settings=settings,
            db=db,
            hiro=hiro,
            last_trade=last_trade,
            now=now,
        )
        if reconciled is not None:
            return reconciled
        return False, f"previous_trade_not_confirmed:txid={txid}"
    if status == "failed":
        return _evaluate_failed_trade_cooldown(
            settings=settings,
            event_time_utc=event_time_utc,
            now=now,
            reason=reason,
            txid=txid,
        )
    return False, f"previous_trade_not_success:status={status},reason={reason},txid={txid}"


def _maybe_send_blocked_alert(
    *,
    settings: Settings,
    db: BotDB,
    notifier: TelegramNotifier,
    state: RiskState,
    now: str,
    pool_id: str,
    action: SignalAction,
    order_usd: float,
    abs_edge_pct: float,
    reason: str,
    log_prefix: str,
) -> RiskState:
    now_epoch = time.time()
    cooldown_sec = max(0, settings.block_alert_cooldown_sec)
    same_reason = reason == state.last_block_alert_reason
    in_cooldown = same_reason and (now_epoch - state.last_block_alert_epoch) < cooldown_sec
    if in_cooldown:
        logging.warning("%s (alert suppressed by cooldown): %s", log_prefix, reason)
        return state

    payload = BotEventPayload(
        event_type="risk_alert",
        strategy="stx-ststx-arb-v1",
        event_time_utc=now,
        pool_id=pool_id,
        side=action.value.replace("_STSTX", ""),
        order_size_usd=order_usd,
        edge_pct_at_decision=abs_edge_pct,
        status="blocked",
        reason=reason,
    )
    send_alert(db, notifier, payload)
    logging.warning("%s: %s", log_prefix, reason)
    return replace(
        state,
        last_block_alert_reason=reason,
        last_block_alert_epoch=now_epoch,
    )


def _execute_trade(
    *,
    settings: Settings,
    db: BotDB,
    hiro: HiroClient,
    notifier: TelegramNotifier,
    executor: Executor,
    risk_state: RiskState,
    now: str,
    pool_id: str,
    stx_usd: float,
    ststx_usd: float,
    market_stx_per_ststx: float,
    intrinsic_stx_per_ststx: float,
    net_edge_pct: float,
    signal_id: int,
    action: SignalAction,
    order_usd: float,
    slippage_pct: float,
    abs_edge_pct: float,
    order_reason: str,
) -> RiskState:
    requested_order_usd = order_usd
    risk_limits = RiskLimits(
        max_order_usd=settings.max_order_usd,
        max_daily_loss_pct=settings.max_daily_loss_pct,
        max_consecutive_losses=settings.max_consecutive_losses,
        max_consecutive_exec_failures=settings.max_consecutive_exec_failures,
    )
    if not settings.dry_run and settings.require_prev_tx_success:
        prev_ok, prev_reason = _check_previous_trade_gate(settings, db, hiro, now)
        if not prev_ok:
            db.insert_order(
                signal_id=signal_id,
                event_time_utc=now,
                side=action.value,
                pool_id=pool_id,
                order_size_usd=order_usd,
                status="blocked",
                reason=prev_reason,
            )
            return _maybe_send_blocked_alert(
                settings=settings,
                db=db,
                notifier=notifier,
                state=risk_state,
                now=now,
                pool_id=pool_id,
                action=action,
                order_usd=order_usd,
                abs_edge_pct=abs_edge_pct,
                reason=prev_reason,
                log_prefix="previous-trade gate blocked",
            )

    if not settings.dry_run and settings.trading_address:
        try:
            balances = hiro.fetch_wallet_balances(settings.trading_address, settings.ststx_token_contract)
            min_balance = max(0.0, settings.min_side_balance_for_trading)
            if balances.stx_balance < min_balance or balances.ststx_balance < min_balance:
                skip_reason = (
                    "balance_guard_min_side_not_met:"
                    f"stx={balances.stx_balance:.6f},ststx={balances.ststx_balance:.6f},min={min_balance:.6f}"
                )
                db.insert_order(
                    signal_id=signal_id,
                    event_time_utc=now,
                    side=action.value,
                    pool_id=pool_id,
                    order_size_usd=order_usd,
                    status="skipped",
                    reason=skip_reason,
                )
                logging.info("trade skipped by min side-balance guard: %s", skip_reason)
                return risk_state
        except Exception as exc:
            logging.warning("min side-balance guard skipped due to balance fetch error: %s", exc.__class__.__name__)

    risk_decision = check_pre_trade(order_usd=order_usd, limits=risk_limits, state=risk_state)
    if not risk_decision.allowed:
        db.insert_order(
            signal_id=signal_id,
            event_time_utc=now,
            side=action.value,
            pool_id=pool_id,
            order_size_usd=order_usd,
            status="blocked",
            reason=risk_decision.reason,
        )
        return _maybe_send_blocked_alert(
            settings=settings,
            db=db,
            notifier=notifier,
            state=risk_state,
            now=now,
            pool_id=pool_id,
            action=action,
            order_usd=order_usd,
            abs_edge_pct=abs_edge_pct,
            reason=risk_decision.reason,
            log_prefix="risk blocked",
        )

    hiro_estimate_stx = 0.0
    planned_fee_stx = 0.0
    if not settings.dry_run:
        fee_rate_micro = hiro.fetch_transfer_fee_rate_microstx_per_byte()
        hiro_estimate_stx = (fee_rate_micro * settings.tx_estimated_bytes) / 1_000_000.0
        planned_fee_stx = compute_final_fee_stx(
            hiro_estimate_stx=hiro_estimate_stx,
            min_fee_floor_stx=settings.min_fee_floor_stx,
            fee_multiplier=settings.fee_multiplier,
            network_fee_cap_stx=settings.network_fee_cap_stx,
        )

    capped_order_usd, capacity_reason = _cap_order_usd_by_wallet_capacity(
        settings=settings,
        hiro=hiro,
        action=action,
        order_usd=order_usd,
        stx_usd=stx_usd,
        ststx_usd=ststx_usd,
        fee_stx=planned_fee_stx,
    )
    if capped_order_usd <= 0:
        db.insert_order(
            signal_id=signal_id,
            event_time_utc=now,
            side=action.value,
            pool_id=pool_id,
            order_size_usd=order_usd,
            status="blocked",
            reason=capacity_reason,
        )
        return _maybe_send_blocked_alert(
            settings=settings,
            db=db,
            notifier=notifier,
            state=risk_state,
            now=now,
            pool_id=pool_id,
            action=action,
            order_usd=order_usd,
            abs_edge_pct=abs_edge_pct,
            reason=capacity_reason,
            log_prefix="balance blocked",
        )
    if capped_order_usd + 1e-9 < requested_order_usd:
        order_usd = capped_order_usd
        order_reason = f"{order_reason}|{capacity_reason}"
        logging.warning("order size capped by balance: req=%.2f cap=%.2f", requested_order_usd, order_usd)

    if not settings.dry_run:
        expected_after_fee = estimate_trade_pnl_stx(
            order_usd=order_usd,
            ststx_usd=ststx_usd,
            intrinsic_stx_per_ststx=intrinsic_stx_per_ststx,
            net_edge_pct=net_edge_pct,
        ) - planned_fee_stx
        if expected_after_fee <= 0:
            reason = (
                "non_positive_expected_pnl_after_fee:"
                f"order_usd={order_usd:.2f},expected={expected_after_fee:.6f}"
            )
            db.insert_order(
                signal_id=signal_id,
                event_time_utc=now,
                side=action.value,
                pool_id=pool_id,
                order_size_usd=order_usd,
                status="blocked",
                reason=reason,
            )
            return _maybe_send_blocked_alert(
                settings=settings,
                db=db,
                notifier=notifier,
                state=risk_state,
                now=now,
                pool_id=pool_id,
                action=action,
                order_usd=order_usd,
                abs_edge_pct=abs_edge_pct,
                reason=reason,
                log_prefix="pnl blocked",
            )

    order_pk = db.insert_order(
        signal_id=signal_id,
        event_time_utc=now,
        side=action.value,
        pool_id=pool_id,
        order_size_usd=order_usd,
        status="submitted",
        reason=order_reason,
    )

    if settings.dry_run:
        trade_pnl_stx = estimate_trade_pnl_stx(
            order_usd=order_usd,
            ststx_usd=ststx_usd,
            intrinsic_stx_per_ststx=intrinsic_stx_per_ststx,
            net_edge_pct=net_edge_pct,
        )
        running_pnl_stx = risk_state.running_pnl_stx + trade_pnl_stx

        avg_price = market_stx_per_ststx
        filled_ststx = order_usd / ststx_usd
        filled_stx = filled_ststx * avg_price
        fee_stx = 0.0

        db.update_order_status(order_pk, status="filled", txid="dry-run", reason="dry_run_fill")
        db.insert_fill(
            order_pk=order_pk,
            event_time_utc=now,
            filled_stx=filled_stx,
            filled_ststx=filled_ststx,
            avg_fill_price_stx_per_ststx=avg_price,
            fee_stx=fee_stx,
            slippage_pct=slippage_pct,
            trade_pnl_stx=trade_pnl_stx,
            running_pnl_stx=running_pnl_stx,
        )
        next_losses = risk_state.consecutive_losses + 1 if trade_pnl_stx < 0 else 0
        next_state = replace(
            risk_state,
            running_pnl_stx=running_pnl_stx,
            consecutive_losses=next_losses,
            consecutive_exec_failures=0,
        )
        update_daily_pnl(db, settings, trade_pnl_stx)
        payload = BotEventPayload(
            event_type="order_filled",
            strategy="stx-ststx-arb-v1",
            event_time_utc=now,
            pool_id=pool_id,
            txid="dry-run",
            side=action.value.replace("_STSTX", ""),
            order_size_usd=order_usd,
            filled_stx=filled_stx,
            filled_ststx=filled_ststx,
            avg_fill_price_stx_per_ststx=avg_price,
            fee_stx=fee_stx,
            slippage_pct=slippage_pct,
            edge_pct_at_decision=abs_edge_pct,
            trade_pnl_stx=trade_pnl_stx,
            running_pnl_stx=running_pnl_stx,
            status="filled",
            reason="dry_run_fill",
        )
        send_alert(db, notifier, payload)
        logging.info("filled(dry-run) action=%s order=%.2f pnl_stx=%.6f", action.value, order_usd, trade_pnl_stx)
        return next_state

    exec_result = executor.execute(
        ExecutionRequest(
            action=action.value,
            order_usd=order_usd,
            pool_id=pool_id,
            edge_pct=abs_edge_pct,
            slippage_pct=slippage_pct,
            stx_usd=stx_usd,
            ststx_usd=ststx_usd,
        ),
        hiro_estimate_stx=hiro_estimate_stx,
    )
    db.update_order_status(order_pk, status=exec_result.status, txid=exec_result.txid, reason=exec_result.reason)

    if exec_result.ok and exec_result.status == "filled":
        trade_pnl_stx = exec_result.trade_pnl_stx
        if trade_pnl_stx is None:
            trade_pnl_stx = estimate_trade_pnl_stx(
                order_usd=order_usd,
                ststx_usd=ststx_usd,
                intrinsic_stx_per_ststx=intrinsic_stx_per_ststx,
                net_edge_pct=net_edge_pct,
            ) - exec_result.fee_stx
        running_pnl_stx = risk_state.running_pnl_stx + trade_pnl_stx
        next_losses = risk_state.consecutive_losses + 1 if trade_pnl_stx < 0 else 0
        next_state = replace(
            risk_state,
            running_pnl_stx=running_pnl_stx,
            consecutive_losses=next_losses,
            consecutive_exec_failures=0,
        )
        db.insert_fill(
            order_pk=order_pk,
            event_time_utc=now,
            filled_stx=exec_result.filled_stx,
            filled_ststx=exec_result.filled_ststx,
            avg_fill_price_stx_per_ststx=exec_result.avg_fill_price_stx_per_ststx,
            fee_stx=exec_result.fee_stx,
            slippage_pct=slippage_pct,
            trade_pnl_stx=trade_pnl_stx,
            running_pnl_stx=running_pnl_stx,
        )
        update_daily_pnl(db, settings, trade_pnl_stx)
        payload = BotEventPayload(
            event_type="order_filled",
            strategy="stx-ststx-arb-v1",
            event_time_utc=now,
            pool_id=pool_id,
            txid=exec_result.txid,
            side=action.value.replace("_STSTX", ""),
            order_size_usd=order_usd,
            filled_stx=exec_result.filled_stx,
            filled_ststx=exec_result.filled_ststx,
            avg_fill_price_stx_per_ststx=exec_result.avg_fill_price_stx_per_ststx,
            fee_stx=exec_result.fee_stx,
            slippage_pct=slippage_pct,
            edge_pct_at_decision=abs_edge_pct,
            trade_pnl_stx=trade_pnl_stx,
            running_pnl_stx=running_pnl_stx,
            status=exec_result.status,
            reason=exec_result.reason,
        )
        send_alert(db, notifier, payload)
        logging.info("filled(live) txid=%s pnl_stx=%.6f reason=%s", exec_result.txid, trade_pnl_stx, order_reason)
        return next_state

    if exec_result.ok:
        expected_pnl_stx = estimate_trade_pnl_stx(
            order_usd=order_usd,
            ststx_usd=ststx_usd,
            intrinsic_stx_per_ststx=intrinsic_stx_per_ststx,
            net_edge_pct=net_edge_pct,
        ) - exec_result.fee_stx
        actual_status = "pending"
        actual_reason = "onchain_confirmation_timeout"
        actual_time = now
        actual_filled_stx = None
        actual_filled_ststx = None
        actual_avg_price = None
        actual_fee_stx = exec_result.fee_stx
        actual_trade_pnl_stx = None
        next_state = risk_state

        if exec_result.txid:
            try:
                outcome = hiro.wait_for_tx_outcome(
                    exec_result.txid,
                    trading_address=settings.trading_address,
                    action=action.value,
                    ststx_contract=settings.ststx_token_contract,
                    timeout_sec=45,
                    poll_interval_sec=3,
                )
                actual_status = outcome.tx_status
                actual_reason = "onchain_confirmed"
                actual_time = outcome.block_time_iso or now
                actual_filled_stx = outcome.filled_stx
                actual_filled_ststx = outcome.filled_ststx
                actual_avg_price = outcome.avg_fill_price_stx_per_ststx
                actual_fee_stx = outcome.fee_stx
                actual_trade_pnl_stx = realized_trade_pnl_stx(
                    action=action,
                    filled_stx=actual_filled_stx,
                    filled_ststx=actual_filled_ststx,
                    intrinsic_stx_per_ststx=intrinsic_stx_per_ststx,
                    network_fee_stx=actual_fee_stx,
                )

                if outcome.tx_status == "success":
                    db.update_order_status(
                        order_pk,
                        status="filled",
                        txid=outcome.txid or exec_result.txid,
                        reason="onchain_success",
                    )
                    if (
                        actual_filled_stx is not None
                        and actual_filled_ststx is not None
                        and actual_avg_price is not None
                        and actual_trade_pnl_stx is not None
                    ):
                        running_pnl_stx = risk_state.running_pnl_stx + actual_trade_pnl_stx
                        next_losses = risk_state.consecutive_losses + 1 if actual_trade_pnl_stx < 0 else 0
                        next_state = replace(
                            risk_state,
                            running_pnl_stx=running_pnl_stx,
                            consecutive_losses=next_losses,
                            consecutive_exec_failures=0,
                        )
                        db.insert_fill(
                            order_pk=order_pk,
                            event_time_utc=actual_time,
                            filled_stx=actual_filled_stx,
                            filled_ststx=actual_filled_ststx,
                            avg_fill_price_stx_per_ststx=actual_avg_price,
                            fee_stx=actual_fee_stx,
                            slippage_pct=slippage_pct,
                            trade_pnl_stx=actual_trade_pnl_stx,
                            running_pnl_stx=running_pnl_stx,
                        )
                        update_daily_pnl(db, settings, actual_trade_pnl_stx)
                elif outcome.tx_status:
                    db.update_order_status(
                        order_pk,
                        status="failed",
                        txid=outcome.txid or exec_result.txid,
                        reason=f"onchain_{outcome.tx_status}",
                    )
                    next_state = _register_execution_failure(
                        settings=settings,
                        db=db,
                        notifier=notifier,
                        state=risk_state,
                        now=now,
                        pool_id=pool_id,
                        action=action,
                        order_usd=order_usd,
                        abs_edge_pct=abs_edge_pct,
                        reason=f"onchain_{outcome.tx_status}",
                    )
            except Exception as exc:
                actual_status = "pending"
                actual_reason = f"onchain_check_error:{exc.__class__.__name__}"

        payload = BotEventPayload(
            event_type="order_submitted",
            strategy="stx-ststx-arb-v1",
            event_time_utc=now,
            pool_id=pool_id,
            txid=exec_result.txid,
            side=action.value.replace("_STSTX", ""),
            order_size_usd=order_usd,
            edge_pct_at_decision=abs_edge_pct,
            fee_stx=exec_result.fee_stx,
            trade_pnl_stx=expected_pnl_stx,
            status=exec_result.status,
            reason=exec_result.reason or "submitted_no_fill",
            actual_event_time_utc=actual_time,
            actual_status=actual_status,
            actual_reason=actual_reason,
            actual_filled_stx=actual_filled_stx,
            actual_filled_ststx=actual_filled_ststx,
            actual_avg_fill_price_stx_per_ststx=actual_avg_price,
            actual_fee_stx=actual_fee_stx,
            actual_trade_pnl_stx=actual_trade_pnl_stx,
        )
        send_alert(db, notifier, payload)
        logging.info("submitted(live) status=%s txid=%s actual=%s", exec_result.status, exec_result.txid, actual_status)
        return next_state

    payload = BotEventPayload(
        event_type="order_failed",
        strategy="stx-ststx-arb-v1",
        event_time_utc=now,
        pool_id=pool_id,
        side=action.value.replace("_STSTX", ""),
        order_size_usd=order_usd,
        edge_pct_at_decision=abs_edge_pct,
        fee_stx=exec_result.fee_stx,
        status=exec_result.status,
        reason=exec_result.reason,
    )
    send_alert(db, notifier, payload)
    logging.error("execution failed: %s", exec_result.reason)
    return _register_execution_failure(
        settings=settings,
        db=db,
        notifier=notifier,
        state=risk_state,
        now=now,
        pool_id=pool_id,
        action=action,
        order_usd=order_usd,
        abs_edge_pct=abs_edge_pct,
        reason=exec_result.reason,
    )


def _register_execution_failure(
    *,
    settings: Settings,
    db: BotDB,
    notifier: TelegramNotifier,
    state: RiskState,
    now: str,
    pool_id: str,
    action: SignalAction,
    order_usd: float,
    abs_edge_pct: float,
    reason: str,
) -> RiskState:
    next_failures = state.consecutive_exec_failures + 1
    next_kill_switch = state.kill_switch or (next_failures >= settings.max_consecutive_exec_failures)
    next_state = replace(
        state,
        consecutive_exec_failures=next_failures,
        kill_switch=next_kill_switch,
    )
    if next_kill_switch and not state.kill_switch:
        payload = BotEventPayload(
            event_type="risk_alert",
            strategy="stx-ststx-arb-v1",
            event_time_utc=now,
            pool_id=pool_id,
            side=action.value.replace("_STSTX", ""),
            order_size_usd=order_usd,
            edge_pct_at_decision=abs_edge_pct,
            status="blocked",
            reason=(
                f"kill_switch_on:consecutive_exec_failures={next_failures}"
                f"/max={settings.max_consecutive_exec_failures},last_reason={reason}"
            ),
        )
        send_alert(db, notifier, payload)
        logging.error(
            "kill-switch activated due to execution failures: %s/%s",
            next_failures,
            settings.max_consecutive_exec_failures,
        )
    return next_state


def _handle_control_command(
    command: str,
    *,
    notifier: TelegramNotifier,
    state: RiskState,
) -> RiskState:
    if command in {"/pause", "/pauseserver"}:
        next_state = replace(state, manual_pause=True)
        notifier.send_text("거래를 일시정지했습니다. `/start` 또는 `/resume`으로 재개하세요.")
        return next_state

    if command in {"/start", "/startserver", "/resume"}:
        next_state = replace(
            state,
            manual_pause=False,
            kill_switch=False,
            consecutive_exec_failures=0,
            consecutive_losses=0,
            last_block_alert_reason="",
            last_block_alert_epoch=0.0,
        )
        notifier.send_text("거래를 재개했습니다.")
        return next_state

    return state


def _render_state_text(settings: Settings, state: RiskState) -> str:
    return "\n".join(
        [
            "[봇 상태]",
            f"manual_pause: {'on' if state.manual_pause else 'off'}",
            f"kill_switch: {'on' if state.kill_switch else 'off'}",
            f"consecutive_exec_failures: {state.consecutive_exec_failures}",
            f"consecutive_losses: {state.consecutive_losses}",
            f"running_pnl_stx: {state.running_pnl_stx:.6f}",
            f"require_prev_tx_success: {'on' if settings.require_prev_tx_success else 'off'}",
            f"prev_fail_retry_cooldown_sec: {settings.prev_fail_retry_cooldown_sec}",
            f"poll_interval_sec: {settings.poll_interval_sec}",
        ]
    )


def _render_cycle_text(status: CycleStatus) -> str:
    until_deadline_hours = status.blocks_until_last_288_window * 10.0 / 60.0
    until_deadline_days = until_deadline_hours / 24.0
    until_unlock_hours = status.blocks_until_unlock_if_init_now * 10.0 / 60.0
    until_unlock_days = until_unlock_hours / 24.0
    window_state = "열림(이번 사이클 마감 구간)" if status.in_last_288_window else "열리기 전"
    return "\n".join(
        [
            "[언스테이킹 사이클]",
            f"현재 burn height: {status.current_burnchain_block_height}",
            f"현재/다음 PoX cycle: {status.current_cycle_id} / {status.next_cycle_id}",
            f"마감구간(마지막 288블록) 상태: {window_state}",
            (
                f"마감구간 시작까지 남은 블록: {status.blocks_until_last_288_window} "
                f"(약 {until_deadline_days:.1f}일)"
            ),
            (
                f"지금 init-withdraw 시 unlock까지 남은 블록: {status.blocks_until_unlock_if_init_now} "
                f"(약 {until_unlock_days:.1f}일)"
            ),
            (
                "참고: 평균 10분/블록 기준 추정이며 실제 시간은 변동될 수 있음."
            ),
        ]
    )


def _render_pool_status_text(
    *,
    settings: Settings,
    pool_id: str,
    stx_usd: float,
    ststx_usd: float,
    liquidity_usd: float,
    signal: SignalDecision,
) -> str:
    action_kr = {
        "BUY_STSTX": "매수(STX->stSTX)",
        "SELL_STSTX": "매도(stSTX->STX)",
        "HOLD": "대기",
    }.get(signal.action.value, signal.action.value)
    return "\n".join(
        [
            "[풀 상태]",
            f"풀: {pool_id}",
            f"시장비율: {signal.market_stx_per_ststx:.6f} STX/stSTX",
            f"내재가치: {signal.intrinsic_stx_per_ststx:.6f} STX/stSTX",
            f"갭(edge): {signal.edge_pct:+.4f}%",
            f"절대갭(abs): {signal.abs_edge_pct:.4f}%",
            f"순갭(net): {signal.net_edge_pct:+.4f}%",
            f"현재판단: {action_kr} ({signal.reason})",
            f"추천주문금액: ${signal.order_usd:.2f}",
            f"추정슬리피지: {signal.slippage_pct:.4f}%",
            f"STX: ${stx_usd:.4f} | stSTX: ${ststx_usd:.4f}",
            f"유동성(USD): ${liquidity_usd:,.0f}",
            f"기준 진입임계치: {settings.entry_threshold_pct:.4f}%",
            f"시간: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        ]
    )


def maybe_send_cycle_hint(
    settings: Settings,
    hiro: HiroClient,
    notifier: TelegramNotifier,
    state: RiskState,
) -> RiskState:
    if not settings.tg_enabled or not settings.cycle_hint_enabled:
        return state
    try:
        status = hiro.fetch_cycle_status()
    except Exception:
        logging.exception("failed to fetch cycle status for hint")
        return state

    stage = ""
    if status.in_last_288_window:
        stage = "window_open"
    elif status.blocks_until_last_288_window <= settings.cycle_hint_threshold_blocks:
        stage = "window_soon"
    if not stage:
        return state

    if (
        state.cycle_hint_last_next_cycle_id == status.next_cycle_id
        and state.cycle_hint_last_stage == stage
    ):
        return state

    if stage == "window_open":
        prefix = "언스테이킹 마감구간(마지막 288블록)에 진입했어."
    else:
        prefix = (
            "언스테이킹 마감구간이 가까워졌어. "
            f"(<= {settings.cycle_hint_threshold_blocks} blocks)"
        )
    notifier.send_text(prefix + "\n" + _render_cycle_text(status))
    return replace(
        state,
        cycle_hint_last_next_cycle_id=status.next_cycle_id,
        cycle_hint_last_stage=stage,
    )


def maybe_send_high_gap_alert(
    *,
    settings: Settings,
    db: BotDB,
    notifier: TelegramNotifier,
    state: RiskState,
    now: str,
    pool_id: str,
    signal: SignalDecision,
) -> RiskState:
    if not settings.tg_enabled or not settings.high_gap_alert_enabled:
        return state

    threshold = max(0.0, settings.high_gap_threshold_pct)
    abs_edge = max(0.0, float(signal.abs_edge_pct))
    if abs_edge < threshold:
        if not state.high_gap_active:
            return state
        payload = BotEventPayload(
            event_type="risk_alert",
            strategy="stx-ststx-arb-v1",
            event_time_utc=now,
            pool_id=pool_id,
            side=signal.action.value.replace("_STSTX", ""),
            order_size_usd=signal.order_usd,
            edge_pct_at_decision=abs_edge,
            status="resolved",
            reason=f"high_gap_resolved:edge={abs_edge:.4f},threshold={threshold:.4f}",
        )
        send_alert(db, notifier, payload)
        return replace(
            state,
            high_gap_active=False,
            high_gap_last_alert_epoch=0.0,
            high_gap_last_bucket=-1,
            high_gap_last_sign=0,
        )

    sign = 1 if signal.edge_pct >= 0 else -1
    step = max(0.0001, settings.high_gap_step_pct)
    bucket = int((abs_edge - threshold) // step)
    now_epoch = time.time()
    reason = ""

    if not state.high_gap_active or sign != state.high_gap_last_sign:
        reason = (
            "high_gap_enter:"
            f"edge={abs_edge:.4f},threshold={threshold:.4f},step={step:.4f},bucket={bucket},sign={sign}"
        )
    elif bucket > state.high_gap_last_bucket:
        reason = (
            "high_gap_expand:"
            f"edge={abs_edge:.4f},threshold={threshold:.4f},step={step:.4f},bucket={bucket},prev_bucket={state.high_gap_last_bucket}"
        )
    elif now_epoch - state.high_gap_last_alert_epoch >= settings.high_gap_repeat_sec:
        reason = (
            "high_gap_reminder:"
            f"edge={abs_edge:.4f},threshold={threshold:.4f},repeat={settings.high_gap_repeat_sec}s,bucket={bucket}"
        )
    else:
        return state

    payload = BotEventPayload(
        event_type="risk_alert",
        strategy="stx-ststx-arb-v1",
        event_time_utc=now,
        pool_id=pool_id,
        side=signal.action.value.replace("_STSTX", ""),
        order_size_usd=signal.order_usd,
        edge_pct_at_decision=abs_edge,
        status="warning",
        reason=reason,
    )
    send_alert(db, notifier, payload)
    return replace(
        state,
        high_gap_active=True,
        high_gap_last_alert_epoch=now_epoch,
        high_gap_last_bucket=bucket,
        high_gap_last_sign=sign,
    )


def run_cycle(
    settings: Settings,
    db: BotDB,
    cg: CoinGeckoClient,
    bf: BitflowClient,
    hiro: HiroClient,
    notifier: TelegramNotifier,
    executor: Executor,
    risk_state: RiskState,
) -> RiskState:
    now = utc_now_iso()
    prices = cg.fetch_prices()
    pool = bf.fetch_pool(settings.bitflow_ststx_pool_id)
    intrinsic = hiro.fetch_intrinsic_stx_per_ststx()

    signal_in = SignalInput(
        stx_usd=prices.stx_usd,
        ststx_usd=prices.ststx_usd,
        intrinsic_stx_per_ststx=intrinsic,
        liquidity_usd=pool.liquidity_in_usd,
        max_order_usd=settings.max_order_usd,
        entry_threshold_pct=settings.entry_threshold_pct,
        min_liquidity_usd=settings.min_liquidity_usd,
        dex_fee_pct=settings.dex_fee_pct,
        execution_buffer_pct=settings.execution_buffer_pct,
    )
    decision = build_signal(signal_in)
    risk_state = maybe_send_high_gap_alert(
        settings=settings,
        db=db,
        notifier=notifier,
        state=risk_state,
        now=now,
        pool_id=pool.pool_id,
        signal=decision,
    )

    signal_id = db.insert_signal(
        event_time_utc=now,
        pool_id=pool.pool_id,
        market_stx_per_ststx=decision.market_stx_per_ststx,
        intrinsic_stx_per_ststx=decision.intrinsic_stx_per_ststx,
        edge_pct=decision.edge_pct,
        abs_edge_pct=decision.abs_edge_pct,
        slippage_pct=decision.slippage_pct,
        net_edge_pct=decision.net_edge_pct,
        action=decision.action.value,
        should_enter=decision.should_enter,
        reason=decision.reason,
        order_usd=decision.order_usd,
    )
    if decision.should_enter:
        return _execute_trade(
            settings=settings,
            db=db,
            hiro=hiro,
            notifier=notifier,
            executor=executor,
            risk_state=risk_state,
            now=now,
            pool_id=pool.pool_id,
            stx_usd=prices.stx_usd,
            ststx_usd=prices.ststx_usd,
            market_stx_per_ststx=decision.market_stx_per_ststx,
            intrinsic_stx_per_ststx=decision.intrinsic_stx_per_ststx,
            net_edge_pct=decision.net_edge_pct,
            signal_id=signal_id,
            action=decision.action,
            order_usd=decision.order_usd,
            slippage_pct=decision.slippage_pct,
            abs_edge_pct=decision.abs_edge_pct,
            order_reason="entry_ok",
        )

    rebalance = _build_rebalance_or_none(
        settings=settings,
        db=db,
        hiro=hiro,
        prices_stx_usd=prices.stx_usd,
        prices_ststx_usd=prices.ststx_usd,
        liquidity_usd=pool.liquidity_in_usd,
        abs_edge_pct=decision.abs_edge_pct,
        signal_action=decision.action,
        now=now,
    )
    if rebalance and rebalance.should_rebalance:
        logging.info(
            "rebalance trigger action=%s drift=%.2f%% net=%.4f%%",
            rebalance.action.value,
            rebalance.drift_abs_pct,
            rebalance.rebalance_net_pct,
        )
        return _execute_trade(
            settings=settings,
            db=db,
            hiro=hiro,
            notifier=notifier,
            executor=executor,
            risk_state=risk_state,
            now=now,
            pool_id=pool.pool_id,
            stx_usd=prices.stx_usd,
            ststx_usd=prices.ststx_usd,
            market_stx_per_ststx=decision.market_stx_per_ststx,
            intrinsic_stx_per_ststx=decision.intrinsic_stx_per_ststx,
            net_edge_pct=rebalance.rebalance_net_pct,
            signal_id=signal_id,
            action=rebalance.action,
            order_usd=rebalance.order_usd,
            slippage_pct=rebalance.slippage_pct,
            abs_edge_pct=decision.abs_edge_pct,
            order_reason=rebalance.reason,
        )

    hold_reason = decision.reason
    if rebalance and not rebalance.should_rebalance:
        hold_reason = f"{decision.reason}|{rebalance.reason}"
    db.insert_order(
        signal_id=signal_id,
        event_time_utc=now,
        side="HOLD",
        pool_id=pool.pool_id,
        order_size_usd=decision.order_usd,
        status="skipped",
        reason=hold_reason,
    )
    logging.info("signal skipped: %s", hold_reason)
    return risk_state


def update_daily_pnl(db: BotDB, settings: Settings, trade_pnl_stx: float) -> None:
    day = utc_day()
    row = db.fetch_daily_pnl(day)
    if row is None:
        trade_count = 1
        win_count = 1 if trade_pnl_stx > 0 else 0
        loss_count = 1 if trade_pnl_stx < 0 else 0
        running = trade_pnl_stx
    else:
        trade_count = int(row["trade_count"]) + 1
        win_count = int(row["win_count"]) + (1 if trade_pnl_stx > 0 else 0)
        loss_count = int(row["loss_count"]) + (1 if trade_pnl_stx < 0 else 0)
        running = float(row["running_pnl_stx"]) + trade_pnl_stx

    db.upsert_daily_pnl(
        day_utc=day,
        start_equity_stx=settings.daily_start_equity_stx,
        end_equity_stx=settings.daily_start_equity_stx + running,
        running_pnl_stx=running,
        trade_count=trade_count,
        win_count=win_count,
        loss_count=loss_count,
    )


def send_alert(db: BotDB, notifier: TelegramNotifier, payload: BotEventPayload) -> None:
    try:
        sent = notifier.send(payload)
        status = "sent" if sent else "skipped"
        db.insert_alert(
            event_time_utc=payload.event_time_utc,
            event_type=payload.event_type,
            payload=payload,
            status=status,
            error_message=None,
        )
    except Exception as exc:
        db.insert_alert(
            event_time_utc=payload.event_time_utc,
            event_type=payload.event_type,
            payload=payload,
            status="failed",
            error_message=str(exc),
        )
        logging.exception("failed to send alert")


def handle_telegram_commands(
    settings: Settings,
    cg: CoinGeckoClient,
    bf: BitflowClient,
    hiro: HiroClient,
    notifier: TelegramNotifier,
    state: RiskState,
) -> RiskState:
    if not settings.tg_enabled:
        return state
    try:
        commands = notifier.fetch_commands()
    except Exception:
        logging.exception("failed to fetch telegram commands")
        return state

    next_state = state
    for cmd in commands:
        command = cmd.text.split()[0].lower()
        if command in {"/pause", "/pauseserver", "/start", "/startserver", "/resume"}:
            next_state = _handle_control_command(command, notifier=notifier, state=next_state)
            continue
        if command == "/state":
            notifier.send_text(_render_state_text(settings, next_state))
            continue
        if command == "/cycle":
            try:
                cycle_status = hiro.fetch_cycle_status()
                notifier.send_text(_render_cycle_text(cycle_status))
            except Exception:
                logging.exception("failed to build /cycle response")
                notifier.send_text("/cycle 조회 중 오류가 발생했습니다.")
            continue
        if command == "/poolstatus":
            try:
                prices = cg.fetch_prices()
                pool = bf.fetch_pool(settings.bitflow_ststx_pool_id)
                intrinsic = hiro.fetch_intrinsic_stx_per_ststx()
                signal_in = SignalInput(
                    stx_usd=prices.stx_usd,
                    ststx_usd=prices.ststx_usd,
                    intrinsic_stx_per_ststx=intrinsic,
                    liquidity_usd=pool.liquidity_in_usd,
                    max_order_usd=settings.max_order_usd,
                    entry_threshold_pct=settings.entry_threshold_pct,
                    min_liquidity_usd=settings.min_liquidity_usd,
                    dex_fee_pct=settings.dex_fee_pct,
                    execution_buffer_pct=settings.execution_buffer_pct,
                )
                signal = build_signal(signal_in)
                notifier.send_text(
                    _render_pool_status_text(
                        settings=settings,
                        pool_id=pool.pool_id,
                        stx_usd=prices.stx_usd,
                        ststx_usd=prices.ststx_usd,
                        liquidity_usd=pool.liquidity_in_usd,
                        signal=signal,
                    )
                )
            except Exception:
                logging.exception("failed to build /poolstatus response")
                notifier.send_text("/poolstatus 조회 중 오류가 발생했습니다.")
            continue
        if command != "/status":
            continue
        if not settings.trading_address:
            notifier.send_text("지갑 주소(TRADING_ADDRESS)가 설정되지 않았습니다.")
            continue
        try:
            intrinsic = hiro.fetch_intrinsic_stx_per_ststx()
            balances = hiro.fetch_wallet_balances(settings.trading_address, settings.ststx_token_contract)
            ststx_as_stx = balances.ststx_balance * intrinsic
            total_stx = balances.stx_balance + ststx_as_stx
            text = "\n".join(
                [
                    "[지갑 상태]",
                    f"주소: {settings.trading_address}",
                    f"STX: {balances.stx_balance:.6f}",
                    f"stSTX: {balances.ststx_balance:.6f}",
                    f"환산비율: 1 stSTX = {intrinsic:.6f} STX",
                    f"stSTX 환산(STX): {ststx_as_stx:.6f}",
                    f"총 보유(STX 환산): {total_stx:.6f}",
                    f"시간: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
                ]
            )
            notifier.send_text(text)
        except Exception:
            logging.exception("failed to build /status response")
            notifier.send_text("/status 조회 중 오류가 발생했습니다.")
    return next_state


def main() -> None:
    parser = argparse.ArgumentParser(description="STX/stSTX arbitrage bot loop")
    parser.add_argument("--once", action="store_true", help="run one cycle and exit")
    args = parser.parse_args()

    settings = load_settings()
    setup_logger(settings.log_level)

    db = BotDB(settings.db_path)
    db.init_schema()

    cg = CoinGeckoClient(
        api_base=settings.coingecko_api_base,
        stx_coin_id=settings.stx_coingecko_id,
        ststx_coin_id=settings.ststx_coingecko_id,
    )
    bf = BitflowClient(settings.bitflow_ticker_url)
    hiro = HiroClient(settings.hiro_api_base)
    notifier = TelegramNotifier(
        bot_token=settings.tg_bot_token,
        chat_id=settings.tg_chat_id,
        enabled=settings.tg_enabled,
        parse_mode=settings.tg_parse_mode,
    )
    executor = Executor(
        trading_private_key=settings.trading_private_key,
        min_fee_floor_stx=settings.min_fee_floor_stx,
        fee_multiplier=settings.fee_multiplier,
        network_fee_cap_stx=settings.network_fee_cap_stx,
        executor_command=settings.executor_command,
        timeout_sec=settings.executor_timeout_sec,
    )

    risk_state = RiskState(
        daily_start_equity_stx=settings.daily_start_equity_stx,
        running_pnl_stx=db.fetch_latest_running_pnl_stx(),
        consecutive_losses=0,
        consecutive_exec_failures=0,
        manual_pause=False,
        kill_switch=False,
    )

    logging.info("bot started dry_run=%s", settings.dry_run)
    next_cycle_hint_check_at = 0.0
    if args.once:
        risk_state = handle_telegram_commands(settings, cg, bf, hiro, notifier, risk_state)
        risk_state = maybe_send_cycle_hint(settings, hiro, notifier, risk_state)
        run_cycle(settings, db, cg, bf, hiro, notifier, executor, risk_state)
        return

    while True:
        try:
            risk_state = handle_telegram_commands(settings, cg, bf, hiro, notifier, risk_state)
            if time.time() >= next_cycle_hint_check_at:
                risk_state = maybe_send_cycle_hint(settings, hiro, notifier, risk_state)
                next_cycle_hint_check_at = time.time() + settings.cycle_hint_check_interval_sec
            risk_state = run_cycle(settings, db, cg, bf, hiro, notifier, executor, risk_state)
        except Exception:
            logging.exception("cycle failed")
        time.sleep(settings.poll_interval_sec)


if __name__ == "__main__":
    main()
