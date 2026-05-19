-- Kalshi Markets, Market Orderbooks, and Market Trades Snowpipe ingestion.
--
-- This file keeps the final RAW table names used by dbt:
--   - RAW_MARKETS, keyed by "ticker"
--   - RAW_MARKET_ORDERBOOKS, keyed by "market_ticker"
--   - RAW_MARKET_TRADES, keyed by "trade_id"
--
-- Snowpipe appends JSONL rows into transient load tables. Append-only streams
-- expose newly loaded rows to merge tasks, and low-frequency cleanup tasks
-- remove old load rows only when the streams have no backlog. Empty market trade
-- files from no-trade windows load as zero-row files and do not create final
-- trade placeholders.
--
-- Execution order:
-- 1. Apply Terraform and confirm output snowflake_s3_read_role_arn already
--    matches the role trusted by Snowflake.
-- 2. Replace <task_warehouse> with the Snowflake warehouse that should run
--    the merge and cleanup tasks.
-- 3. Run the storage integration ALTER so the existing S3_MLB_TEAMS_INT
--    integration can read the Kalshi market prefixes without introducing a
--    second Snowflake external ID/IAM trust path.
-- 4. Run the file format, stages, load/final tables, pipes, streams, and tasks.
-- 5. Run SHOW PIPES and copy each notification_channel ARN into the Terraform
--    Snowpipe S3 notification variables. See docs/snowpipe_s3_notifications.md.

USE DATABASE PROD;
USE SCHEMA RAW;

ALTER STORAGE INTEGRATION S3_MLB_TEAMS_INT
  SET STORAGE_ALLOWED_LOCATIONS = (
    's3://snowflake-kalshi-project/raw/mlb/teams/',
    's3://snowflake-kalshi-project/raw/kalshi/events/',
    's3://snowflake-kalshi-project/raw/kalshi/series/',
    's3://snowflake-kalshi-project/raw/kalshi/markets/',
    's3://snowflake-kalshi-project/raw/kalshi/market_orderbooks/',
    's3://snowflake-kalshi-project/raw/kalshi/market_trades/'
  );

CREATE FILE FORMAT IF NOT EXISTS FF_KALSHI_JSONL
  TYPE = JSON
  COMPRESSION = AUTO
  MULTI_LINE = FALSE;

CREATE STAGE IF NOT EXISTS STG_KALSHI_MARKETS
  URL = 's3://snowflake-kalshi-project/raw/kalshi/markets/'
  STORAGE_INTEGRATION = S3_MLB_TEAMS_INT
  FILE_FORMAT = (FORMAT_NAME = FF_KALSHI_JSONL);

CREATE STAGE IF NOT EXISTS STG_KALSHI_MARKET_ORDERBOOKS
  URL = 's3://snowflake-kalshi-project/raw/kalshi/market_orderbooks/'
  STORAGE_INTEGRATION = S3_MLB_TEAMS_INT
  FILE_FORMAT = (FORMAT_NAME = FF_KALSHI_JSONL);

CREATE STAGE IF NOT EXISTS STG_KALSHI_MARKET_TRADES
  URL = 's3://snowflake-kalshi-project/raw/kalshi/market_trades/'
  STORAGE_INTEGRATION = S3_MLB_TEAMS_INT
  FILE_FORMAT = (FORMAT_NAME = FF_KALSHI_JSONL);

CREATE TRANSIENT TABLE IF NOT EXISTS RAW_KALSHI_MARKETS_LOAD (
  "ticker" VARCHAR,
  "event_ticker" VARCHAR,
  "market_type" VARCHAR,
  "status" VARCHAR,
  "result" VARCHAR,
  "title" VARCHAR,
  "subtitle" VARCHAR,
  "yes_sub_title" VARCHAR,
  "no_sub_title" VARCHAR,
  "rules_primary" VARCHAR,
  "rules_secondary" VARCHAR,
  "response_price_units" VARCHAR,
  "price_level_structure" VARCHAR,
  "strike_type" VARCHAR,
  "expiration_value" VARCHAR,
  "early_close_condition" VARCHAR,
  "primary_participant_key" VARCHAR,
  "can_close_early" BOOLEAN,
  "fractional_trading_enabled" BOOLEAN,
  "created_time" VARCHAR,
  "open_time" VARCHAR,
  "close_time" VARCHAR,
  "expected_expiration_time" VARCHAR,
  "expiration_time" VARCHAR,
  "latest_expiration_time" VARCHAR,
  "updated_time" VARCHAR,
  "fee_waiver_expiration_time" VARCHAR,
  "last_price_dollars" VARCHAR,
  "liquidity_dollars" VARCHAR,
  "no_ask_dollars" VARCHAR,
  "no_bid_dollars" VARCHAR,
  "notional_value_dollars" VARCHAR,
  "previous_price_dollars" VARCHAR,
  "previous_yes_ask_dollars" VARCHAR,
  "previous_yes_bid_dollars" VARCHAR,
  "yes_ask_dollars" VARCHAR,
  "yes_bid_dollars" VARCHAR,
  "open_interest_fp" VARCHAR,
  "volume_24h_fp" VARCHAR,
  "volume_fp" VARCHAR,
  "yes_ask_size_fp" VARCHAR,
  "yes_bid_size_fp" VARCHAR,
  "settlement_timer_seconds" NUMBER,
  "tick_size" VARCHAR,
  "floor_strike" VARCHAR,
  "cap_strike" VARCHAR,
  "custom_strike" VARIANT,
  "price_ranges" VARIANT,
  "ingested_at" TIMESTAMP_NTZ,
  "raw_payload" VARIANT,
  "source_file" VARCHAR,
  "source_row_number" NUMBER,
  "snowpipe_loaded_at" TIMESTAMP_NTZ
)
DATA_RETENTION_TIME_IN_DAYS = 1;

