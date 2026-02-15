import os
import sqlite3
import tempfile
import unittest
from datetime import datetime

from src.compat import UTC
from src.observation_store import Observation, init_db, log_observation


class TestObservationStore(unittest.TestCase):
    def test_init_and_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "data", "test.db")
            init_db(db_path)
            obs = Observation(
                ts=datetime(2026, 2, 15, 12, 0, 0, tzinfo=UTC),
                coin="BTC",
                odds=0.91,
                price=64000.0,
                momentum_5m=0.004,
                would_trade=True,
                actual_result=None,
            )
            log_observation(db_path, obs)

            with sqlite3.connect(db_path) as conn:
                row = conn.execute(
                    "SELECT coin, odds, price, momentum_5m, would_trade FROM observations"
                ).fetchone()

            self.assertIsNotNone(row)
            assert row is not None
            self.assertEqual(row[0], "BTC")
            self.assertAlmostEqual(row[1], 0.91)
            self.assertAlmostEqual(row[2], 64000.0)
            self.assertAlmostEqual(row[3], 0.004)
            self.assertEqual(row[4], 1)


if __name__ == "__main__":
    unittest.main()
