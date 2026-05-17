from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SQL_PATH = REPO_ROOT / "infra" / "snowflake" / "kalshi_events_series_snowpipe.sql"
RUNBOOK_PATH = REPO_ROOT / "docs" / "kalshi_events_series_snowpipe.md"


def _sql() -> str:
    return SQL_PATH.read_text(encoding="utf-8")


def _runbook() -> str:
    return RUNBOOK_PATH.read_text(encoding="utf-8")


def test_kalshi_snowpipe_sql_defines_only_events_and_series_objects():
    sql = _sql()

    assert "RAW_KALSHI_EVENTS_LOAD" in sql
    assert "RAW_KALSHI_SERIES_LOAD" in sql
    assert "PIPE_KALSHI_EVENTS" in sql
    assert "PIPE_KALSHI_SERIES" in sql
    assert "RAW_EVENTS" in sql
    assert "RAW_SERIES" in sql

    assert "RAW_KALSHI_MARKETS_LOAD" not in sql
    assert "ORDERBOOK" not in sql
    assert "TRADES" not in sql
    assert "ORDERS" not in sql


def test_load_tables_are_transient_and_streams_are_append_only():
    sql = _sql()

    assert "CREATE TRANSIENT TABLE IF NOT EXISTS RAW_KALSHI_EVENTS_LOAD" in sql
    assert "CREATE TRANSIENT TABLE IF NOT EXISTS RAW_KALSHI_SERIES_LOAD" in sql
    assert "DATA_RETENTION_TIME_IN_DAYS = 1" in sql
    assert "CREATE STREAM IF NOT EXISTS STRM_RAW_KALSHI_EVENTS_LOAD" in sql
    assert "CREATE STREAM IF NOT EXISTS STRM_RAW_KALSHI_SERIES_LOAD" in sql
    assert sql.count("APPEND_ONLY = TRUE") == 2


def test_merge_tasks_key_final_raw_tables_and_dedupe_stream_rows():
    sql = _sql()

    assert 'MERGE INTO RAW_EVENTS AS target' in sql
    assert 'ON target."event_ticker" = source."event_ticker"' in sql
    assert 'PARTITION BY "event_ticker"' in sql
    assert 'WHERE METADATA$ACTION = \'INSERT\'' in sql

    assert 'MERGE INTO RAW_SERIES AS target' in sql
    assert 'ON target."ticker" = source."ticker"' in sql
    assert 'PARTITION BY "ticker"' in sql
    assert "WHEN MATCHED THEN UPDATE SET" in sql
    assert "WHEN NOT MATCHED THEN INSERT" in sql


def test_cleanup_tasks_wait_for_streams_to_drain_before_deleting_load_rows():
    sql = _sql()

    assert "CREATE TASK IF NOT EXISTS TASK_CLEANUP_KALSHI_EVENTS_LOAD" in sql
    assert "CREATE TASK IF NOT EXISTS TASK_CLEANUP_KALSHI_SERIES_LOAD" in sql
    assert "WHEN NOT SYSTEM$STREAM_HAS_DATA('PROD.RAW.STRM_RAW_KALSHI_EVENTS_LOAD')" in sql
    assert "WHEN NOT SYSTEM$STREAM_HAS_DATA('PROD.RAW.STRM_RAW_KALSHI_SERIES_LOAD')" in sql
    assert 'DELETE FROM RAW_KALSHI_EVENTS_LOAD' in sql
    assert 'DELETE FROM RAW_KALSHI_SERIES_LOAD' in sql
    assert "DATEADD('day', -2, CURRENT_TIMESTAMP())" in sql


def test_runbook_includes_copy_task_and_final_raw_validation_queries():
    runbook = _runbook()

    assert "COPY_HISTORY" in runbook
    assert "RAW_KALSHI_EVENTS_LOAD" in runbook
    assert "RAW_KALSHI_SERIES_LOAD" in runbook
    assert "TASK_MERGE_KALSHI_EVENTS" in runbook
    assert "TASK_MERGE_KALSHI_SERIES" in runbook
    assert 'FROM PROD.RAW.RAW_EVENTS' in runbook
    assert 'FROM PROD.RAW.RAW_SERIES' in runbook
    assert 'HAVING COUNT(*) > 1' in runbook