CREATE TRANSIENT TABLE IF NOT EXISTS RAW_KALSHI_MARKET_ORDERBOOKS_LOAD (
  "market_ticker" VARCHAR,
  "orderbook" VARIANT,
  "ingested_at" TIMESTAMP_NTZ,
  "raw_payload" VARIANT,
  "source_file" VARCHAR,
  "source_row_number" NUMBER,
  "snowpipe_loaded_at" TIMESTAMP_NTZ
)
DATA_RETENTION_TIME_IN_DAYS = 1;

CREATE TRANSIENT TABLE IF NOT EXISTS RAW_KALSHI_MARKET_TRADES_LOAD (
  "trade_id" VARCHAR,
  "ticker" VARCHAR,
  "count_fp" VARCHAR,
  "taker_side" VARCHAR,
  "no_price_dollars" VARCHAR,
  "yes_price_dollars" VARCHAR,
  "created_time" VARCHAR,
  "ingested_at" TIMESTAMP_NTZ,
  "raw_payload" VARIANT,
  "source_file" VARCHAR,
  "source_row_number" NUMBER,
  "snowpipe_loaded_at" TIMESTAMP_NTZ
)
DATA_RETENTION_TIME_IN_DAYS = 1;

CREATE TABLE IF NOT EXISTS RAW_MARKETS (
  "ticker" VARCHAR,
  "event_ticker" VARCHAR,
  "market_type" VARCHAR,
  "status" VARCHAR,
  "result" VARCHAR,
  "title" VARCHAR,
  "subtitle" VARCHAR,
  "yes_sub_title" VARCHAR,
  "no_sub_title" VARCHAR,
  "rules_primary" VARCHAR,
  "rules_secondary" VARCHAR,
  "response_price_units" VARCHAR,
  "price_level_structure" VARCHAR,
  "strike_type" VARCHAR,
  "expiration_value" VARCHAR,
  "early_close_condition" VARCHAR,
  "primary_participant_key" VARCHAR,
  "can_close_early" BOOLEAN,
  "fractional_trading_enabled" BOOLEAN,
  "created_time" VARCHAR,
  "open_time" VARCHAR,
  "close_time" VARCHAR,
  "expected_expiration_time" VARCHAR,
  "expiration_time" VARCHAR,
  "latest_expiration_time" VARCHAR,
  "updated_time" VARCHAR,
  "fee_waiver_expiration_time" VARCHAR,
  "last_price_dollars" VARCHAR,
  "liquidity_dollars" VARCHAR,
  "no_ask_dollars" VARCHAR,
  "no_bid_dollars" VARCHAR,
  "notional_value_dollars" VARCHAR,
  "previous_price_dollars" VARCHAR,
  "previous_yes_ask_dollars" VARCHAR,
  "previous_yes_bid_dollars" VARCHAR,
  "yes_ask_dollars" VARCHAR,
  "yes_bid_dollars" VARCHAR,
  "open_interest_fp" VARCHAR,
  "volume_24h_fp" VARCHAR,
  "volume_fp" VARCHAR,
  "yes_ask_size_fp" VARCHAR,
  "yes_bid_size_fp" VARCHAR,
  "settlement_timer_seconds" NUMBER,
  "tick_size" VARCHAR,
  "floor_strike" VARCHAR,
  "cap_strike" VARCHAR,
  "custom_strike" VARIANT,
  "price_ranges" VARIANT,
  "ingested_at" TIMESTAMP_NTZ,
  "raw_payload" VARIANT,
  "source_file" VARCHAR,
  "source_row_number" NUMBER,
  "snowpipe_loaded_at" TIMESTAMP_NTZ,
  PRIMARY KEY ("ticker")
);

ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "ticker" VARCHAR;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "event_ticker" VARCHAR;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "market_type" VARCHAR;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "status" VARCHAR;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "result" VARCHAR;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "title" VARCHAR;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "subtitle" VARCHAR;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "yes_sub_title" VARCHAR;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "no_sub_title" VARCHAR;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "rules_primary" VARCHAR;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "rules_secondary" VARCHAR;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "response_price_units" VARCHAR;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "price_level_structure" VARCHAR;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "strike_type" VARCHAR;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "expiration_value" VARCHAR;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "early_close_condition" VARCHAR;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "primary_participant_key" VARCHAR;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "can_close_early" BOOLEAN;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "fractional_trading_enabled" BOOLEAN;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "created_time" VARCHAR;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "open_time" VARCHAR;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "close_time" VARCHAR;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "expected_expiration_time" VARCHAR;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "expiration_time" VARCHAR;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "latest_expiration_time" VARCHAR;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "updated_time" VARCHAR;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "fee_waiver_expiration_time" VARCHAR;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "last_price_dollars" VARCHAR;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "liquidity_dollars" VARCHAR;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "no_ask_dollars" VARCHAR;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "no_bid_dollars" VARCHAR;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "notional_value_dollars" VARCHAR;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "previous_price_dollars" VARCHAR;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "previous_yes_ask_dollars" VARCHAR;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "previous_yes_bid_dollars" VARCHAR;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "yes_ask_dollars" VARCHAR;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "yes_bid_dollars" VARCHAR;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "open_interest_fp" VARCHAR;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "volume_24h_fp" VARCHAR;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "volume_fp" VARCHAR;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "yes_ask_size_fp" VARCHAR;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "yes_bid_size_fp" VARCHAR;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "settlement_timer_seconds" NUMBER;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "tick_size" VARCHAR;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "floor_strike" VARCHAR;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "cap_strike" VARCHAR;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "custom_strike" VARIANT;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "price_ranges" VARIANT;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "ingested_at" TIMESTAMP_NTZ;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "raw_payload" VARIANT;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "source_file" VARCHAR;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "source_row_number" NUMBER;
ALTER TABLE RAW_MARKETS ADD COLUMN IF NOT EXISTS "snowpipe_loaded_at" TIMESTAMP_NTZ;

