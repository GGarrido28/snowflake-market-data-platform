import logging
from typing import Any

import requests


logging.basicConfig(level=logging.INFO)

DEFAULT_SPORT_ID = 1
DEFAULT_TIMEOUT_SECONDS = 30
MLB_STATS_API_BASE_URL = "https://statsapi.mlb.com/api/v1"


class Teams:
    """Client for MLB Stats API team endpoints."""

    def __init__(
        self,
        base_url: str = MLB_STATS_API_BASE_URL,
        session: requests.Session | None = None,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
    ):
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.timeout = timeout

    def fetch_teams(self, sport_id: int = DEFAULT_SPORT_ID) -> list[dict[str, Any]]:
        """Fetches MLB teams from the Stats API."""
        response = self.session.get(
            f"{self.base_url}/teams",
            params={"sportId": sport_id},
            timeout=self.timeout,
        )
        response.raise_for_status()
        teams = response.json().get("teams", [])
        logging.info("Fetched %s MLB team(s) from the Stats API.", len(teams))
        return teams
