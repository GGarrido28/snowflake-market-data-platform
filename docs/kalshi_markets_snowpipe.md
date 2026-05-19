# Kalshi Markets Snowpipe Runbook

Kalshi Markets, market orderbook snapshots, and market trades are high-change
entities. The Lambda added under Issue #54 lands scoped JSONL files in S3. This
Snowpipe layer loads those files into transient inbox tables, then streams and
tasks merge the latest rows into the final RAW tables that dbt already reads.

## Data Flow

```text
Kalshi API -> Markets Lambda -> S3 JSON Lines -> Snowpipe -> transient load tables
  -> append-only streams -> merge tasks -> final RAW market tables -> dbt
```

The Lambda writes newline-delimited JSON under:

```text
s3://snowflake-kalshi-project/raw/kalshi/markets/ingested_date=YYYY-MM-DD/kalshi_markets_*.jsonl
s3://snowflake-kalshi-project/raw/kalshi/market_orderbooks/ingested_date=YYYY-MM-DD/kalshi_market_orderbooks_*.jsonl
s3://snowflake-kalshi-project/raw/kalshi/market_trades/ingested_date=YYYY-MM-DD/kalshi_market_trades_*.jsonl
```

Snowpipe loads those files into:

- `RAW_KALSHI_MARKETS_LOAD`
- `RAW_KALSHI_MARKET_ORDERBOOKS_LOAD`
- `RAW_KALSHI_MARKET_TRADES_LOAD`

The final current-state/fact tables remain:

- `RAW_MARKETS`, keyed by `"ticker"`
- `RAW_MARKET_ORDERBOOKS`, keyed by `"market_ticker"`
- `RAW_MARKET_TRADES`, keyed by `"trade_id"`

Empty market trade files from no-trade windows are valid zero-row files. They
should show in Snowpipe load history, create no placeholder rows, and leave
`RAW_MARKET_TRADES` unchanged.

## Operational Prerequisites

These steps require different credentials; keep the manual smoke checks out of
CI.

- AWS SSO/profile access for account `893072528957`, normally profile
  `ggarrido`, with Lambda, ECR, Terraform backend, S3, EventBridge Scheduler,
  and IAM permissions.
- Snowflake role access that can alter `S3_MLB_TEAMS_INT`, create objects in
  `PROD.RAW`, resume tasks, and run dbt against `PROD.RAW`, `PROD.STAGE`, and
  `PROD.KALSHI`.
- Kalshi API credentials already stored in AWS Secrets Manager and wired to the
  Kalshi Lambda environment by Terraform.
- Docker Desktop running when building/pushing the Lambda image.
- `terraform.tfvars` has all three market pipe notification channels set
  together after `SHOW PIPES` returns the Snowflake-managed SQS ARNs.

Use the repository `.env` or equivalent process environment for dbt:

```powershell
Get-Content ..\.env | ForEach-Object {
  if ($_.Trim() -and -not $_.Trim().StartsWith('#')) {
    $parts = $_ -split '=', 2
    [Environment]::SetEnvironmentVariable($parts[0], $parts[1], 'Process')
  }
}
```

## Operator Checklist

1. Deploy or update the Kalshi Lambda image and Terraform-managed Lambda
   resources.
2. Verify the EventBridge Scheduler entry exists and is intentionally enabled
   or disabled.
3. Run `infra/snowflake/kalshi_markets_snowpipe.sql` with
   `<task_warehouse>` replaced and resume the merge/cleanup tasks.
4. Copy the three market pipe `notification_channel` values into Terraform and
   apply the S3 bucket notification configuration.
5. Invoke a scoped manual smoke test or wait for the schedule.
6. Confirm S3 files, Snowpipe load history, stream/task state, final RAW rows,
   and targeted dbt build/test.

## Setup Steps

