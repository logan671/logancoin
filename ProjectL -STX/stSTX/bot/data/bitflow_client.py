from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.request import urlopen


@dataclass(frozen=True)
class PoolSnapshot:
    pool_id: str
    liquidity_in_usd: float
    base_volume: float
    target_volume: float
    last_price: float


class BitflowClient:
    def __init__(self, ticker_url: str):
        self.ticker_url = ticker_url

    def fetch_pool(self, pool_id: str) -> PoolSnapshot:
        with urlopen(self.ticker_url, timeout=10) as resp:
            rows = json.loads(resp.read().decode("utf-8"))

        for row in rows:
            if row.get("pool_id") == pool_id:
                return PoolSnapshot(
                    pool_id=pool_id,
                    liquidity_in_usd=float(row.get("liquidity_in_usd") or 0.0),
                    base_volume=float(row.get("base_volume") or 0.0),
                    target_volume=float(row.get("target_volume") or 0.0),
                    last_price=float(row.get("last_price") or 0.0),
                )
        raise ValueError(f"Pool not found in Bitflow ticker: {pool_id}")

