from __future__ import annotations


def compute_intrinsic_stx_per_ststx(
    reserve_total_stx: float,
    ststx_supply: float,
    ststxbtc_supply: float,
    ststxbtc_v2_supply: float,
) -> float:
    """
    Compute intrinsic STX per stSTX from on-chain supplies.

    Formula:
      stx_for_ststx = reserve_total_stx - ststxbtc_supply - ststxbtc_v2_supply
      intrinsic = stx_for_ststx / ststx_supply
    """
    if ststx_supply <= 0:
        raise ValueError("ststx_supply must be > 0")

    stx_for_ststx = reserve_total_stx - ststxbtc_supply - ststxbtc_v2_supply
    if stx_for_ststx <= 0:
        raise ValueError("stx_for_ststx must be > 0")

    return stx_for_ststx / ststx_supply

