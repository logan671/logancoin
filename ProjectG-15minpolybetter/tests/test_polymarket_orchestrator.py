import unittest

from src.market_scanner import MarketInfo
from src.polymarket_orchestrator import should_refresh_market


class TestPolymarketOrchestrator(unittest.TestCase):
    def test_should_refresh_when_no_current(self) -> None:
        latest = MarketInfo(
            slug="btc-updown-15m-20260213-1200",
            condition_id="c1",
            yes_token_id="y1",
            no_token_id="n1",
            end_date_iso=None,
            active=True,
            closed=False,
            resolved=False,
        )
        self.assertTrue(should_refresh_market(None, latest))

    def test_should_not_refresh_inactive(self) -> None:
        latest = MarketInfo(
            slug="btc-updown-15m-20260213-1200",
            condition_id="c1",
            yes_token_id="y1",
            no_token_id="n1",
            end_date_iso=None,
            active=False,
            closed=False,
            resolved=False,
        )
        self.assertFalse(should_refresh_market(None, latest))

    def test_should_refresh_on_slug_change(self) -> None:
        current = MarketInfo(
            slug="btc-updown-15m-20260213-1145",
            condition_id="c0",
            yes_token_id="y0",
            no_token_id="n0",
            end_date_iso=None,
            active=True,
            closed=False,
            resolved=False,
        )
        latest = MarketInfo(
            slug="btc-updown-15m-20260213-1200",
            condition_id="c1",
            yes_token_id="y1",
            no_token_id="n1",
            end_date_iso=None,
            active=True,
            closed=False,
            resolved=False,
        )
        self.assertTrue(should_refresh_market(current, latest))

    def test_should_not_refresh_same_slug(self) -> None:
        current = MarketInfo(
            slug="btc-updown-15m-20260213-1200",
            condition_id="c1",
            yes_token_id="y1",
            no_token_id="n1",
            end_date_iso=None,
            active=True,
            closed=False,
            resolved=False,
        )
        latest = MarketInfo(
            slug="btc-updown-15m-20260213-1200",
            condition_id="c1",
            yes_token_id="y1",
            no_token_id="n1",
            end_date_iso=None,
            active=True,
            closed=False,
            resolved=False,
        )
        self.assertFalse(should_refresh_market(current, latest))


if __name__ == "__main__":
    unittest.main()
