from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Awaitable, Callable, Iterable

from .compat import UTC, dataclass
from .market_scanner import (
    MarketInfo,
    fetch_latest_market_by_prefix,
    get_next_window_open_time,
)
from .polymarket_ws import run_clob_feed

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SubscriptionState:
    coin: str
    current: MarketInfo | None = None
    task: asyncio.Task | None = None


def should_refresh_market(current: MarketInfo | None, latest: MarketInfo | None) -> bool:
    if latest is None:
        return False
    if not latest.active or latest.closed or latest.resolved:
        return False
    if current is None:
        return True
    return current.slug != latest.slug


async def _stop_task(task: asyncio.Task | None) -> None:
    if task is None:
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        return


async def _start_ws_task(
    ws_url: str,
    token_ids: Iterable[str],
    reconnect_delay: float,
    stop_event: asyncio.Event,
    on_book: Callable[[object], Awaitable[None]] | None,
) -> asyncio.Task:
    return asyncio.create_task(
        run_clob_feed(
            url=ws_url,
            token_ids=token_ids,
            reconnect_delay=reconnect_delay,
            stop_event=stop_event,
            on_book=on_book,
        )
    )


async def run_market_subscription(
    coin: str,
    gamma_url: str,
    ws_url: str,
    poll_interval: float,
    reconnect_delay: float,
    stop_event: asyncio.Event,
    on_book: Callable[[object], Awaitable[None]] | None = None,
    on_market: Callable[[MarketInfo], Awaitable[None]] | None = None,
) -> None:
    state = SubscriptionState(coin=coin.upper())

    while not stop_event.is_set():
        now = datetime.now(UTC)
        latest = await fetch_latest_market_by_prefix(gamma_url, state.coin)

        if should_refresh_market(state.current, latest):
            await _stop_task(state.task)
            if latest is None:
                logger.warning("no market info for %s", state.coin)
            else:
                if on_market:
                    await on_market(latest)
                token_ids = [latest.yes_token_id, latest.no_token_id]
                state.task = await _start_ws_task(
                    ws_url=ws_url,
                    token_ids=token_ids,
                    reconnect_delay=reconnect_delay,
                    stop_event=stop_event,
                    on_book=on_book,
                )
                state.current = latest
                logger.info("subscribed %s to %s", state.coin, latest.slug)

        sleep_until = min(
            poll_interval,
            max(1.0, (get_next_window_open_time(now_utc=now) - now).total_seconds()),
        )
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=sleep_until)
        except asyncio.TimeoutError:
            continue

    await _stop_task(state.task)
