from kalshi.base import KalshiBase

class Events(KalshiBase):
    def get_events(self, limit=100, params=None, all_pages=False):
        '''Fetches a list of events with optional filtering parameters.'''
        if all_pages:
            return self.get_paginated_results("GET", "/events", params=params)
        else:
            response = self.make_request("GET", "/events", limit=limit, params=params)
            return response.json().get("events", [])
