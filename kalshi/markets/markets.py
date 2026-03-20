from kalshi.base import KalshiBase

class Markets(KalshiBase):
    def get_all_markets(self, limit=100, params=None, all_pages=False, status: str =None, mve_filter:str=None) -> list:
        '''Fetches a list of markets with optional filtering parameters.'''
        if all_pages:
            return self.get_paginated_results("GET", "/markets", params=params, status=status, mve_filter=mve_filter)
        else:
            response = self.make_request("GET", "/markets", limit=limit, params=params, status=status, mve_filter=mve_filter)
            return response.json().get("markets", [])
