-- Kalshi Events and Series Snowpipe ingestion.
--
-- This file keeps the final RAW table names used by dbt:
--   - RAW_EVENTS, keyed by "event_ticker"
--   - RAW_SERIES, keyed by "ticker"
--
-- Snowpipe appends JSONL rows into transient load tables. Append-only streams
-- expose newly loaded rows to merge tasks, and low-frequency cleanup tasks
-- remove old load rows only when the streams have no backlog.
--
-- Execution order:
-- 1. Apply Terraform and confirm output snowflake_s3_read_role_arn already
--    matches the role trusted by Snowflake.
-- 2. Replace <task_warehouse> with the Snowflake warehouse that should run
--    the merge and cleanup tasks.
-- 3. Run the storage integration ALTER so the existing S3_MLB_TEAMS_INT
--    integration can read the Kalshi prefixes without introducing a second
--    Snowflake external ID/IAM trust path.
-- 4. Run the file format, stages, load/final tables, pipes, streams, and tasks.
-- 5. Run SHOW PIPES and wire each notification_channel ARN into S3
--    ObjectCreated notifications:
--      - raw/kalshi/events/ + .jsonl -> PIPE_KALSHI_EVENTS
--      - raw/kalshi/series/ + .jsonl -> PIPE_KALSHI_SERIES

USE DATABASE PROD;
USE SCHEMA RAW;

ALTER STORAGE INTEGRATION S3_MLB_TEAMS_INT
  SET STORAGE_ALLOWED_LOCATIONS = (
    's3://snowflake-kalshi-project/raw/mlb/teams/',
    's3://snowflake-kalshi-project/raw/kalshi/events/',
    's3://snowflake-kalshi-project/raw/kalshi/series/'
  );

CREATE FILE FORMAT IF NOT EXISTS FF_KALSHI_JSONL
  TYPE = JSON
  COMPRESSION = AUTO
  MULTI_LINE = FALSE;

CREATE STAGE IF NOT EXISTS STG_KALSHI_EVENTS
  URL = 's3://snowflake-kalshi-project/raw/kalshi/events/'
  STORAGE_INTEGRATION = S3_MLB_TEAMS_INT
  FILE_FORMAT = (FORMAT_NAME = FF_KALSHI_JSONL);

CREATE STAGE IF NOT EXISTS STG_KALSHI_SERIES
  URL = 's3://snowflake-kalshi-project/raw/kalshi/series/'
  STORAGE_INTEGRATION = S3_MLB_TEAMS_INT
  FILE_FORMAT = (FORMAT_NAME = FF_KALSHI_JSONL);

CREATE TRANSIENT TABLE IF NOT EXISTS RAW_KALSHI_EVENTS_LOAD (
  "event_ticker" VARCHAR,
  "series_ticker" VARCHAR,
  "category" VARCHAR,
  "title" VARCHAR,
  "sub_title" VARCHAR,
  "available_on_brokers" BOOLEAN,
  "mutually_exclusive" BOOLEAN,
  "collateral_return_type" VARCHAR,
  "last_updated_ts" VARCHAR,
  "product_metadata" VARIANT,
  "ingested_at" TIMESTAMP_NTZ,
  "raw_payload" VARIANT,
  "source_file" VARCHAR,
  "source_row_number" NUMBER,
  "snowpipe_loaded_at" TIMESTAMP_NTZ
)
DATA_RETENTION_TIME_IN_DAYS = 1;

CREATE TRANSIENT TABLE IF NOT EXISTS RAW_KALSHI_SERIES_LOAD (
  "ticker" VARCHAR,
  "category" VARCHAR,
  "title" VARCHAR,
  "tags" VARIANT,
  "frequency" VARCHAR,
  "fee_multiplier" NUMBER,
  "fee_type" VARCHAR,
  "last_updated_ts" VARCHAR,
  "ingested_at" TIMESTAMP_NTZ,
  "raw_payload" VARIANT,
  "source_file" VARCHAR,
  "source_row_number" NUMBER,
  "snowpipe_loaded_at" TIMESTAMP_NTZ
)
DATA_RETENTION_TIME_IN_DAYS = 1;

