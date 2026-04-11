import os
import unittest
from unittest.mock import patch

from kalshi.events import Events
from snow_py.scraping.events import EventsScraper


class EventEndpointTests(unittest.TestCase):
    @patch("kalshi.events.events.KalshiBase.__init__", return_value=None)
    def test_get_all_events_uses_pagination_limit_when_requested(self, _mock_base_init):
        expected_rows = [{"event_ticker": "KXTEST-25"}]

        with patch.object(Events, "get_paginated_results", return_value=expected_rows) as mock_paginated:
            events = Events()

            result = events.get_all_events(all_pages=True, limit=1000, status="open", series_ticker="KXTEST")

        self.assertEqual(result, expected_rows)
        mock_paginated.assert_called_once_with(
            "GET",
            "/events",
            params=None,
            limit=1000,
            status="open",
            series_ticker="KXTEST",
        )

    @patch("kalshi.events.events.KalshiBase.__init__", return_value=None)
    def test_get_target_events_uses_exact_event_endpoint(self, _mock_base_init):
        event_payload = {"event_ticker": "KXMASTERS-25", "series_ticker": "KXMASTERS"}

        with patch.object(Events, "get_event", return_value=event_payload) as mock_get_event:
            events = Events()

            result = events.get_target_events(event_ticker="KXMASTERS-25", status=None)

        mock_get_event.assert_called_once_with("KXMASTERS-25")
        self.assertEqual(result, [event_payload])

    @patch("kalshi.events.events.KalshiBase.__init__", return_value=None)
    def test_get_target_events_uses_series_scope(self, _mock_base_init):
        expected_rows = [{"event_ticker": "KXMASTERS-25", "series_ticker": "KXMASTERS"}]

        with patch.object(Events, "get_all_events", return_value=expected_rows) as mock_get_all_events:
            events = Events()

            result = events.get_target_events(series_ticker="KXMASTERS", status=None)

        mock_get_all_events.assert_called_once_with(
            all_pages=True,
            limit=1000,
            status=None,
            series_ticker="KXMASTERS",
        )
        self.assertEqual(result, expected_rows)


class EventsScraperTests(unittest.TestCase):
    @patch("snow_py.base.SnowflakeManager")
    def test_default_event_status_is_open(self, _mock_snowflake_manager):
        scraper = EventsScraper()

        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(scraper._get_event_status(), "open")

    @patch("snow_py.base.SnowflakeManager")
    def test_all_event_status_removes_filter(self, _mock_snowflake_manager):
        scraper = EventsScraper()

        with patch.dict(os.environ, {"KALSHI_EVENTS_STATUS": "all"}, clear=True):
            self.assertIsNone(scraper._get_event_status())

    @patch("snow_py.base.SnowflakeManager")
    def test_scraper_requires_scope_when_all_status_is_configured(self, _mock_snowflake_manager):
        scraper = EventsScraper()

        with patch.dict(os.environ, {"KALSHI_EVENTS_STATUS": "all"}, clear=True):
            with self.assertRaisesRegex(ValueError, "KALSHI_EVENTS_EVENT_TICKER or KALSHI_EVENTS_SERIES_TICKER"):
                scraper._validate_event_scope(scraper._get_event_status(), *scraper._get_event_scope())

    @patch("snow_py.base.SnowflakeManager")
    @patch("snow_py.scraping.events.Events")
    def test_scraper_loads_events_with_configured_status(self, mock_events_class, _mock_snowflake_manager):
        mock_events_class.return_value.get_target_events.return_value = [{"event_ticker": "KXTEST-25"}]

        scraper = EventsScraper()
        with patch.object(scraper, "store_data_in_snowflake") as mock_store:
            with patch.dict(os.environ, {"KALSHI_EVENTS_STATUS": "closed"}, clear=True):
                scraper.run()

        mock_events_class.return_value.get_target_events.assert_called_once_with(
            event_ticker=None,
            series_ticker=None,
            status="closed",
        )
        mock_store.assert_called_once_with([{"event_ticker": "KXTEST-25"}], "RAW_EVENTS", ["event_ticker"])

    @patch("snow_py.base.SnowflakeManager")
    @patch("snow_py.scraping.events.Events")
    def test_scraper_loads_exact_event_when_event_scope_is_configured(
        self,
        mock_events_class,
        _mock_snowflake_manager,
    ):
        mock_events_class.return_value.get_target_events.return_value = [{"event_ticker": "KXMASTERS-25"}]

        scraper = EventsScraper()
        with patch.object(scraper, "store_data_in_snowflake") as mock_store:
            with patch.dict(
                os.environ,
                {
                    "KALSHI_EVENTS_STATUS": "all",
                    "KALSHI_EVENTS_EVENT_TICKER": "KXMASTERS-25",
                },
                clear=True,
            ):
                scraper.run()

        mock_events_class.return_value.get_target_events.assert_called_once_with(
            event_ticker="KXMASTERS-25",
            series_ticker=None,
            status=None,
        )
        mock_store.assert_called_once_with([{"event_ticker": "KXMASTERS-25"}], "RAW_EVENTS", ["event_ticker"])


if __name__ == "__main__":
    unittest.main()
