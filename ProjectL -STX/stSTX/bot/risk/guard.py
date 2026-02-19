from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskLimits:
    max_order_usd: float
    max_daily_loss_pct: float
    max_consecutive_losses: int


@dataclass(frozen=True)
class RiskState:
    daily_start_equity_stx: float
    running_pnl_stx: float
    consecutive_losses: int
    kill_switch: bool = False


@dataclass(frozen=True)
class RiskDecision:
    allowed: bool
    reason: str


def check_pre_trade(
    order_usd: float,
    limits: RiskLimits,
    state: RiskState,
) -> RiskDecision:
    if state.kill_switch:
        return RiskDecision(allowed=False, reason="kill_switch_on")

    if order_usd <= 0:
        return RiskDecision(allowed=False, reason="invalid_order_size")

    if order_usd > limits.max_order_usd:
        return RiskDecision(allowed=False, reason="order_above_max")

    if state.consecutive_losses >= limits.max_consecutive_losses:
        return RiskDecision(allowed=False, reason="max_consecutive_losses_reached")

    if state.daily_start_equity_stx <= 0:
        return RiskDecision(allowed=False, reason="invalid_daily_start_equity")

    daily_loss_pct = _compute_daily_loss_pct(
        daily_start_equity_stx=state.daily_start_equity_stx,
        running_pnl_stx=state.running_pnl_stx,
    )
    if daily_loss_pct >= limits.max_daily_loss_pct:
        return RiskDecision(allowed=False, reason="max_daily_loss_reached")

    return RiskDecision(allowed=True, reason="risk_ok")


def _compute_daily_loss_pct(daily_start_equity_stx: float, running_pnl_stx: float) -> float:
    if running_pnl_stx >= 0:
        return 0.0
    return abs(running_pnl_stx) / daily_start_equity_stx * 100.0

