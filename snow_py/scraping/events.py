from market_data_platform.pipelines.kalshi.events import Events, EventsScraper

__all__ = ["Events", "EventsScraper"]

if __name__ == "__main__":
    EventsScraper().run()
