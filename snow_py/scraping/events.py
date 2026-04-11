import logging
import os

from kalshi.events import Events
from snow_py.base import Scraper

logging.basicConfig(level=logging.INFO)

class EventsScraper(Scraper):
    def __init__(self):
        super().__init__()

    def _get_event_status(self) -> str | None:
        '''Reads the configured Kalshi events status filter from the environment.'''
        configured_status = os.getenv("KALSHI_EVENTS_STATUS", "open").strip().lower()
        if configured_status in {"", "all"}:
            return None
        return configured_status

    def _get_event_scope(self) -> tuple[str | None, str | None]:
        '''Reads optional event scoping from the environment.'''
        event_ticker = os.getenv("KALSHI_EVENTS_EVENT_TICKER")
        series_ticker = os.getenv("KALSHI_EVENTS_SERIES_TICKER")

        if event_ticker and series_ticker:
            raise ValueError("Set only one of KALSHI_EVENTS_EVENT_TICKER or KALSHI_EVENTS_SERIES_TICKER.")

        return event_ticker, series_ticker

    def _validate_event_scope(
        self,
        event_status: str | None,
        event_ticker: str | None,
        series_ticker: str | None,
    ) -> None:
        '''Prevents accidental full historical backfills when no event scope is provided.'''
        if event_status is None and not event_ticker and not series_ticker:
            raise ValueError(
                "Set KALSHI_EVENTS_EVENT_TICKER or KALSHI_EVENTS_SERIES_TICKER when KALSHI_EVENTS_STATUS=all."
            )

    def run(self):
        '''Runs the scraper.'''
        logging.info("Starting scraper...")

        # Events
        try:
            events = Events()
            event_status = self._get_event_status()
            event_ticker, series_ticker = self._get_event_scope()
            self._validate_event_scope(event_status, event_ticker, series_ticker)

            if event_ticker:
                logging.info("Fetching exact Kalshi event: %s", event_ticker)
            elif series_ticker:
                logging.info("Fetching Kalshi events for series: %s", series_ticker)
            elif event_status is None:
                logging.info("Fetching Kalshi events with no status filter.")
            else:
                logging.info("Fetching Kalshi events with status filter: %s", event_status)

            event_data = events.get_target_events(
                event_ticker=event_ticker,
                series_ticker=series_ticker,
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
