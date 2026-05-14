import logging
from time import perf_counter

from market_data_platform.sources.kalshi.base import KalshiBase


DEFAULT_MARKETS_PAGE_SIZE = 1000
DEFAULT_TRADES_PAGE_SIZE = 1000
DETAIL_PROGRESS_EVERY = 100

class Markets(KalshiBase):
    def __init__(self):
        super().__init__()
        self.markets = []
        self.orderbook = []
        self.trades = []
        
    def get_all_markets(self, limit=DEFAULT_MARKETS_PAGE_SIZE, params=None, all_pages=False, **kwargs) -> list:
        '''Fetches a list of markets with optional filtering parameters.'''
        if all_pages:
            return self.get_paginated_results("GET", "/markets", params=params, limit=limit, **kwargs)
        else:
            response = self.make_request("GET", "/markets", limit=limit, params=params, **kwargs)
            return response.json().get("markets", [])
    
    def get_market_orderbook(self, market_ticker: str) -> dict:
        '''Fetches the order book for a specific market.'''
        response = self.make_request("GET", f"/markets/{market_ticker}/orderbook")
        return response.json().get("orderbook_fp", {})
    
    def get_market_trades(
        self,
        market_ticker: str | None = None,
        limit: int = DEFAULT_TRADES_PAGE_SIZE,
        all_pages: bool = True,
    ) -> list:
        '''Fetches trades for a specific market.

        Defaults to paginating through the full trade history via the cursor; the
        Kalshi API caps a single page at 1000 rows, so a one-shot request would
        silently truncate any market with more trades than that.
        '''
        if all_pages:
            return self.get_paginated_results(
                "GET",
                "/markets/trades",
                limit=limit,
                ticker=market_ticker,
            )
        response = self.make_request("GET", "/markets/trades", limit=limit, ticker=market_ticker)
        return response.json().get("trades", [])

    def get_market(self, market_ticker: str) -> dict:
        '''Fetches a single market by ticker.'''
        response = self.make_request("GET", f"/markets/{market_ticker}")
        return response.json().get("market", {})

    def get_target_markets(self, market_ticker: str | None = None, event_ticker: str | None = None) -> list:
        '''Fetches the scoped set of markets for a specific market or event.'''
        if market_ticker and event_ticker:
            raise ValueError("Set either market_ticker or event_ticker, not both.")
        if not market_ticker and not event_ticker:
            raise ValueError("A market_ticker or event_ticker is required for targeted market scraping.")

        if market_ticker:
            market = self.get_market(market_ticker)
            self.markets = [market] if market else []
        else:
            self.markets = self.get_all_markets(
                all_pages=True,
                limit=DEFAULT_MARKETS_PAGE_SIZE,
                event_ticker=event_ticker,
            )
        return self.markets

    def get_market_details(
        self,
        markets: list[dict] | None = None,
        progress_every: int = DETAIL_PROGRESS_EVERY,
        paginate_trades: bool = True,
    ) -> dict:
        '''Fetches orderbooks and trades for a list of markets with progress logging.

        When `paginate_trades` is True (default), each market's full trade history is
        pulled via the cursor — accurate but proportional to historical depth. Set to
        False to sample the most recent 1000 trades per market when running across
        many markets where bulk volume matters more than completeness.
        '''
        if markets is None:
            markets = self.markets

        self.orderbook = []
        self.trades = []

        total_markets = len(markets or [])
        if not total_markets:
            return {
                "orderbook": self.orderbook,
                "trades": self.trades,
            }

        logging.info(
            "Trade pagination: %s. %s market(s) to process.",
            "ON (full trade history per market)" if paginate_trades else "OFF (latest page only)",
            total_markets,
        )

        start = perf_counter()
        for index, market in enumerate(markets, start=1):
            market_ticker = market.get("ticker")
            if market_ticker:
                orderbook = self.get_market_orderbook(market_ticker)
                if orderbook:
                    self.orderbook.append({
                        "market_ticker": market_ticker,
                        "orderbook": orderbook,
                    })

                trades = self.get_market_trades(market_ticker, all_pages=paginate_trades)
                if trades:
                    self.trades.extend(trades)

            if (
                index == 1
                or index == total_markets
                or (progress_every and index % progress_every == 0)
            ):
                elapsed = perf_counter() - start
                logging.info(
                    "Processed %s/%s markets for orderbooks/trades in %.1fs (%s orderbooks, %s trades).",
                    index,
                    total_markets,
                    elapsed,
                    len(self.orderbook),
                    len(self.trades),
                )

        return {
            "orderbook": self.orderbook,
            "trades": self.trades,
        }
    def get_market_endpoints(self, market_ticker: str | None = None, event_ticker: str | None = None):
        '''Runs all market-related endpoints and stores results in class attributes.'''
        self.markets = self.get_target_markets(
            market_ticker=market_ticker,
            event_ticker=event_ticker,
        )
        detail_data = self.get_market_details(self.markets)
        return {
            "markets": self.markets,
            "orderbook": detail_data["orderbook"],
            "trades": detail_data["trades"],
        }