CREATE TABLE IF NOT EXISTS RAW_MARKET_ORDERBOOKS (
  "market_ticker" VARCHAR,
  "orderbook" VARIANT,
  "ingested_at" TIMESTAMP_NTZ,
  "raw_payload" VARIANT,
  "source_file" VARCHAR,
  "source_row_number" NUMBER,
  "snowpipe_loaded_at" TIMESTAMP_NTZ,
  PRIMARY KEY ("market_ticker")
);

ALTER TABLE RAW_MARKET_ORDERBOOKS ADD COLUMN IF NOT EXISTS "market_ticker" VARCHAR;
ALTER TABLE RAW_MARKET_ORDERBOOKS ADD COLUMN IF NOT EXISTS "orderbook" VARIANT;
ALTER TABLE RAW_MARKET_ORDERBOOKS ADD COLUMN IF NOT EXISTS "ingested_at" TIMESTAMP_NTZ;
ALTER TABLE RAW_MARKET_ORDERBOOKS ADD COLUMN IF NOT EXISTS "raw_payload" VARIANT;
ALTER TABLE RAW_MARKET_ORDERBOOKS ADD COLUMN IF NOT EXISTS "source_file" VARCHAR;
ALTER TABLE RAW_MARKET_ORDERBOOKS ADD COLUMN IF NOT EXISTS "source_row_number" NUMBER;
ALTER TABLE RAW_MARKET_ORDERBOOKS ADD COLUMN IF NOT EXISTS "snowpipe_loaded_at" TIMESTAMP_NTZ;

CREATE TABLE IF NOT EXISTS RAW_MARKET_TRADES (
  "trade_id" VARCHAR,
  "ticker" VARCHAR,
  "count_fp" VARCHAR,
  "taker_side" VARCHAR,
  "no_price_dollars" VARCHAR,
  "yes_price_dollars" VARCHAR,
  "created_time" VARCHAR,
  "ingested_at" TIMESTAMP_NTZ,
  "raw_payload" VARIANT,
  "source_file" VARCHAR,
  "source_row_number" NUMBER,
  "snowpipe_loaded_at" TIMESTAMP_NTZ,
  PRIMARY KEY ("trade_id")
);

