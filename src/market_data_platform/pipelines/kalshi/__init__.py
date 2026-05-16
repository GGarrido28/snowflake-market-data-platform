__all__ = ["EventsScraper", "MarketsScraper", "SeriesScraper"]


def __getattr__(name: str):
    if name == "EventsScraper":
        from market_data_platform.pipelines.kalshi.events import EventsScraper

        return EventsScraper
    if name == "MarketsScraper":
        from market_data_platform.pipelines.kalshi.markets import MarketsScraper

        return MarketsScraper
    if name == "SeriesScraper":
        from market_data_platform.pipelines.kalshi.series import SeriesScraper

        return SeriesScraper
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
