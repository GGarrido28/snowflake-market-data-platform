import datetime as dt
import os
import unittest
from unittest.mock import patch

from market_data_platform.pipelines.kalshi import markets_landing


class FakeMarketsClient:
    def __init__(self):
        self.target_market_calls: list[dict] = []
        self.detail_calls: list[dict] = []

    def get_target_markets(self, *, market_ticker=None, event_ticker=None):
        self.target_market_calls.append(
            {
                "market_ticker": market_ticker,
                "event_ticker": event_ticker,
            }
        )
        ticker = market_ticker or f"{event_ticker}-MKT"
        return [
            {
                "ticker": ticker,
                "event_ticker": event_ticker or "EVT",
                "market_type": "binary",
                "status": "open",
                "title": "Will the home team win?",
            }
        ]

    def get_market_details(self, markets, *, paginate_trades=True, trade_fetch_options_by_ticker=None):
        markets = list(markets)
        self.detail_calls.append(
            {
                "markets": markets,
                "paginate_trades": paginate_trades,
                "trade_fetch_options_by_ticker": trade_fetch_options_by_ticker or {},
            }
        )
        return {
            "orderbook": [
                {
                    "market_ticker": markets[0]["ticker"],
                    "orderbook": {"yes_dollars": [["0.5100", "15.00"]]},
                }
            ],
            "trades": [
                {
                    "trade_id": "trade-1",
                    "ticker": markets[0]["ticker"],
                    "yes_price_dollars": "0.5100",
                    "count_fp": "10",
                    "created_time": "2026-05-14T13:29:30Z",
                }
            ],
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
            "bytes": 123,
            "content_type": "application/x-ndjson",
        }


class FakeNoTradeMarketsClient(FakeMarketsClient):
    def get_market_details(self, markets, *, paginate_trades=True, trade_fetch_options_by_ticker=None):
        result = super().get_market_details(
            markets,
            paginate_trades=paginate_trades,
            trade_fetch_options_by_ticker=trade_fetch_options_by_ticker,
        )
        result["trades"] = []
        return result


class FakeStateStore:
    def __init__(self, initial_state=None):
        self.initial_state = initial_state
        self.get_calls: list[dict] = []
        self.put_calls: list[dict] = []

    def get_json(self, *, bucket, key):
        self.get_calls.append({"bucket": bucket, "key": key})
        return self.initial_state

    def put_json(self, *, bucket, key, payload):
        self.put_calls.append({"bucket": bucket, "key": key, "payload": payload})
        return {
            "bucket": bucket,
            "key": key,
            "s3_uri": f"s3://{bucket}/{key}",
            "bytes": 123,
            "content_type": "application/json",
        }


