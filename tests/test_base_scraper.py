import unittest
from unittest.mock import patch

from snow_py.base import Scraper


class DummyScraper(Scraper):
    def run(self):
        pass


class ScraperStorageTests(unittest.TestCase):
    @patch("snow_py.base.SnowflakeManager")
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

    @patch("snow_py.base.SnowflakeManager")
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

    @patch("snow_py.base.SnowflakeManager")
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