ALTER TABLE RAW_MARKET_TRADES ADD COLUMN IF NOT EXISTS "trade_id" VARCHAR;
ALTER TABLE RAW_MARKET_TRADES ADD COLUMN IF NOT EXISTS "ticker" VARCHAR;
ALTER TABLE RAW_MARKET_TRADES ADD COLUMN IF NOT EXISTS "count_fp" VARCHAR;
ALTER TABLE RAW_MARKET_TRADES ADD COLUMN IF NOT EXISTS "taker_side" VARCHAR;
ALTER TABLE RAW_MARKET_TRADES ADD COLUMN IF NOT EXISTS "no_price_dollars" VARCHAR;
ALTER TABLE RAW_MARKET_TRADES ADD COLUMN IF NOT EXISTS "yes_price_dollars" VARCHAR;
ALTER TABLE RAW_MARKET_TRADES ADD COLUMN IF NOT EXISTS "created_time" VARCHAR;
ALTER TABLE RAW_MARKET_TRADES ADD COLUMN IF NOT EXISTS "ingested_at" TIMESTAMP_NTZ;
ALTER TABLE RAW_MARKET_TRADES ADD COLUMN IF NOT EXISTS "raw_payload" VARIANT;
ALTER TABLE RAW_MARKET_TRADES ADD COLUMN IF NOT EXISTS "source_file" VARCHAR;
ALTER TABLE RAW_MARKET_TRADES ADD COLUMN IF NOT EXISTS "source_row_number" NUMBER;
ALTER TABLE RAW_MARKET_TRADES ADD COLUMN IF NOT EXISTS "snowpipe_loaded_at" TIMESTAMP_NTZ;

CREATE PIPE IF NOT EXISTS PIPE_KALSHI_MARKETS
  AUTO_INGEST = TRUE
AS
COPY INTO RAW_KALSHI_MARKETS_LOAD (
  "ticker",
  "event_ticker",
  "market_type",
  "status",
  "result",
  "title",
  "subtitle",
  "yes_sub_title",
  "no_sub_title",
  "rules_primary",
  "rules_secondary",
  "response_price_units",
  "price_level_structure",
  "strike_type",
  "expiration_value",
  "early_close_condition",
  "primary_participant_key",
  "can_close_early",
  "fractional_trading_enabled",
  "created_time",
  "open_time",
  "close_time",
  "expected_expiration_time",
  "expiration_time",
  "latest_expiration_time",
  "updated_time",
  "fee_waiver_expiration_time",
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
  "ingested_at",
  "raw_payload",
  "source_file",
  "source_row_number",
  "snowpipe_loaded_at"
)
FROM (
  SELECT
    $1:ticker::VARCHAR,
    $1:event_ticker::VARCHAR,
    $1:market_type::VARCHAR,
    $1:status::VARCHAR,
    $1:result::VARCHAR,
    $1:title::VARCHAR,
    $1:subtitle::VARCHAR,
    $1:yes_sub_title::VARCHAR,
    $1:no_sub_title::VARCHAR,
    $1:rules_primary::VARCHAR,
    $1:rules_secondary::VARCHAR,
    $1:response_price_units::VARCHAR,
    $1:price_level_structure::VARCHAR,
    $1:strike_type::VARCHAR,
    $1:expiration_value::VARCHAR,
    $1:early_close_condition::VARCHAR,
    $1:primary_participant_key::VARCHAR,
    $1:can_close_early::BOOLEAN,
    $1:fractional_trading_enabled::BOOLEAN,
    $1:created_time::VARCHAR,
    $1:open_time::VARCHAR,
    $1:close_time::VARCHAR,
    $1:expected_expiration_time::VARCHAR,
    $1:expiration_time::VARCHAR,
    $1:latest_expiration_time::VARCHAR,
    $1:updated_time::VARCHAR,
    $1:fee_waiver_expiration_time::VARCHAR,
    $1:last_price_dollars::VARCHAR,
    $1:liquidity_dollars::VARCHAR,
    $1:no_ask_dollars::VARCHAR,
    $1:no_bid_dollars::VARCHAR,
    $1:notional_value_dollars::VARCHAR,
    $1:previous_price_dollars::VARCHAR,
    $1:previous_yes_ask_dollars::VARCHAR,
    $1:previous_yes_bid_dollars::VARCHAR,
    $1:yes_ask_dollars::VARCHAR,
    $1:yes_bid_dollars::VARCHAR,
    $1:open_interest_fp::VARCHAR,
    $1:volume_24h_fp::VARCHAR,
    $1:volume_fp::VARCHAR,
    $1:yes_ask_size_fp::VARCHAR,
    $1:yes_bid_size_fp::VARCHAR,
    TRY_TO_NUMBER($1:settlement_timer_seconds::VARCHAR),
    $1:tick_size::VARCHAR,
    $1:floor_strike::VARCHAR,
    $1:cap_strike::VARCHAR,
    $1:custom_strike::VARIANT,
    $1:price_ranges::VARIANT,
    TRY_TO_TIMESTAMP_NTZ($1:ingested_at::VARCHAR),
    COALESCE($1:raw_payload, $1)::VARIANT,
    METADATA$FILENAME,
    METADATA$FILE_ROW_NUMBER,
    CAST(METADATA$START_SCAN_TIME AS TIMESTAMP_NTZ)
  FROM @STG_KALSHI_MARKETS
)
PATTERN = '.*[.]jsonl';

