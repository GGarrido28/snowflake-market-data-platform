from kalshi.base import KalshiBase


class Series(KalshiBase):
    def __init__(self):
        super().__init__()
        self.series = []

    def get_all_series(self, limit=100, params=None, all_pages=False, **kwargs) -> list:
        '''Fetches a list of series with optional filtering parameters.'''
        if all_pages:
            self.series = self.get_paginated_results("GET", "/series", params=params, limit=limit, **kwargs)
        else:
            response = self.make_request("GET", "/series", limit=limit, params=params, **kwargs)
            self.series = response.json().get("series", [])
        return self.series
