from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from .binance_ws import run_price_feed
from .compat import UTC
from .config import settings
from .observation_store import Observation, init_db, log_observation
from .odds_feed import MarketBook, passes_liquidity_filter
from .polymarket_orchestrator import run_market_subscription
from .price_feed import SymbolPriceBuffer
from .signal_engine import SignalInput, calculate_bet_size, determine_zone, should_trade

logger = logging.getLogger(__name__)


def _ensure_logging() -> None:
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)


async def run_btc_observer(stop_event: asyncio.Event | None = None) -> None:
    _ensure_logging()
    init_db(settings.DB_PATH)
    stop_event = stop_event or asyncio.Event()
    print(f"BTC observer started (db={settings.DB_PATH})", flush=True)
    logger.info("BTC observer started (db=%s)", settings.DB_PATH)
    last_logged_ts: datetime | None = None
    price_buffer = SymbolPriceBuffer(max_window_seconds=300)
    current_market = {"yes": None, "no": None, "end": None}

    async def on_market(market) -> None:
        current_market["yes"] = market.yes_token_id
        current_market["no"] = market.no_token_id
        current_market["end"] = market.end_date_iso
        logger.info("market set slug=%s", market.slug)

    def _side_for_token(token_id: str | None) -> str | None:
        if token_id is None:
            return None
        if current_market["yes"] == token_id:
            return "up"
        if current_market["no"] == token_id:
            return "down"
        return None

    def _remaining_seconds(now: datetime) -> int:
        end_iso = current_market["end"]
        if not end_iso:
            return 0
        text = str(end_iso).replace("Z", "+00:00")
        try:
            end_dt = datetime.fromisoformat(text)
        except ValueError:
            return 0
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=UTC)
        else:
            end_dt = end_dt.astimezone(UTC)
        return max(0, int((end_dt - now).total_seconds()))

    async def on_book(book: MarketBook) -> None:
        nonlocal last_logged_ts
        if book.implied_odds is None:
            return
        now = datetime.now(UTC)
        if last_logged_ts is not None and (now - last_logged_ts).total_seconds() < 60:
            return
        latest_price = price_buffer.latest()
        momentum = price_buffer.get_5min_change(now=now)
        direction = price_buffer.get_direction(now=now)
        odds = book.implied_odds
        side = _side_for_token(book.token_id)
        zone = determine_zone(odds)
        bet_size = None
        liquidity_ok = False
        if zone is not None:
            bet_size = calculate_bet_size(zone, settings.BUYIN_SIZE)
            liquidity_ok, _ = passes_liquidity_filter(
                book=book,
                bet_size=bet_size,
                ask_multiplier=settings.LIQUIDITY_ASK_MULTIPLIER,
                max_spread=settings.MAX_SPREAD,
                recent_trade_window=settings.RECENT_TRADE_WINDOW,
                now=now,
            )

        decision = should_trade(
            SignalInput(
                odds=odds,
                side=side or "up",
                momentum_5m=momentum,
                direction=direction,
                is_data_fresh=price_buffer.is_fresh(settings.DATA_FRESHNESS_SECONDS, now=now),
                liquidity_ok=liquidity_ok,
                remaining_seconds=_remaining_seconds(now),
                has_open_position=False,
                buyin_balance=settings.BUYIN_SIZE,
                min_bet_size=1.0,
                circuit_breaker_active=False,
            )
        )
        obs = Observation(
            ts=now,
            coin="BTC",
            odds=odds,
            price=latest_price.price if latest_price else None,
            momentum_5m=momentum,
            would_trade=decision.should_trade,
            actual_result=None,
        )
        log_observation(settings.DB_PATH, obs)
        last_logged_ts = now
        logger.info(
            "BTC odds=%.4f price=%s 5m=%s trade=%s reason=%s",
            odds,
            f"{latest_price.price:.2f}" if latest_price else "na",
            f"{momentum:.4f}" if momentum is not None else "na",
            "Y" if decision.should_trade else "N",
            decision.reason,
        )

    async def price_task() -> None:
        await run_price_feed(
            symbol="btcusdt",
            buffer=price_buffer,
            reconnect_delay=settings.WS_RECONNECT_DELAY,
            stop_event=stop_event,
        )

    async def market_task() -> None:
        await run_market_subscription(
            coin="BTC",
            gamma_url=settings.GAMMA_API_URL,
            ws_url=settings.POLYMARKET_CLOB_WS,
            poll_interval=30.0,
            reconnect_delay=settings.WS_RECONNECT_DELAY,
            stop_event=stop_event,
            on_book=on_book,
            on_market=on_market,
        )

    await asyncio.gather(price_task(), market_task())


def main() -> None:
    _ensure_logging()
    asyncio.run(run_btc_observer())


if __name__ == "__main__":
    main()
