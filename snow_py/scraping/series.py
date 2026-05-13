import logging
import os

from kalshi.markets import Series
from snow_py.base import Scraper

logging.basicConfig(level=logging.INFO)

class SeriesScraper(Scraper):
    def __init__(self):
        super().__init__()

    def _get_series_scope(self) -> str | None:
        '''Reads the optional series ticker scope from the environment.'''
        return os.getenv("KALSHI_SERIES_TICKER") or None

    def run(self):
        '''Runs the scraper.'''
        logging.info("Starting scraper...")

        # Series
        try:
            series = Series()
            series_ticker = self._get_series_scope()
            if series_ticker:
                logging.info("Fetching scoped series from Kalshi: %s", series_ticker)
                series_row = series.get_series(series_ticker)
                series_data = [series_row] if series_row else []
            else:
                series_data = series.get_all_series(all_pages=True)
            self.store_data_in_snowflake(series_data, "RAW_SERIES", ["ticker"])
        except Exception as e:
            logging.error(f"Error fetching series data: {e}")
        finally:
            if self.snowflake_manager:
                self.snowflake_manager.close()

if __name__ == "__main__":
    scrape = SeriesScraper()
    scrape.run()
