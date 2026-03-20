import logging

from kalshi.markets import Markets
from snowflake.connection import SnowflakeManager

logging.basicConfig(level=logging.INFO)

class Scraper:
    def __init__(self):
        self.snowflake_manager = SnowflakeManager()
        
    def store_data_in_snowflake(self, data: list, table_name: str):
        '''Stores a list of dictionaries in a Snowflake table.'''
        if self.snowflake_manager.check_table_exists(table_name):
            success, log = self.snowflake_manager.insert_rows(table_name, data)
            if not success:
                logging.error(f"Failed to insert rows: {log}")
        else:
            self.snowflake_manager.create_table(table_name, data[0].keys())
            success, log = self.snowflake_manager.insert_rows(table_name, data)
            if not success:
                logging.error(f"Failed to insert rows: {log}")
                
    def run(self):
        '''Runs the scraper.'''
        logging.info("Starting scraper...")
        
        try:
            markets = Markets()
            market_data = markets.get_market_endpoints()
            self.store_data_in_snowflake(market_data["markets"], "RAW_MARKETS")
            self.store_data_in_snowflake(market_data["orderbook"], "RAW_MARKET_ORDERBOOKS")
            self.store_data_in_snowflake(market_data["trades"], "RAW_MARKET_TRADES")
            logging.info("Scraper finished.")
        except Exception as e:
            logging.error(f"Error running scraper: {e}")
        finally:
            if self.snowflake_manager:
                self.snowflake_manager.close()
                
if __name__ == "__main__":
    scrape = Scraper()
    scrape.run()