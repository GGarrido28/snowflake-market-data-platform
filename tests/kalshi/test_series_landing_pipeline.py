import datetime as dt
import os
import unittest
from unittest.mock import patch

from market_data_platform.pipelines.kalshi import series_landing


class FakeSeriesClient:
    def __init__(self):
        self.tickers: list[str] = []

    def get_series(self, series_ticker: str):
        self.tickers.append(series_ticker)
        return {
            "ticker": series_ticker,
            "category": "Sports",
            "title": "MLB spreads",
            "tags": ["MLB"],
            "frequency": "recurring",
            "fee_multiplier": 1,
            "fee_type": "contract",
            "last_updated_ts": "2026-05-14T13:00:00Z",
        }


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
            "bytes": 321,
            "content_type": "application/x-ndjson",
        }


class KalshiSeriesLandingPipelineTests(unittest.TestCase):
    def test_run_fetches_normalizes_and_writes_series_to_s3(self):
        series_client = FakeSeriesClient()
        s3_writer = FakeS3Writer()
        now = dt.datetime(2026, 5, 14, 13, 30, 45, tzinfo=dt.timezone.utc)

        summary = series_landing.run(
            {
                "s3_bucket": "snowflake-landing",
                "s3_prefix": "raw/kalshi/series",
                "series_ticker": "KXMLBSPREAD",
            },
            series_client=series_client,
            s3_writer=s3_writer,
            now=now,
        )

        self.assertEqual(series_client.tickers, ["KXMLBSPREAD"])
        self.assertEqual(summary["row_count"], 1)
        self.assertEqual(
            summary["s3_uri"],
            "s3://snowflake-landing/raw/kalshi/series/ingested_date=2026-05-14/kalshi_series_20260514T133045Z.jsonl",
        )
        self.assertEqual(s3_writer.calls[0]["bucket"], "snowflake-landing")
        self.assertEqual(
            s3_writer.calls[0]["key"],
            "raw/kalshi/series/ingested_date=2026-05-14/kalshi_series_20260514T133045Z.jsonl",
        )
        row = s3_writer.calls[0]["rows"][0]
        self.assertEqual(row["ticker"], "KXMLBSPREAD")
        self.assertEqual(row["raw_payload"]["title"], "MLB spreads")
        self.assertEqual(row["ingested_at"], "2026-05-14T13:30:45Z")

    def test_run_uses_env_bucket_prefix_and_series_ticker(self):
        s3_writer = FakeS3Writer()
        env = {
            "KALSHI_SERIES_S3_BUCKET": "snowflake-shared",
            "KALSHI_SERIES_S3_PREFIX": "landing/kalshi/series",
            "KALSHI_SERIES_TICKER": "KXMLBHIT",
        }

        with patch.dict(os.environ, env, clear=True):
            summary = series_landing.run(
                {},
                series_client=FakeSeriesClient(),
                s3_writer=s3_writer,
                now=dt.datetime(2026, 5, 14, tzinfo=dt.timezone.utc),
            )

        self.assertEqual(summary["series_ticker"], "KXMLBHIT")
        self.assertEqual(summary["bucket"], "snowflake-shared")
        self.assertTrue(summary["key"].startswith("landing/kalshi/series/"))

    def test_run_requires_series_scope(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "series_ticker"):
                series_landing.run(
                    {"s3_bucket": "snowflake-landing"},
                    series_client=FakeSeriesClient(),
                    s3_writer=FakeS3Writer(),
                )


if __name__ == "__main__":
    unittest.main()
