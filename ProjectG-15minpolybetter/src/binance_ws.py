from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime

from .compat import UTC, dataclass
from typing import Awaitable, Callable

import websockets

from .price_feed import SymbolPriceBuffer

logger = logging.getLogger(__name__)

BINANCE_WS_TEMPLATE = "wss://stream.binance.com:9443/ws/{symbol}@trade"


@dataclass(slots=True)
class TradeTick:
    symbol: str
    price: float
    ts: datetime


def parse_trade_message(message: dict) -> TradeTick:
    symbol = str(message.get("s") or "").lower()
    if not symbol:
        raise ValueError("trade message missing symbol")

    raw_price = message.get("p")
    if raw_price is None:
        raise ValueError("trade message missing price")

    raw_ts = message.get("T")
    if raw_ts is None:
        raise ValueError("trade message missing timestamp")

    price = float(raw_price)
    ts = datetime.fromtimestamp(float(raw_ts) / 1000.0, tz=UTC)
    return TradeTick(symbol=symbol, price=price, ts=ts)


async def _consume_stream(
    symbol: str,
    buffer: SymbolPriceBuffer,
    stop_event: asyncio.Event | None = None,
    on_tick: Callable[[TradeTick], Awaitable[None]] | None = None,
) -> None:
    url = BINANCE_WS_TEMPLATE.format(symbol=symbol.lower())
    async with websockets.connect(url, ping_interval=20, ping_timeout=20) as ws:
        async for raw in ws:
            if stop_event and stop_event.is_set():
                return
            payload = json.loads(raw)
            tick = parse_trade_message(payload)
            buffer.add_tick(tick.price, ts=tick.ts)
            if on_tick:
                await on_tick(tick)


async def run_price_feed(
    symbol: str,
    buffer: SymbolPriceBuffer,
    reconnect_delay: float = 5.0,
    stop_event: asyncio.Event | None = None,
    on_tick: Callable[[TradeTick], Awaitable[None]] | None = None,
) -> None:
    while True:
        if stop_event and stop_event.is_set():
            return
        try:
            await _consume_stream(symbol, buffer, stop_event=stop_event, on_tick=on_tick)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning("binance ws error for %s: %s", symbol, exc)
            await asyncio.sleep(reconnect_delay)
