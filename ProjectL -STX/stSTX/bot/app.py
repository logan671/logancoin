from __future__ import annotations

import argparse
import logging
import time
from dataclasses import replace
from datetime import datetime, timezone

from bot.config import Settings, load_settings
from bot.data.bitflow_client import BitflowClient
from bot.data.coingecko_client import CoinGeckoClient
from bot.data.hiro_client import HiroClient
from bot.execution.executor import ExecutionRequest, Executor
from bot.notify.telegram_notifier import BotEventPayload, TelegramNotifier
from bot.risk.guard import RiskLimits, RiskState, check_pre_trade
from bot.storage.db import BotDB, utc_now_iso
from bot.strategy.rebalance import RebalanceDecision, RebalanceInput, build_rebalance_decision
from bot.strategy.signal import SignalAction, SignalInput, build_signal


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
    risk_limits = RiskLimits(
        max_order_usd=settings.max_order_usd,
        max_daily_loss_pct=settings.max_daily_loss_pct,
        max_consecutive_losses=settings.max_consecutive_losses,
    )
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
        logging.warning("risk blocked: %s", risk_decision.reason)
        return risk_state

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
        next_state = replace(risk_state, running_pnl_stx=running_pnl_stx, consecutive_losses=next_losses)
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

    fee_rate_micro = hiro.fetch_transfer_fee_rate_microstx_per_byte()
    hiro_estimate_stx = (fee_rate_micro * settings.tx_estimated_bytes) / 1_000_000.0
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
        next_state = replace(risk_state, running_pnl_stx=running_pnl_stx, consecutive_losses=next_losses)
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
    return risk_state


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


def handle_telegram_commands(settings: Settings, hiro: HiroClient, notifier: TelegramNotifier) -> None:
    if not settings.tg_enabled:
        return
    try:
        commands = notifier.fetch_commands()
    except Exception:
        logging.exception("failed to fetch telegram commands")
        return

    for cmd in commands:
        command = cmd.text.split()[0].lower()
        command = command.split("@", 1)[0]
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
                    "지갑 상태",
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
        kill_switch=False,
    )

    logging.info("bot started dry_run=%s", settings.dry_run)
    if args.once:
        handle_telegram_commands(settings, hiro, notifier)
        run_cycle(settings, db, cg, bf, hiro, notifier, executor, risk_state)
        return

    while True:
        try:
            handle_telegram_commands(settings, hiro, notifier)
            risk_state = run_cycle(settings, db, cg, bf, hiro, notifier, executor, risk_state)
        except Exception:
            logging.exception("cycle failed")
        time.sleep(settings.poll_interval_sec)


if __name__ == "__main__":
    main()
