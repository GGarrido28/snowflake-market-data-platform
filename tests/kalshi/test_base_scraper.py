import unittest
from unittest.mock import patch

from market_data_platform.pipelines.base import Scraper
from market_data_platform.sources.kalshi.base import KalshiBase


class DummyScraper(Scraper):
    def run(self):
        pass


class FakeResponse:
    status_code = 200
    text = ""

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


class KalshiBaseRateLimitTests(unittest.TestCase):
    def test_configured_read_limit_caps_advertised_api_limit(self):
        with patch.object(KalshiBase, "_get_auth_headers", return_value={}):
            client = KalshiBase(read_limit_per_second=8)

            with patch.object(
                client,
                "_send_request",
                return_value=FakeResponse({"read_limit": 20, "write_limit": 20}),
            ):
                limits = client._get_api_limits()

        self.assertEqual(limits["read_limit"], 8)
        self.assertEqual(limits["write_limit"], 20)

    def test_configured_read_limit_rejects_fractional_values(self):
        with patch.object(KalshiBase, "_get_auth_headers", return_value={}):
            with self.assertRaisesRegex(ValueError, "read_limit_per_second must be a whole integer"):
                KalshiBase(read_limit_per_second=8.5)

    def test_configured_read_limit_allows_whole_number_strings(self):
        with patch.object(KalshiBase, "_get_auth_headers", return_value={}):
            client = KalshiBase(read_limit_per_second="8")

        self.assertEqual(client.api_limits["read_limit"], 8)

    def test_configured_read_limit_uses_advertised_limit_when_lower_than_cap(self):
        with patch.object(KalshiBase, "_get_auth_headers", return_value={}):
            client = KalshiBase(read_limit_per_second=20)

            with patch.object(
                client,
                "_send_request",
                return_value=FakeResponse({"read_limit": 12, "write_limit": 20}),
            ):
                limits = client._get_api_limits()

        self.assertEqual(limits["read_limit"], 12)

    def test_configured_read_limit_rejects_nonpositive_values(self):
        with patch.object(KalshiBase, "_get_auth_headers", return_value={}):
            with self.assertRaisesRegex(
                ValueError,
                "read_limit_per_second must be greater than zero",
            ):
                KalshiBase(read_limit_per_second=0)

    def test_configured_read_limit_rejects_noninteger_strings(self):
        with patch.object(KalshiBase, "_get_auth_headers", return_value={}):
            with self.assertRaisesRegex(
                ValueError,
                "read_limit_per_second must be a whole integer",
            ):
                KalshiBase(read_limit_per_second="8.5")


class ScraperStorageTests(unittest.TestCase):
    @patch("market_data_platform.pipelines.base.SnowflakeManager")
    def test_store_data_in_snowflake_uses_upsert_for_existing_keyed_tables(self, mock_snowflake_manager):
        manager = mock_snowflake_manager.return_value
        manager.check_table_exists.return_value = True
        manager.insert_rows.return_value = (True, None)

        scraper = DummyScraper()
        scraper.store_data_in_snowflake(
            [{"event_ticker": "KXTEST-25", "title": "Test Event"}],
            "RAW_EVENTS",
            ["event_ticker"],
        )

        manager.insert_rows.assert_called_once_with(
            target_table="RAW_EVENTS",
            columns=["event_ticker", "title"],
            rows=[{"event_ticker": "KXTEST-25", "title": "Test Event"}],
            contains_dicts=True,
            update=True,
            return_error_msg=True,
        )

    @patch("market_data_platform.pipelines.base.SnowflakeManager")
    def test_store_data_in_snowflake_uses_upsert_after_creating_keyed_tables(self, mock_snowflake_manager):
        manager = mock_snowflake_manager.return_value
        manager.check_table_exists.return_value = False
        manager.create_table.return_value = True
        manager.insert_rows.return_value = (True, None)

        scraper = DummyScraper()
        scraper.store_data_in_snowflake(
            [{"ticker": "KXTEST", "title": "Test Series"}],
            "RAW_SERIES",
            ["ticker"],
        )

        manager.create_table.assert_called_once_with(
            dict_list=[{"ticker": "KXTEST", "title": "Test Series"}],
            primary_keys=["ticker"],
            table_name="RAW_SERIES",
            delete=True,
        )
        manager.insert_rows.assert_called_once_with(
            target_table="RAW_SERIES",
            columns=["ticker", "title"],
            rows=[{"ticker": "KXTEST", "title": "Test Series"}],
            contains_dicts=True,
            update=True,
            return_error_msg=True,
        )

    @patch("market_data_platform.pipelines.base.SnowflakeManager")
    def test_store_data_in_snowflake_keeps_non_keyed_loads_insert_only(self, mock_snowflake_manager):
        manager = mock_snowflake_manager.return_value
        manager.check_table_exists.return_value = True
        manager.insert_rows.return_value = (True, None)

        scraper = DummyScraper()
        scraper.store_data_in_snowflake(
            [{"name": "no primary key table"}],
            "RAW_MISC",
            None,
        )

        manager.insert_rows.assert_called_once_with(
            target_table="RAW_MISC",
            columns=["name"],
            rows=[{"name": "no primary key table"}],
            contains_dicts=True,
            update=False,
            return_error_msg=True,
        )


if __name__ == "__main__":
    unittest.main()