CREATE PIPE IF NOT EXISTS PIPE_KALSHI_MARKET_ORDERBOOKS
  AUTO_INGEST = TRUE
AS
COPY INTO RAW_KALSHI_MARKET_ORDERBOOKS_LOAD (
  "market_ticker",
  "orderbook",
  "ingested_at",
  "raw_payload",
  "source_file",
  "source_row_number",
  "snowpipe_loaded_at"
)
FROM (
  SELECT
    $1:market_ticker::VARCHAR,
    $1:orderbook::VARIANT,
    TRY_TO_TIMESTAMP_NTZ($1:ingested_at::VARCHAR),
    COALESCE($1:raw_payload, $1)::VARIANT,
    METADATA$FILENAME,
    METADATA$FILE_ROW_NUMBER,
    CAST(METADATA$START_SCAN_TIME AS TIMESTAMP_NTZ)
  FROM @STG_KALSHI_MARKET_ORDERBOOKS
)
PATTERN = '.*[.]jsonl';

CREATE PIPE IF NOT EXISTS PIPE_KALSHI_MARKET_TRADES
  AUTO_INGEST = TRUE
AS
COPY INTO RAW_KALSHI_MARKET_TRADES_LOAD (
  "trade_id",
  "ticker",
  "count_fp",
  "taker_side",
  "no_price_dollars",
  "yes_price_dollars",
  "created_time",
  "ingested_at",
  "raw_payload",
  "source_file",
  "source_row_number",
  "snowpipe_loaded_at"
)
FROM (
  SELECT
    $1:trade_id::VARCHAR,
    COALESCE($1:ticker::VARCHAR, $1:market_ticker::VARCHAR),
    $1:count_fp::VARCHAR,
    $1:taker_side::VARCHAR,
    $1:no_price_dollars::VARCHAR,
    $1:yes_price_dollars::VARCHAR,
    $1:created_time::VARCHAR,
    TRY_TO_TIMESTAMP_NTZ($1:ingested_at::VARCHAR),
    COALESCE($1:raw_payload, $1)::VARIANT,
    METADATA$FILENAME,
    METADATA$FILE_ROW_NUMBER,
    CAST(METADATA$START_SCAN_TIME AS TIMESTAMP_NTZ)
  FROM @STG_KALSHI_MARKET_TRADES
)
PATTERN = '.*[.]jsonl';

CREATE STREAM IF NOT EXISTS STRM_RAW_KALSHI_MARKETS_LOAD
  ON TABLE RAW_KALSHI_MARKETS_LOAD
  APPEND_ONLY = TRUE;

CREATE STREAM IF NOT EXISTS STRM_RAW_KALSHI_MARKET_ORDERBOOKS_LOAD
  ON TABLE RAW_KALSHI_MARKET_ORDERBOOKS_LOAD
  APPEND_ONLY = TRUE;

CREATE STREAM IF NOT EXISTS STRM_RAW_KALSHI_MARKET_TRADES_LOAD
  ON TABLE RAW_KALSHI_MARKET_TRADES_LOAD
  APPEND_ONLY = TRUE;

CREATE TASK IF NOT EXISTS TASK_MERGE_KALSHI_MARKETS
  WAREHOUSE = <task_warehouse>
  WHEN SYSTEM$STREAM_HAS_DATA('PROD.RAW.STRM_RAW_KALSHI_MARKETS_LOAD')
