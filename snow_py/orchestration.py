import logging

from snow_py.scraping import (
    MarketsScraper,
    SeriesScraper,
    EventsScraper
)


logging.basicConfig(level=logging.INFO)


def run_all_scrapers():
    scraper_classes = [
        MarketsScraper,
        SeriesScraper,
        EventsScraper,
    ]

    for scraper_class in scraper_classes:
        try:
            scraper = scraper_class()
            scraper.run()
        except Exception as e:
            scraper_name = getattr(scraper_class, "__name__", repr(scraper_class))
            logging.error(f"Error running {scraper_name}: {e}")

if __name__ == "__main__":
    run_all_scrapers()
