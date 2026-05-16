# Kalshi Events And Series Snowpipe Runbook

Kalshi Events and Series are high-change current-state entities. Unlike the MLB
Teams reference-data path, Snowpipe lands each JSONL file into transient inbox
tables first. Streams and tasks then merge the latest row per stable key into
the final RAW tables that dbt already reads.

## Data Flow

```text
Kalshi API -> Lambda -> S3 JSON Lines -> Snowpipe -> transient load tables
  -> append-only streams -> merge tasks -> RAW_EVENTS and RAW_SERIES -> dbt
```

The Lambda schedules write newline-delimited JSON under:

```text
s3://snowflake-kalshi-project/raw/kalshi/events/ingested_date=YYYY-MM-DD/kalshi_events_*.jsonl
s3://snowflake-kalshi-project/raw/kalshi/series/ingested_date=YYYY-MM-DD/kalshi_series_*.jsonl
```

Snowpipe loads those files into:

- `RAW_KALSHI_EVENTS_LOAD`
- `RAW_KALSHI_SERIES_LOAD`

The final current-state tables remain:

- `RAW_EVENTS`, keyed by `"event_ticker"`
- `RAW_SERIES`, keyed by `"ticker"`

## Setup Steps

1. Confirm Terraform has been applied and the Snowflake S3 read role can read
   the Kalshi landing prefixes:

   ```powershell
   terraform -chdir=infra/terraform output -raw snowflake_s3_read_role_arn
   ```

2. Open `infra/snowflake/kalshi_events_series_snowpipe.sql` and replace
   `<task_warehouse>` with the Snowflake warehouse that should run the merge and
   cleanup tasks.

3. Run the SQL file in Snowflake with a role that can alter the existing
   `S3_MLB_TEAMS_INT` storage integration and create objects in `PROD.RAW`.

   The SQL reuses `S3_MLB_TEAMS_INT` intentionally. Reusing the existing
   integration keeps the already-configured Snowflake external ID and AWS IAM
   trust path intact while expanding the allowed S3 locations to include the
   Kalshi Events and Series prefixes.

4. Run:

   ```sql
   SHOW PIPES LIKE 'PIPE_KALSHI_EVENTS';
   SHOW PIPES LIKE 'PIPE_KALSHI_SERIES';
   ```

   Copy each `notification_channel` ARN into S3 `ObjectCreated` notifications:

   | Pipe | Prefix | Suffix |
   | --- | --- | --- |
   | `PIPE_KALSHI_EVENTS` | `raw/kalshi/events/` | `.jsonl` |
   | `PIPE_KALSHI_SERIES` | `raw/kalshi/series/` | `.jsonl` |

5. If files landed before notifications existed, refresh the pipes:

   ```sql
   ALTER PIPE PROD.RAW.PIPE_KALSHI_EVENTS REFRESH;
   ALTER PIPE PROD.RAW.PIPE_KALSHI_SERIES REFRESH;
   ```

## Validation SQL

Check pipe status:

```sql
SELECT SYSTEM$PIPE_STATUS('PROD.RAW.PIPE_KALSHI_EVENTS') AS events_pipe_status;
SELECT SYSTEM$PIPE_STATUS('PROD.RAW.PIPE_KALSHI_SERIES') AS series_pipe_status;
```

Check recent Snowpipe loads:

```sql
SELECT *
FROM TABLE(PROD.INFORMATION_SCHEMA.COPY_HISTORY(
  TABLE_NAME => 'RAW_KALSHI_EVENTS_LOAD',
  START_TIME => DATEADD('hour', -2, CURRENT_TIMESTAMP()),
  PIPE_NAME => 'PIPE_KALSHI_EVENTS'
));

SELECT *
FROM TABLE(PROD.INFORMATION_SCHEMA.COPY_HISTORY(
  TABLE_NAME => 'RAW_KALSHI_SERIES_LOAD',
  START_TIME => DATEADD('hour', -2, CURRENT_TIMESTAMP()),
  PIPE_NAME => 'PIPE_KALSHI_SERIES'
));
```

Check load-table and stream state:

```sql
SELECT COUNT(*) AS events_load_rows
FROM PROD.RAW.RAW_KALSHI_EVENTS_LOAD;

SELECT COUNT(*) AS series_load_rows
FROM PROD.RAW.RAW_KALSHI_SERIES_LOAD;

SELECT SYSTEM$STREAM_HAS_DATA('PROD.RAW.STRM_RAW_KALSHI_EVENTS_LOAD') AS events_stream_has_data;
SELECT SYSTEM$STREAM_HAS_DATA('PROD.RAW.STRM_RAW_KALSHI_SERIES_LOAD') AS series_stream_has_data;
```

Check task execution:

```sql
SELECT *
FROM TABLE(PROD.INFORMATION_SCHEMA.TASK_HISTORY(
  TASK_NAME => 'TASK_MERGE_KALSHI_EVENTS',
  SCHEDULED_TIME_RANGE_START => DATEADD('hour', -2, CURRENT_TIMESTAMP())
));

SELECT *
FROM TABLE(PROD.INFORMATION_SCHEMA.TASK_HISTORY(
  TASK_NAME => 'TASK_MERGE_KALSHI_SERIES',
  SCHEDULED_TIME_RANGE_START => DATEADD('hour', -2, CURRENT_TIMESTAMP())
));
```

Confirm final RAW row counts and key uniqueness:

```sql
SELECT COUNT(*) AS raw_events_rows
FROM PROD.RAW.RAW_EVENTS;

SELECT COUNT(*) AS raw_series_rows
FROM PROD.RAW.RAW_SERIES;

SELECT "event_ticker", COUNT(*) AS row_count
FROM PROD.RAW.RAW_EVENTS
GROUP BY "event_ticker"
HAVING COUNT(*) > 1;

SELECT "ticker", COUNT(*) AS row_count
FROM PROD.RAW.RAW_SERIES
GROUP BY "ticker"
HAVING COUNT(*) > 1;
```

The duplicate checks should return zero rows.

## Cleanup Behavior

The cleanup tasks run daily after 2 AM Central and delete load-table rows older
than two days only when the corresponding append-only stream reports no backlog.
This keeps Snowpipe inbox tables small without truncating them or deleting rows
before the merge tasks have consumed the stream.