1. Deploy or update the Kalshi Markets Lambda from PowerShell:

   ```powershell
   .\scripts\deploy_kalshi_lambdas.ps1 `
     -Profile ggarrido `
     -Region us-east-2
   ```

   Issue #54 provides the required Lambda, IAM, S3 landing prefixes, and manual
   invoke output. Issue #55 provides bounded incremental trade watermarking.
   Issue #56 provides the conservative EventBridge schedule.

   For a plan-only deployment check that preserves the currently deployed image
   tag:

   ```powershell
   .\scripts\deploy_kalshi_lambdas.ps1 `
     -Profile ggarrido `
     -Region us-east-2 `
     -SkipBuild `
     -PlanOnly
   ```

   To apply only scheduler-related Terraform changes while preserving the
   deployed Lambda image tag:

   ```powershell
   .\scripts\deploy_ingestion_schedulers.ps1 `
     -Profile ggarrido `
     -Region us-east-2
   ```

2. Confirm Terraform has been applied and the Snowflake S3 read role can read
   the Kalshi market landing prefixes:

   ```powershell
   terraform -chdir=infra/terraform output -raw snowflake_s3_read_role_arn
   ```

3. Open `infra/snowflake/kalshi_markets_snowpipe.sql` and replace
   `<task_warehouse>` with the Snowflake warehouse that should run the merge and
   cleanup tasks.

4. Run the SQL file in Snowflake with a role that can alter the existing
   `S3_MLB_TEAMS_INT` storage integration and create objects in `PROD.RAW`.

   The SQL intentionally reuses `S3_MLB_TEAMS_INT` so the already-configured
   Snowflake external ID and AWS IAM trust path remains the single S3 read path.

5. Run:

   ```sql
   SHOW PIPES LIKE 'PIPE_KALSHI_MARKETS';
   SHOW PIPES LIKE 'PIPE_KALSHI_MARKET_ORDERBOOKS';
   SHOW PIPES LIKE 'PIPE_KALSHI_MARKET_TRADES';
   ```

   Copy each `notification_channel` ARN into Terraform-managed S3
   `ObjectCreated` notifications:

   | Pipe | Prefix | Suffix |
   | --- | --- | --- |
   | `PIPE_KALSHI_MARKETS` | `raw/kalshi/markets/` | `.jsonl` |
   | `PIPE_KALSHI_MARKET_ORDERBOOKS` | `raw/kalshi/market_orderbooks/` | `.jsonl` |
   | `PIPE_KALSHI_MARKET_TRADES` | `raw/kalshi/market_trades/` | `.jsonl` |

   The shared bucket notification Terraform workflow is documented in
   [`snowpipe_s3_notifications.md`](./snowpipe_s3_notifications.md). Configure
   the MLB Teams, Kalshi Events, Kalshi Series, and Kalshi market-related pipe
   notification channels together because Terraform owns the bucket's full
   notification configuration.

   The market-specific Terraform variables are:

   ```hcl
   kalshi_markets_pipe_notification_channel           = "arn:aws:sqs:..."
   kalshi_market_orderbooks_pipe_notification_channel = "arn:aws:sqs:..."
   kalshi_market_trades_pipe_notification_channel     = "arn:aws:sqs:..."
   ```

   After applying Terraform, verify S3 sees all three market event notification
   prefixes:

   ```powershell
   aws s3api get-bucket-notification-configuration `
     --bucket snowflake-kalshi-project `
     --profile ggarrido `
     --region us-east-2
   ```

6. If files landed before notifications existed, refresh the pipes:

   ```sql
   ALTER PIPE PROD.RAW.PIPE_KALSHI_MARKETS REFRESH;
   ALTER PIPE PROD.RAW.PIPE_KALSHI_MARKET_ORDERBOOKS REFRESH;
   ALTER PIPE PROD.RAW.PIPE_KALSHI_MARKET_TRADES REFRESH;
   ```

## Manual Smoke Tests

These checks require AWS credentials, deployed Lambda functions, and Kalshi
credentials configured through AWS Secrets Manager. Keep them separate from
CI-safe tests.

Manual smoke checks require AWS credentials and live Snowflake/Kalshi
configuration; do not wire them into pull-request CI.

Invoke a single market:

```powershell
$Region = "us-east-2"
$Profile = "ggarrido"
$MarketsFunctionName = terraform -chdir=infra/terraform output -raw kalshi_markets_lambda_function_name

aws lambda invoke `
  --function-name $MarketsFunctionName `
  --payload '{"market_ticker":"KXTEST","trade_fetch_mode":"incremental"}' `
  --cli-binary-format raw-in-base64-out `
  --region $Region `
  --profile $Profile `
  kalshi-markets-response.json

