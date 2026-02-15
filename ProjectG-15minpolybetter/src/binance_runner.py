from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from .binance_ws import run_price_feed
from .compat import UTC
from .price_feed import SymbolPriceBuffer

logger = logging.getLogger(__name__)


def _ensure_logging() -> None:
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)


async def run_btc_price_logger() -> None:
    _ensure_logging()
    buffer = SymbolPriceBuffer(max_window_seconds=300)
    last_logged: datetime | None = None

    async def on_tick(tick) -> None:
        nonlocal last_logged
        now = datetime.now(UTC)
        if last_logged is not None and (now - last_logged).total_seconds() < 60:
            return
        last_logged = now
        change = buffer.get_5min_change(now=now)
        logger.info("BTC price=%.2f 5m=%.4f", tick.price, change or 0.0)

    await run_price_feed(
        symbol="btcusdt",
        buffer=buffer,
        reconnect_delay=5.0,
        stop_event=None,
        on_tick=on_tick,
    )


def main() -> None:
    _ensure_logging()
    asyncio.run(run_btc_price_logger())


if __name__ == "__main__":
    main()
