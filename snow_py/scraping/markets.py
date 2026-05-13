import logging
import os
from pathlib import Path
from time import perf_counter

from kalshi.markets import Markets
from snow_py.base import Scraper

logging.basicConfig(level=logging.INFO)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class MarketsScraper(Scraper):
    def __init__(self):
        super().__init__()

    def _get_market_scope(self) -> tuple[str | None, str | None, str | None]:
        '''Reads the targeted scrape scope from the environment. At most one of the three scope vars may be set.'''
        market_ticker = os.getenv("KALSHI_MARKET_TICKER")
        event_ticker = os.getenv("KALSHI_EVENT_TICKER")
        event_query_file = os.getenv("KALSHI_MARKETS_EVENT_QUERY_FILE")

        set_count = sum(1 for value in (market_ticker, event_ticker, event_query_file) if value)
        if set_count > 1:
            raise ValueError(
                "Set only one of KALSHI_MARKET_TICKER, KALSHI_EVENT_TICKER, "
                "or KALSHI_MARKETS_EVENT_QUERY_FILE."
            )
        if set_count == 0:
            raise ValueError(
                "Set KALSHI_MARKET_TICKER, KALSHI_EVENT_TICKER, or KALSHI_MARKETS_EVENT_QUERY_FILE "
                "before running the markets scraper."
            )

        return market_ticker, event_ticker, event_query_file

    def _load_event_tickers_from_query(self, query_file: str) -> list[str]:
        '''Loads the configured SQL file and returns its `event_ticker` column as a deduped list.

        Contract: the SQL must produce a column named `event_ticker` (case-insensitive — SnowflakeManager
        lowercases column names). NULL values are skipped; duplicates are removed while preserving
        first-seen order.
        '''
        path = Path(query_file).expanduser()
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        if not path.exists():
            raise FileNotFoundError(
                f"Event query file not found at {path}. "
                "Set KALSHI_MARKETS_EVENT_QUERY_FILE to a valid path (absolute, or relative to the repo root)."
            )

        sql = path.read_text(encoding="utf-8")
        rows = self.snowflake_manager.execute(sql, raise_exc=True)

        raw_tickers = [row.get("event_ticker") for row in rows if row.get("event_ticker")]
        tickers = list(dict.fromkeys(raw_tickers))

        if not tickers:
            logging.warning("Event query returned 0 tickers: %s", path)
        else:
            dropped = len(raw_tickers) - len(tickers)
            if dropped:
                logging.info(
                    "Event query returned %s ticker(s) from %s (%s duplicate(s) dropped)",
                    len(tickers),
                    path,
                    dropped,
                )
            else:
                logging.info("Event query returned %s ticker(s) from %s", len(tickers), path)
        return tickers

    def _fetch_markets_for_event_list(
        self,
        markets_client: Markets,
        event_tickers: list[str],
    ) -> list[dict]:
        '''Fetches markets for each event ticker and concatenates the results.'''
        all_markets: list[dict] = []
        for event_ticker in event_tickers:
            try:
                markets_for_event = markets_client.get_target_markets(event_ticker=event_ticker)
                logging.info("Fetched %s markets for event %s", len(markets_for_event), event_ticker)
                all_markets.extend(markets_for_event)
            except Exception as e:
                logging.warning("Failed to fetch markets for event %s: %s", event_ticker, e)
        return all_markets

    def run(self):
        '''Runs the scraper.'''
        logging.info("Starting scraper...")

        # Markets
        try:
            markets = Markets()
            market_ticker, event_ticker, event_query_file = self._get_market_scope()
            markets_started_at = perf_counter()
            if event_query_file:
                logging.info("Fetching scoped markets from Kalshi for events from query: %s", event_query_file)
                event_tickers = self._load_event_tickers_from_query(event_query_file)
                market_rows = self._fetch_markets_for_event_list(markets, event_tickers)
            elif market_ticker:
                logging.info("Fetching scoped market from Kalshi: %s", market_ticker)
                market_rows = markets.get_target_markets(market_ticker=market_ticker)
            else:
                logging.info("Fetching scoped event from Kalshi: %s", event_ticker)
                market_rows = markets.get_target_markets(event_ticker=event_ticker)
            logging.info(
                "Fetched %s scoped markets in %.1fs.",
                len(market_rows),
                perf_counter() - markets_started_at,
            )

            self._recreate_table_if_schema_changed("RAW_MARKETS", market_rows, ["ticker"])
            self.store_data_in_snowflake(market_rows, "RAW_MARKETS", ["ticker"])

            logging.info(
                "Fetching orderbooks and recent trades for %s markets. This is the long-running phase.",
                len(market_rows),
            )
            detail_data = markets.get_market_details(market_rows)
            self._recreate_table_if_schema_changed(
                "RAW_MARKET_ORDERBOOKS",
                detail_data["orderbook"],
                ["market_ticker"],
            )
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
