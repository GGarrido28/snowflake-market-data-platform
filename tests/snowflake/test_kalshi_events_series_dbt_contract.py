import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DBT_MODELS_PATH = REPO_ROOT / "dbt" / "models"
SOURCES_PATH = DBT_MODELS_PATH / "sources.yml"
STAGING_SCHEMA_PATH = DBT_MODELS_PATH / "staging" / "schema.yml"
EVENTS_MODEL_PATH = DBT_MODELS_PATH / "staging" / "stg_kalshi_events.sql"
SERIES_MODEL_PATH = DBT_MODELS_PATH / "staging" / "stg_kalshi_series.sql"
SNOWPIPE_SQL_PATH = REPO_ROOT / "infra" / "snowflake" / "kalshi_events_series_snowpipe.sql"


EVENTS_STAGING_PROJECTION = {
    "event_ticker": "event_ticker",
    "series_ticker": "series_ticker",
    "category": "category",
    "title": "event_title",
    "sub_title": "event_subtitle",
    "available_on_brokers": "is_available_on_brokers",
    "mutually_exclusive": "is_mutually_exclusive",
    "collateral_return_type": "collateral_return_type",
    "last_updated_ts": "updated_at",
    "product_metadata": "product_metadata",
}

SERIES_STAGING_PROJECTION = {
    "ticker": "series_ticker",
    "category": "category",
    "title": "series_title",
    "tags": "tags",
    "frequency": "frequency",
    "fee_multiplier": "fee_multiplier",
    "fee_type": "fee_type",
    "last_updated_ts": "updated_at",
}

LOAD_METADATA_COLUMNS = {
    "ingested_at",
    "raw_payload",
    "source_file",
    "source_row_number",
    "snowpipe_loaded_at",
}


def _table_block(source_text: str, table_name: str) -> str:
    match = re.search(
        rf"^      - name: {re.escape(table_name)}\n(?P<body>.*?)(?=^      - name: |^  - name: |\Z)",
        source_text,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert match is not None, f"Could not find source table block for {table_name}"
    return match.group("body")


def _create_table_columns(sql_text: str, table_name: str) -> set[str]:
    match = re.search(
        rf"CREATE TABLE IF NOT EXISTS {re.escape(table_name)} \(\n(?P<body>.*?)\n\);",
        sql_text,
        flags=re.DOTALL,
    )
    assert match is not None, f"Could not find CREATE TABLE block for {table_name}"
    return set(re.findall(r'^\s+"([^"]+)"\s+\w+', match.group("body"), flags=re.MULTILINE))


def _projected_columns(sql_text: str) -> dict[str, str]:
    match = re.search(r"select(?P<select>.*?)from source", sql_text, flags=re.IGNORECASE | re.DOTALL)
    assert match is not None, "Could not find staging select list"
    return {
        raw_column: alias
        for raw_column, alias in re.findall(
            r'"([^"]+)"[^,\n]*?\bas\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            match.group("select"),
            flags=re.IGNORECASE,
        )
    }


def _documented_columns(schema_text: str, model_name: str) -> list[str]:
    columns: list[str] = []
    in_model = False

    for line in schema_text.splitlines():
        stripped = line.strip()
        indent = len(line) - len(line.lstrip(" "))

        if stripped.startswith("- name: ") and indent == 2:
            in_model = stripped.split(": ", 1)[1] == model_name
            continue

        if in_model and stripped.startswith("- name: ") and indent == 6:
            columns.append(stripped.split(": ", 1)[1])

    return columns


def test_dbt_sources_still_point_at_final_raw_events_and_series_tables():
    sources = SOURCES_PATH.read_text(encoding="utf-8")

    assert "identifier: RAW_EVENTS" in _table_block(sources, "events")
    assert "identifier: RAW_SERIES" in _table_block(sources, "series")
    assert "identifier: RAW_KALSHI_EVENTS_LOAD" not in sources
    assert "identifier: RAW_KALSHI_SERIES_LOAD" not in sources


def test_staging_models_project_landed_events_and_series_columns():
    assert _projected_columns(EVENTS_MODEL_PATH.read_text(encoding="utf-8")) == EVENTS_STAGING_PROJECTION
    assert _projected_columns(SERIES_MODEL_PATH.read_text(encoding="utf-8")) == SERIES_STAGING_PROJECTION


def test_snowpipe_final_raw_tables_cover_staging_inputs_and_load_metadata():
    snowpipe_sql = SNOWPIPE_SQL_PATH.read_text(encoding="utf-8")
    events_columns = _create_table_columns(snowpipe_sql, "RAW_EVENTS")
    series_columns = _create_table_columns(snowpipe_sql, "RAW_SERIES")

    assert set(EVENTS_STAGING_PROJECTION).issubset(events_columns)
    assert set(SERIES_STAGING_PROJECTION).issubset(series_columns)
    assert LOAD_METADATA_COLUMNS.issubset(events_columns)
    assert LOAD_METADATA_COLUMNS.issubset(series_columns)


def test_staging_schema_documents_events_and_series_model_outputs():
    schema = STAGING_SCHEMA_PATH.read_text(encoding="utf-8")

    assert _documented_columns(schema, "stg_kalshi_events") == list(EVENTS_STAGING_PROJECTION.values())
    assert _documented_columns(schema, "stg_kalshi_series") == list(SERIES_STAGING_PROJECTION.values())
