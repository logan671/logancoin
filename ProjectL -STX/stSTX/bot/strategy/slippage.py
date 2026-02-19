from __future__ import annotations


def estimate_slippage_pct(order_usd: float, liquidity_usd: float) -> float:
    """
    Rough impact model for sizing screen.

    impact_pct ~= 2 * order_usd / liquidity_usd * 100
    """
    if order_usd <= 0:
        return 0.0
    if liquidity_usd <= 0:
        return 100.0
    return (2.0 * order_usd / liquidity_usd) * 100.0