AS
MERGE INTO RAW_MARKETS AS target
USING (
  WITH ranked AS (
    SELECT
      "ticker",
      "event_ticker",
      "market_type",
      "status",
      "result",
      "title",
      "subtitle",
      "yes_sub_title",
      "no_sub_title",
      "rules_primary",
      "rules_secondary",
      "response_price_units",
      "price_level_structure",
      "strike_type",
      "expiration_value",
      "early_close_condition",
      "primary_participant_key",
      "can_close_early",
      "fractional_trading_enabled",
      "created_time",
      "open_time",
      "close_time",
      "expected_expiration_time",
      "expiration_time",
      "latest_expiration_time",
      "updated_time",
      "fee_waiver_expiration_time",
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
      "ingested_at",
      "raw_payload",
      "source_file",
      "source_row_number",
      "snowpipe_loaded_at",
      ROW_NUMBER() OVER (
        PARTITION BY "ticker"
        ORDER BY
          TRY_TO_TIMESTAMP_NTZ("updated_time") DESC NULLS LAST,
          "ingested_at" DESC NULLS LAST,
          "snowpipe_loaded_at" DESC NULLS LAST,
          "source_file" DESC,
          "source_row_number" DESC
      ) AS row_rank
    FROM STRM_RAW_KALSHI_MARKETS_LOAD
    WHERE METADATA$ACTION = 'INSERT'
      AND "ticker" IS NOT NULL
  )
  SELECT
    "ticker",
    "event_ticker",
    "market_type",
    "status",
    "result",
    "title",
    "subtitle",
    "yes_sub_title",
    "no_sub_title",
    "rules_primary",
    "rules_secondary",
    "response_price_units",
    "price_level_structure",
    "strike_type",
    "expiration_value",
    "early_close_condition",
    "primary_participant_key",
    "can_close_early",
    "fractional_trading_enabled",
    "created_time",
    "open_time",
    "close_time",
    "expected_expiration_time",
    "expiration_time",
    "latest_expiration_time",
    "updated_time",
    "fee_waiver_expiration_time",
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
    "ingested_at",
    "raw_payload",
    "source_file",
    "source_row_number",
    "snowpipe_loaded_at"
  FROM ranked
  WHERE row_rank = 1
) AS source
ON target."ticker" = source."ticker"
WHEN MATCHED THEN UPDATE SET
  target."event_ticker" = source."event_ticker",
  target."market_type" = source."market_type",
  target."status" = source."status",
  target."result" = source."result",
  target."title" = source."title",
  target."subtitle" = source."subtitle",
  target."yes_sub_title" = source."yes_sub_title",
  target."no_sub_title" = source."no_sub_title",
  target."rules_primary" = source."rules_primary",
  target."rules_secondary" = source."rules_secondary",
  target."response_price_units" = source."response_price_units",
  target."price_level_structure" = source."price_level_structure",
  target."strike_type" = source."strike_type",
  target."expiration_value" = source."expiration_value",
  target."early_close_condition" = source."early_close_condition",
  target."primary_participant_key" = source."primary_participant_key",
  target."can_close_early" = source."can_close_early",
  target."fractional_trading_enabled" = source."fractional_trading_enabled",
  target."created_time" = source."created_time",
  target."open_time" = source."open_time",
  target."close_time" = source."close_time",
  target."expected_expiration_time" = source."expected_expiration_time",
  target."expiration_time" = source."expiration_time",
  target."latest_expiration_time" = source."latest_expiration_time",
  target."updated_time" = source."updated_time",
  target."fee_waiver_expiration_time" = source."fee_waiver_expiration_time",
  target."last_price_dollars" = source."last_price_dollars",
  target."liquidity_dollars" = source."liquidity_dollars",
  target."no_ask_dollars" = source."no_ask_dollars",
  target."no_bid_dollars" = source."no_bid_dollars",
  target."notional_value_dollars" = source."notional_value_dollars",
  target."previous_price_dollars" = source."previous_price_dollars",
  target."previous_yes_ask_dollars" = source."previous_yes_ask_dollars",
  target."previous_yes_bid_dollars" = source."previous_yes_bid_dollars",
  target."yes_ask_dollars" = source."yes_ask_dollars",
  target."yes_bid_dollars" = source."yes_bid_dollars",
  target."open_interest_fp" = source."open_interest_fp",
  target."volume_24h_fp" = source."volume_24h_fp",
  target."volume_fp" = source."volume_fp",
  target."yes_ask_size_fp" = source."yes_ask_size_fp",
  target."yes_bid_size_fp" = source."yes_bid_size_fp",
  target."settlement_timer_seconds" = source."settlement_timer_seconds",
  target."tick_size" = source."tick_size",
  target."floor_strike" = source."floor_strike",
  target."cap_strike" = source."cap_strike",
  target."custom_strike" = source."custom_strike",
  target."price_ranges" = source."price_ranges",
  target."ingested_at" = source."ingested_at",
  target."raw_payload" = source."raw_payload",
  target."source_file" = source."source_file",
  target."source_row_number" = source."source_row_number",
  target."snowpipe_loaded_at" = source."snowpipe_loaded_at"