class KalshiMarketsLandingPipelineTests(unittest.TestCase):
    def test_run_fetches_normalizes_and_writes_market_entities_to_s3(self):
        markets_client = FakeMarketsClient()
        s3_writer = FakeS3Writer()
        state_store = FakeStateStore()
        now = dt.datetime(2026, 5, 14, 13, 30, 45, tzinfo=dt.timezone.utc)

        summary = markets_landing.run(
            {
                "s3_bucket": "snowflake-landing",
                "market_ticker": "KXTEST",
                "markets_s3_prefix": "raw/kalshi/markets",
                "market_orderbooks_s3_prefix": "raw/kalshi/market_orderbooks",
                "market_trades_s3_prefix": "raw/kalshi/market_trades",
            },
            markets_client=markets_client,
            s3_writer=s3_writer,
            state_store=state_store,
            now=now,
        )

        self.assertEqual(
            markets_client.target_market_calls,
            [{"market_ticker": "KXTEST", "event_ticker": None}],
        )
        self.assertEqual(markets_client.detail_calls[0]["paginate_trades"], True)
        self.assertEqual(
            markets_client.detail_calls[0]["trade_fetch_options_by_ticker"],
            {
                "KXTEST": {
                    "all_pages": True,
                    "min_ts": 1778679045,
                    "max_ts": 1778765445,
                }
            },
        )
        self.assertEqual(
            summary["row_counts"],
            {
                "markets": 1,
                "market_orderbooks": 1,
                "market_trades": 1,
            },
        )
        self.assertEqual(
            [call["key"] for call in s3_writer.calls],
            [
                "raw/kalshi/markets/ingested_date=2026-05-14/kalshi_markets_20260514T133045Z.jsonl",
                (
                    "raw/kalshi/market_orderbooks/ingested_date=2026-05-14/"
                    "kalshi_market_orderbooks_20260514T133045Z.jsonl"
                ),
                "raw/kalshi/market_trades/ingested_date=2026-05-14/kalshi_market_trades_20260514T133045Z.jsonl",
            ],
        )

        market_row = s3_writer.calls[0]["rows"][0]
        orderbook_row = s3_writer.calls[1]["rows"][0]
        trade_row = s3_writer.calls[2]["rows"][0]
        self.assertEqual(market_row["ticker"], "KXTEST")
        self.assertEqual(market_row["raw_payload"]["title"], "Will the home team win?")
        self.assertEqual(orderbook_row["market_ticker"], "KXTEST")
        self.assertEqual(orderbook_row["raw_payload"]["orderbook"], {"yes_dollars": [["0.5100", "15.00"]]})
        self.assertEqual(trade_row["trade_id"], "trade-1")
        self.assertEqual(trade_row["ingested_at"], "2026-05-14T13:30:45Z")
        self.assertEqual(summary["trade_fetch_mode"], "incremental")
        self.assertEqual(
            state_store.put_calls[0]["key"],
            "state/kalshi/market_trades/market_ticker=KXTEST/watermark.json",
        )
        self.assertEqual(
            state_store.put_calls[0]["payload"]["last_seen_trade_time"],
            "2026-05-14T13:29:30Z",
        )
        self.assertEqual(
            state_store.put_calls[0]["payload"]["checked_through_time"],
            "2026-05-14T13:30:45Z",
        )

    def test_run_uses_event_query_file_loader_and_fetches_each_event(self):
        markets_client = FakeMarketsClient()
        s3_writer = FakeS3Writer()
        state_store = FakeStateStore()

        summary = markets_landing.run(
            {
                "s3_bucket": "snowflake-landing",
                "event_query_file": "src/market_data_platform/queries/kalshi/markets_mlb_events.sql",
            },
            markets_client=markets_client,
            s3_writer=s3_writer,
            state_store=state_store,
            event_ticker_loader=lambda query_file: ["EVT-1", "EVT-2"],
            now=dt.datetime(2026, 5, 14, tzinfo=dt.timezone.utc),
        )

        self.assertEqual(summary["event_tickers"], ["EVT-1", "EVT-2"])
        self.assertEqual(
            markets_client.target_market_calls,
            [
                {"market_ticker": None, "event_ticker": "EVT-1"},
                {"market_ticker": None, "event_ticker": "EVT-2"},
            ],
        )
        self.assertEqual(summary["row_counts"]["markets"], 2)

    def test_run_uses_env_bucket_prefixes_event_scope_and_trade_pagination(self):
        markets_client = FakeMarketsClient()
        s3_writer = FakeS3Writer()
        state_store = FakeStateStore()
        env = {
            "KALSHI_MARKETS_S3_BUCKET": "snowflake-shared",
            "KALSHI_MARKETS_S3_PREFIX": "landing/kalshi/markets",
            "KALSHI_MARKET_ORDERBOOKS_S3_PREFIX": "landing/kalshi/orderbooks",
            "KALSHI_MARKET_TRADES_S3_PREFIX": "landing/kalshi/trades",
            "KALSHI_EVENT_TICKER": "EVT-ENV",
            "KALSHI_MARKETS_PAGINATE_TRADES": "true",
        }

        with patch.dict(os.environ, env, clear=True):
            summary = markets_landing.run(
                {},
                markets_client=markets_client,
                s3_writer=s3_writer,
                state_store=state_store,
                now=dt.datetime(2026, 5, 14, tzinfo=dt.timezone.utc),
            )

        self.assertEqual(summary["event_ticker"], "EVT-ENV")
        self.assertEqual(summary["trade_fetch_mode"], "full_history")
        self.assertEqual(markets_client.detail_calls[0]["paginate_trades"], True)
        self.assertEqual(markets_client.detail_calls[0]["trade_fetch_options_by_ticker"], {"EVT-ENV-MKT": {"all_pages": True}})
        self.assertEqual(s3_writer.calls[0]["bucket"], "snowflake-shared")
        self.assertTrue(s3_writer.calls[0]["key"].startswith("landing/kalshi/markets/"))
        self.assertTrue(s3_writer.calls[1]["key"].startswith("landing/kalshi/orderbooks/"))
        self.assertTrue(s3_writer.calls[2]["key"].startswith("landing/kalshi/trades/"))
        self.assertEqual(state_store.put_calls, [])

    def test_incremental_run_uses_existing_watermark_with_overlap(self):
        markets_client = FakeMarketsClient()
        state_store = FakeStateStore(
            {
                "version": 1,
                "market_ticker": "KXTEST",
                "checked_through_ts": 1778761845,
                "checked_through_time": "2026-05-14T12:30:45Z",
            }
        )

        markets_landing.run(
            {
                "s3_bucket": "snowflake-landing",
                "market_ticker": "KXTEST",
                "trade_watermark_overlap_seconds": 30,
            },
            markets_client=markets_client,
            s3_writer=FakeS3Writer(),
            state_store=state_store,
            now=dt.datetime(2026, 5, 14, 13, 30, 45, tzinfo=dt.timezone.utc),
        )

        self.assertEqual(
            markets_client.detail_calls[0]["trade_fetch_options_by_ticker"]["KXTEST"],
            {
                "all_pages": True,
                "min_ts": 1778761815,
                "max_ts": 1778765445,
            },
        )

    def test_incremental_run_honors_zero_overlap(self):
        markets_client = FakeMarketsClient()
        state_store = FakeStateStore(
            {
                "version": 1,
                "market_ticker": "KXTEST",
                "checked_through_ts": 1778761845,
                "checked_through_time": "2026-05-14T12:30:45Z",
            }
        )

        markets_landing.run(
            {
                "s3_bucket": "snowflake-landing",
                "market_ticker": "KXTEST",
                "trade_watermark_overlap_seconds": 0,
            },
            markets_client=markets_client,
            s3_writer=FakeS3Writer(),
            state_store=state_store,
            now=dt.datetime(2026, 5, 14, 13, 30, 45, tzinfo=dt.timezone.utc),
        )

        self.assertEqual(
            markets_client.detail_calls[0]["trade_fetch_options_by_ticker"]["KXTEST"]["min_ts"],
            1778761845,
        )

    def test_incremental_empty_trade_run_still_advances_checked_through_state(self):
        state_store = FakeStateStore()

        markets_landing.run(
            {
                "s3_bucket": "snowflake-landing",
                "market_ticker": "KXTEST",
            },
            markets_client=FakeNoTradeMarketsClient(),
            s3_writer=FakeS3Writer(),
            state_store=state_store,
            now=dt.datetime(2026, 5, 14, 13, 30, 45, tzinfo=dt.timezone.utc),
        )

        state = state_store.put_calls[0]["payload"]
        self.assertEqual(state["market_ticker"], "KXTEST")
        self.assertEqual(state["checked_through_time"], "2026-05-14T13:30:45Z")
        self.assertNotIn("last_seen_trade_time", state)

    def test_backfill_mode_requires_explicit_start_and_does_not_update_watermark_by_default(self):
        markets_client = FakeMarketsClient()
        state_store = FakeStateStore()

        summary = markets_landing.run(
            {
                "s3_bucket": "snowflake-landing",
                "market_ticker": "KXTEST",
                "trade_fetch_mode": "backfill",
                "trade_backfill_start_time": "2026-05-13T00:00:00Z",
                "trade_backfill_end_time": "2026-05-14T00:00:00Z",
            },
            markets_client=markets_client,
            s3_writer=FakeS3Writer(),
            state_store=state_store,
            now=dt.datetime(2026, 5, 14, 13, 30, 45, tzinfo=dt.timezone.utc),
        )

        self.assertEqual(summary["trade_fetch_mode"], "backfill")
        self.assertEqual(
            markets_client.detail_calls[0]["trade_fetch_options_by_ticker"]["KXTEST"],
            {
                "all_pages": True,
                "min_ts": 1778630400,
                "max_ts": 1778716800,
            },
        )
        self.assertEqual(state_store.put_calls, [])

    def test_backfill_bounds_require_backfill_mode(self):
        with self.assertRaisesRegex(ValueError, "Set trade_fetch_mode=backfill"):
            markets_landing.run(
                {
                    "s3_bucket": "snowflake-landing",
                    "market_ticker": "KXTEST",
                    "trade_backfill_start_time": "2026-05-13T00:00:00Z",
                },
                markets_client=FakeMarketsClient(),
                s3_writer=FakeS3Writer(),
                state_store=FakeStateStore(),
            )

    def test_run_rejects_multiple_market_scopes(self):
        with self.assertRaisesRegex(ValueError, "Set only one of market_ticker"):
            markets_landing.run(
                {
                    "s3_bucket": "snowflake-landing",
                    "market_ticker": "KXTEST",
                    "event_ticker": "EVT",
                },
                markets_client=FakeMarketsClient(),
                s3_writer=FakeS3Writer(),
                state_store=FakeStateStore(),
            )

    def test_normalizers_preserve_raw_payload_and_ingestion_timestamp(self):
        rows = markets_landing.normalize_market_trades(
            [{"trade_id": "trade-1", "ticker": "KXTEST"}],
            ingested_at="2026-05-14T13:30:45Z",
        )

        self.assertEqual(rows[0]["trade_id"], "trade-1")
        self.assertEqual(rows[0]["raw_payload"], {"trade_id": "trade-1", "ticker": "KXTEST"})
        self.assertEqual(rows[0]["ingested_at"], "2026-05-14T13:30:45Z")


if __name__ == "__main__":
    unittest.main()
