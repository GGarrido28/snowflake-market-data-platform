import logging

from kalshi.markets import Markets
from snow_py.base import Scraper

logging.basicConfig(level=logging.INFO)

class MarketsScraper(Scraper):
    def __init__(self):
        super().__init__()
                
    def run(self):
        '''Runs the scraper.'''
        logging.info("Starting scraper...")
        
        # Markets
        try:
            markets = Markets()
            market_data = markets.get_market_endpoints()
            self.store_data_in_snowflake(market_data["markets"], "RAW_MARKETS", ["ticker"])
            self.store_data_in_snowflake(market_data["orderbook"], "RAW_MARKET_ORDERBOOKS", ["market_id"])
            self.store_data_in_snowflake(market_data["trades"], "RAW_MARKET_TRADES", ["trade_id"])
            logging.info("Scraper finished.")
        except Exception as e:
            logging.error(f"Error running scraper: {e}")
        finally:
            if self.snowflake_manager:
                self.snowflake_manager.close()
                
if __name__ == "__main__":
    scrape = MarketsScraper()
    scrape.run()
