from __future__ import annotations

import asyncio
import json
import logging
from .compat import dataclass
from typing import Awaitable, Callable, Iterable

import websockets

from .odds_feed import MarketBook, parse_orderbook_message

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ClobMessage:
    raw: dict
    book: MarketBook | None


def _has_orderbook_keys(payload: dict) -> bool:
    if "bids" in payload and "asks" in payload:
        return True
    if "buys" in payload and "sells" in payload:
        return True
    return False


def _extract_orderbook_payload(message: dict) -> dict | None:
    if _has_orderbook_keys(message):
        return message

    for key in ("data", "payload", "result"):
        nested = message.get(key)
        if isinstance(nested, dict) and _has_orderbook_keys(nested):
            return nested

    return None


def _normalize_message(raw: object) -> dict | None:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                return item
    return None


def parse_clob_message(message: dict) -> ClobMessage:
    normalized = _normalize_message(message)
    if normalized is None:
        return ClobMessage(raw=message, book=None)

    payload = _extract_orderbook_payload(normalized)
    if payload is None:
        return ClobMessage(raw=normalized, book=None)

    book = parse_orderbook_message(payload)
    return ClobMessage(raw=normalized, book=book)


def build_subscribe_message(token_ids: Iterable[str]) -> dict:
    return {
        "type": "market",
        "assets_ids": list(token_ids),
    }


async def _consume_clob_stream(
    url: str,
    subscribe_message: dict | None,
    stop_event: asyncio.Event | None,
    on_message: Callable[[ClobMessage], Awaitable[None]] | None,
    on_book: Callable[[MarketBook], Awaitable[None]] | None,
) -> None:
    async with websockets.connect(url, ping_interval=20, ping_timeout=20) as ws:
        logger.info("polymarket ws connected")
        if subscribe_message:
            await ws.send(json.dumps(subscribe_message))
            logger.info("polymarket ws subscribed: %s", subscribe_message)

        message_count = 0
        async for raw in ws:
            if stop_event and stop_event.is_set():
                return
            payload = json.loads(raw)
            message_count += 1
            if message_count == 1 or message_count % 50 == 0:
                logger.info("polymarket ws message count=%d", message_count)
            parsed = parse_clob_message(payload)
            if on_message:
                await on_message(parsed)
            if parsed.book and on_book:
                await on_book(parsed.book)


async def run_clob_feed(
    url: str,
    token_ids: Iterable[str],
    reconnect_delay: float = 5.0,
    stop_event: asyncio.Event | None = None,
    on_message: Callable[[ClobMessage], Awaitable[None]] | None = None,
    on_book: Callable[[MarketBook], Awaitable[None]] | None = None,
    subscribe_message: dict | None = None,
) -> None:
    while True:
        if stop_event and stop_event.is_set():
            return
        try:
            message = subscribe_message or build_subscribe_message(token_ids)
            await _consume_clob_stream(url, message, stop_event, on_message, on_book)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning("polymarket ws error: %s", exc)
            await asyncio.sleep(reconnect_delay)
