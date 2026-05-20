import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DBT_MODELS_PATH = REPO_ROOT / "dbt" / "models"
SOURCES_PATH = DBT_MODELS_PATH / "sources.yml"
STAGING_SCHEMA_PATH = DBT_MODELS_PATH / "staging" / "schema.yml"
MARKETS_MODEL_PATH = DBT_MODELS_PATH / "staging" / "stg_kalshi_markets.sql"
ORDERBOOKS_MODEL_PATH = DBT_MODELS_PATH / "staging" / "stg_kalshi_market_orderbooks.sql"
TRADES_MODEL_PATH = DBT_MODELS_PATH / "staging" / "stg_kalshi_market_trades.sql"
FCT_MARKETS_MODEL_PATH = DBT_MODELS_PATH / "marts" / "kalshi" / "fct_markets.sql"
FCT_ORDERBOOKS_MODEL_PATH = DBT_MODELS_PATH / "marts" / "kalshi" / "fct_market_orderbooks.sql"
SNOWPIPE_SQL_PATH = REPO_ROOT / "infra" / "snowflake" / "kalshi_markets_snowpipe.sql"


MARKETS_REQUIRED_PROJECTION = {
    "ticker": "market_ticker",
    "event_ticker": "event_ticker",
    "title": "market_title",
}

MARKETS_OPTIONAL_PROJECTION = {
    "market_type": "market_type",
    "status": "market_status",
    "result": "market_result",
    "yes_sub_title": "yes_subtitle",
    "no_sub_title": "no_subtitle",
    "rules_primary": "primary_rules",
    "rules_secondary": "secondary_rules",
    "response_price_units": "response_price_units",
    "price_level_structure": "price_level_structure",
    "strike_type": "strike_type",
    "expiration_value": "expiration_value",
    "early_close_condition": "early_close_condition",
    "primary_participant_key": "primary_participant_key",
    "can_close_early": "can_close_early",
    "fractional_trading_enabled": "is_fractional_trading_enabled",
    "created_time": "created_at",
    "open_time": "open_at",
    "close_time": "close_at",
    "expected_expiration_time": "expected_expiration_at",
    "expiration_time": "expiration_at",
    "latest_expiration_time": "latest_expiration_at",
    "updated_time": "updated_at",
    "fee_waiver_expiration_time": "fee_waiver_expiration_at",
    "last_price_dollars": "last_price_dollars",
    "liquidity_dollars": "liquidity_dollars",
    "no_ask_dollars": "no_ask_dollars",
    "no_bid_dollars": "no_bid_dollars",
    "notional_value_dollars": "notional_value_dollars",
    "previous_price_dollars": "previous_price_dollars",
    "previous_yes_ask_dollars": "previous_yes_ask_dollars",
    "previous_yes_bid_dollars": "previous_yes_bid_dollars",
    "yes_ask_dollars": "yes_ask_dollars",
    "yes_bid_dollars": "yes_bid_dollars",
    "open_interest_fp": "open_interest_fp",
    "volume_24h_fp": "volume_24h_fp",
    "volume_fp": "volume_fp",
    "yes_ask_size_fp": "yes_ask_size_fp",
    "yes_bid_size_fp": "yes_bid_size_fp",
    "settlement_timer_seconds": "settlement_timer_seconds",
    "tick_size": "tick_size",
    "floor_strike": "floor_strike",
    "cap_strike": "cap_strike",
    "custom_strike": "custom_strike",
    "price_ranges": "price_ranges",
}

MARKETS_STAGING_OUTPUT = [
    "market_ticker",
    "event_ticker",
    "market_title",
    "market_type",
    "market_status",
    "market_result",
    "market_subtitle",
    "yes_subtitle",
    "no_subtitle",
    "primary_rules",
    "secondary_rules",
    "response_price_units",
    "price_level_structure",
    "strike_type",
    "expiration_value",
    "early_close_condition",
    "primary_participant_key",
    "can_close_early",
    "is_fractional_trading_enabled",
    "created_at",
    "open_at",
    "close_at",
    "expected_expiration_at",
    "expiration_at",
    "latest_expiration_at",
    "updated_at",
    "fee_waiver_expiration_at",
    "last_price_dollars",
    "liquidity_dollars",
    "no_ask_dollars",
    "no_bid_dollars",
    "notional_value_dollars",
    "previous_price_dollars",
    "previous_yes_ask_dollars",
    "previous_yes_bid_dollars",
    "yes_ask_dollars",
    "yes_bid_dollars",
    "open_interest_fp",
    "volume_24h_fp",
    "volume_fp",
    "yes_ask_size_fp",
    "yes_bid_size_fp",
    "settlement_timer_seconds",
    "tick_size",
    "floor_strike",
    "cap_strike",
    "custom_strike",
    "price_ranges",
]

