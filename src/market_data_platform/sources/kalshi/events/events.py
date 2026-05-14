from market_data_platform.sources.kalshi.base import KalshiBase

DEFAULT_EVENTS_PAGE_SIZE = 200

class Events(KalshiBase):
    def __init__(self):
        super().__init__()
        self.events = []
        
    def get_all_events(self, limit=DEFAULT_EVENTS_PAGE_SIZE, params=None, all_pages=False, status: str =None, **kwargs):
        '''Fetches a list of events with optional filtering parameters.'''
        if all_pages:
            self.events = self.get_paginated_results("GET", "/events", params=params, limit=limit, status=status, **kwargs)
        else:
            response = self.make_request("GET", "/events", limit=limit, params=params, status=status, **kwargs)
            self.events = response.json().get("events", [])
        return self.events

    def get_event(self, event_ticker: str) -> dict:
        '''Fetches a single event by ticker.'''
        response = self.make_request("GET", f"/events/{event_ticker}")
        return response.json().get("event", {})

    def get_target_events(
        self,
        event_ticker: str | None = None,
        series_ticker: str | None = None,
        status: str | None = None,
    ) -> list:
        '''Fetches a scoped set of events using either exact event or series filters.'''
        if event_ticker and series_ticker:
            raise ValueError("Set either event_ticker or series_ticker, not both.")

        if event_ticker:
            event = self.get_event(event_ticker)
            self.events = [event] if event else []
        else:
            self.events = self.get_all_events(
                all_pages=True,
                limit=DEFAULT_EVENTS_PAGE_SIZE,
                status=status,
                series_ticker=series_ticker,
            )
        return self.events
