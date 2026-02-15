from __future__ import annotations

import unittest
from datetime import datetime

from src.compat import UTC
from src.binance_ws import parse_trade_message


class TestBinanceWs(unittest.TestCase):
    def test_parse_trade_message(self) -> None:
        payload = {
            "e": "trade",
            "s": "BTCUSDT",
            "p": "64250.12",
            "T": 1700000000000,
        }

        tick = parse_trade_message(payload)

        self.assertEqual(tick.symbol, "btcusdt")
        self.assertEqual(tick.price, 64250.12)
        self.assertEqual(
            tick.ts,
            datetime.fromtimestamp(1700000000000 / 1000.0, tz=UTC),
        )

    def test_parse_trade_message_missing_symbol(self) -> None:
        with self.assertRaisesRegex(ValueError, "trade message missing symbol"):
            parse_trade_message({})

    def test_parse_trade_message_missing_price(self) -> None:
        with self.assertRaisesRegex(ValueError, "trade message missing price"):
            parse_trade_message({"s": "BTCUSDT"})

    def test_parse_trade_message_missing_timestamp(self) -> None:
        with self.assertRaisesRegex(ValueError, "trade message missing timestamp"):
            parse_trade_message({"s": "BTCUSDT", "p": "1.0"})


if __name__ == "__main__":
    unittest.main()
