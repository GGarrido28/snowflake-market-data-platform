from market_data_platform.pipelines.kalshi.series import Series, SeriesScraper

__all__ = ["Series", "SeriesScraper"]

if __name__ == "__main__":
    SeriesScraper().run()
