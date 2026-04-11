from kalshi.base import KalshiBase

class Series(KalshiBase):
    def __init__(self):
        super().__init__()
        self.series = []

    def get_all_series(self) -> list:
        '''Fetches a list of series with optional filtering parameters.'''
        response = self.make_request("GET", "/series")
        self.series = response.json().get("series", [])
        return self.series