import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SQL_PATH = REPO_ROOT / "infra" / "snowflake" / "kalshi_events_series_snowpipe.sql"
RUNBOOK_PATH = REPO_ROOT / "docs" / "kalshi_events_series_snowpipe.md"


def _sql() -> str:
    return SQL_PATH.read_text(encoding="utf-8")


def _runbook() -> str:
    return RUNBOOK_PATH.read_text(encoding="utf-8")


class KalshiEventsSeriesSnowpipeSqlTests(unittest.TestCase):
    def test_kalshi_snowpipe_sql_defines_only_events_and_series_objects(self):
        sql = _sql()

        self.assertIn("RAW_KALSHI_EVENTS_LOAD", sql)
        self.assertIn("RAW_KALSHI_SERIES_LOAD", sql)
        self.assertIn("PIPE_KALSHI_EVENTS", sql)
        self.assertIn("PIPE_KALSHI_SERIES", sql)
        self.assertIn("RAW_EVENTS", sql)
        self.assertIn("RAW_SERIES", sql)

        self.assertNotIn("RAW_KALSHI_MARKETS_LOAD", sql)
        self.assertNotIn("ORDERBOOK", sql)
        self.assertNotIn("TRADES", sql)
        self.assertNotIn("ORDERS", sql)

    def test_load_tables_are_transient_and_streams_are_append_only(self):
        sql = _sql()

        self.assertIn("CREATE TRANSIENT TABLE IF NOT EXISTS RAW_KALSHI_EVENTS_LOAD", sql)
        self.assertIn("CREATE TRANSIENT TABLE IF NOT EXISTS RAW_KALSHI_SERIES_LOAD", sql)
        self.assertIn("DATA_RETENTION_TIME_IN_DAYS = 1", sql)
        self.assertIn("CREATE STREAM IF NOT EXISTS STRM_RAW_KALSHI_EVENTS_LOAD", sql)
        self.assertIn("CREATE STREAM IF NOT EXISTS STRM_RAW_KALSHI_SERIES_LOAD", sql)
        self.assertEqual(sql.count("APPEND_ONLY = TRUE"), 2)

    def test_merge_tasks_key_final_raw_tables_and_dedupe_stream_rows(self):
        sql = _sql()

        self.assertIn('MERGE INTO RAW_EVENTS AS target', sql)
        self.assertIn('ON target."event_ticker" = source."event_ticker"', sql)
        self.assertIn('PARTITION BY "event_ticker"', sql)
        self.assertIn("WHERE METADATA$ACTION = 'INSERT'", sql)

        self.assertIn('MERGE INTO RAW_SERIES AS target', sql)
        self.assertIn('ON target."ticker" = source."ticker"', sql)
        self.assertIn('PARTITION BY "ticker"', sql)
        self.assertIn("WHEN MATCHED THEN UPDATE SET", sql)
        self.assertIn("WHEN NOT MATCHED THEN INSERT", sql)

    def test_cleanup_tasks_wait_for_streams_to_drain_before_deleting_load_rows(self):
        sql = _sql()

        self.assertIn("CREATE TASK IF NOT EXISTS TASK_CLEANUP_KALSHI_EVENTS_LOAD", sql)
        self.assertIn("CREATE TASK IF NOT EXISTS TASK_CLEANUP_KALSHI_SERIES_LOAD", sql)
        self.assertIn("WHEN NOT SYSTEM$STREAM_HAS_DATA('PROD.RAW.STRM_RAW_KALSHI_EVENTS_LOAD')", sql)
        self.assertIn("WHEN NOT SYSTEM$STREAM_HAS_DATA('PROD.RAW.STRM_RAW_KALSHI_SERIES_LOAD')", sql)
        self.assertIn("DELETE FROM RAW_KALSHI_EVENTS_LOAD", sql)
        self.assertIn("DELETE FROM RAW_KALSHI_SERIES_LOAD", sql)
        self.assertIn("DATEADD('day', -2, CURRENT_TIMESTAMP())", sql)

    def test_runbook_includes_copy_task_and_final_raw_validation_queries(self):
        runbook = _runbook()

        self.assertIn("COPY_HISTORY", runbook)
        self.assertIn("RAW_KALSHI_EVENTS_LOAD", runbook)
        self.assertIn("RAW_KALSHI_SERIES_LOAD", runbook)
        self.assertIn("TASK_MERGE_KALSHI_EVENTS", runbook)
        self.assertIn("TASK_MERGE_KALSHI_SERIES", runbook)
        self.assertIn("FROM PROD.RAW.RAW_EVENTS", runbook)
        self.assertIn("FROM PROD.RAW.RAW_SERIES", runbook)
        self.assertIn("HAVING COUNT(*) > 1", runbook)

    def test_runbook_covers_deploy_invoke_and_manual_smoke_boundaries(self):
        runbook = _runbook()

        self.assertIn("scripts\\deploy_kalshi_lambdas.ps1", runbook)
        self.assertIn("scripts\\deploy_ingestion_schedulers.ps1", runbook)
        self.assertIn("kalshi_events_lambda_function_name", runbook)
        self.assertIn("kalshi_series_lambda_function_name", runbook)
        self.assertIn("aws lambda invoke", runbook)
        self.assertIn("raw/kalshi/events/", runbook)
        self.assertIn("raw/kalshi/series/", runbook)
        self.assertIn("Manual Smoke Tests", runbook)
        self.assertIn("CI-Safe Tests", runbook)
        self.assertIn("python -m unittest discover -s tests -v", runbook)
        self.assertIn("dbt parse --profiles-dir .", runbook)

    def test_runbook_documents_cost_controls(self):
        runbook = _runbook()

        self.assertIn("Cost Controls", runbook)
        self.assertIn('kalshi_events_schedule_state = "DISABLED"', runbook)
        self.assertIn('kalshi_series_schedule_state = "DISABLED"', runbook)
        self.assertIn("KXMLBSPREAD", runbook)
        self.assertIn("BaseBall", runbook)
        self.assertIn("transient inbox tables", runbook)
        self.assertIn("one day of", runbook)
        self.assertIn("latest row per stable", runbook)


if __name__ == "__main__":
    unittest.main()
