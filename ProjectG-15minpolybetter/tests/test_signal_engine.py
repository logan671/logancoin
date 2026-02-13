import unittest

from src.signal_engine import SignalInput, determine_zone, should_trade


class TestSignalEngine(unittest.TestCase):
    def test_determine_zone(self) -> None:
        self.assertEqual(determine_zone(0.86), "caution")
        self.assertEqual(determine_zone(0.91), "standard")
        self.assertEqual(determine_zone(0.96), "confidence")
        self.assertIsNone(determine_zone(0.80))

    def test_should_trade_standard_success(self) -> None:
        decision = should_trade(
            SignalInput(
                odds=0.91,
                side="up",
                momentum_5m=0.004,
                direction="up",
                is_data_fresh=True,
                liquidity_ok=True,
                remaining_seconds=240,
                has_open_position=False,
                buyin_balance=50.0,
                min_bet_size=2.5,
                circuit_breaker_active=False,
            )
        )
        self.assertTrue(decision.should_trade)
        self.assertEqual(decision.zone, "standard")
        self.assertEqual(decision.bet_size, 5.0)
        self.assertEqual(decision.reason, "ok")

    def test_should_trade_direction_mismatch(self) -> None:
        decision = should_trade(
            SignalInput(
                odds=0.91,
                side="up",
                momentum_5m=0.004,
                direction="down",
                is_data_fresh=True,
                liquidity_ok=True,
                remaining_seconds=240,
                has_open_position=False,
                buyin_balance=50.0,
                min_bet_size=2.5,
                circuit_breaker_active=False,
            )
        )
        self.assertFalse(decision.should_trade)
        self.assertEqual(decision.reason, "direction-mismatch")

    def test_should_trade_circuit_breaker(self) -> None:
        decision = should_trade(
            SignalInput(
                odds=0.96,
                side="up",
                momentum_5m=None,
                direction="up",
                is_data_fresh=True,
                liquidity_ok=True,
                remaining_seconds=240,
                has_open_position=False,
                buyin_balance=50.0,
                min_bet_size=2.5,
                circuit_breaker_active=True,
            )
        )
        self.assertFalse(decision.should_trade)
        self.assertEqual(decision.reason, "circuit-breaker-active")


if __name__ == "__main__":
    unittest.main()
