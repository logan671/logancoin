from __future__ import annotations

from .compat import dataclass


@dataclass(slots=True)
class SignalInput:
    odds: float
    side: str
    momentum_5m: float | None
    direction: str | None
    is_data_fresh: bool
    liquidity_ok: bool
    remaining_seconds: int
    has_open_position: bool
    buyin_balance: float
    min_bet_size: float
    circuit_breaker_active: bool


@dataclass(slots=True)
class SignalDecision:
    should_trade: bool
    zone: str | None
    bet_size: float
    reason: str


@dataclass(slots=True)
class SignalThresholds:
    odds_caution_min: float = 0.85
    odds_caution_max: float = 0.89
    odds_standard_min: float = 0.90
    odds_standard_max: float = 0.94
    odds_confidence_min: float = 0.95
    momentum_caution: float = 0.005
    momentum_standard: float = 0.003
    bet_pct_caution: float = 0.05
    bet_pct_standard: float = 0.10
    bet_pct_confidence: float = 0.15
    max_bet_pct: float = 0.15
    min_remaining_seconds: int = 120


DEFAULT_THRESHOLDS = SignalThresholds()


def determine_zone(odds: float, t: SignalThresholds = DEFAULT_THRESHOLDS) -> str | None:
    if t.odds_caution_min <= odds <= t.odds_caution_max:
        return "caution"
    if t.odds_standard_min <= odds <= t.odds_standard_max:
        return "standard"
    if odds >= t.odds_confidence_min:
        return "confidence"
    return None


def calculate_bet_size(zone: str, buyin_balance: float, t: SignalThresholds = DEFAULT_THRESHOLDS) -> float:
    if zone == "caution":
        pct = t.bet_pct_caution
    elif zone == "standard":
        pct = t.bet_pct_standard
    elif zone == "confidence":
        pct = t.bet_pct_confidence
    else:
        raise ValueError("unknown zone")

    bet_size = buyin_balance * pct
    max_allowed = buyin_balance * t.max_bet_pct
    return round(min(bet_size, max_allowed), 2)


def _direction_matches(side: str, direction: str | None) -> bool:
    normalized_side = side.lower()
    if normalized_side not in {"up", "down"}:
        return False
    if direction not in {"up", "down", "flat"}:
        return False
    return normalized_side == direction


def should_trade(data: SignalInput, t: SignalThresholds = DEFAULT_THRESHOLDS) -> SignalDecision:
    zone = determine_zone(data.odds, t=t)
    if zone is None:
        return SignalDecision(False, None, 0.0, "odds-below-threshold")

    if data.circuit_breaker_active:
        return SignalDecision(False, zone, 0.0, "circuit-breaker-active")
    if data.has_open_position:
        return SignalDecision(False, zone, 0.0, "open-position-exists")
    if not data.is_data_fresh:
        return SignalDecision(False, zone, 0.0, "stale-price-data")
    if not data.liquidity_ok:
        return SignalDecision(False, zone, 0.0, "liquidity-filter-failed")
    if data.remaining_seconds < t.min_remaining_seconds:
        return SignalDecision(False, zone, 0.0, "insufficient-time-remaining")
    if not _direction_matches(data.side, data.direction):
        return SignalDecision(False, zone, 0.0, "direction-mismatch")

    if zone == "caution":
        if data.momentum_5m is None or abs(data.momentum_5m) < t.momentum_caution:
            return SignalDecision(False, zone, 0.0, "insufficient-momentum-caution")
    elif zone == "standard":
        if data.momentum_5m is None or abs(data.momentum_5m) < t.momentum_standard:
            return SignalDecision(False, zone, 0.0, "insufficient-momentum-standard")

    bet_size = calculate_bet_size(zone, data.buyin_balance, t=t)
    if data.buyin_balance < data.min_bet_size:
        return SignalDecision(False, zone, 0.0, "buyin-below-minimum")
    if bet_size < data.min_bet_size:
        return SignalDecision(False, zone, 0.0, "computed-bet-below-minimum")

    return SignalDecision(True, zone, bet_size, "ok")