ORDERBOOKS_STAGING_PROJECTION = {
    "market_ticker": "market_ticker",
    "orderbook": "orderbook",
}

TRADES_STAGING_PROJECTION = {
    "trade_id": "trade_id",
    "ticker": "market_ticker",
    "count_fp": "count_fp",
    "taker_side": "taker_side",
    "no_price_dollars": "no_price_dollars",
    "yes_price_dollars": "yes_price_dollars",
    "created_time": "trade_time",
}

TRADES_NUMERIC_CASTS = {
    "count_fp": ("count_fp", 38, 6),
    "no_price_dollars": ("no_price_dollars", 18, 4),
    "yes_price_dollars": ("yes_price_dollars", 18, 4),
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


def _alter_table_columns(sql_text: str, table_name: str) -> set[str]:
    return set(
        re.findall(
            rf'ALTER TABLE {re.escape(table_name)} ADD COLUMN IF NOT EXISTS "([^"]+)"',
            sql_text,
        )
    )


def _select_expressions(sql_text: str) -> list[str]:
    match = re.search(r"select(?P<select>.*?)from source", sql_text, flags=re.IGNORECASE | re.DOTALL)
    assert match is not None, "Could not find staging select list"
    expressions: list[str] = []
    current: list[str] = []
    depth = 0
    quote_char = ""

    for char in match.group("select"):
        if quote_char:
            current.append(char)
            if char == quote_char:
                quote_char = ""
            continue

        if char in {"'", '"'}:
            quote_char = char
        elif char == "(":
            depth += 1
        elif char == ")" and depth:
            depth -= 1
        elif char == "," and depth == 0:
            expression = "".join(current).strip()
            if expression:
                expressions.append(expression)
            current = []
            continue

        current.append(char)

    expression = "".join(current).strip()
    if expression:
        expressions.append(expression)

    return expressions


def _direct_projected_columns(sql_text: str) -> dict[str, str]:
    return {
        raw_columns[-1]: alias_match.group(1)
        for expression in _select_expressions(sql_text)
        if (raw_columns := re.findall(r'"([^"]+)"', expression))
        and (
            alias_match := re.search(
                r"\bas\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:\}\})?\s*$",
                expression,
                flags=re.IGNORECASE,
            )
        )
    }


def _optional_projection_calls(sql_text: str) -> dict[str, str]:
    return {
        raw_column: alias
        for raw_column, alias in re.findall(
            r"optional_[a-z_]+\(\s*raw_markets_column_names,\s*'([^']+)',\s*'([^']+)'",
            sql_text,
        )
    }


def _try_decimal_casts(sql_text: str) -> dict[str, tuple[str, int, int]]:
    return {
        raw_column: (alias, int(precision), int(scale))
        for raw_column, precision, scale, alias in re.findall(
            r'try_to_decimal\(\s*cast\("([^"]+)"\s+as\s+varchar\),\s*(\d+),\s*(\d+)\s*\)\s+as\s+'
            r"([a-zA-Z_][a-zA-Z0-9_]*)",
            sql_text,
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


class KalshiMarketsDbtContractTests(unittest.TestCase):
    def test_dbt_sources_still_point_at_final_raw_market_tables(self):
        sources = SOURCES_PATH.read_text(encoding="utf-8")

        self.assertIn("identifier: RAW_MARKETS", _table_block(sources, "markets"))
        self.assertIn("identifier: RAW_MARKET_ORDERBOOKS", _table_block(sources, "market_orderbooks"))
        self.assertIn("identifier: RAW_MARKET_TRADES", _table_block(sources, "market_trades"))
        self.assertNotIn("identifier: RAW_KALSHI_MARKETS_LOAD", sources)
        self.assertNotIn("identifier: RAW_KALSHI_MARKET_ORDERBOOKS_LOAD", sources)
        self.assertNotIn("identifier: RAW_KALSHI_MARKET_TRADES_LOAD", sources)

    def test_staging_models_project_landed_market_columns(self):
        markets_sql = MARKETS_MODEL_PATH.read_text(encoding="utf-8")

        self.assertEqual(
            {
                key: value
                for key, value in _direct_projected_columns(markets_sql).items()
                if key in MARKETS_REQUIRED_PROJECTION
            },
            MARKETS_REQUIRED_PROJECTION,
        )
        self.assertEqual(_optional_projection_calls(markets_sql), MARKETS_OPTIONAL_PROJECTION)
        self.assertIn('"subtitle" as market_subtitle', markets_sql)
        self.assertIn('"yes_sub_title" = "no_sub_title"', markets_sql)

        self.assertEqual(
            _direct_projected_columns(ORDERBOOKS_MODEL_PATH.read_text(encoding="utf-8")),
            ORDERBOOKS_STAGING_PROJECTION,
        )
        self.assertEqual(
            _direct_projected_columns(TRADES_MODEL_PATH.read_text(encoding="utf-8")),
            TRADES_STAGING_PROJECTION,
        )

    def test_trade_staging_casts_decimal_strings_at_sql_boundary(self):
        trades_sql = TRADES_MODEL_PATH.read_text(encoding="utf-8")

        self.assertEqual(_try_decimal_casts(trades_sql), TRADES_NUMERIC_CASTS)

    def test_snowpipe_final_raw_tables_cover_staging_inputs_and_load_metadata(self):
        snowpipe_sql = SNOWPIPE_SQL_PATH.read_text(encoding="utf-8")

        expected_markets_columns = (
            set(MARKETS_REQUIRED_PROJECTION)
            | set(MARKETS_OPTIONAL_PROJECTION)
            | {"subtitle"}
            | LOAD_METADATA_COLUMNS
        )
        expected_orderbook_columns = set(ORDERBOOKS_STAGING_PROJECTION) | LOAD_METADATA_COLUMNS
        expected_trade_columns = set(TRADES_STAGING_PROJECTION) | LOAD_METADATA_COLUMNS

        for table_name, expected_columns in (
            ("RAW_MARKETS", expected_markets_columns),
            ("RAW_MARKET_ORDERBOOKS", expected_orderbook_columns),
            ("RAW_MARKET_TRADES", expected_trade_columns),
        ):
            self.assertTrue(expected_columns.issubset(_create_table_columns(snowpipe_sql, table_name)))
            self.assertTrue(expected_columns.issubset(_alter_table_columns(snowpipe_sql, table_name)))

    def test_staging_schema_documents_market_model_outputs(self):
        schema = STAGING_SCHEMA_PATH.read_text(encoding="utf-8")

        self.assertEqual(_documented_columns(schema, "stg_kalshi_markets"), MARKETS_STAGING_OUTPUT)
        self.assertEqual(
            _documented_columns(schema, "stg_kalshi_market_orderbooks"),
            list(ORDERBOOKS_STAGING_PROJECTION.values()),
        )
        self.assertEqual(
            _documented_columns(schema, "stg_kalshi_market_trades"),
            list(TRADES_STAGING_PROJECTION.values()),
        )

    def test_downstream_market_marts_use_staging_models(self):
        fct_markets = FCT_MARKETS_MODEL_PATH.read_text(encoding="utf-8")
        fct_orderbooks = FCT_ORDERBOOKS_MODEL_PATH.read_text(encoding="utf-8")

        self.assertIn("ref('stg_kalshi_markets')", fct_markets)
        self.assertIn("ref('stg_kalshi_events')", fct_markets)
        self.assertIn("ref('stg_kalshi_market_orderbooks')", fct_orderbooks)
        self.assertIn("ref('stg_kalshi_markets')", fct_orderbooks)
        self.assertIn("ref('stg_kalshi_events')", fct_orderbooks)


if __name__ == "__main__":
    unittest.main()
