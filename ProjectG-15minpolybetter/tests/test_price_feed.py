from datetime import datetime, timedelta

import unittest

from src.compat import UTC
from src.price_feed import SymbolPriceBuffer


class TestSymbolPriceBuffer(unittest.TestCase):
    def test_get_5min_change_up(self) -> None:
        buf = SymbolPriceBuffer(max_window_seconds=300)
        base = datetime(2026, 2, 13, 10, 0, 0, tzinfo=UTC)
        buf.add_tick(100.0, ts=base)
        buf.add_tick(101.0, ts=base + timedelta(minutes=5))
        change = buf.get_5min_change(now=base + timedelta(minutes=5))
        assert change is not None
        self.assertAlmostEqual(change, 0.01)

    def test_get_direction_down(self) -> None:
        buf = SymbolPriceBuffer(max_window_seconds=300)
        base = datetime(2026, 2, 13, 10, 0, 0, tzinfo=UTC)
        buf.add_tick(100.0, ts=base)
        buf.add_tick(99.0, ts=base + timedelta(minutes=5))
        self.assertEqual(buf.get_direction(now=base + timedelta(minutes=5)), "down")

    def test_freshness(self) -> None:
        buf = SymbolPriceBuffer(max_window_seconds=300)
        base = datetime(2026, 2, 13, 10, 0, 0, tzinfo=UTC)
        buf.add_tick(100.0, ts=base)
        self.assertTrue(buf.is_fresh(now=base + timedelta(seconds=2)))
        self.assertFalse(buf.is_fresh(now=base + timedelta(seconds=4)))

    def test_trim_old_points(self) -> None:
        buf = SymbolPriceBuffer(max_window_seconds=300)
        base = datetime(2026, 2, 13, 10, 0, 0, tzinfo=UTC)
        buf.add_tick(100.0, ts=base)
        buf.add_tick(101.0, ts=base + timedelta(minutes=6))
        self.assertEqual(len(buf.points), 1)


if __name__ == "__main__":
    unittest.main()
