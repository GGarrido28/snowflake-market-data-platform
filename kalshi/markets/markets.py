from kalshi.base import KalshiBase

class Markets(KalshiBase):
    def get_all_markets(self, limit=100, params=None, all_pages=False):
        '''Fetches a list of markets with optional filtering parameters.'''
        if all_pages:
            return self.get_paginated_results("GET", "/markets", params=params)
        else:
            response = self.make_request("GET", "/markets", limit=limit, params=params)
            return response.json().get("markets", [])
