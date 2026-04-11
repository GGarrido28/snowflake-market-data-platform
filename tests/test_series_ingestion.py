import re
import unittest
from pathlib import Path
from unittest.mock import patch

from kalshi.markets.series import Series
from snow_py.scraping.series import SeriesScraper


REPO_ROOT = Path(__file__).resolve().parents[1]
SERIES_SQL_PATH = REPO_ROOT / "dbt" / "models" / "staging" / "stg_kalshi_series.sql"
STAGING_SCHEMA_PATH = REPO_ROOT / "dbt" / "models" / "staging" / "schema.yml"


class SeriesPaginationTests(unittest.TestCase):
    @patch("kalshi.markets.series.KalshiBase.__init__", return_value=None)
    def test_get_all_series_uses_pagination_when_requested(self, _mock_base_init):
        expected_rows = [{"ticker": "KXTEST"}]

        with patch.object(Series, "get_paginated_results", return_value=expected_rows) as mock_paginated:
            series = Series()

            result = series.get_all_series(all_pages=True, category="economics")

        self.assertEqual(result, expected_rows)
        self.assertEqual(series.series, expected_rows)
        mock_paginated.assert_called_once_with(
            "GET",
            "/series",
            params=None,
            limit=100,
            category="economics",
        )

    @patch("snow_py.base.SnowflakeManager")
    @patch("snow_py.scraping.series.Series")
    def test_scraper_loads_all_series_pages(
        self,
        mock_series_class,
        _mock_snowflake_manager,
    ):
        mock_series_class.return_value.get_all_series.return_value = [{"ticker": "KXTEST"}]

        scraper = SeriesScraper()
        with patch.object(scraper, "store_data_in_snowflake") as mock_store:
            scraper.run()

        mock_series_class.return_value.get_all_series.assert_called_once_with(all_pages=True)
        mock_store.assert_any_call([{"ticker": "KXTEST"}], "RAW_SERIES", ["ticker"])


class StgKalshiSeriesContractTests(unittest.TestCase):
    def test_schema_docs_match_sql_output_columns(self):
        documented_columns = self._get_documented_columns(STAGING_SCHEMA_PATH.read_text())
        projected_columns = self._get_projected_columns(SERIES_SQL_PATH.read_text())

        self.assertEqual(documented_columns, projected_columns)

    def _get_documented_columns(self, schema_text: str) -> list[str]:
        columns: list[str] = []
        in_series_model = False

        for line in schema_text.splitlines():
            stripped = line.strip()
            indent = len(line) - len(line.lstrip(" "))

            if stripped.startswith("- name: ") and indent == 2:
                model_name = stripped.split(": ", 1)[1]
                in_series_model = model_name == "stg_kalshi_series"
                continue

            if in_series_model and stripped.startswith("- name: ") and indent == 6:
                columns.append(stripped.split(": ", 1)[1])

        return columns

    def _get_projected_columns(self, sql_text: str) -> list[str]:
        match = re.search(r"select(.*)from source", sql_text, flags=re.IGNORECASE | re.DOTALL)
        self.assertIsNotNone(match, "Could not find select list in stg_kalshi_series.sql")

        select_list = match.group(1)
        return re.findall(r"\bas\s+([a-zA-Z_][a-zA-Z0-9_]*)", select_list, flags=re.IGNORECASE)


if __name__ == "__main__":
    unittest.main()
