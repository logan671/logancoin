from __future__ import annotations

import json
from datetime import datetime, timedelta

from .compat import UTC, dataclass


@dataclass(slots=True)
class MarketInfo:
    slug: str
    condition_id: str
    yes_token_id: str
    no_token_id: str
    end_date_iso: str | None
    active: bool
    closed: bool
    resolved: bool


def floor_to_15_minutes(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    minute_floor = dt.minute - (dt.minute % 15)
    return dt.replace(minute=minute_floor, second=0, microsecond=0)


def get_current_slug(coin: str, now_utc: datetime | None = None) -> str:
    normalized = coin.lower()
    if normalized not in {"btc", "eth"}:
        raise ValueError("coin must be one of: BTC, ETH")

    now = now_utc or datetime.now(UTC)
    window_start = floor_to_15_minutes(now.astimezone(UTC))
    date_part = window_start.strftime("%Y%m%d-%H%M")
    return f"{normalized}-updown-15m-{date_part}"


def get_slug_prefix(coin: str) -> str:
    normalized = coin.lower()
    if normalized not in {"btc", "eth"}:
        raise ValueError("coin must be one of: BTC, ETH")
    return f"{normalized}-updown-15m-"


def _parse_json_list(value: object) -> list[object] | None:
    if value is None:
        return None
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return None
        if isinstance(parsed, list):
            return parsed
    return None


def _extract_token_ids(
    clob_token_ids: object,
    outcomes: object | None = None,
) -> tuple[str, str]:
    parsed_tokens = _parse_json_list(clob_token_ids) or []
    parsed_outcomes = _parse_json_list(outcomes) or []

    # Case 1: array of dicts with outcome/token_id
    if parsed_tokens and isinstance(parsed_tokens[0], dict):
        yes_token_id: str | None = None
        no_token_id: str | None = None
        for entry in parsed_tokens:
            outcome = str(entry.get("outcome", "")).upper()
            token_id = str(entry.get("token_id", "")).strip()
            if not token_id:
                continue
            if outcome in {"YES", "UP"}:
                yes_token_id = token_id
            elif outcome in {"NO", "DOWN"}:
                no_token_id = token_id
        if yes_token_id and no_token_id:
            return yes_token_id, no_token_id

    # Case 2: array of token ids (strings), map by outcomes if present
    token_ids = [str(t).strip() for t in parsed_tokens if str(t).strip()]
    if len(token_ids) >= 2 and parsed_outcomes:
        mapping = {}
        for outcome, token_id in zip(parsed_outcomes, token_ids):
            key = str(outcome).upper()
            mapping[key] = token_id
        yes_token_id = mapping.get("YES") or mapping.get("UP")
        no_token_id = mapping.get("NO") or mapping.get("DOWN")
        if yes_token_id and no_token_id:
            return yes_token_id, no_token_id

    # Fallback: use first two as yes/no
    if len(token_ids) >= 2:
        return token_ids[0], token_ids[1]

    raise ValueError("failed to parse yes/no token ids from gamma response")


def _to_market_info(row: dict) -> MarketInfo:
    slug = str(row["slug"])
    condition_id = str(row["conditionId"])
    clob_token_ids = row.get("clobTokenIds", [])
    outcomes = row.get("outcomes")
    yes_token_id, no_token_id = _extract_token_ids(clob_token_ids, outcomes=outcomes)

    return MarketInfo(
        slug=slug,
        condition_id=condition_id,
        yes_token_id=yes_token_id,
        no_token_id=no_token_id,
        end_date_iso=row.get("endDate"),
        active=bool(row.get("active", False)),
        closed=bool(row.get("closed", False)),
        resolved=bool(row.get("resolved", False)),
    )


def parse_market_from_gamma(markets: list[dict], expected_slug: str) -> MarketInfo | None:
    for row in markets:
        if str(row.get("slug", "")).strip() == expected_slug:
            return _to_market_info(row)
    return None


async def fetch_market_by_slug(
    base_url: str,
    slug: str,
    timeout_seconds: float = 10.0,
) -> MarketInfo | None:
    import aiohttp

    url = f"{base_url.rstrip('/')}/markets?slug={slug}"
    timeout = aiohttp.ClientTimeout(total=timeout_seconds)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as resp:
            resp.raise_for_status()
            payload = await resp.json()
            if not isinstance(payload, list):
                raise ValueError("gamma response must be a list")
    return parse_market_from_gamma(payload, slug)


def _parse_iso_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


async def fetch_latest_market_by_prefix(
    base_url: str,
    coin: str,
    limit: int = 200,
    timeout_seconds: float = 10.0,
) -> MarketInfo | None:
    import aiohttp

    prefix = get_slug_prefix(coin)
    url = f"{base_url.rstrip('/')}/events"
    params = {
        "closed": "false",
        "order": "id",
        "ascending": "false",
        "limit": str(limit),
    }
    timeout = aiohttp.ClientTimeout(total=timeout_seconds)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url, params=params) as resp:
            resp.raise_for_status()
            payload = await resp.json()
            if not isinstance(payload, list):
                raise ValueError("gamma events response must be a list")

    candidates: list[tuple[datetime, MarketInfo]] = []
    for event in payload:
        markets = event.get("markets", [])
        if not isinstance(markets, list):
            continue
        for market in markets:
            slug = str(market.get("slug", "")).strip()
            if not slug.startswith(prefix):
                continue
            if not market.get("enableOrderBook", True):
                continue
            try:
                info = _to_market_info(market)
            except Exception:
                continue
            if not info.active or info.closed or info.resolved:
                continue
            end_ts = _parse_iso_ts(info.end_date_iso) or datetime.min.replace(tzinfo=UTC)
            candidates.append((end_ts, info))

    if not candidates:
        markets_url = f"{base_url.rstrip('/')}/markets"
        market_params = {
            "closed": "false",
            "order": "id",
            "ascending": "false",
            "limit": str(limit),
        }
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(markets_url, params=market_params) as resp:
                resp.raise_for_status()
                markets_payload = await resp.json()
                if not isinstance(markets_payload, list):
                    raise ValueError("gamma markets response must be a list")
        for market in markets_payload:
            slug = str(market.get("slug", "")).strip()
            if not slug.startswith(prefix):
                continue
            if not market.get("enableOrderBook", True):
                continue
            try:
                info = _to_market_info(market)
            except Exception:
                continue
            if not info.active or info.closed or info.resolved:
                continue
            end_ts = _parse_iso_ts(info.end_date_iso) or datetime.min.replace(tzinfo=UTC)
            candidates.append((end_ts, info))

    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def get_next_window_open_time(now_utc: datetime | None = None) -> datetime:
    now = now_utc or datetime.now(UTC)
    floored = floor_to_15_minutes(now.astimezone(UTC))
    return floored + timedelta(minutes=15)