Get-Content kalshi-markets-response.json
```

The response should include `row_counts` and `writes` for `markets`,
`market_orderbooks`, and `market_trades`. The trade row count may be zero in a
quiet window; that is expected as long as the market and orderbook files land.

Invoke the query-file scope used by the schedule:

```powershell
aws lambda invoke `
  --function-name $MarketsFunctionName `
  --payload '{"event_query_file":"src/market_data_platform/queries/kalshi/markets_mlb_events.sql","trade_fetch_mode":"incremental"}' `
  --cli-binary-format raw-in-base64-out `
  --region $Region `
  --profile $Profile `
  kalshi-markets-query-response.json
```

Invoke an explicit event scope when validating one event without the query-file
Snowflake dependency:

```powershell
aws lambda invoke `
  --function-name $MarketsFunctionName `
  --payload '{"event_ticker":"KXMLBSPREAD-26MAY19","trade_fetch_mode":"incremental"}' `
  --cli-binary-format raw-in-base64-out `
  --region $Region `
  --profile $Profile `
  kalshi-markets-event-response.json
```

Run an explicit bounded backfill only when you intend to revisit historical
trades. Backfills do not advance the scheduled incremental watermark unless the
payload opts into that behavior in code.

```powershell
aws lambda invoke `
  --function-name $MarketsFunctionName `
  --payload '{"market_ticker":"KXTEST","trade_fetch_mode":"backfill","trade_start_ts":"2026-05-18T00:00:00Z","trade_end_ts":"2026-05-19T00:00:00Z"}' `
  --cli-binary-format raw-in-base64-out `
  --region $Region `
  --profile $Profile `
  kalshi-markets-backfill-response.json
```

Check the scheduler payload and state:

```powershell
$ScheduleName = terraform -chdir=infra/terraform output -raw kalshi_markets_schedule_name

aws scheduler get-schedule `
  --name $ScheduleName `
  --group-name default `
  --region $Region `
  --profile $Profile
```

The deployed schedule should use the bounded query-file scope unless
`kalshi_markets_market_ticker` or `kalshi_markets_event_ticker` is configured
for a narrower run.

## Validation SQL

Run these checks after the Lambda smoke invoke or scheduled run has written S3
files and the Snowpipe notifications have had time to fire.

Check S3 files first. The presence of a trades file with zero data rows is not
an error; confirm it reached S3 and Snowpipe load history.

```powershell
aws s3 ls s3://snowflake-kalshi-project/raw/kalshi/markets/ --recursive --human-readable --summarize --profile ggarrido --region us-east-2
aws s3 ls s3://snowflake-kalshi-project/raw/kalshi/market_orderbooks/ --recursive --human-readable --summarize --profile ggarrido --region us-east-2
aws s3 ls s3://snowflake-kalshi-project/raw/kalshi/market_trades/ --recursive --human-readable --summarize --profile ggarrido --region us-east-2
aws s3 ls s3://snowflake-kalshi-project/state/kalshi/market_trades/ --recursive --human-readable --summarize --profile ggarrido --region us-east-2
```

Check pipe status:

```sql
SELECT SYSTEM$PIPE_STATUS('PROD.RAW.PIPE_KALSHI_MARKETS') AS markets_pipe_status;
SELECT SYSTEM$PIPE_STATUS('PROD.RAW.PIPE_KALSHI_MARKET_ORDERBOOKS') AS orderbooks_pipe_status;
SELECT SYSTEM$PIPE_STATUS('PROD.RAW.PIPE_KALSHI_MARKET_TRADES') AS trades_pipe_status;
```

Check recent Snowpipe loads:

```sql
SELECT *
FROM TABLE(PROD.INFORMATION_SCHEMA.COPY_HISTORY(
  TABLE_NAME => 'RAW_KALSHI_MARKETS_LOAD',
  START_TIME => DATEADD('hour', -2, CURRENT_TIMESTAMP()),
  PIPE_NAME => 'PIPE_KALSHI_MARKETS'
));

