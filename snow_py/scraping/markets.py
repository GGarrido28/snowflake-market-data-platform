import logging
import os
from time import perf_counter

from kalshi.markets import Markets
from snow_py.base import Scraper

logging.basicConfig(level=logging.INFO)

class MarketsScraper(Scraper):
    def __init__(self):
        super().__init__()

    def _get_market_scope(self) -> tuple[str | None, str | None]:
        '''Reads the targeted scrape scope from the environment.'''
        market_ticker = os.getenv("KALSHI_MARKET_TICKER")
        event_ticker = os.getenv("KALSHI_EVENT_TICKER")

        if market_ticker and event_ticker:
            raise ValueError("Set only one of KALSHI_MARKET_TICKER or KALSHI_EVENT_TICKER.")
        if not market_ticker and not event_ticker:
            raise ValueError(
                "Set KALSHI_MARKET_TICKER or KALSHI_EVENT_TICKER before running the markets scraper."
            )

        return market_ticker, event_ticker

    def run(self):
        '''Runs the scraper.'''
        logging.info("Starting scraper...")

        # Markets
        try:
            markets = Markets()
            market_ticker, event_ticker = self._get_market_scope()
            if market_ticker:
                logging.info("Fetching scoped market from Kalshi: %s", market_ticker)
            else:
                logging.info("Fetching scoped event from Kalshi: %s", event_ticker)
            markets_started_at = perf_counter()
            market_rows = markets.get_target_markets(
                market_ticker=market_ticker,
                event_ticker=event_ticker,
            )
            logging.info(
                "Fetched %s scoped markets in %.1fs.",
                len(market_rows),
                perf_counter() - markets_started_at,
            )

            self.store_data_in_snowflake(market_rows, "RAW_MARKETS", ["ticker"])

            logging.info(
                "Fetching orderbooks and recent trades for %s markets. This is the long-running phase.",
                len(market_rows),
            )
            detail_data = markets.get_market_details(market_rows)
            self.store_data_in_snowflake(detail_data["orderbook"], "RAW_MARKET_ORDERBOOKS", ["market_ticker"])
            self.store_data_in_snowflake(detail_data["trades"], "RAW_MARKET_TRADES", ["trade_id"])
            logging.info("Scraper finished.")
        except Exception as e:
            logging.error(f"Error running scraper: {e}")
        finally:
            if self.snowflake_manager:
                self.snowflake_manager.close()

if __name__ == "__main__":
    scrape = MarketsScraper()
    scrape.run()