CREATE TABLE IF NOT EXISTS RAW_EVENTS (
  "event_ticker" VARCHAR,
  "series_ticker" VARCHAR,
  "category" VARCHAR,
  "title" VARCHAR,
  "sub_title" VARCHAR,
  "available_on_brokers" BOOLEAN,
  "mutually_exclusive" BOOLEAN,
  "collateral_return_type" VARCHAR,
  "last_updated_ts" VARCHAR,
  "product_metadata" VARIANT,
  "ingested_at" TIMESTAMP_NTZ,
  "raw_payload" VARIANT,
  "source_file" VARCHAR,
  "source_row_number" NUMBER,
  "snowpipe_loaded_at" TIMESTAMP_NTZ,
  PRIMARY KEY ("event_ticker")
);

ALTER TABLE RAW_EVENTS ADD COLUMN IF NOT EXISTS "ingested_at" TIMESTAMP_NTZ;
ALTER TABLE RAW_EVENTS ADD COLUMN IF NOT EXISTS "event_ticker" VARCHAR;
ALTER TABLE RAW_EVENTS ADD COLUMN IF NOT EXISTS "series_ticker" VARCHAR;
ALTER TABLE RAW_EVENTS ADD COLUMN IF NOT EXISTS "category" VARCHAR;
ALTER TABLE RAW_EVENTS ADD COLUMN IF NOT EXISTS "title" VARCHAR;
ALTER TABLE RAW_EVENTS ADD COLUMN IF NOT EXISTS "sub_title" VARCHAR;
ALTER TABLE RAW_EVENTS ADD COLUMN IF NOT EXISTS "available_on_brokers" BOOLEAN;
ALTER TABLE RAW_EVENTS ADD COLUMN IF NOT EXISTS "mutually_exclusive" BOOLEAN;
ALTER TABLE RAW_EVENTS ADD COLUMN IF NOT EXISTS "collateral_return_type" VARCHAR;
ALTER TABLE RAW_EVENTS ADD COLUMN IF NOT EXISTS "last_updated_ts" VARCHAR;
ALTER TABLE RAW_EVENTS ADD COLUMN IF NOT EXISTS "product_metadata" VARIANT;
ALTER TABLE RAW_EVENTS ADD COLUMN IF NOT EXISTS "raw_payload" VARIANT;
ALTER TABLE RAW_EVENTS ADD COLUMN IF NOT EXISTS "source_file" VARCHAR;
ALTER TABLE RAW_EVENTS ADD COLUMN IF NOT EXISTS "source_row_number" NUMBER;
ALTER TABLE RAW_EVENTS ADD COLUMN IF NOT EXISTS "snowpipe_loaded_at" TIMESTAMP_NTZ;

CREATE TABLE IF NOT EXISTS RAW_SERIES (
  "ticker" VARCHAR,
  "category" VARCHAR,
  "title" VARCHAR,
  "tags" VARIANT,
  "frequency" VARCHAR,
  "fee_multiplier" NUMBER,
  "fee_type" VARCHAR,
  "last_updated_ts" VARCHAR,
  "ingested_at" TIMESTAMP_NTZ,
  "raw_payload" VARIANT,
  "source_file" VARCHAR,
  "source_row_number" NUMBER,
  "snowpipe_loaded_at" TIMESTAMP_NTZ,
  PRIMARY KEY ("ticker")
);