WHEN NOT MATCHED THEN INSERT (
  "ticker",
  "event_ticker",
  "market_type",
  "status",
  "result",
  "title",
  "subtitle",
  "yes_sub_title",
  "no_sub_title",
  "rules_primary",
  "rules_secondary",
  "response_price_units",
  "price_level_structure",
  "strike_type",
  "expiration_value",
  "early_close_condition",
  "primary_participant_key",
  "can_close_early",
  "fractional_trading_enabled",
  "created_time",
  "open_time",
  "close_time",
  "expected_expiration_time",
  "expiration_time",
  "latest_expiration_time",
  "updated_time",
  "fee_waiver_expiration_time",
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
  "ingested_at",
  "raw_payload",
  "source_file",
  "source_row_number",
  "snowpipe_loaded_at"
) VALUES (
  source."ticker",
  source."event_ticker",
  source."market_type",
  source."status",
  source."result",
  source."title",
  source."subtitle",
  source."yes_sub_title",
  source."no_sub_title",
  source."rules_primary",
  source."rules_secondary",
  source."response_price_units",
  source."price_level_structure",
  source."strike_type",
  source."expiration_value",
  source."early_close_condition",
  source."primary_participant_key",
  source."can_close_early",
  source."fractional_trading_enabled",
  source."created_time",
  source."open_time",
  source."close_time",
  source."expected_expiration_time",
  source."expiration_time",
  source."latest_expiration_time",
  source."updated_time",
  source."fee_waiver_expiration_time",
  source."last_price_dollars",
  source."liquidity_dollars",
  source."no_ask_dollars",
  source."no_bid_dollars",
  source."notional_value_dollars",
  source."previous_price_dollars",
  source."previous_yes_ask_dollars",
  source."previous_yes_bid_dollars",
  source."yes_ask_dollars",
  source."yes_bid_dollars",
  source."open_interest_fp",
  source."volume_24h_fp",
  source."volume_fp",
  source."yes_ask_size_fp",
  source."yes_bid_size_fp",
  source."settlement_timer_seconds",
  source."tick_size",
  source."floor_strike",
  source."cap_strike",
  source."custom_strike",
  source."price_ranges",
  source."ingested_at",
  source."raw_payload",
  source."source_file",
  source."source_row_number",
  source."snowpipe_loaded_at"
);

CREATE TASK IF NOT EXISTS TASK_MERGE_KALSHI_MARKET_ORDERBOOKS
  WAREHOUSE = <task_warehouse>
  WHEN SYSTEM$STREAM_HAS_DATA('PROD.RAW.STRM_RAW_KALSHI_MARKET_ORDERBOOKS_LOAD')
AS
MERGE INTO RAW_MARKET_ORDERBOOKS AS target
USING (
  WITH ranked AS (
    SELECT
      "market_ticker",
      "orderbook",
      "ingested_at",
      "raw_payload",
      "source_file",
      "source_row_number",
      "snowpipe_loaded_at",
      ROW_NUMBER() OVER (
        PARTITION BY "market_ticker"
        ORDER BY
          "ingested_at" DESC NULLS LAST,
          "snowpipe_loaded_at" DESC NULLS LAST,
          "source_file" DESC,
          "source_row_number" DESC
      ) AS row_rank
    FROM STRM_RAW_KALSHI_MARKET_ORDERBOOKS_LOAD
    WHERE METADATA$ACTION = 'INSERT'
      AND "market_ticker" IS NOT NULL
  )
  SELECT
    "market_ticker",
    "orderbook",
    "ingested_at",
    "raw_payload",
    "source_file",
    "source_row_number",
    "snowpipe_loaded_at"
  FROM ranked
  WHERE row_rank = 1
) AS source
ON target."market_ticker" = source."market_ticker"
WHEN MATCHED THEN UPDATE SET
  target."orderbook" = source."orderbook",
  target."ingested_at" = source."ingested_at",
  target."raw_payload" = source."raw_payload",
  target."source_file" = source."source_file",
  target."source_row_number" = source."source_row_number",
  target."snowpipe_loaded_at" = source."snowpipe_loaded_at"
WHEN NOT MATCHED THEN INSERT (
  "market_ticker",
  "orderbook",
  "ingested_at",
  "raw_payload",
  "source_file",
  "source_row_number",
  "snowpipe_loaded_at"
) VALUES (
  source."market_ticker",
  source."orderbook",
  source."ingested_at",
  source."raw_payload",
  source."source_file",
  source."source_row_number",
  source."snowpipe_loaded_at"
);

CREATE TASK IF NOT EXISTS TASK_MERGE_KALSHI_MARKET_TRADES
  WAREHOUSE = <task_warehouse>
  WHEN SYSTEM$STREAM_HAS_DATA('PROD.RAW.STRM_RAW_KALSHI_MARKET_TRADES_LOAD')
AS
MERGE INTO RAW_MARKET_TRADES AS target
USING (
  WITH ranked AS (
    SELECT
      "trade_id",
      "ticker",
      "count_fp",
      "taker_side",
      "no_price_dollars",
      "yes_price_dollars",
      "created_time",
      "ingested_at",
      "raw_payload",
      "source_file",
      "source_row_number",
      "snowpipe_loaded_at",
      ROW_NUMBER() OVER (
        PARTITION BY "trade_id"
        ORDER BY
          TRY_TO_TIMESTAMP_NTZ("created_time") DESC NULLS LAST,
          "ingested_at" DESC NULLS LAST,
          "snowpipe_loaded_at" DESC NULLS LAST,
          "source_file" DESC,
          "source_row_number" DESC
      ) AS row_rank
    FROM STRM_RAW_KALSHI_MARKET_TRADES_LOAD
    WHERE METADATA$ACTION = 'INSERT'
      AND "trade_id" IS NOT NULL
  )
  SELECT
    "trade_id",
    "ticker",
    "count_fp",
    "taker_side",
    "no_price_dollars",
    "yes_price_dollars",
    "created_time",
    "ingested_at",
    "raw_payload",
    "source_file",
    "source_row_number",
    "snowpipe_loaded_at"
  FROM ranked
  WHERE row_rank = 1
) AS source
ON target."trade_id" = source."trade_id"
WHEN MATCHED THEN UPDATE SET
  target."ticker" = source."ticker",
  target."count_fp" = source."count_fp",
  target."taker_side" = source."taker_side",
  target."no_price_dollars" = source."no_price_dollars",
  target."yes_price_dollars" = source."yes_price_dollars",
  target."created_time" = source."created_time",
  target."ingested_at" = source."ingested_at",
  target."raw_payload" = source."raw_payload",
  target."source_file" = source."source_file",
  target."source_row_number" = source."source_row_number",
  target."snowpipe_loaded_at" = source."snowpipe_loaded_at"
