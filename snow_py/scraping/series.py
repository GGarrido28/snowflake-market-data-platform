import logging

from kalshi.markets import Series
from snow_py.base import Scraper

logging.basicConfig(level=logging.INFO)

class SeriesScraper(Scraper):
    def __init__(self):
        super().__init__()

    def run(self):
        '''Runs the scraper.'''
        logging.info("Starting scraper...")

        # Series
        try:
            series = Series()
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
