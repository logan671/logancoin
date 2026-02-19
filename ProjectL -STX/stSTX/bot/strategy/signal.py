from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .slippage import estimate_slippage_pct


class SignalAction(str, Enum):
    BUY_STSTX = "BUY_STSTX"
    SELL_STSTX = "SELL_STSTX"
    HOLD = "HOLD"


@dataclass(frozen=True)
class SignalInput:
    stx_usd: float
    ststx_usd: float
    intrinsic_stx_per_ststx: float
    liquidity_usd: float
    max_order_usd: float
    entry_threshold_pct: float
    min_liquidity_usd: float
    dex_fee_pct: float
    execution_buffer_pct: float


@dataclass(frozen=True)
class SignalDecision:
    should_enter: bool
    action: SignalAction
    reason: str
    market_stx_per_ststx: float
    intrinsic_stx_per_ststx: float
    edge_pct: float
    abs_edge_pct: float
    slippage_pct: float
    net_edge_pct: float
    order_usd: float


def build_signal(data: SignalInput) -> SignalDecision:
    _validate_input(data)

    market_ratio = data.ststx_usd / data.stx_usd
    edge_pct = ((market_ratio / data.intrinsic_stx_per_ststx) - 1.0) * 100.0
    abs_edge_pct = abs(edge_pct)

    # edge < 0 means market ratio < intrinsic => stSTX is cheap vs STX
    action = SignalAction.BUY_STSTX if edge_pct < 0 else SignalAction.SELL_STSTX

    order_usd = _recommend_order_usd(
        abs_edge_pct=abs_edge_pct,
        entry_threshold_pct=data.entry_threshold_pct,
        max_order_usd=data.max_order_usd,
    )
    slippage_pct = estimate_slippage_pct(order_usd=order_usd, liquidity_usd=data.liquidity_usd)
    net_edge_pct = abs_edge_pct - data.dex_fee_pct - slippage_pct - data.execution_buffer_pct

    if data.liquidity_usd < data.min_liquidity_usd:
        return SignalDecision(
            should_enter=False,
            action=SignalAction.HOLD,
            reason="liquidity_below_min",
            market_stx_per_ststx=market_ratio,
            intrinsic_stx_per_ststx=data.intrinsic_stx_per_ststx,
            edge_pct=edge_pct,
            abs_edge_pct=abs_edge_pct,
            slippage_pct=slippage_pct,
            net_edge_pct=net_edge_pct,
            order_usd=order_usd,
        )

    if abs_edge_pct < data.entry_threshold_pct:
        return SignalDecision(
            should_enter=False,
            action=SignalAction.HOLD,
            reason="edge_below_threshold",
            market_stx_per_ststx=market_ratio,
            intrinsic_stx_per_ststx=data.intrinsic_stx_per_ststx,
            edge_pct=edge_pct,
            abs_edge_pct=abs_edge_pct,
            slippage_pct=slippage_pct,
            net_edge_pct=net_edge_pct,
            order_usd=order_usd,
        )

    if net_edge_pct <= 0:
        return SignalDecision(
            should_enter=False,
            action=SignalAction.HOLD,
            reason="net_edge_non_positive",
            market_stx_per_ststx=market_ratio,
            intrinsic_stx_per_ststx=data.intrinsic_stx_per_ststx,
            edge_pct=edge_pct,
            abs_edge_pct=abs_edge_pct,
            slippage_pct=slippage_pct,
            net_edge_pct=net_edge_pct,
            order_usd=order_usd,
        )

    return SignalDecision(
        should_enter=True,
        action=action,
        reason="entry_ok",
        market_stx_per_ststx=market_ratio,
        intrinsic_stx_per_ststx=data.intrinsic_stx_per_ststx,
        edge_pct=edge_pct,
        abs_edge_pct=abs_edge_pct,
        slippage_pct=slippage_pct,
        net_edge_pct=net_edge_pct,
        order_usd=order_usd,
    )


def _recommend_order_usd(abs_edge_pct: float, entry_threshold_pct: float, max_order_usd: float) -> float:
    """
    Dynamic size between 100 and max_order_usd.
    Larger edge gives larger position, capped at max_order_usd.
    """
    min_order = min(100.0, max_order_usd)
    if abs_edge_pct <= entry_threshold_pct:
        return min_order

    # Linear ramp over +1.5% edge range.
    ramp = min(1.0, (abs_edge_pct - entry_threshold_pct) / 1.5)
    return min_order + (max_order_usd - min_order) * ramp


def _validate_input(data: SignalInput) -> None:
    if data.stx_usd <= 0:
        raise ValueError("stx_usd must be > 0")
    if data.ststx_usd <= 0:
        raise ValueError("ststx_usd must be > 0")
    if data.intrinsic_stx_per_ststx <= 0:
        raise ValueError("intrinsic_stx_per_ststx must be > 0")
    if data.max_order_usd <= 0:
        raise ValueError("max_order_usd must be > 0")
    if data.entry_threshold_pct <= 0:
        raise ValueError("entry_threshold_pct must be > 0")
    if data.min_liquidity_usd < 0:
        raise ValueError("min_liquidity_usd must be >= 0")
    if data.dex_fee_pct < 0:
        raise ValueError("dex_fee_pct must be >= 0")
    if data.execution_buffer_pct < 0:
        raise ValueError("execution_buffer_pct must be >= 0")

