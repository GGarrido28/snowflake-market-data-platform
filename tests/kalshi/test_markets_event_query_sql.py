import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
QUERY_PATH = REPO_ROOT / "src" / "market_data_platform" / "queries" / "kalshi" / "markets_mlb_events.sql"


class MarketsEventQuerySqlTests(unittest.TestCase):
    def test_mlb_events_query_scopes_to_supported_mlb_series(self):
        query = QUERY_PATH.read_text(encoding="utf-8")

        self.assertIn('WHERE "series_ticker" IN', query)
        self.assertEqual(query.count("WHERE"), 1)
        for ticker in ("KXMLBTOTAL", "KXMLBSPREAD", "KXMLBGAME"):
            self.assertIn(f"'{ticker}'", query)


if __name__ == "__main__":
    unittest.main()
