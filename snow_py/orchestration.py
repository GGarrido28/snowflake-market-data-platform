from snow_py.scraping import (
    MarketsScraper,
    SeriesScraper,
    EventsScraper
)

def run_all_scrapers():
    scrapers = [
        MarketsScraper(),
        SeriesScraper(),
        EventsScraper()
    ]

    for scraper in scrapers:
        scraper.run()

if __name__ == "__main__":
    run_all_scrapers()
