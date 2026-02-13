import os
import unittest

from src.market_scanner import fetch_market_by_slug, get_current_slug


RUN_LIVE = os.getenv("RUN_LIVE_API_TESTS") == "1"
GAMMA_API_URL = "https://gamma-api.polymarket.com"


@unittest.skipUnless(RUN_LIVE, "set RUN_LIVE_API_TESTS=1 to run live integration test")
class TestMarketScannerIntegration(unittest.IsolatedAsyncioTestCase):
    async def test_fetch_market_by_slug_live(self) -> None:
        slug = get_current_slug("BTC")
        result = await fetch_market_by_slug(GAMMA_API_URL, slug)

        if result is None:
            self.skipTest(f"live market not found for slug={slug}")

        self.assertEqual(result.slug, slug)
        self.assertTrue(bool(result.condition_id))
        self.assertTrue(bool(result.yes_token_id))
        self.assertTrue(bool(result.no_token_id))


if __name__ == "__main__":
    unittest.main()
