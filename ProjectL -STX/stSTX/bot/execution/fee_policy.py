from __future__ import annotations


def compute_final_fee_stx(
    *,
    hiro_estimate_stx: float,
    min_fee_floor_stx: float,
    fee_multiplier: float,
    network_fee_cap_stx: float,
) -> float:
    if hiro_estimate_stx < 0:
        raise ValueError("hiro_estimate_stx must be >= 0")
    if min_fee_floor_stx <= 0:
        raise ValueError("min_fee_floor_stx must be > 0")
    if fee_multiplier < 1.0:
        raise ValueError("fee_multiplier must be >= 1.0")
    if network_fee_cap_stx <= 0:
        raise ValueError("network_fee_cap_stx must be > 0")

    recommended = max(hiro_estimate_stx, min_fee_floor_stx)
    return min(recommended * fee_multiplier, network_fee_cap_stx)

