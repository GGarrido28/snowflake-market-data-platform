import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
QUERY_PATH = REPO_ROOT / "src" / "market_data_platform" / "queries" / "kalshi" / "markets_mlb_events.sql"


class MarketsEventQuerySqlTests(unittest.TestCase):
    def test_mlb_events_query_scopes_to_supported_mlb_series(self):
        query = QUERY_PATH.read_text(encoding="utf-8")
        normalized_query = query.lower()

        self.assertIn('where "series_ticker" in', normalized_query)
        self.assertEqual(normalized_query.count("where"), 2)
        for ticker in ("KXMLBTOTAL", "KXMLBSPREAD", "KXMLBGAME"):
            self.assertIn(f"'{ticker}'", query)
        self.assertIn("current_timestamp()", normalized_query)
        self.assertIn("america/new_york", normalized_query)
        self.assertIn("try_to_date", normalized_query)
        self.assertIn("split_part", normalized_query)
        self.assertNotIn("limit 5", normalized_query)
        self.assertNotIn("last_updated_ts", normalized_query)
        self.assertRegex(normalized_query, r"order\s+by\s+event_ticker")


if __name__ == "__main__":
    unittest.main()
