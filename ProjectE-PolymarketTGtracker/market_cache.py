import json
import os
import time
from typing import Dict, Optional

import requests

from config import GAMMA_API_BASE, MARKET_CACHE_TTL_SECONDS

CACHE_PATH = os.path.join(os.path.dirname(__file__), "market_cache.json")
LOG_PATH = os.path.join(os.path.dirname(__file__), "market_cache.log")


def _log(message: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"{ts} {message}\n")


def _load_cache() -> Optional[dict]:
    if not os.path.exists(CACHE_PATH):
        return None
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _save_cache(data: dict) -> None:
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f)


def _fetch_markets() -> list[dict]:
    markets = []
    offset = 0
    limit = 200
    while True:
        resp = _request_gamma(
            params={"limit": limit, "offset": offset},
            timeout=20,
        )
        if resp is None:
            _log(f"fetch_markets_failed offset={offset}")
            break
        batch = resp
        if not batch:
            break
        markets.extend(batch)
        if len(batch) < limit:
            break
        offset += limit
    return markets


def build_token_map() -> Dict[str, dict]:
    cache = _load_cache()
    now = int(time.time())
    if cache and now - cache.get("ts", 0) < MARKET_CACHE_TTL_SECONDS:
        return cache.get("token_map", {})

    markets = _fetch_markets()
    token_map: Dict[str, dict] = {}

    for m in markets:
        outcomes = m.get("outcomes") or []
        clob_ids = m.get("clobTokenIds") or []
        if isinstance(outcomes, str):
            try:
                outcomes = json.loads(outcomes)
            except Exception:
                outcomes = []
        if isinstance(clob_ids, str):
            try:
                clob_ids = json.loads(clob_ids)
            except Exception:
                clob_ids = []
        if len(outcomes) != len(clob_ids):
            continue
        for outcome, token_id in zip(outcomes, clob_ids):
            token_map[str(token_id)] = {
                "question": m.get("question") or m.get("title") or "",
                "outcome": outcome,
                "slug": m.get("slug") or "",
            }

    _save_cache({"ts": now, "token_map": token_map})
    return token_map


def get_market_for_token(token_id: str) -> Optional[dict]:
    token_map = build_token_map()
    return token_map.get(str(token_id))


def get_market_for_token_cached(token_id: str) -> Optional[dict]:
    cache = _load_cache()
    if not cache:
        return None
    now = int(time.time())
    if now - cache.get("ts", 0) >= MARKET_CACHE_TTL_SECONDS:
        return None
    token_map = cache.get("token_map", {})
    return token_map.get(str(token_id))


def fetch_market_for_token(token_id: str) -> Optional[dict]:
    data = _request_gamma(
        params={"clob_token_ids": str(token_id), "limit": 1},
        timeout=6,
        retries=3,
        backoff=1.2,
    )
    if not data:
        _log(f"token_lookup_failed token_id={token_id}")
        return None
    market = data[0]
    outcomes = market.get("outcomes") or []
    clob_ids = market.get("clobTokenIds") or []
    if isinstance(outcomes, str):
        try:
            outcomes = json.loads(outcomes)
        except Exception:
            outcomes = []
    if isinstance(clob_ids, str):
        try:
            clob_ids = json.loads(clob_ids)
        except Exception:
            clob_ids = []
    if len(outcomes) != len(clob_ids):
        _log(f"token_lookup_mismatch token_id={token_id} outcomes={len(outcomes)} clob_ids={len(clob_ids)}")
        return None
    for outcome, tid in zip(outcomes, clob_ids):
        if str(tid) == str(token_id):
            return {
                "question": market.get("question") or market.get("title") or "",
                "outcome": outcome,
                "slug": market.get("slug") or "",
            }
    _log(f"token_lookup_no_match token_id={token_id}")
    # Return market info without outcome to at least show title/link.
    return {
        "question": market.get("question") or market.get("title") or "",
        "outcome": "?",
        "slug": market.get("slug") or "",
    }


def get_market_for_token_fast(token_id: str) -> Optional[dict]:
    cached = get_market_for_token_cached(token_id)
    if cached:
        _log(f"cache_hit token_id={token_id}")
        return cached
    _log(f"cache_miss token_id={token_id}")
    market = fetch_market_for_token(token_id)
    if not market:
        return None
    cache = _load_cache() or {}
    token_map = cache.get("token_map", {})
    token_map[str(token_id)] = market
    _save_cache({"ts": int(time.time()), "token_map": token_map})
    _log(f"cache_write token_id={token_id}")
    return market


def _request_gamma(params: dict, timeout: int, retries: int = 2, backoff: float = 1.5) -> Optional[list[dict]]:
    url = f"{GAMMA_API_BASE}/markets"
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            _log(f"gamma_ok attempt={attempt} params={params} items={len(data)}")
            return data
        except Exception as exc:
            _log(f"gamma_error attempt={attempt} params={params} error={exc}")
            if attempt < retries:
                time.sleep(backoff * attempt)
    return None
