import logging

from kalshi.events import Events
from snow_py.base import Scraper

logging.basicConfig(level=logging.INFO)

class EventsScraper(Scraper):
    def __init__(self):
        super().__init__()

    def run(self):
        '''Runs the scraper.'''
        logging.info("Starting scraper...")

        # Events
        try:
            events = Events()
            event_data = events.get_all_events(all_pages=True, status='open')
            self.store_data_in_snowflake(event_data, "RAW_EVENTS", ["event_ticker"])
        except Exception as e:
            logging.error(f"Error fetching events data: {e}")
        finally:
            if self.snowflake_manager:
                self.snowflake_manager.close()

if __name__ == "__main__":
    scrape = EventsScraper()
    scrape.run()
