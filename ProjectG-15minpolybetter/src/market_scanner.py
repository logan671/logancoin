from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


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


def _extract_token_ids(clob_token_ids: list[dict]) -> tuple[str, str]:
    yes_token_id: str | None = None
    no_token_id: str | None = None
    for entry in clob_token_ids:
        outcome = str(entry.get("outcome", "")).upper()
        token_id = str(entry.get("token_id", "")).strip()
        if not token_id:
            continue
        if outcome in {"YES", "UP"}:
            yes_token_id = token_id
        elif outcome in {"NO", "DOWN"}:
            no_token_id = token_id
    if not yes_token_id or not no_token_id:
        raise ValueError("failed to parse yes/no token ids from gamma response")
    return yes_token_id, no_token_id


def _to_market_info(row: dict) -> MarketInfo:
    slug = str(row["slug"])
    condition_id = str(row["conditionId"])
    clob_token_ids = row.get("clobTokenIds", [])
    if not isinstance(clob_token_ids, list):
        raise ValueError("clobTokenIds must be a list")
    yes_token_id, no_token_id = _extract_token_ids(clob_token_ids)

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


def get_next_window_open_time(now_utc: datetime | None = None) -> datetime:
    now = now_utc or datetime.now(UTC)
    floored = floor_to_15_minutes(now.astimezone(UTC))
    return floored + timedelta(minutes=15)
