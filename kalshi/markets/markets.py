from kalshi.base import KalshiBase

class Markets(KalshiBase):
    def __init__(self):
        self.markets = []
        self.orderbook = []
        self.trades = []
        
    def get_all_markets(self, limit=100, params=None, all_pages=False, **kwargs) -> list:
        '''Fetches a list of markets with optional filtering parameters.'''
        if all_pages:
            return self.get_paginated_results("GET", "/markets", params=params, **kwargs)
        else:
            response = self.make_request("GET", "/markets", limit=limit, params=params, **kwargs)
            return response.json().get("markets", [])
    
    def get_market_orderbook(self, market_id: str) -> dict:
        '''Fetches the order book for a specific market.'''
        response = self.make_request("GET", f"/markets/{market_id}/orderbook")
        return response.json()
    
    def get_market_trades(self, market_id: str=None, limit=100) -> list:
        '''Fetches recent trades for a specific market.'''
        response = self.make_request("GET", "/markets/trades", limit=limit, ticker=market_id)
        return response.json().get("trades", [])
    
    def get_market_endpoints(self):
        '''Runs all market-related endpoints and stores results in class attributes.'''
        self.markets = self.get_all_markets(all_pages=True, status='open', mve_filter='exclude')
        for market in self.markets:
            market_id = market.get("id")
            if market_id:
                self.orderbook.append(self.get_market_orderbook(market_id))
                self.trades.append(self.get_market_trades(market_id))
        return {
            "markets": self.markets,
            "orderbook": self.orderbook,
            "trades": self.trades
        }