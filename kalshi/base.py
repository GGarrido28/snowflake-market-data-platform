import requests
import datetime
from time import sleep
import logging

from kalshi.utils import load_private_key_from_file, sign_pss_text, load_api_key_id

logging.basicConfig(level=logging.INFO)

PAGINATED_ENDPOINT_RESULT_KEYS = {
    "/markets": "markets",
    "/events": "events",
    "/series": "series",
    "/markets/trades": "trades",
    "/portfolio/history": "history",
    "/portfolio/fills": "fills",
    "/portfolio/orders": "orders",
}

class KalshiBase:
    '''Base class for Kalshi API interactions. Handles authentication and request signing.'''
    def __init__(self):
        self.base_url = 'https://api.elections.kalshi.com/trade-api/v2' # Base URL for Kalshi API, despite the elections subdomain, this is the correct endpoint for all API interactions.
        self.headers = self._get_auth_headers("GET", "/") # Initial headers, will be updated for each request
        self.api_limits = {"read_limit": 20, "write_limit": 20}
        self.rate_limit_window_start = datetime.datetime.now()
        self.request_counts = {"GET": 0, "POST": 0}

    def _get_auth_headers(self, method: str, path: str) -> dict:
        '''Generates the necessary authentication headers for a request.'''
        current_time = datetime.datetime.now()
        timestamp = current_time.timestamp()
        current_time_milliseconds = int(timestamp * 1000)
        timestampt_str = str(current_time_milliseconds)

        private_key = load_private_key_from_file()

        # Strip query parameters from path before signing
        path_without_query = path.split('?')[0]
        full_path = "/trade-api/v2" + path_without_query
        msg_string = timestampt_str + method + full_path
        sig = sign_pss_text(private_key, msg_string)

        headers = {
            'KALSHI-ACCESS-KEY': load_api_key_id(),
            'KALSHI-ACCESS-SIGNATURE': sig,
            'KALSHI-ACCESS-TIMESTAMP': timestampt_str
        }
        return headers
    
    def _get_api_limits(self) -> dict:
        '''Fetches the current API rate limits for the authenticated user.'''
        response = self.make_request("GET", "/account/limits")
        read_limit = response.json().get("read_limit", 20)
        write_limit = response.json().get("write_limit", 20)
        self.api_limits = {"read_limit": read_limit, "write_limit": write_limit}
        return self.api_limits

    def _wait_for_rate_limit(self, method: str) -> None:
        '''Sleeps until the next rate-limit window when this request would exceed the current limit.'''
        window_seconds = 1
        now = datetime.datetime.now()
        elapsed = (now - self.rate_limit_window_start).total_seconds()

        if elapsed >= window_seconds:
            self.rate_limit_window_start = now
            self.request_counts = {"GET": 0, "POST": 0}

        method = method.upper()
        limit_key = "read_limit" if method == "GET" else "write_limit"
        limit = self.api_limits.get(limit_key, 20)

        if self.request_counts[method] >= limit:
            logging.info(f"Rate limit reached for {method} requests. Sleeping until next window...")
            sleep(max(0, window_seconds - elapsed))
            self.rate_limit_window_start = datetime.datetime.now()
            self.request_counts = {"GET": 0, "POST": 0}

        self.request_counts[method] += 1

    def _send_request(self, method: str, url: str, headers: dict, params=None) -> requests.Response:
        '''Sends the HTTP request without applying client-side rate limiting.'''
        if method == "GET":
            return requests.get(url, headers=headers, params=params)
        if method == "POST":
            return requests.post(url, headers=headers, json=params)
        raise ValueError("Unsupported HTTP method")
    
    def make_request(self, method: str, path: str, limit=100, cursor=None, params=None, **kwargs) -> requests.Response:
        '''Helper method to make authenticated requests to the Kalshi API. Handles signing and error checking.'''
        method = method.upper()
        query_params = {k: v for k, v in {**kwargs, "limit": limit, "cursor": cursor}.items() if v is not None}
        query_string = "&".join(f"{k}={v}" for k, v in query_params.items())
        url = f"{self.base_url}{path}?{query_string}" if query_string else f"{self.base_url}{path}"
        headers = self._get_auth_headers(method, path)
        self._wait_for_rate_limit(method)
        response = self._send_request(method, url, headers, params=params)

        if response.status_code == 200:
            return response
        elif response.status_code == 429:
            raise Exception("Rate limit exceeded. Please try again later.")
        elif response.status_code >= 500:
            raise Exception(f"Server error: {response.status_code}. Please try again later.")
        elif response.status_code >= 400:
            raise Exception(f"Client error: {response.status_code}. Response: {response.text}")

        return response
    
    def get_paginated_results(self, method: str, path: str, params=None, **kwargs) -> list:
        '''Helper method to fetch all results from a paginated endpoint.'''
        if path not in PAGINATED_ENDPOINT_RESULT_KEYS:
            raise ValueError(f"Endpoint {path} is not supported for pagination.")
        self._get_api_limits()
        all_results = []
        cursor = None
        dict_key = PAGINATED_ENDPOINT_RESULT_KEYS[path]
        while True:
            response = self.make_request(method, path, cursor=cursor, params=params, **kwargs)
            data = response.json()
            results = data.get(dict_key, [])
            all_results.extend(results)
            cursor = data.get("cursor")
            if not cursor:
                break
        return all_results
