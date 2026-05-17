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

1. Deploy or update the Kalshi Events and Series Lambdas, schedules, and shared
   infrastructure from PowerShell:

   ```powershell
   .\scripts\deploy_kalshi_lambdas.ps1 `
     -Profile ggarrido `
     -Region us-east-2
   ```

   The script builds and pushes the Lambda image, applies Terraform, and smoke
   invokes both Kalshi Lambdas unless `-SkipInvoke`, `-SkipEventsInvoke`, or
   `-SkipSeriesInvoke` is supplied. For scheduler-only changes after the image
   is already deployed, use:

   ```powershell
   .\scripts\deploy_ingestion_schedulers.ps1 -Profile ggarrido -Region us-east-2
   ```

2. Confirm Terraform has been applied and the Snowflake S3 read role can read
   the Kalshi landing prefixes:

   ```powershell
   terraform -chdir=infra/terraform output -raw snowflake_s3_read_role_arn
   ```

3. Open `infra/snowflake/kalshi_events_series_snowpipe.sql` and replace
   `<task_warehouse>` with the Snowflake warehouse that should run the merge and
   cleanup tasks.

4. Run the SQL file in Snowflake with a role that can alter the existing
   `S3_MLB_TEAMS_INT` storage integration and create objects in `PROD.RAW`.

   The SQL reuses `S3_MLB_TEAMS_INT` intentionally. Reusing the existing
   integration keeps the already-configured Snowflake external ID and AWS IAM
   trust path intact while expanding the allowed S3 locations to include the
   Kalshi Events and Series prefixes.

5. Run:

   ```sql
   SHOW PIPES LIKE 'PIPE_KALSHI_EVENTS';
   SHOW PIPES LIKE 'PIPE_KALSHI_SERIES';
   ```

   Copy each `notification_channel` ARN into S3 `ObjectCreated` notifications:

   | Pipe | Prefix | Suffix |
   | --- | --- | --- |
   | `PIPE_KALSHI_EVENTS` | `raw/kalshi/events/` | `.jsonl` |
   | `PIPE_KALSHI_SERIES` | `raw/kalshi/series/` | `.jsonl` |

6. If files landed before notifications existed, refresh the pipes:

   ```sql
   ALTER PIPE PROD.RAW.PIPE_KALSHI_EVENTS REFRESH;
   ALTER PIPE PROD.RAW.PIPE_KALSHI_SERIES REFRESH;
   ```

## Manual Smoke Tests

These manual smoke tests require AWS credentials, deployed Lambda functions, and
Kalshi credentials configured through AWS Secrets Manager. Keep them separate
from CI-safe tests.

Invoke Events with the conservative MLB scope:

```powershell
$Region = "us-east-2"
$EventsFunctionName = terraform -chdir=infra/terraform output -raw kalshi_events_lambda_function_name

aws lambda invoke `
  --function-name $EventsFunctionName `
  --payload '{"series_tickers":["KXMLBSPREAD","KXMLBTOTAL","KXMLBGAME"],"status":"open"}' `
  --cli-binary-format raw-in-base64-out `
  --region $Region `
  kalshi-events-response.json

Get-Content kalshi-events-response.json
```

The response should include a positive `row_count` when matching Events are
available and an `s3_uri` under `raw/kalshi/events/`.

Invoke Series with the conservative tag scope:

```powershell
$Region = "us-east-2"
$SeriesFunctionName = terraform -chdir=infra/terraform output -raw kalshi_series_lambda_function_name

aws lambda invoke `
  --function-name $SeriesFunctionName `
  --payload '{"tags":["BaseBall"]}' `
  --cli-binary-format raw-in-base64-out `
  --region $Region `
  kalshi-series-response.json

Get-Content kalshi-series-response.json
```

The response should include a positive `row_count` and an `s3_uri` under
`raw/kalshi/series/`.

## Validation SQL

Run these checks after the Lambda smoke invoke or scheduled run has written S3
files and the Snowpipe notifications have had time to fire.

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

## dbt Staging Contract

The final `RAW_EVENTS` and `RAW_SERIES` tables remain the only dbt sources for
Kalshi Events and Series. The transient load tables are Snowpipe inboxes and
must not be referenced by dbt models.

| Staging model | Raw table | Raw columns projected |
| --- | --- | --- |
| `stg_kalshi_events` | `RAW_EVENTS` | `event_ticker`, `series_ticker`, `category`, `title`, `sub_title`, `available_on_brokers`, `mutually_exclusive`, `collateral_return_type`, `last_updated_ts`, `product_metadata` |
| `stg_kalshi_series` | `RAW_SERIES` | `ticker`, `category`, `title`, `tags`, `frequency`, `fee_multiplier`, `fee_type`, `last_updated_ts` |

The S3/Snowpipe path adds audit columns to both final raw tables:
`ingested_at`, `raw_payload`, `source_file`, `source_row_number`, and
`snowpipe_loaded_at`. Those columns are retained on the raw sources for load
validation and drift inspection, but the staging models do not currently project
them into the analytics contract.

After sample Events and Series files have landed and the merge tasks have run,
validate dbt with:

```powershell
cd dbt
$env:DBT_PROFILES_DIR = (Get-Location).Path
dbt deps
dbt parse
dbt compile --select stg_kalshi_events stg_kalshi_series
dbt build --select stg_kalshi_series stg_kalshi_events
```

## CI-Safe Tests

These tests do not require live AWS or Snowflake credentials and should remain
green in pull requests:

```powershell
C:\Users\gabri\anaconda3\Scripts\conda.exe run -n snowflake-kalshi python -m unittest discover -s tests -v

cd dbt
Copy-Item profiles.yml.example profiles.yml
C:\Users\gabri\anaconda3\Scripts\conda.exe run -n snowflake-kalshi dbt deps
$env:SNOWFLAKE_ACCOUNT = "ci"
$env:SNOWFLAKE_USER = "ci"
$env:SNOWFLAKE_WAREHOUSE = "ci"
$env:SNOWFLAKE_PRIVATE_KEY_PATH = "NUL"
C:\Users\gabri\anaconda3\Scripts\conda.exe run -n snowflake-kalshi dbt parse --profiles-dir .
```

## Cleanup Behavior

The cleanup tasks run daily after 2 AM Central and delete load-table rows older
than two days only when the corresponding append-only stream reports no backlog.
This keeps Snowpipe inbox tables small without truncating them or deleting rows
before the merge tasks have consumed the stream.

## Cost Controls

This path intentionally differs from the MLB Teams append-only pattern because
Kalshi Events and Series change more often than static team metadata.

- EventBridge schedules default to hourly and can be paused with
  `kalshi_events_schedule_state = "DISABLED"` or
  `kalshi_series_schedule_state = "DISABLED"`.
- Events are scoped by default to `KXMLBSPREAD`, `KXMLBTOTAL`, and `KXMLBGAME`
  with `status = "open"` instead of crawling every historical event.
- Series are scoped by default to rows tagged `BaseBall` instead of every
  Kalshi series.
- Snowpipe loads append-only files into transient inbox tables with one day of
  retention, then stream-triggered tasks merge only the latest row per stable
  key into `RAW_EVENTS` and `RAW_SERIES`.
- Cleanup tasks remove old load-table rows only after the matching stream has no
  backlog, keeping storage small without losing unmerged rows.
