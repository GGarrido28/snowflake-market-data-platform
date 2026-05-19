import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SQL_PATH = REPO_ROOT / "infra" / "snowflake" / "kalshi_markets_snowpipe.sql"
RUNBOOK_PATH = REPO_ROOT / "docs" / "kalshi_markets_snowpipe.md"


def _sql() -> str:
    return SQL_PATH.read_text(encoding="utf-8")


def _runbook() -> str:
    return RUNBOOK_PATH.read_text(encoding="utf-8")


class KalshiMarketsSnowpipeSqlTests(unittest.TestCase):
    def test_market_snowpipe_sql_defines_three_entity_paths(self):
        sql = _sql()

        for object_name in (
            "RAW_KALSHI_MARKETS_LOAD",
            "RAW_KALSHI_MARKET_ORDERBOOKS_LOAD",
            "RAW_KALSHI_MARKET_TRADES_LOAD",
            "PIPE_KALSHI_MARKETS",
            "PIPE_KALSHI_MARKET_ORDERBOOKS",
            "PIPE_KALSHI_MARKET_TRADES",
            "RAW_MARKETS",
            "RAW_MARKET_ORDERBOOKS",
            "RAW_MARKET_TRADES",
        ):
            self.assertIn(object_name, sql)

        for prefix in (
            "raw/kalshi/markets/",
            "raw/kalshi/market_orderbooks/",
            "raw/kalshi/market_trades/",
        ):
            self.assertIn(prefix, sql)

        self.assertNotIn("RAW_KALSHI_ORDERS", sql)
        self.assertNotIn("USER_ORDERS", sql)

    def test_load_tables_are_transient_and_streams_are_append_only(self):
        sql = _sql()

        self.assertIn("CREATE TRANSIENT TABLE IF NOT EXISTS RAW_KALSHI_MARKETS_LOAD", sql)
        self.assertIn("CREATE TRANSIENT TABLE IF NOT EXISTS RAW_KALSHI_MARKET_ORDERBOOKS_LOAD", sql)
        self.assertIn("CREATE TRANSIENT TABLE IF NOT EXISTS RAW_KALSHI_MARKET_TRADES_LOAD", sql)
        self.assertGreaterEqual(sql.count("DATA_RETENTION_TIME_IN_DAYS = 1"), 3)
        self.assertEqual(sql.count("APPEND_ONLY = TRUE"), 3)

    def test_merge_tasks_key_final_raw_tables_and_dedupe_stream_rows(self):
        sql = _sql()

        self.assertIn('MERGE INTO RAW_MARKETS AS target', sql)
        self.assertIn('ON target."ticker" = source."ticker"', sql)
        self.assertIn('PARTITION BY "ticker"', sql)

        self.assertIn('MERGE INTO RAW_MARKET_ORDERBOOKS AS target', sql)
        self.assertIn('ON target."market_ticker" = source."market_ticker"', sql)
        self.assertIn('PARTITION BY "market_ticker"', sql)

        self.assertIn('MERGE INTO RAW_MARKET_TRADES AS target', sql)
        self.assertIn('ON target."trade_id" = source."trade_id"', sql)
        self.assertIn('PARTITION BY "trade_id"', sql)
        self.assertIn('AND "trade_id" IS NOT NULL', sql)

        self.assertEqual(sql.count("WHERE METADATA$ACTION = 'INSERT'"), 3)
        self.assertIn("WHEN MATCHED THEN UPDATE SET", sql)
        self.assertIn("WHEN NOT MATCHED THEN INSERT", sql)

    def test_trade_copy_accepts_ticker_or_market_ticker_without_placeholder_rows(self):
        sql = _sql()

        self.assertIn('COALESCE($1:ticker::VARCHAR, $1:market_ticker::VARCHAR)', sql)
        self.assertIn("Empty market trade", sql)
        self.assertNotIn("unknown_trade", sql.lower())
        self.assertNotIn("placeholder", sql.lower().replace("trade placeholders", ""))

    def test_cleanup_tasks_wait_for_streams_to_drain_before_deleting_load_rows(self):
        sql = _sql()

        for entity in (
            "MARKETS",
            "MARKET_ORDERBOOKS",
            "MARKET_TRADES",
        ):
            self.assertIn(f"CREATE TASK IF NOT EXISTS TASK_CLEANUP_KALSHI_{entity}_LOAD", sql)
            self.assertIn(f"DELETE FROM RAW_KALSHI_{entity}_LOAD", sql)

        self.assertIn("WHEN NOT SYSTEM$STREAM_HAS_DATA('PROD.RAW.STRM_RAW_KALSHI_MARKETS_LOAD')", sql)
        self.assertIn("WHEN NOT SYSTEM$STREAM_HAS_DATA('PROD.RAW.STRM_RAW_KALSHI_MARKET_ORDERBOOKS_LOAD')", sql)
        self.assertIn("WHEN NOT SYSTEM$STREAM_HAS_DATA('PROD.RAW.STRM_RAW_KALSHI_MARKET_TRADES_LOAD')", sql)
        self.assertIn("DATEADD('day', -2, CURRENT_TIMESTAMP())", sql)

    def test_runbook_includes_pipe_task_and_final_raw_validation_queries(self):
        runbook = _runbook()

        for token in (
            "COPY_HISTORY",
            "RAW_KALSHI_MARKETS_LOAD",
            "RAW_KALSHI_MARKET_ORDERBOOKS_LOAD",
            "RAW_KALSHI_MARKET_TRADES_LOAD",
            "TASK_MERGE_KALSHI_MARKETS",
            "TASK_MERGE_KALSHI_MARKET_ORDERBOOKS",
            "TASK_MERGE_KALSHI_MARKET_TRADES",
            "FROM PROD.RAW.RAW_MARKETS",
            "FROM PROD.RAW.RAW_MARKET_ORDERBOOKS",
            "FROM PROD.RAW.RAW_MARKET_TRADES",
            "HAVING COUNT(*) > 1",
        ):
            self.assertIn(token, runbook)

        self.assertIn("zero-row", runbook)
        self.assertIn("market_trades", runbook)

    def test_runbook_covers_issue_54_dependency_and_ci_safe_validation(self):
        runbook = _runbook()

        self.assertIn("Kalshi Markets Lambda", runbook)
        self.assertIn("Issue #54", runbook)
        self.assertIn("Issue #58", runbook)
        self.assertIn("Until #58 is applied", runbook)
        self.assertIn("aws lambda invoke", runbook)
        self.assertIn("snowpipe_s3_notifications.md", runbook)
        self.assertIn("Manual Smoke Tests", runbook)
        self.assertIn("CI-Safe Tests", runbook)
        self.assertIn("python -m unittest discover -s tests -v", runbook)
        self.assertIn("dbt parse --profiles-dir .", runbook)


if __name__ == "__main__":
    unittest.main()
