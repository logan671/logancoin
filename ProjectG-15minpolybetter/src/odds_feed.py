from __future__ import annotations

from datetime import datetime, timedelta

from .compat import UTC, dataclass


@dataclass(slots=True)
class OrderLevel:
    price: float
    size: float


@dataclass(slots=True)
class MarketBook:
    token_id: str
    best_bid: OrderLevel | None
    best_ask: OrderLevel | None
    last_trade_ts: datetime | None = None

    @property
    def spread(self) -> float | None:
        if not self.best_bid or not self.best_ask:
            return None
        return self.best_ask.price - self.best_bid.price

    @property
    def implied_odds(self) -> float | None:
        if not self.best_ask:
            return None
        return self.best_ask.price


def _to_float(value: object) -> float:
    return float(str(value))


def parse_orderbook_message(message: dict) -> MarketBook:
    token_id = str(message.get("asset_id") or message.get("token_id") or "").strip()
    if not token_id:
        raise ValueError("orderbook message missing token id")

    bids = message.get("bids", None)
    asks = message.get("asks", None)
    if bids is None and asks is None:
        bids = message.get("buys", [])
        asks = message.get("sells", [])

    best_bid = None
    best_ask = None

    if bids:
        top = bids[0]
        best_bid = OrderLevel(price=_to_float(top["price"]), size=_to_float(top["size"]))

    if asks:
        top = asks[0]
        best_ask = OrderLevel(price=_to_float(top["price"]), size=_to_float(top["size"]))

    ts = None
    raw_ts = message.get("timestamp")
    if raw_ts is not None:
        ts_value = float(raw_ts)
        if ts_value > 1_000_000_000_000:
            ts_value = ts_value / 1000.0
        ts = datetime.fromtimestamp(ts_value, tz=UTC)

    return MarketBook(
        token_id=token_id,
        best_bid=best_bid,
        best_ask=best_ask,
        last_trade_ts=ts,
    )


def has_recent_trade(last_trade_ts: datetime | None, window_seconds: int, now: datetime | None = None) -> bool:
    if last_trade_ts is None:
        return False
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    return current - last_trade_ts <= timedelta(seconds=window_seconds)


def passes_liquidity_filter(
    book: MarketBook,
    bet_size: float,
    ask_multiplier: float,
    max_spread: float,
    recent_trade_window: int,
    now: datetime | None = None,
) -> tuple[bool, str]:
    if not book.best_bid or not book.best_ask:
        return False, "missing-best-level"

    spread = book.spread
    if spread is None:
        return False, "missing-spread"
    if spread > max_spread:
        return False, "wide-spread"

    required_ask = bet_size * ask_multiplier
    if book.best_ask.size < required_ask:
        return False, "insufficient-ask-size"

    if not has_recent_trade(book.last_trade_ts, recent_trade_window, now=now):
        return False, "stale-trade"

    return True, "ok"
