import unittest
from unittest.mock import Mock

from market_data_platform.sources.mlb.team import Teams


class MlbTeamSourceTests(unittest.TestCase):
    def test_fetch_teams_requests_default_mlb_sport_id(self):
        response = Mock()
        response.json.return_value = {
            "teams": [
                {"id": 119, "name": "Los Angeles Dodgers"},
                {"id": 147, "name": "New York Yankees"},
            ]
        }
        session = Mock()
        session.get.return_value = response

        teams = Teams(session=session).fetch_teams()

        self.assertEqual(
            teams,
            [
                {"id": 119, "name": "Los Angeles Dodgers"},
                {"id": 147, "name": "New York Yankees"},
            ],
        )
        session.get.assert_called_once_with(
            "https://statsapi.mlb.com/api/v1/teams",
            params={"sportId": 1},
            timeout=30,
        )
        response.raise_for_status.assert_called_once_with()

    def test_fetch_teams_allows_custom_sport_id_base_url_and_timeout(self):
        response = Mock()
        response.json.return_value = {"teams": []}
        session = Mock()
        session.get.return_value = response

        teams = Teams(
            base_url="https://example.test/api/v1/",
            session=session,
            timeout=5,
        ).fetch_teams(sport_id=11)

        self.assertEqual(teams, [])
        session.get.assert_called_once_with(
            "https://example.test/api/v1/teams",
            params={"sportId": 11},
            timeout=5,
        )


if __name__ == "__main__":
    unittest.main()