ALTER TABLE RAW_SERIES ADD COLUMN IF NOT EXISTS "ingested_at" TIMESTAMP_NTZ;
ALTER TABLE RAW_SERIES ADD COLUMN IF NOT EXISTS "ticker" VARCHAR;
ALTER TABLE RAW_SERIES ADD COLUMN IF NOT EXISTS "category" VARCHAR;
ALTER TABLE RAW_SERIES ADD COLUMN IF NOT EXISTS "title" VARCHAR;
ALTER TABLE RAW_SERIES ADD COLUMN IF NOT EXISTS "tags" VARIANT;
ALTER TABLE RAW_SERIES ADD COLUMN IF NOT EXISTS "frequency" VARCHAR;
ALTER TABLE RAW_SERIES ADD COLUMN IF NOT EXISTS "fee_multiplier" NUMBER;
ALTER TABLE RAW_SERIES ADD COLUMN IF NOT EXISTS "fee_type" VARCHAR;
ALTER TABLE RAW_SERIES ADD COLUMN IF NOT EXISTS "last_updated_ts" VARCHAR;
ALTER TABLE RAW_SERIES ADD COLUMN IF NOT EXISTS "raw_payload" VARIANT;
ALTER TABLE RAW_SERIES ADD COLUMN IF NOT EXISTS "source_file" VARCHAR;
ALTER TABLE RAW_SERIES ADD COLUMN IF NOT EXISTS "source_row_number" NUMBER;
ALTER TABLE RAW_SERIES ADD COLUMN IF NOT EXISTS "snowpipe_loaded_at" TIMESTAMP_NTZ;

CREATE PIPE IF NOT EXISTS PIPE_KALSHI_EVENTS
  AUTO_INGEST = TRUE
AS
COPY INTO RAW_KALSHI_EVENTS_LOAD (
  "event_ticker",
  "series_ticker",
  "category",
  "title",
  "sub_title",
  "available_on_brokers",
  "mutually_exclusive",
  "collateral_return_type",
  "last_updated_ts",
  "product_metadata",
  "ingested_at",
  "raw_payload",
  "source_file",
  "source_row_number",
  "snowpipe_loaded_at"
)
FROM (
  SELECT
    $1:event_ticker::VARCHAR,
    $1:series_ticker::VARCHAR,
    $1:category::VARCHAR,
    $1:title::VARCHAR,
    $1:sub_title::VARCHAR,
    $1:available_on_brokers::BOOLEAN,
    $1:mutually_exclusive::BOOLEAN,
    $1:collateral_return_type::VARCHAR,
    $1:last_updated_ts::VARCHAR,
    $1:product_metadata::VARIANT,
    TRY_TO_TIMESTAMP_NTZ($1:ingested_at::VARCHAR),
    COALESCE($1:raw_payload, $1)::VARIANT,
    METADATA$FILENAME,
    METADATA$FILE_ROW_NUMBER,
    CAST(METADATA$START_SCAN_TIME AS TIMESTAMP_NTZ)
  FROM @STG_KALSHI_EVENTS
)
PATTERN = '.*[.]jsonl';

CREATE PIPE IF NOT EXISTS PIPE_KALSHI_SERIES
  AUTO_INGEST = TRUE
AS
COPY INTO RAW_KALSHI_SERIES_LOAD (
  "ticker",
  "category",
  "title",
  "tags",
  "frequency",
  "fee_multiplier",
  "fee_type",
  "last_updated_ts",
  "ingested_at",
  "raw_payload",
  "source_file",
  "source_row_number",
  "snowpipe_loaded_at"
)
FROM (
  SELECT
    $1:ticker::VARCHAR,
    $1:category::VARCHAR,
    $1:title::VARCHAR,
    $1:tags::VARIANT,
    $1:frequency::VARCHAR,
    TRY_TO_NUMBER($1:fee_multiplier::VARCHAR),
    $1:fee_type::VARCHAR,
    $1:last_updated_ts::VARCHAR,
    TRY_TO_TIMESTAMP_NTZ($1:ingested_at::VARCHAR),
    COALESCE($1:raw_payload, $1)::VARIANT,
    METADATA$FILENAME,
    METADATA$FILE_ROW_NUMBER,
    CAST(METADATA$START_SCAN_TIME AS TIMESTAMP_NTZ)
  FROM @STG_KALSHI_SERIES
)
PATTERN = '.*[.]jsonl';

CREATE STREAM IF NOT EXISTS STRM_RAW_KALSHI_EVENTS_LOAD
  ON TABLE RAW_KALSHI_EVENTS_LOAD
  APPEND_ONLY = TRUE;