WHEN NOT MATCHED THEN INSERT (
  "trade_id",
  "ticker",
  "count_fp",
  "taker_side",
  "no_price_dollars",
  "yes_price_dollars",
  "created_time",
  "ingested_at",
  "raw_payload",
  "source_file",
  "source_row_number",
  "snowpipe_loaded_at"
) VALUES (
  source."trade_id",
  source."ticker",
  source."count_fp",
  source."taker_side",
  source."no_price_dollars",
  source."yes_price_dollars",
  source."created_time",
  source."ingested_at",
  source."raw_payload",
  source."source_file",
  source."source_row_number",
  source."snowpipe_loaded_at"
);

CREATE TASK IF NOT EXISTS TASK_CLEANUP_KALSHI_MARKETS_LOAD
  WAREHOUSE = <task_warehouse>
  SCHEDULE = 'USING CRON 0 3 * * * America/Chicago'
  WHEN NOT SYSTEM$STREAM_HAS_DATA('PROD.RAW.STRM_RAW_KALSHI_MARKETS_LOAD')
AS
DELETE FROM RAW_KALSHI_MARKETS_LOAD
WHERE "snowpipe_loaded_at" < DATEADD('day', -2, CURRENT_TIMESTAMP());

CREATE TASK IF NOT EXISTS TASK_CLEANUP_KALSHI_MARKET_ORDERBOOKS_LOAD
  WAREHOUSE = <task_warehouse>
  SCHEDULE = 'USING CRON 15 3 * * * America/Chicago'
  WHEN NOT SYSTEM$STREAM_HAS_DATA('PROD.RAW.STRM_RAW_KALSHI_MARKET_ORDERBOOKS_LOAD')
AS
DELETE FROM RAW_KALSHI_MARKET_ORDERBOOKS_LOAD
WHERE "snowpipe_loaded_at" < DATEADD('day', -2, CURRENT_TIMESTAMP());

CREATE TASK IF NOT EXISTS TASK_CLEANUP_KALSHI_MARKET_TRADES_LOAD
  WAREHOUSE = <task_warehouse>
  SCHEDULE = 'USING CRON 30 3 * * * America/Chicago'
  WHEN NOT SYSTEM$STREAM_HAS_DATA('PROD.RAW.STRM_RAW_KALSHI_MARKET_TRADES_LOAD')
AS
DELETE FROM RAW_KALSHI_MARKET_TRADES_LOAD
WHERE "snowpipe_loaded_at" < DATEADD('day', -2, CURRENT_TIMESTAMP());

ALTER TASK TASK_MERGE_KALSHI_MARKETS RESUME;
ALTER TASK TASK_MERGE_KALSHI_MARKET_ORDERBOOKS RESUME;
ALTER TASK TASK_MERGE_KALSHI_MARKET_TRADES RESUME;
ALTER TASK TASK_CLEANUP_KALSHI_MARKETS_LOAD RESUME;
ALTER TASK TASK_CLEANUP_KALSHI_MARKET_ORDERBOOKS_LOAD RESUME;
ALTER TASK TASK_CLEANUP_KALSHI_MARKET_TRADES_LOAD RESUME;

SHOW PIPES LIKE 'PIPE_KALSHI_MARKETS';
SHOW PIPES LIKE 'PIPE_KALSHI_MARKET_ORDERBOOKS';
SHOW PIPES LIKE 'PIPE_KALSHI_MARKET_TRADES';

-- Use after S3 notifications are configured to queue recent files that landed
-- before the notifications existed. For files older than 7 days, run COPY INTO
-- manually from STG_KALSHI_MARKETS, STG_KALSHI_MARKET_ORDERBOOKS, or
-- STG_KALSHI_MARKET_TRADES.
-- ALTER PIPE PIPE_KALSHI_MARKETS REFRESH;
-- ALTER PIPE PIPE_KALSHI_MARKET_ORDERBOOKS REFRESH;
-- ALTER PIPE PIPE_KALSHI_MARKET_TRADES REFRESH;
