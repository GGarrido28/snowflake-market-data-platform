import datetime as dt
import os
import unittest
from unittest.mock import patch

from market_data_platform.pipelines.mlb import teams_pipeline


class FakeTeamsClient:
    def __init__(self):
        self.sport_ids: list[int] = []

    def fetch_teams(self, sport_id: int = 1):
        self.sport_ids.append(sport_id)
        return [
            {
                "id": 119,
                "name": "Los Angeles Dodgers",
                "teamCode": "lan",
                "abbreviation": "LAD",
                "teamName": "Dodgers",
                "locationName": "Los Angeles",
                "firstYearOfPlay": "1884",
                "sport": {"id": 1, "name": "Major League Baseball"},
                "league": {"id": 104, "name": "National League"},
                "division": {"id": 203, "name": "National League West"},
                "venue": {"id": 22, "name": "Dodger Stadium"},
                "active": True,
            }
        ]


class FakeS3Writer:
    def __init__(self):
        self.calls: list[dict] = []

    def put_json_lines(self, *, bucket, key, rows):
        rows = list(rows)
        self.calls.append({"bucket": bucket, "key": key, "rows": rows})
        return {
            "bucket": bucket,
            "key": key,
            "s3_uri": f"s3://{bucket}/{key}",
            "bytes": 123,
            "content_type": "application/x-ndjson",
        }


class MlbTeamsPipelineTests(unittest.TestCase):
    def test_run_fetches_normalizes_and_writes_teams_to_s3(self):
        teams_client = FakeTeamsClient()
        s3_writer = FakeS3Writer()
        now = dt.datetime(2026, 5, 14, 13, 30, 45, tzinfo=dt.timezone.utc)

        summary = teams_pipeline.run(
            {"s3_bucket": "snowflake-landing", "s3_prefix": "raw/mlb/teams", "sport_id": 1},
            teams_client=teams_client,
            s3_writer=s3_writer,
            now=now,
        )

        self.assertEqual(teams_client.sport_ids, [1])
        self.assertEqual(summary["row_count"], 1)
        self.assertEqual(
            summary["s3_uri"],
            "s3://snowflake-landing/raw/mlb/teams/ingested_date=2026-05-14/mlb_teams_20260514T133045Z.jsonl",
        )
        self.assertEqual(s3_writer.calls[0]["bucket"], "snowflake-landing")
        self.assertEqual(
            s3_writer.calls[0]["key"],
            "raw/mlb/teams/ingested_date=2026-05-14/mlb_teams_20260514T133045Z.jsonl",
        )
        row = s3_writer.calls[0]["rows"][0]
        self.assertEqual(row["team_id"], 119)
        self.assertEqual(row["sport_id"], 1)
        self.assertEqual(row["league_name"], "National League")
        self.assertEqual(row["raw_payload"]["name"], "Los Angeles Dodgers")
        self.assertEqual(row["ingested_at"], "2026-05-14T13:30:45Z")

    def test_run_uses_env_bucket_and_prefix_when_event_omits_s3_config(self):
        s3_writer = FakeS3Writer()
        env = {
            "SNOWFLAKE_S3_BUCKET": "snowflake-shared",
            "MLB_TEAMS_S3_PREFIX": "landing/mlb/teams",
            "MLB_TEAMS_SPORT_ID": "11",
        }

        with patch.dict(os.environ, env, clear=True):
            summary = teams_pipeline.run(
                {},
                teams_client=FakeTeamsClient(),
                s3_writer=s3_writer,
                now=dt.datetime(2026, 5, 14, tzinfo=dt.timezone.utc),
            )

        self.assertEqual(summary["sport_id"], 11)
        self.assertEqual(summary["bucket"], "snowflake-shared")
        self.assertTrue(summary["key"].startswith("landing/mlb/teams/"))

    def test_run_requires_s3_bucket(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "MLB_TEAMS_S3_BUCKET"):
                teams_pipeline.run({}, teams_client=FakeTeamsClient(), s3_writer=FakeS3Writer())


if __name__ == "__main__":
    unittest.main()
