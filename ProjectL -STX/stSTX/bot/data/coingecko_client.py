from __future__ import annotations

import json
import time
import os
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen


@dataclass(frozen=True)
class MarketPrices:
    stx_usd: float
    ststx_usd: float


class CoinGeckoClient:
    def __init__(self, api_base: str, stx_coin_id: str = "blockstack", ststx_coin_id: str = "stacking-dao"):
        self.api_base = api_base.rstrip("/")
        self.stx_coin_id = stx_coin_id
        self.ststx_coin_id = ststx_coin_id
        self._last_prices: MarketPrices | None = None

    def fetch_prices(self) -> MarketPrices:
        ids = f"{self.stx_coin_id},{self.ststx_coin_id}"
        qs = urlencode({"ids": ids, "vs_currencies": "usd"})
        url = f"{self.api_base}/simple/price?{qs}"

        last_err: Exception | None = None
        for i in range(3):
            try:
                with urlopen(url, timeout=10) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))

                stx_usd = float(payload[self.stx_coin_id]["usd"])
                ststx_usd = float(payload[self.ststx_coin_id]["usd"])
                if stx_usd <= 0 or ststx_usd <= 0:
                    raise ValueError("Invalid CoinGecko prices")
                prices = MarketPrices(stx_usd=stx_usd, ststx_usd=ststx_usd)
                self._last_prices = prices
                return prices
            except (HTTPError, URLError, TimeoutError, KeyError, ValueError, json.JSONDecodeError) as exc:
                last_err = exc
                if i < 2:
                    time.sleep(0.6 * (i + 1))
                    continue

        if self._last_prices is not None:
            return self._last_prices
        fallback = self._fallback_prices_from_env()
        if fallback is not None:
            self._last_prices = fallback
            return fallback
        raise RuntimeError(f"CoinGecko fetch failed without cache: {last_err}")

    def _fallback_prices_from_env(self) -> MarketPrices | None:
        stx_raw = os.getenv("STX_USD_FALLBACK", "").strip()
        ststx_raw = os.getenv("STSTX_USD_FALLBACK", "").strip()
        if not stx_raw or not ststx_raw:
            return None
        try:
            stx_usd = float(stx_raw)
            ststx_usd = float(ststx_raw)
        except ValueError:
            return None
        if stx_usd <= 0 or ststx_usd <= 0:
            return None
        return MarketPrices(stx_usd=stx_usd, ststx_usd=ststx_usd)
