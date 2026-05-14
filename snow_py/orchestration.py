from market_data_platform.orchestration.cli import (
    main,
    run_all_scrapers,
    scrape_one_event,
    scrape_one_market,
    scrape_one_series,
)

__all__ = [
    "main",
    "run_all_scrapers",
    "scrape_one_event",
    "scrape_one_market",
    "scrape_one_series",
]

if __name__ == "__main__":
    main()
