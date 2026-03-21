import logging

from kalshi.markets import Markets
from snow_py.connection import SnowflakeManager

logging.basicConfig(level=logging.INFO)

class Scraper:
    def __init__(self):
        self.snowflake_manager = SnowflakeManager("PROD", "RAW")

    def _normalize_records(self, data: list) -> list[dict]:
        '''Flattens nested API responses into Snowflake-friendly row dictionaries.'''
        normalized: list[dict] = []
        for item in data or []:
            if isinstance(item, dict):
                normalized.append(item)
            elif isinstance(item, list):
                normalized.extend(row for row in item if isinstance(row, dict))
        return normalized

    def store_data_in_snowflake(self, data: list, table_name: str, primary_keys: list | None = None):
        '''Stores a list of dictionaries in a Snowflake table.'''
        normalized_data = self._normalize_records(data)
        logging.info(f"{table_name}: prepared {len(normalized_data)} rows for Snowflake.")
        if not normalized_data:
            logging.info(f"No rows returned for {table_name}; skipping Snowflake load.")
            return

        if primary_keys is None:
            primary_keys = []

        if self.snowflake_manager.check_table_exists(table_name):
            success, log = self.snowflake_manager.insert_rows(
                target_table=table_name,
                columns=list(normalized_data[0].keys()),
                rows=normalized_data,
                contains_dicts=True,
                return_error_msg=True
            )
            if not success:
                logging.error(f"Failed to insert rows: {log}")
        else:
            created = self.snowflake_manager.create_table(
                dict_list=normalized_data,
                primary_keys=primary_keys,
                table_name=table_name,
                delete=True
            )
            if not created:
                logging.warning(f"Skipping insert for {table_name} because table creation did not run.")
                return
            success, log = self.snowflake_manager.insert_rows(
                target_table=table_name,
                columns=list(normalized_data[0].keys()),
                rows=normalized_data,
                contains_dicts=True,
                return_error_msg=True
            )
            if not success:
                logging.error(f"Failed to insert rows: {log}")
                
    def run(self):
        '''Runs the scraper.'''
        logging.info("Starting scraper...")
        
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
    scrape = Scraper()
    scrape.run()
