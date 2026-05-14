from market_data_platform.pipelines.kalshi.markets import Markets, MarketsScraper

__all__ = ["Markets", "MarketsScraper"]

if __name__ == "__main__":
    MarketsScraper().run()
