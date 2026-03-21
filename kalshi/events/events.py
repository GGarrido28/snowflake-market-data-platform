from kalshi.base import KalshiBase

class Events(KalshiBase):
    def __init__(self):
        super().__init__()
        self.events = []
        
    def get_all_events(self, limit=100, params=None, all_pages=False, status: str =None):
        '''Fetches a list of events with optional filtering parameters.'''
        if all_pages:
            return self.get_paginated_results("GET", "/events", params=params, status=status)
        else:
            response = self.make_request("GET", "/events", limit=limit, params=params, status=status)
            return response.json().get("events", [])
