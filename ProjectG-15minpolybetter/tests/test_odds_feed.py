from datetime import datetime, timedelta

import unittest

from src.compat import UTC
from src.odds_feed import parse_orderbook_message, passes_liquidity_filter


class TestOddsFeed(unittest.TestCase):
    def test_parse_orderbook_message(self) -> None:
        message = {
            "asset_id": "token-1",
            "bids": [{"price": "0.91", "size": "100"}],
            "asks": [{"price": "0.92", "size": "90"}],
            "timestamp": 1770979200,
        }
        book = parse_orderbook_message(message)
        self.assertEqual(book.token_id, "token-1")
        assert book.best_bid is not None
        assert book.best_ask is not None
        self.assertAlmostEqual(book.best_bid.price, 0.91)
        self.assertAlmostEqual(book.best_ask.price, 0.92)
        self.assertAlmostEqual(book.spread or 0, 0.01)
        self.assertEqual(book.last_trade_ts, datetime.fromtimestamp(1770979200, tz=UTC))

    def test_parse_orderbook_message_ms_timestamp_and_buys_sells(self) -> None:
        message = {
            "token_id": "token-2",
            "buys": [{"price": "0.40", "size": "10"}],
            "sells": [{"price": "0.41", "size": "11"}],
            "timestamp": 1770979200000,
        }
        book = parse_orderbook_message(message)
        assert book.best_bid is not None
        assert book.best_ask is not None
        self.assertAlmostEqual(book.best_bid.price, 0.40)
        self.assertAlmostEqual(book.best_ask.price, 0.41)
        self.assertEqual(book.last_trade_ts, datetime.fromtimestamp(1770979200, tz=UTC))

    def test_passes_liquidity_filter_ok(self) -> None:
        now = datetime(2026, 2, 13, 12, 0, 0, tzinfo=UTC)
        book = parse_orderbook_message(
            {
                "asset_id": "token-1",
                "bids": [{"price": "0.90", "size": "200"}],
                "asks": [{"price": "0.91", "size": "30"}],
                "timestamp": now.timestamp(),
            }
        )
        ok, reason = passes_liquidity_filter(
            book=book,
            bet_size=5.0,
            ask_multiplier=3.0,
            max_spread=0.02,
            recent_trade_window=300,
            now=now + timedelta(seconds=30),
        )
        self.assertTrue(ok)
        self.assertEqual(reason, "ok")

    def test_passes_liquidity_filter_stale_trade(self) -> None:
        now = datetime(2026, 2, 13, 12, 0, 0, tzinfo=UTC)
        book = parse_orderbook_message(
            {
                "asset_id": "token-1",
                "bids": [{"price": "0.90", "size": "200"}],
                "asks": [{"price": "0.91", "size": "30"}],
                "timestamp": now.timestamp(),
            }
        )
        ok, reason = passes_liquidity_filter(
            book=book,
            bet_size=5.0,
            ask_multiplier=3.0,
            max_spread=0.02,
            recent_trade_window=300,
            now=now + timedelta(minutes=10),
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "stale-trade")


if __name__ == "__main__":
    unittest.main()