CREATE STREAM IF NOT EXISTS STRM_RAW_KALSHI_SERIES_LOAD
  ON TABLE RAW_KALSHI_SERIES_LOAD
  APPEND_ONLY = TRUE;

CREATE TASK IF NOT EXISTS TASK_MERGE_KALSHI_EVENTS
  WAREHOUSE = <task_warehouse>
  WHEN SYSTEM$STREAM_HAS_DATA('PROD.RAW.STRM_RAW_KALSHI_EVENTS_LOAD')
AS
MERGE INTO RAW_EVENTS AS target
USING (
  WITH ranked AS (
    SELECT
      "event_ticker",
      "series_ticker",
      "category",
      "title",
      "sub_title",
      "available_on_brokers",
      "mutually_exclusive",
      "collateral_return_type",
      "last_updated_ts",
      "product_metadata",
      "ingested_at",
      "raw_payload",
      "source_file",
      "source_row_number",
      "snowpipe_loaded_at",
      ROW_NUMBER() OVER (
        PARTITION BY "event_ticker"
        ORDER BY
          "ingested_at" DESC NULLS LAST,
          "snowpipe_loaded_at" DESC NULLS LAST,
          "source_file" DESC,
          "source_row_number" DESC
      ) AS row_rank
    FROM STRM_RAW_KALSHI_EVENTS_LOAD
    WHERE METADATA$ACTION = 'INSERT'
      AND "event_ticker" IS NOT NULL
  )
  SELECT
    "event_ticker",
    "series_ticker",
    "category",
    "title",
    "sub_title",
    "available_on_brokers",
    "mutually_exclusive",
    "collateral_return_type",
    "last_updated_ts",
    "product_metadata",
    "ingested_at",
    "raw_payload",
    "source_file",
    "source_row_number",
    "snowpipe_loaded_at"
  FROM ranked
  WHERE row_rank = 1
) AS source
ON target."event_ticker" = source."event_ticker"
WHEN MATCHED THEN UPDATE SET
  target."series_ticker" = source."series_ticker",
  target."category" = source."category",
  target."title" = source."title",
  target."sub_title" = source."sub_title",
  target."available_on_brokers" = source."available_on_brokers",
  target."mutually_exclusive" = source."mutually_exclusive",
  target."collateral_return_type" = source."collateral_return_type",
  target."last_updated_ts" = source."last_updated_ts",
  target."product_metadata" = source."product_metadata",
  target."ingested_at" = source."ingested_at",
  target."raw_payload" = source."raw_payload",
  target."source_file" = source."source_file",
  target."source_row_number" = source."source_row_number",
  target."snowpipe_loaded_at" = source."snowpipe_loaded_at"
WHEN NOT MATCHED THEN INSERT (
  "event_ticker",
  "series_ticker",
  "category",
  "title",
  "sub_title",
  "available_on_brokers",
  "mutually_exclusive",
  "collateral_return_type",
  "last_updated_ts",
  "product_metadata",
  "ingested_at",
  "raw_payload",
  "source_file",
  "source_row_number",
  "snowpipe_loaded_at"
) VALUES (
  source."event_ticker",
  source."series_ticker",
  source."category",
  source."title",
  source."sub_title",
  source."available_on_brokers",
  source."mutually_exclusive",
  source."collateral_return_type",
  source."last_updated_ts",
  source."product_metadata",
  source."ingested_at",
  source."raw_payload",
  source."source_file",
  source."source_row_number",
  source."snowpipe_loaded_at"
);

CREATE TASK IF NOT EXISTS TASK_MERGE_KALSHI_SERIES
  WAREHOUSE = <task_warehouse>
  WHEN SYSTEM$STREAM_HAS_DATA('PROD.RAW.STRM_RAW_KALSHI_SERIES_LOAD')
