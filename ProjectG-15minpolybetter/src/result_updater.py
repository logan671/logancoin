from __future__ import annotations

import sqlite3
from datetime import datetime

import aiohttp

from .compat import UTC
from .market_scanner import _to_market_info, get_slug_prefix


def _normalize_outcome(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip().upper()
    if text in {"YES", "NO", "UP", "DOWN"}:
        return text
    return None


def _extract_outcome(row: dict) -> str | None:
    for key in ("resolvedOutcome", "winningOutcome", "outcome", "result", "finalOutcome", "resolution"):
        outcome = _normalize_outcome(row.get(key))
        if outcome:
            return outcome
    return None


async def _fetch_closed_markets(gamma_url: str, limit: int = 200) -> list[dict]:
    url = f"{gamma_url.rstrip('/')}/markets"
    params = {
        "closed": "true",
        "order": "id",
        "ascending": "false",
        "limit": str(limit),
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            resp.raise_for_status()
            payload = await resp.json()
            if not isinstance(payload, list):
                raise ValueError("gamma markets response must be a list")
            return payload


def _compute_pnl(entry_odds: float, bet_size: float, side: str, outcome: str) -> float:
    win = (side in {"up", "yes"} and outcome in {"UP", "YES"}) or (
        side in {"down", "no"} and outcome in {"DOWN", "NO"}
    )
    if win:
        return round(bet_size * (1.0 / entry_odds - 1.0), 6)
    return round(-bet_size, 6)


def _update_market_results(
    conn: sqlite3.Connection,
    slug: str,
    outcome: str,
) -> int:
    rows = conn.execute(
        """
        SELECT id, entry_odds, bet_size, side
        FROM observations
        WHERE market_slug = ?
          AND would_trade = 1
          AND filled = 1
          AND (actual_result IS NULL OR actual_result = '')
        """,
        (slug,),
    ).fetchall()

    updated = 0
    for row_id, entry_odds, bet_size, side in rows:
        if entry_odds is None or bet_size is None or side is None:
            continue
        pnl = _compute_pnl(float(entry_odds), float(bet_size), str(side).lower(), outcome)
        conn.execute(
            "UPDATE observations SET actual_result = ?, pnl = ? WHERE id = ?",
            (outcome, pnl, row_id),
        )
        updated += 1
    return updated


async def update_resolved_results(db_path: str, gamma_url: str, coin: str) -> None:
    prefix = get_slug_prefix(coin)
    markets = await _fetch_closed_markets(gamma_url)

    resolved: list[tuple[str, str]] = []
    for row in markets:
        slug = str(row.get("slug", "")).strip()
        if not slug.startswith(prefix):
            continue
        try:
            info = _to_market_info(row)
        except Exception:
            continue
        if not info.resolved:
            continue
        outcome = _extract_outcome(row)
        if outcome is None:
            continue
        resolved.append((info.slug, outcome))

    if not resolved:
        return

    with sqlite3.connect(db_path) as conn:
        for slug, outcome in resolved:
            _update_market_results(conn, slug, outcome)
