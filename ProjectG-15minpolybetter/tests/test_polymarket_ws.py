from __future__ import annotations

import unittest
from datetime import datetime

from src.compat import UTC
from src.polymarket_ws import build_subscribe_message, parse_clob_message


class TestPolymarketWs(unittest.TestCase):
    def test_build_subscribe_message(self) -> None:
        message = build_subscribe_message(["token-yes", "token-no"])
        self.assertEqual(message["type"], "market")
        self.assertEqual(message["assets_ids"], ["token-yes", "token-no"])

    def test_parse_clob_message_top_level(self) -> None:
        payload = {
            "asset_id": "token-yes",
            "bids": [{"price": "0.45", "size": "120"}],
            "asks": [{"price": "0.46", "size": "80"}],
            "timestamp": 1700000000,
        }

        parsed = parse_clob_message(payload)
        self.assertIsNotNone(parsed.book)
        assert parsed.book is not None
        self.assertEqual(parsed.book.token_id, "token-yes")
        self.assertEqual(parsed.book.best_bid.price, 0.45)
        self.assertEqual(parsed.book.best_ask.price, 0.46)
        self.assertEqual(parsed.book.last_trade_ts, datetime.fromtimestamp(1700000000, tz=UTC))

    def test_parse_clob_message_nested(self) -> None:
        payload = {
            "event": "book",
            "data": {
                "token_id": "token-no",
                "buys": [{"price": "0.52", "size": "50"}],
                "sells": [{"price": "0.53", "size": "40"}],
            },
        }

        parsed = parse_clob_message(payload)
        self.assertIsNotNone(parsed.book)
        assert parsed.book is not None
        self.assertEqual(parsed.book.token_id, "token-no")
        self.assertEqual(parsed.book.best_bid.price, 0.52)
        self.assertEqual(parsed.book.best_ask.price, 0.53)

    def test_parse_clob_message_no_orderbook(self) -> None:
        payload = {"event": "heartbeat"}
        parsed = parse_clob_message(payload)
        self.assertIsNone(parsed.book)

    def test_parse_clob_message_list_payload(self) -> None:
        payload = [
            {"event": "heartbeat"},
            {
                "token_id": "token-list",
                "bids": [{"price": "0.40", "size": "10"}],
                "asks": [{"price": "0.41", "size": "11"}],
            },
        ]
        parsed = parse_clob_message(payload)
        self.assertIsNotNone(parsed.book)


if __name__ == "__main__":
    unittest.main()
