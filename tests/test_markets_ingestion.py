import os
import unittest
from unittest.mock import patch

from kalshi.markets import Markets
from snow_py.scraping.markets import MarketsScraper


class MarketEndpointTests(unittest.TestCase):
    @patch("kalshi.markets.markets.KalshiBase.__init__", return_value=None)
    def test_get_target_markets_uses_single_market_endpoint(self, _mock_base_init):
        market_payload = {"ticker": "KXTEST", "event_ticker": "EVT"}

        with patch.object(Markets, "get_market", return_value=market_payload) as mock_get_market:
            markets = Markets()

            result = markets.get_target_markets(market_ticker="KXTEST")

        mock_get_market.assert_called_once_with("KXTEST")
        self.assertEqual(result, [market_payload])

    @patch("kalshi.markets.markets.KalshiBase.__init__", return_value=None)
    def test_get_target_markets_uses_event_filter(self, _mock_base_init):
        expected_rows = [{"ticker": "KXTEST", "event_ticker": "EVT"}]

        with patch.object(Markets, "get_all_markets", return_value=expected_rows) as mock_get_all_markets:
            markets = Markets()

            result = markets.get_target_markets(event_ticker="EVT")

        mock_get_all_markets.assert_called_once_with(
            all_pages=True,
            limit=1000,
            event_ticker="EVT",
        )
        self.assertEqual(result, expected_rows)

    @patch("kalshi.markets.markets.KalshiBase.__init__", return_value=None)
    def test_get_all_markets_uses_pagination_limit_when_requested(self, _mock_base_init):
        expected_rows = [{"ticker": "KXTEST"}]

        with patch.object(Markets, "get_paginated_results", return_value=expected_rows) as mock_paginated:
            markets = Markets()

            result = markets.get_all_markets(all_pages=True, limit=1000, status="open")

        self.assertEqual(result, expected_rows)
        mock_paginated.assert_called_once_with(
            "GET",
            "/markets",
            params=None,
            limit=1000,
            status="open",
        )

    @patch("kalshi.markets.markets.KalshiBase.__init__", return_value=None)
    def test_get_market_endpoints_uses_market_ticker_for_orderbooks_and_trades(self, _mock_base_init):
        markets = Markets()
        markets.markets = []
        markets.orderbook = []
        markets.trades = []

        sample_orderbook = {"yes_dollars": [["0.5100", "15.00"]]}
        sample_trades = [{"trade_id": "trade-1", "ticker": "KXTEST"}]

        with patch.object(Markets, "get_target_markets", return_value=[{"ticker": "KXTEST"}]):
            with patch.object(Markets, "get_market_orderbook", return_value=sample_orderbook) as mock_orderbook:
                with patch.object(Markets, "get_market_trades", return_value=sample_trades) as mock_trades:
                    result = markets.get_market_endpoints(market_ticker="KXTEST")

        mock_orderbook.assert_called_once_with("KXTEST")
        mock_trades.assert_called_once_with("KXTEST")
        self.assertEqual(result["markets"], [{"ticker": "KXTEST"}])
        self.assertEqual(
            result["orderbook"],
            [{"market_ticker": "KXTEST", "orderbook": sample_orderbook}],
        )
        self.assertEqual(result["trades"], sample_trades)


class MarketsScraperTests(unittest.TestCase):
    @patch("snow_py.base.SnowflakeManager")
    def test_scraper_requires_a_target_scope(self, _mock_snowflake_manager):
        scraper = MarketsScraper()

        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "KALSHI_MARKET_TICKER or KALSHI_EVENT_TICKER"):
                scraper._get_market_scope()

    @patch("snow_py.base.SnowflakeManager")
    @patch("snow_py.scraping.markets.Markets")
    def test_scraper_loads_market_payloads(self, mock_markets_class, _mock_snowflake_manager):
        mock_markets = mock_markets_class.return_value
        mock_markets.get_target_markets.return_value = [{"ticker": "KXTEST"}]
        mock_markets.get_market_details.return_value = {
            "orderbook": [{"market_ticker": "KXTEST", "orderbook": {"yes_dollars": []}}],
            "trades": [{"trade_id": "trade-1", "ticker": "KXTEST"}],
        }
        _mock_snowflake_manager.return_value.check_table_exists.return_value = False

        scraper = MarketsScraper()
        with patch.object(scraper, "store_data_in_snowflake") as mock_store:
            with patch.object(scraper, "_get_market_scope", return_value=("KXTEST", None)):
                scraper.run()

        mock_markets.get_target_markets.assert_called_once_with(
            market_ticker="KXTEST",
            event_ticker=None,
        )
        mock_markets.get_market_details.assert_called_once_with([{"ticker": "KXTEST"}])
        mock_store.assert_any_call([{"ticker": "KXTEST"}], "RAW_MARKETS", ["ticker"])
        mock_store.assert_any_call(
            [{"market_ticker": "KXTEST", "orderbook": {"yes_dollars": []}}],
            "RAW_MARKET_ORDERBOOKS",
            ["market_ticker"],
        )
        mock_store.assert_any_call(
            [{"trade_id": "trade-1", "ticker": "KXTEST"}],
            "RAW_MARKET_TRADES",
            ["trade_id"],
        )

    @patch("snow_py.base.SnowflakeManager")
    @patch("snow_py.scraping.markets.Markets")
    def test_scraper_recreates_orderbook_table_when_schema_changes(
        self,
        mock_markets_class,
        mock_snowflake_manager,
    ):
        orderbook_rows = [{"market_ticker": "KXTEST", "orderbook": {"yes_dollars": []}}]
        mock_markets = mock_markets_class.return_value
        mock_markets.get_target_markets.return_value = [{"ticker": "KXTEST"}]
        mock_markets.get_market_details.return_value = {
            "orderbook": orderbook_rows,
            "trades": [],
        }
        snowflake_manager = mock_snowflake_manager.return_value
        snowflake_manager.check_table_exists.side_effect = lambda table_name: table_name == "RAW_MARKET_ORDERBOOKS"
        snowflake_manager.get_tables.return_value = {
            "raw_market_orderbooks": {
                "market_id": "VARCHAR",
                "orderbook": "VARIANT",
            }
        }
        snowflake_manager.create_table.return_value = True

        scraper = MarketsScraper()
        with patch.object(scraper, "store_data_in_snowflake"):
            with patch.object(scraper, "_get_market_scope", return_value=(None, "EVT")):
                scraper.run()

        snowflake_manager.create_table.assert_called_once_with(
            dict_list=orderbook_rows,
            primary_keys=["market_ticker"],
            table_name="RAW_MARKET_ORDERBOOKS",
            delete=True,
        )


if __name__ == "__main__":
    unittest.main()