AS
MERGE INTO RAW_SERIES AS target
USING (
  WITH ranked AS (
    SELECT
      "ticker",
      "category",
      "title",
      "tags",
      "frequency",
      "fee_multiplier",
      "fee_type",
      "last_updated_ts",
      "ingested_at",
      "raw_payload",
      "source_file",
      "source_row_number",
      "snowpipe_loaded_at",
      ROW_NUMBER() OVER (
        PARTITION BY "ticker"
        ORDER BY
          "ingested_at" DESC NULLS LAST,
          "snowpipe_loaded_at" DESC NULLS LAST,
          "source_file" DESC,
          "source_row_number" DESC
      ) AS row_rank
    FROM STRM_RAW_KALSHI_SERIES_LOAD
    WHERE METADATA$ACTION = 'INSERT'
      AND "ticker" IS NOT NULL
  )
  SELECT
    "ticker",
    "category",
    "title",
    "tags",
    "frequency",
    "fee_multiplier",
    "fee_type",
    "last_updated_ts",
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
  target."category" = source."category",
  target."title" = source."title",
  target."tags" = source."tags",
  target."frequency" = source."frequency",
  target."fee_multiplier" = source."fee_multiplier",
  target."fee_type" = source."fee_type",
  target."last_updated_ts" = source."last_updated_ts",
  target."ingested_at" = source."ingested_at",
  target."raw_payload" = source."raw_payload",
  target."source_file" = source."source_file",
  target."source_row_number" = source."source_row_number",
  target."snowpipe_loaded_at" = source."snowpipe_loaded_at"
WHEN NOT MATCHED THEN INSERT (
  "ticker",
  "category",
  "title",
  "tags",
  "frequency",
  "fee_multiplier",
  "fee_type",
  "last_updated_ts",
  "ingested_at",
  "raw_payload",
  "source_file",
  "source_row_number",
  "snowpipe_loaded_at"
) VALUES (
  source."ticker",
  source."category",
  source."title",
  source."tags",
  source."frequency",
  source."fee_multiplier",
  source."fee_type",
  source."last_updated_ts",
  source."ingested_at",
  source."raw_payload",
  source."source_file",
  source."source_row_number",
  source."snowpipe_loaded_at"
);

CREATE TASK IF NOT EXISTS TASK_CLEANUP_KALSHI_EVENTS_LOAD
  WAREHOUSE = <task_warehouse>
  SCHEDULE = 'USING CRON 30 2 * * * America/Chicago'
  WHEN NOT SYSTEM$STREAM_HAS_DATA('PROD.RAW.STRM_RAW_KALSHI_EVENTS_LOAD')
AS
DELETE FROM RAW_KALSHI_EVENTS_LOAD
WHERE "snowpipe_loaded_at" < DATEADD('day', -2, CURRENT_TIMESTAMP());

CREATE TASK IF NOT EXISTS TASK_CLEANUP_KALSHI_SERIES_LOAD
  WAREHOUSE = <task_warehouse>
  SCHEDULE = 'USING CRON 45 2 * * * America/Chicago'
  WHEN NOT SYSTEM$STREAM_HAS_DATA('PROD.RAW.STRM_RAW_KALSHI_SERIES_LOAD')
AS
DELETE FROM RAW_KALSHI_SERIES_LOAD
WHERE "snowpipe_loaded_at" < DATEADD('day', -2, CURRENT_TIMESTAMP());

ALTER TASK TASK_MERGE_KALSHI_EVENTS RESUME;
ALTER TASK TASK_MERGE_KALSHI_SERIES RESUME;
ALTER TASK TASK_CLEANUP_KALSHI_EVENTS_LOAD RESUME;
ALTER TASK TASK_CLEANUP_KALSHI_SERIES_LOAD RESUME;

SHOW PIPES LIKE 'PIPE_KALSHI_EVENTS';
SHOW PIPES LIKE 'PIPE_KALSHI_SERIES';

-- Use after S3 notifications are configured to queue recent files that landed
-- before the notifications existed. For files older than 7 days, run COPY INTO
-- manually from STG_KALSHI_EVENTS or STG_KALSHI_SERIES.
-- ALTER PIPE PIPE_KALSHI_EVENTS REFRESH;
-- ALTER PIPE PIPE_KALSHI_SERIES REFRESH;