SELECT *
FROM TABLE(PROD.INFORMATION_SCHEMA.COPY_HISTORY(
  TABLE_NAME => 'RAW_KALSHI_MARKET_ORDERBOOKS_LOAD',
  START_TIME => DATEADD('hour', -2, CURRENT_TIMESTAMP()),
  PIPE_NAME => 'PIPE_KALSHI_MARKET_ORDERBOOKS'
));

SELECT *
FROM TABLE(PROD.INFORMATION_SCHEMA.COPY_HISTORY(
  TABLE_NAME => 'RAW_KALSHI_MARKET_TRADES_LOAD',
  START_TIME => DATEADD('hour', -2, CURRENT_TIMESTAMP()),
  PIPE_NAME => 'PIPE_KALSHI_MARKET_TRADES'
));
```

Check load-table and stream state:

```sql
SELECT COUNT(*) AS markets_load_rows
FROM PROD.RAW.RAW_KALSHI_MARKETS_LOAD;

SELECT COUNT(*) AS orderbooks_load_rows
FROM PROD.RAW.RAW_KALSHI_MARKET_ORDERBOOKS_LOAD;

SELECT COUNT(*) AS trades_load_rows
FROM PROD.RAW.RAW_KALSHI_MARKET_TRADES_LOAD;

SELECT SYSTEM$STREAM_HAS_DATA('PROD.RAW.STRM_RAW_KALSHI_MARKETS_LOAD') AS markets_stream_has_data;
SELECT SYSTEM$STREAM_HAS_DATA('PROD.RAW.STRM_RAW_KALSHI_MARKET_ORDERBOOKS_LOAD') AS orderbooks_stream_has_data;
SELECT SYSTEM$STREAM_HAS_DATA('PROD.RAW.STRM_RAW_KALSHI_MARKET_TRADES_LOAD') AS trades_stream_has_data;
```

Check task execution:

```sql
SHOW TASKS LIKE 'TASK_%KALSHI%MARKET%';

SELECT *
FROM TABLE(PROD.INFORMATION_SCHEMA.TASK_HISTORY(
  TASK_NAME => 'TASK_MERGE_KALSHI_MARKETS',
  SCHEDULED_TIME_RANGE_START => DATEADD('hour', -2, CURRENT_TIMESTAMP())
));

SELECT *
FROM TABLE(PROD.INFORMATION_SCHEMA.TASK_HISTORY(
  TASK_NAME => 'TASK_MERGE_KALSHI_MARKET_ORDERBOOKS',
  SCHEDULED_TIME_RANGE_START => DATEADD('hour', -2, CURRENT_TIMESTAMP())
));

SELECT *
FROM TABLE(PROD.INFORMATION_SCHEMA.TASK_HISTORY(
  TASK_NAME => 'TASK_MERGE_KALSHI_MARKET_TRADES',
  SCHEDULED_TIME_RANGE_START => DATEADD('hour', -2, CURRENT_TIMESTAMP())
));
```

Confirm final RAW row counts and key uniqueness:

```sql
SELECT COUNT(*) AS raw_markets_rows, MAX("snowpipe_loaded_at") AS latest_load
FROM PROD.RAW.RAW_MARKETS;

SELECT COUNT(*) AS raw_orderbooks_rows, MAX("snowpipe_loaded_at") AS latest_load
FROM PROD.RAW.RAW_MARKET_ORDERBOOKS;

SELECT COUNT(*) AS raw_trades_rows, MAX("snowpipe_loaded_at") AS latest_load
FROM PROD.RAW.RAW_MARKET_TRADES;

SELECT "ticker", COUNT(*) AS row_count
FROM PROD.RAW.RAW_MARKETS
GROUP BY "ticker"
HAVING COUNT(*) > 1;

SELECT "market_ticker", COUNT(*) AS row_count
FROM PROD.RAW.RAW_MARKET_ORDERBOOKS
GROUP BY "market_ticker"
HAVING COUNT(*) > 1;

