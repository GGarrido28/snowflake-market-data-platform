from market_data_platform.sources.kalshi.base import KalshiBase

DEFAULT_SERIES_PAGE_SIZE = 100


class Series(KalshiBase):
    def __init__(self):
        super().__init__()
        self.series = []

    def get_all_series(self, limit=DEFAULT_SERIES_PAGE_SIZE, params=None, all_pages=False, **kwargs) -> list:
        '''Fetches a list of series with optional filtering parameters.'''
        if all_pages:
            self.series = self.get_paginated_results("GET", "/series", params=params, limit=limit, **kwargs)
        else:
            response = self.make_request("GET", "/series", limit=limit, params=params, **kwargs)
            self.series = response.json().get("series", [])
        return self.series

    def get_series(self, series_ticker: str) -> dict:
        '''Fetches a single series by ticker.'''
        response = self.make_request("GET", f"/series/{series_ticker}")
        return response.json().get("series", {})
