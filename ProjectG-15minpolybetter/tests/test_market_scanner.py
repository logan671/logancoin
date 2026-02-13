from datetime import UTC, datetime

import unittest

from src.market_scanner import (
    floor_to_15_minutes,
    get_current_slug,
    parse_market_from_gamma,
)


class TestMarketScanner(unittest.TestCase):
    def test_floor_to_15_minutes(self) -> None:
        dt = datetime(2026, 2, 13, 10, 44, 59, tzinfo=UTC)
        floored = floor_to_15_minutes(dt)
        self.assertEqual(floored, datetime(2026, 2, 13, 10, 30, tzinfo=UTC))

    def test_get_current_slug(self) -> None:
        dt = datetime(2026, 2, 13, 10, 44, 59, tzinfo=UTC)
        slug = get_current_slug("BTC", now_utc=dt)
        self.assertEqual(slug, "btc-updown-15m-20260213-1030")

    def test_invalid_coin(self) -> None:
        with self.assertRaises(ValueError):
            get_current_slug("SOL")

    def test_parse_market_from_gamma(self) -> None:
        payload = [
            {
                "slug": "btc-updown-15m-20260213-1030",
                "conditionId": "cond-1",
                "active": True,
                "closed": False,
                "resolved": False,
                "endDate": "2026-02-13T10:45:00Z",
                "clobTokenIds": [
                    {"outcome": "YES", "token_id": "yes-token"},
                    {"outcome": "NO", "token_id": "no-token"},
                ],
            }
        ]

        market = parse_market_from_gamma(payload, "btc-updown-15m-20260213-1030")
        assert market is not None
        self.assertEqual(market.condition_id, "cond-1")
        self.assertEqual(market.yes_token_id, "yes-token")
        self.assertEqual(market.no_token_id, "no-token")


if __name__ == "__main__":
    unittest.main()
