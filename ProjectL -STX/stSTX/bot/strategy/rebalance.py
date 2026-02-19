from __future__ import annotations

from dataclasses import dataclass

from bot.data.hiro_client import WalletBalances
from bot.strategy.signal import SignalAction
from bot.strategy.slippage import estimate_slippage_pct


@dataclass(frozen=True)
class RebalanceInput:
    balances: WalletBalances
    stx_usd: float
    ststx_usd: float
    liquidity_usd: float
    target_stx_weight: float
    drift_pct: float
    min_order_usd: float
    max_order_usd: float
    dex_fee_pct: float
    buffer_pct: float
    abs_edge_pct: float
    signal_action: SignalAction
    daily_count: int
    max_per_day: int


@dataclass(frozen=True)
class RebalanceDecision:
    should_rebalance: bool
    action: SignalAction
    reason: str
    order_usd: float
    current_stx_weight: float
    drift_abs_pct: float
    slippage_pct: float
    expected_improvement_pct: float
    rebalance_net_pct: float


def build_rebalance_decision(x: RebalanceInput) -> RebalanceDecision:
    if x.daily_count >= x.max_per_day:
        return _skip("rebalance_daily_limit", x)

    stx_value = x.balances.stx_balance * x.stx_usd
    ststx_value = x.balances.ststx_balance * x.ststx_usd
    total_value = stx_value + ststx_value
    if total_value <= 0:
        return _skip("rebalance_empty_portfolio", x)

    current_stx_weight = stx_value / total_value
    drift_abs_pct = abs(current_stx_weight - x.target_stx_weight) * 100.0
    if drift_abs_pct < x.drift_pct:
        return _skip("rebalance_drift_small", x, current_stx_weight=current_stx_weight, drift_abs_pct=drift_abs_pct)

    action = SignalAction.BUY_STSTX if current_stx_weight > x.target_stx_weight else SignalAction.SELL_STSTX
    expected_improvement_pct = x.abs_edge_pct if action == x.signal_action else 0.0

    drift_ratio = min(1.0, drift_abs_pct / max(x.drift_pct, 1e-6))
    order_usd = x.min_order_usd + (x.max_order_usd - x.min_order_usd) * drift_ratio
    slippage_pct = estimate_slippage_pct(order_usd=order_usd, liquidity_usd=x.liquidity_usd)
    rebalance_net_pct = expected_improvement_pct - x.dex_fee_pct - slippage_pct - x.buffer_pct
    if rebalance_net_pct <= 0:
        return RebalanceDecision(
            should_rebalance=False,
            action=SignalAction.HOLD,
            reason="rebalance_net_non_positive",
            order_usd=order_usd,
            current_stx_weight=current_stx_weight,
            drift_abs_pct=drift_abs_pct,
            slippage_pct=slippage_pct,
            expected_improvement_pct=expected_improvement_pct,
            rebalance_net_pct=rebalance_net_pct,
        )

    return RebalanceDecision(
        should_rebalance=True,
        action=action,
        reason="rebalance_entry_ok",
        order_usd=order_usd,
        current_stx_weight=current_stx_weight,
        drift_abs_pct=drift_abs_pct,
        slippage_pct=slippage_pct,
        expected_improvement_pct=expected_improvement_pct,
        rebalance_net_pct=rebalance_net_pct,
    )


def _skip(
    reason: str,
    x: RebalanceInput,
    *,
    current_stx_weight: float = 0.0,
    drift_abs_pct: float = 0.0,
) -> RebalanceDecision:
    return RebalanceDecision(
        should_rebalance=False,
        action=SignalAction.HOLD,
        reason=reason,
        order_usd=0.0,
        current_stx_weight=current_stx_weight,
        drift_abs_pct=drift_abs_pct,
        slippage_pct=0.0,
        expected_improvement_pct=0.0,
        rebalance_net_pct=0.0,
    )
