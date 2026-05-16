import datetime as dt
import os
import unittest
from unittest.mock import patch

from market_data_platform.pipelines.kalshi import events_landing


class FakeEventsClient:
    def __init__(self):
        self.calls: list[dict] = []

    def get_target_events(self, *, event_ticker=None, series_ticker=None, status=None):
        self.calls.append(
            {
                "event_ticker": event_ticker,
                "series_ticker": series_ticker,
                "status": status,
            }
        )
        ticker = event_ticker or f"{series_ticker}-26MAY101920DETKC"
        return [
            {
                "event_ticker": ticker,
                "series_ticker": series_ticker or "KXMLBSPREAD",
                "category": "Sports",
                "title": "Detroit vs. Kansas City",
                "sub_title": "Spread",
                "available_on_brokers": True,
                "mutually_exclusive": False,
                "collateral_return_type": "default",
                "last_updated_ts": "2026-05-14T13:10:00Z",
                "product_metadata": {"league": "MLB"},
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
            "bytes": 456,
            "content_type": "application/x-ndjson",
        }


class KalshiEventsLandingPipelineTests(unittest.TestCase):
    def test_run_fetches_normalizes_and_writes_events_to_s3(self):
        events_client = FakeEventsClient()
        s3_writer = FakeS3Writer()
        now = dt.datetime(2026, 5, 14, 13, 30, 45, tzinfo=dt.timezone.utc)

        summary = events_landing.run(
            {
                "s3_bucket": "snowflake-landing",
                "s3_prefix": "raw/kalshi/events",
                "series_ticker": "KXMLBSPREAD",
                "status": "open",
            },
            events_client=events_client,
            s3_writer=s3_writer,
            now=now,
        )

        self.assertEqual(
            events_client.calls,
            [
                {
                    "event_ticker": None,
                    "series_ticker": "KXMLBSPREAD",
                    "status": "open",
                }
            ],
        )
        self.assertEqual(summary["row_count"], 1)
        self.assertEqual(
            summary["s3_uri"],
            "s3://snowflake-landing/raw/kalshi/events/ingested_date=2026-05-14/kalshi_events_20260514T133045Z.jsonl",
        )
        self.assertEqual(s3_writer.calls[0]["bucket"], "snowflake-landing")
        self.assertEqual(
            s3_writer.calls[0]["key"],
            "raw/kalshi/events/ingested_date=2026-05-14/kalshi_events_20260514T133045Z.jsonl",
        )
        row = s3_writer.calls[0]["rows"][0]
        self.assertEqual(row["event_ticker"], "KXMLBSPREAD-26MAY101920DETKC")
        self.assertEqual(row["series_ticker"], "KXMLBSPREAD")
        self.assertEqual(row["raw_payload"]["product_metadata"], {"league": "MLB"})
        self.assertEqual(row["ingested_at"], "2026-05-14T13:30:45Z")

    def test_run_uses_env_bucket_prefix_and_default_open_status(self):
        events_client = FakeEventsClient()
        s3_writer = FakeS3Writer()
        env = {
            "KALSHI_EVENTS_S3_BUCKET": "snowflake-shared",
            "KALSHI_EVENTS_S3_PREFIX": "landing/kalshi/events",
        }

        with patch.dict(os.environ, env, clear=True):
            summary = events_landing.run(
                {},
                events_client=events_client,
                s3_writer=s3_writer,
                now=dt.datetime(2026, 5, 14, tzinfo=dt.timezone.utc),
            )

        self.assertEqual(events_client.calls[0]["status"], "open")
        self.assertEqual(
            [call["series_ticker"] for call in events_client.calls],
            ["KXMLBSPREAD", "KXMLBTOTAL", "KXMLBGAME"],
        )
        self.assertEqual(summary["series_tickers"], ["KXMLBSPREAD", "KXMLBTOTAL", "KXMLBGAME"])
        self.assertEqual(summary["bucket"], "snowflake-shared")
        self.assertTrue(summary["key"].startswith("landing/kalshi/events/"))

    def test_run_accepts_event_ticker_without_default_series_ticker_conflict(self):
        events_client = FakeEventsClient()
        s3_writer = FakeS3Writer()
        env = {
            "KALSHI_EVENTS_S3_BUCKET": "snowflake-shared",
            "KALSHI_EVENTS_SERIES_TICKERS": "KXMLBSPREAD,KXMLBTOTAL,KXMLBGAME",
        }

        with patch.dict(os.environ, env, clear=True):
            summary = events_landing.run(
                {"event_ticker": "KXEXACT-26"},
                events_client=events_client,
                s3_writer=s3_writer,
                now=dt.datetime(2026, 5, 14, tzinfo=dt.timezone.utc),
            )

        self.assertEqual(events_client.calls[0]["event_ticker"], "KXEXACT-26")
        self.assertIsNone(events_client.calls[0]["series_ticker"])
        self.assertEqual(summary["event_ticker"], "KXEXACT-26")
        self.assertEqual(summary["series_tickers"], [])

    def test_all_status_uses_default_series_tickers(self):
        events_client = FakeEventsClient()

        with patch.dict(os.environ, {}, clear=True):
            summary = events_landing.run(
                {"s3_bucket": "snowflake-landing", "status": "all"},
                events_client=events_client,
                s3_writer=FakeS3Writer(),
            )

        self.assertIsNone(summary["status"])
        self.assertEqual(
            [call["series_ticker"] for call in events_client.calls],
            ["KXMLBSPREAD", "KXMLBTOTAL", "KXMLBGAME"],
        )

    def test_run_rejects_multiple_event_scopes(self):
        with self.assertRaisesRegex(ValueError, "either event_ticker or series_tickers"):
            events_landing.run(
                {
                    "s3_bucket": "snowflake-landing",
                    "event_ticker": "KXTEST-26",
                    "series_ticker": "KXTEST",
                },
                events_client=FakeEventsClient(),
                s3_writer=FakeS3Writer(),
            )


if __name__ == "__main__":
    unittest.main()