SELECT "trade_id", COUNT(*) AS row_count
FROM PROD.RAW.RAW_MARKET_TRADES
GROUP BY "trade_id"
HAVING COUNT(*) > 1;
```

The duplicate checks should return zero rows.

For zero-row market trade files, validate that Snowpipe processed the file and
that the final trades table did not receive a null-key row:

```sql
SELECT COUNT(*) AS null_trade_id_rows
FROM PROD.RAW.RAW_MARKET_TRADES
WHERE "trade_id" IS NULL;
```

The result should be zero.

## Expected Outcomes

| Layer | Success signal |
| --- | --- |
| Lambda | Response contains `row_counts` and S3 `writes` for `markets`, `market_orderbooks`, and `market_trades`. |
| S3 | New JSONL files appear under all three market prefixes; trade files may be zero-row. |
| Snowpipe | `COPY_HISTORY` shows loaded files for the corresponding load tables. |
| Streams/tasks | Streams drain after merge tasks run; task history shows successful runs. |
| Final RAW | Stable keys are unique and `"snowpipe_loaded_at"` is populated for automated rows. |
| dbt | Targeted market staging and mart `dbt build` completes with tests passing. |

## dbt Staging Contract

The final `RAW_MARKETS`, `RAW_MARKET_ORDERBOOKS`, and `RAW_MARKET_TRADES`
tables remain the only dbt sources for market analytics. The transient load
tables are Snowpipe inboxes and must not be referenced by dbt models.

| Staging model | Raw table | Stable key |
| --- | --- | --- |
| `stg_kalshi_markets` | `RAW_MARKETS` | `ticker` |
| `stg_kalshi_market_orderbooks` | `RAW_MARKET_ORDERBOOKS` | `market_ticker` |
| `stg_kalshi_market_trades` | `RAW_MARKET_TRADES` | `trade_id` |

The S3/Snowpipe path adds audit columns to all three final raw tables:
`ingested_at`, `raw_payload`, `source_file`, `source_row_number`, and
`snowpipe_loaded_at`. Those columns are retained on raw sources for validation
and drift inspection. Snowflake stores these as quoted lower-case identifiers,
so manual validation queries must reference `"snowpipe_loaded_at"`,
`"source_file"`, and `"source_row_number"` with double quotes. The staging
models keep their existing analytics contract.

Before running dbt, confirm automated Snowpipe rows reached the final raw
tables:

```sql
SELECT COUNT(*) AS rows_loaded, MAX("snowpipe_loaded_at") AS latest_load
FROM PROD.RAW.RAW_MARKETS;

SELECT COUNT(*) AS rows_loaded, MAX("snowpipe_loaded_at") AS latest_load
FROM PROD.RAW.RAW_MARKET_ORDERBOOKS;

SELECT COUNT(*) AS rows_loaded, MAX("snowpipe_loaded_at") AS latest_load
FROM PROD.RAW.RAW_MARKET_TRADES;
```

After sample market files have landed and the merge tasks have run, validate dbt
with:

```powershell
cd dbt
$env:DBT_PROFILES_DIR = (Get-Location).Path
dbt deps
dbt parse
dbt compile --select stg_kalshi_markets stg_kalshi_market_orderbooks stg_kalshi_market_trades fct_markets fct_market_orderbooks
dbt build --select stg_kalshi_markets stg_kalshi_market_orderbooks stg_kalshi_market_trades fct_markets fct_market_orderbooks
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

The cleanup tasks run daily after 3 AM Central and delete load-table rows older
than two days only when the corresponding append-only stream reports no backlog.
This keeps Snowpipe inbox tables small without truncating them or deleting rows
before the merge tasks have consumed the stream.

## Cost Controls

This path intentionally differs from the MLB Teams append-only pattern because
Kalshi markets, orderbooks, and trades change frequently and can become costly
when crawled broadly.

- Kalshi Markets schedules should stay at 30 minutes or slower unless cost and
  freshness have been validated.
- The scheduled scope is bounded by one exact market ticker, one event ticker,
  or the packaged MLB event-query SQL file. It does not crawl every market.
- Trade ingestion defaults to `incremental` with per-market watermark objects
  under `state/kalshi/market_trades/`.
- First runs are bounded to the latest 24 hours by default.
- Backfills are explicit and opt-in through `trade_fetch_mode = "backfill"` and
  start/end timestamps.
- Snowpipe loads append-only files into transient inbox tables with one day of
  retention, then stream-triggered tasks merge only the latest row per stable
  key into final RAW tables.
