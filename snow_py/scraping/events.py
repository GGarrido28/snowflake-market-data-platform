import logging
import os
from pathlib import Path

from kalshi.events import Events
from snow_py.base import Scraper

logging.basicConfig(level=logging.INFO)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class EventsScraper(Scraper):
    def __init__(self):
        super().__init__()

    def _get_event_status(self) -> str | None:
        '''Reads the configured Kalshi events status filter from the environment.'''
        configured_status = os.getenv("KALSHI_EVENTS_STATUS", "open").strip().lower()
        if configured_status in {"", "all"}:
            return None
        return configured_status

    def _get_event_scope(self) -> tuple[str | None, str | None, str | None]:
        '''Reads optional event scoping from the environment. At most one of the three scope vars may be set.'''
        event_ticker = os.getenv("KALSHI_EVENTS_EVENT_TICKER")
        series_ticker = os.getenv("KALSHI_EVENTS_SERIES_TICKER")
        series_query_file = os.getenv("KALSHI_EVENTS_SERIES_QUERY_FILE")

        set_count = sum(1 for value in (event_ticker, series_ticker, series_query_file) if value)
        if set_count > 1:
            raise ValueError(
                "Set only one of KALSHI_EVENTS_EVENT_TICKER, KALSHI_EVENTS_SERIES_TICKER, "
                "or KALSHI_EVENTS_SERIES_QUERY_FILE."
            )

        return event_ticker, series_ticker, series_query_file

    def _validate_event_scope(
        self,
        event_status: str | None,
        event_ticker: str | None,
        series_ticker: str | None,
        series_query_file: str | None,
    ) -> None:
        '''Prevents accidental full historical backfills when no event scope is provided.'''
        if event_status is None and not (event_ticker or series_ticker or series_query_file):
            raise ValueError(
                "Set KALSHI_EVENTS_EVENT_TICKER, KALSHI_EVENTS_SERIES_TICKER, "
                "or KALSHI_EVENTS_SERIES_QUERY_FILE when KALSHI_EVENTS_STATUS=all."
            )

    def _load_series_tickers_from_query(self, query_file: str) -> list[str]:
        '''Loads the configured SQL file and returns the `ticker` column from its result set.'''
        path = Path(query_file).expanduser()
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        if not path.exists():
            raise FileNotFoundError(
                f"Series query file not found at {path}. "
                "Set KALSHI_EVENTS_SERIES_QUERY_FILE to a valid path (absolute, or relative to the repo root)."
            )

        sql = path.read_text(encoding="utf-8")
        rows = self.snowflake_manager.execute(sql, raise_exc=True)

        tickers: list[str] = []
        for row in rows:
            ticker = row.get("ticker")
            if ticker:
                tickers.append(ticker)

        if not tickers:
            logging.warning("Series query returned 0 tickers: %s", path)
        else:
            logging.info("Series query returned %s ticker(s) from %s", len(tickers), path)
        return tickers

    def _fetch_events_for_series_list(
        self,
        events_client: Events,
        series_tickers: list[str],
        status: str | None,
    ) -> list[dict]:
        '''Fetches events for each series ticker and concatenates the results.'''
        all_events: list[dict] = []
        for ticker in series_tickers:
            try:
                events_for_series = events_client.get_target_events(
                    series_ticker=ticker,
                    status=status,
                )
                logging.info("Fetched %s events for series %s", len(events_for_series), ticker)
                all_events.extend(events_for_series)
            except Exception as e:
                logging.warning("Failed to fetch events for series %s: %s", ticker, e)
        return all_events

    def run(self):
        '''Runs the scraper.'''
        logging.info("Starting scraper...")

        # Events
        try:
            events = Events()
            event_status = self._get_event_status()
            event_ticker, series_ticker, series_query_file = self._get_event_scope()
            self._validate_event_scope(event_status, event_ticker, series_ticker, series_query_file)

            if series_query_file:
                logging.info("Fetching Kalshi events for series from query: %s", series_query_file)
                series_tickers = self._load_series_tickers_from_query(series_query_file)
                event_data = self._fetch_events_for_series_list(events, series_tickers, event_status)
            elif event_ticker:
                logging.info("Fetching exact Kalshi event: %s", event_ticker)
                event_data = events.get_target_events(
                    event_ticker=event_ticker,
                    status=event_status,
                )
            elif series_ticker:
                logging.info("Fetching Kalshi events for series: %s", series_ticker)
                event_data = events.get_target_events(
                    series_ticker=series_ticker,
                    status=event_status,
                )
            else:
                logging.info("Fetching Kalshi events with status filter: %s", event_status)
                event_data = events.get_target_events(
                    status=event_status,
                )

            self.store_data_in_snowflake(event_data, "RAW_EVENTS", ["event_ticker"])
        except Exception as e:
            logging.error(f"Error fetching events data: {e}")
        finally:
            if self.snowflake_manager:
                self.snowflake_manager.close()

if __name__ == "__main__":
    scrape = EventsScraper()
    scrape.run()
