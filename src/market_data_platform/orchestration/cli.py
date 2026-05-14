import argparse
import logging
import os

from market_data_platform.pipelines.kalshi import (
    EventsScraper,
    MarketsScraper,
    SeriesScraper,
)


logging.basicConfig(level=logging.INFO)


_MARKET_SCOPE_ENVS = (
    "KALSHI_MARKET_TICKER",
    "KALSHI_EVENT_TICKER",
    "KALSHI_MARKETS_EVENT_QUERY_FILE",
)
_EVENT_SCOPE_ENVS = (
    "KALSHI_EVENTS_EVENT_TICKER",
    "KALSHI_EVENTS_SERIES_TICKER",
    "KALSHI_EVENTS_SERIES_QUERY_FILE",
)
_SERIES_SCOPE_ENVS = ("KALSHI_SERIES_TICKER",)


def _set_exclusive_scope(scope_envs: tuple[str, ...], chosen_env: str, value: str) -> None:
    '''Clears every env var in `scope_envs` and sets only `chosen_env` = `value`.

    The scrapers each enforce an "at most one scope env" guard; this ensures
    pre-existing shell state never collides with the scope the caller just
    asked for.
    '''
    for env in scope_envs:
        os.environ.pop(env, None)
    os.environ[chosen_env] = value


def _run_scraper(scraper_class) -> None:
    try:
        scraper = scraper_class()
        scraper.run()
    except Exception as e:
        scraper_name = getattr(scraper_class, "__name__", repr(scraper_class))
        logging.error(f"Error running {scraper_name}: {e}")


def run_all_scrapers() -> None:
    '''Runs all three scrapers using whatever scope env vars are already set.'''
    for scraper_class in (MarketsScraper, SeriesScraper, EventsScraper):
        _run_scraper(scraper_class)


def scrape_one_market(
    *,
    market_ticker: str | None = None,
    event_ticker: str | None = None,
) -> None:
    '''Scrapes one market (or all markets for one event) plus its orderbook and
    full trade history.

    Mutates process env vars in `_MARKET_SCOPE_ENVS` so the scraper picks up the
    requested scope; pre-existing values in that family are cleared first. The
    chosen scope value is left set on the process after the call returns — fine
    for the CLI (process exits), worth knowing in a notebook where a later
    direct `MarketsScraper().run()` would silently reuse it.
    '''
    if bool(market_ticker) == bool(event_ticker):
        raise ValueError("Provide exactly one of market_ticker or event_ticker.")
    chosen_env = "KALSHI_MARKET_TICKER" if market_ticker else "KALSHI_EVENT_TICKER"
    chosen_value = market_ticker or event_ticker
    assert chosen_value is not None  # guarded by the bool(x) == bool(y) check above
    _set_exclusive_scope(_MARKET_SCOPE_ENVS, chosen_env, chosen_value)
    _run_scraper(MarketsScraper)


def scrape_one_event(
    *,
    event_ticker: str | None = None,
    series_ticker: str | None = None,
) -> None:
    '''Scrapes events for one specific event ticker or one specific series.

    Mutates process env vars in `_EVENT_SCOPE_ENVS` so the scraper picks up the
    requested scope; pre-existing values in that family are cleared first. The
    chosen scope value is left set on the process after the call returns — fine
    for the CLI (process exits), worth knowing in a notebook where a later
    direct `EventsScraper().run()` would silently reuse it.
    '''
    if bool(event_ticker) == bool(series_ticker):
        raise ValueError("Provide exactly one of event_ticker or series_ticker.")
    chosen_env = "KALSHI_EVENTS_EVENT_TICKER" if event_ticker else "KALSHI_EVENTS_SERIES_TICKER"
    chosen_value = event_ticker or series_ticker
    assert chosen_value is not None  # guarded by the bool(x) == bool(y) check above
    _set_exclusive_scope(_EVENT_SCOPE_ENVS, chosen_env, chosen_value)
    _run_scraper(EventsScraper)


def scrape_one_series(*, series_ticker: str) -> None:
    '''Scrapes a single series row by ticker.

    Mutates `KALSHI_SERIES_TICKER` on the process so the scraper picks up the
    requested scope. The env var is left set after the call returns — fine for
    the CLI (process exits), worth knowing in a notebook where a later direct
    `SeriesScraper().run()` would silently reuse it.
    '''
    if not series_ticker:
        raise ValueError("series_ticker is required.")
    _set_exclusive_scope(_SERIES_SCOPE_ENVS, "KALSHI_SERIES_TICKER", series_ticker)
    _run_scraper(SeriesScraper)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="market_data_platform.orchestration",
        description="Kalshi scraping orchestration. Pick a scope to keep request volume down during piecewise development.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("all", help="Run all scrapers using whatever KALSHI_* scope env vars are set.")

    market_parser = sub.add_parser(
        "market",
        help="Scrape markets + orderbooks + trades for one market or one event.",
    )
    market_group = market_parser.add_mutually_exclusive_group(required=True)
    market_group.add_argument("--market-ticker", help="Exact market ticker to scrape.")
    market_group.add_argument("--event-ticker", help="Event ticker; scrapes every market under it.")

    events_parser = sub.add_parser(
        "events",
        help="Scrape events scoped to one event ticker or one series ticker.",
    )
    events_group = events_parser.add_mutually_exclusive_group(required=True)
    events_group.add_argument("--event-ticker", help="Exact event ticker to scrape.")
    events_group.add_argument("--series-ticker", help="Series ticker; scrapes every event under it.")

    series_parser = sub.add_parser("series", help="Scrape a single series row by ticker.")
    series_parser.add_argument("--ticker", required=True, help="Series ticker to scrape.")

    return parser


def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)

    if args.command == "all":
        run_all_scrapers()
    elif args.command == "market":
        scrape_one_market(
            market_ticker=args.market_ticker,
            event_ticker=args.event_ticker,
        )
    elif args.command == "events":
        scrape_one_event(
            event_ticker=args.event_ticker,
            series_ticker=args.series_ticker,
        )
    elif args.command == "series":
        scrape_one_series(series_ticker=args.ticker)


if __name__ == "__main__":
    main()
