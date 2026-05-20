# AWS Lambda Deployment

This repo deploys ingestion jobs as AWS Lambda container images backed by ECR. Terraform owns the AWS resources; Docker and the AWS CLI build, push, and invoke the image.

## Prerequisites

- AWS CLI authenticated to the target account.
- Docker Desktop or another Docker engine with `buildx`.
- Terraform `>= 1.10`.
- Existing S3 landing bucket: `snowflake-kalshi-project`.
- Terraform remote state bootstrapped as described in [`terraform_state.md`](./terraform_state.md).

The managed Lambdas write to:

```text
s3://snowflake-kalshi-project/raw/mlb/teams/
s3://snowflake-kalshi-project/raw/kalshi/events/
s3://snowflake-kalshi-project/raw/kalshi/series/
s3://snowflake-kalshi-project/raw/kalshi/markets/
s3://snowflake-kalshi-project/raw/kalshi/market_orderbooks/
s3://snowflake-kalshi-project/raw/kalshi/market_trades/
```

The Kalshi Markets Lambda also stores non-secret per-market trade watermark
state under `s3://snowflake-kalshi-project/state/kalshi/market_trades/`.

## Configure Terraform

Copy the example variables file. This project uses `us-east-2` for AWS resources:

```powershell
Copy-Item infra/terraform/terraform.tfvars.example infra/terraform/terraform.tfvars
```

Initialize Terraform:

```powershell
terraform -chdir=infra/terraform init
```

The MLB teams schedule is intentionally created in a disabled state because team metadata is low-change reference data. Override `mlb_teams_schedule_expression`, `mlb_teams_schedule_timezone`, or set `mlb_teams_schedule_state = "ENABLED"` in `terraform.tfvars` if you need recurring refreshes before applying.

Kalshi Events and Series schedules default to hourly and enabled. Kalshi
Markets defaults to every 30 minutes and enabled, offset at 15 and 45 minutes
past each hour so it does not start at the same minute as Events and Series.
When no exact market/event scope is set, the scheduled payload uses the packaged
MLB event-query SQL file at
`src/market_data_platform/queries/kalshi/markets_mlb_events.sql`.

```hcl
kalshi_events_schedule_expression = "cron(0 * * * ? *)"
kalshi_events_schedule_timezone   = "America/Chicago"
kalshi_events_schedule_state      = "ENABLED"
kalshi_series_schedule_expression = "cron(0 * * * ? *)"
kalshi_series_schedule_timezone   = "America/Chicago"
kalshi_series_schedule_state      = "ENABLED"
kalshi_markets_schedule_expression = "cron(15,45 * * * ? *)"
kalshi_markets_schedule_timezone   = "America/Chicago"
kalshi_markets_schedule_state      = "ENABLED"
```

Set any Kalshi schedule state to `DISABLED` in `terraform.tfvars` to pause scheduled ingestion without removing the schedule. Keep Events and Series hourly or slower, and keep Markets at 30 minutes or slower unless you have validated the cost/freshness tradeoff. Keep Markets offset from Events and Series to avoid stacking Kalshi requests on the hour. Configure Kalshi authentication with `kalshi_api_secret_arn` or `kalshi_api_secret_name`; Terraform passes the matching `KALSHI_SECRET_ARN` or `KALSHI_SECRET_NAME` environment variable and grants the Lambda roles read access to that secret reference. The SQL-driven Markets schedule also needs the `kalshi_markets_snowflake_*` settings so the Lambda can run the query that selects event tickers.

## Deploy With Script

The MLB Teams deploy path is:

```powershell
.\scripts\deploy_mlb_teams_lambda.ps1 -Profile ggarrido -Region us-east-2
```

The Kalshi Events and Series deploy path is:

```powershell
.\scripts\deploy_kalshi_lambdas.ps1 `
  -Profile ggarrido `
  -Region us-east-2
```

The scripts initialize Terraform, bootstrap ECR, log Docker into ECR, build and push the Lambda image, apply the full Terraform stack, and invoke smoke tests. Run them from PowerShell. The Kalshi script defaults Events to the MLB series tickers `KXMLBSPREAD`, `KXMLBTOTAL`, and `KXMLBGAME`, and defaults Series to rows whose tags contain `BaseBall`; override with `-EventsEventTicker`, `-EventsSeriesTicker`, `-EventsSeriesTickers`, `-SeriesTicker`, or `-SeriesTags` when needed.

## Deploy Scheduler Only

After the Lambda image has already been deployed, use the ingestion scheduler script to plan and apply Terraform without rebuilding or pushing a container image. It preserves the deployed image tag and manages Terraform scheduler changes, including the Kalshi Events, Series, and Markets schedules:

```powershell
.\scripts\deploy_ingestion_schedulers.ps1 -Profile ggarrido -Region us-east-2
```

The script reads the current `lambda_image_uri` from Terraform state and passes that image tag back into Terraform, so scheduler-only deploys do not accidentally change the Lambda image. After apply, it verifies the MLB Teams, Kalshi Events, Kalshi Series, and Kalshi Markets schedules. To preview without applying, run:

```powershell
.\scripts\deploy_ingestion_schedulers.ps1 -Profile ggarrido -Region us-east-2 -PlanOnly
```

Use `-AutoApprove` only when you want the script to apply the saved Terraform plan without an interactive confirmation.

If your SSO session has expired, refresh it first:

```powershell
aws sso login --profile ggarrido
```

## Manual Bootstrap ECR

The Lambda function cannot be created until an image exists in ECR. Create the ECR repository first:

```powershell
terraform -chdir=infra/terraform apply "-target=aws_ecr_repository.mlb_teams"
```

## Build And Push The Lambda Image

Use the current Git commit as the image tag so Terraform can detect future image changes:

```powershell
$Region = "us-east-2"
$ImageTag = git rev-parse --short HEAD
$RepositoryUrl = terraform -chdir=infra/terraform output -raw ecr_repository_url
$Registry = $RepositoryUrl.Split("/")[0]
$ImageUri = "${RepositoryUrl}:${ImageTag}"

$Password = (aws ecr get-login-password --region $Region --profile ggarrido).Trim()
$Password | docker login --username AWS --password-stdin $Registry

docker buildx build --platform linux/amd64 -f aws/docker/Dockerfile.lambda -t $ImageUri --push .
```

## Deploy Lambda Resources

Apply the full Terraform stack, passing the image tag you pushed:

```powershell
terraform -chdir=infra/terraform apply -var "lambda_image_tag=$ImageTag"
```

Terraform creates:

- ECR repository for the Lambda image.
- IAM execution roles with CloudWatch logs permissions.
- S3 write policies scoped to `snowflake-kalshi-project/raw/mlb/teams/*`, `snowflake-kalshi-project/raw/kalshi/events/*`, and `snowflake-kalshi-project/raw/kalshi/series/*`.
- The Kalshi Markets Lambda can also read/write its non-secret market trade watermark object under `snowflake-kalshi-project/state/kalshi/market_trades/*`.
- Optional Kalshi Secrets Manager read policy attached only to the Kalshi Lambda roles when `kalshi_api_secret_arn` or `kalshi_api_secret_name` is configured.
- IAM read role scoped to the managed MLB and Kalshi S3 prefixes for Snowflake external stage access.
- CloudWatch log groups.
- Lambda functions using the pushed container image.
- EventBridge Scheduler schedule for the MLB Teams Lambda, disabled by default but visible in AWS and Terraform.
- Hourly EventBridge Scheduler schedules for the Kalshi Events and Series Lambdas, enabled by default and scoped to conservative MLB/BaseBall payloads.
- A 30-minute EventBridge Scheduler schedule for the Kalshi Markets Lambda, enabled by default, offset at 15 and 45 minutes past each hour, and scoped to the configured Markets target or the packaged MLB event-query SQL file.

Snowpipe setup instructions live in [`docs/mlb_teams_snowpipe.md`](./mlb_teams_snowpipe.md).

## Invoke A Smoke Test

Invoke the function once and inspect the returned S3 URI:

```powershell
$FunctionName = terraform -chdir=infra/terraform output -raw lambda_function_name

aws lambda invoke `
  --function-name $FunctionName `
  --payload "{}" `
  --cli-binary-format raw-in-base64-out `
  --region $Region `
  response.json

Get-Content response.json
```

The response should include `row_count` and an `s3_uri` under `s3://snowflake-kalshi-project/raw/mlb/teams/`.

For the intended one-time dimension load, run this smoke test after Snowpipe notifications are configured, then validate the file loaded into `PROD.RAW.RAW_MLB_TEAMS`.

## Invoke Kalshi Events And Series

The Kalshi deploy script smoke invokes both Lambdas with the default MLB scope. To invoke manually after deployment, Kalshi Events defaults to `status = "open"` and the series tickers `KXMLBSPREAD`, `KXMLBTOTAL`, and `KXMLBGAME`; it also accepts an exact event ticker or custom series ticker list:

```powershell
$EventsFunctionName = terraform -chdir=infra/terraform output -raw kalshi_events_lambda_function_name

aws lambda invoke `
  --function-name $EventsFunctionName `
  --payload '{"series_tickers":["KXMLBSPREAD","KXMLBTOTAL","KXMLBGAME"],"status":"open"}' `
  --cli-binary-format raw-in-base64-out `
  --region $Region `
  kalshi-events-response.json

Get-Content kalshi-events-response.json
```

Kalshi Series defaults to rows whose tags contain `BaseBall`, or accepts an exact series ticker in either the invocation payload or `kalshi_series_ticker`:

```powershell
$SeriesFunctionName = terraform -chdir=infra/terraform output -raw kalshi_series_lambda_function_name

aws lambda invoke `
  --function-name $SeriesFunctionName `
  --payload '{"tags":["BaseBall"]}' `
  --cli-binary-format raw-in-base64-out `
  --region $Region `
  kalshi-series-response.json

Get-Content kalshi-series-response.json
```

The responses include `row_count` and `s3_uri` values under the `raw/kalshi/events/` or `raw/kalshi/series/` prefixes.

Snowflake RAW landing setup for these prefixes lives in [`docs/kalshi_events_series_snowpipe.md`](./kalshi_events_series_snowpipe.md).

## Invoke Kalshi Markets

Kalshi Markets requires a conservative scope: set exactly one market ticker,
event ticker, or event-query SQL file for manual runs. The scheduled run does
not need a single ticker binding; if no exact Markets scope is configured, its
payload uses `src/market_data_platform/queries/kalshi/markets_mlb_events.sql`
to query Snowflake for the event tickers to ingest. The default trade mode is incremental.
For each scoped market, the Lambda reads its own state object such as
`state/kalshi/market_trades/market_ticker=KXTEST/watermark.json`, fetches trades
using Kalshi `min_ts`/`max_ts` bounds, writes market trade JSONL, then advances
the watermark after the S3 landing writes succeed. A market with no existing
state is bounded to the last 24 hours by default. Reserved concurrency is not
set by default because some AWS accounts do not have enough unreserved
concurrency headroom; set `kalshi_markets_reserved_concurrency = 1` only when
the account can support a dedicated reservation.

```powershell
$MarketsFunctionName = terraform -chdir=infra/terraform output -raw kalshi_markets_lambda_function_name

aws lambda invoke `
  --function-name $MarketsFunctionName `
  --payload '{"market_ticker":"KXTEST","trade_fetch_mode":"incremental"}' `
  --cli-binary-format raw-in-base64-out `
  --region $Region `
  kalshi-markets-response.json

Get-Content kalshi-markets-response.json
```

Manual backfills are opt-in and should include explicit time bounds. Backfill
mode does not update the scheduled watermark unless `update_trade_watermark` is
set to `true` in the payload:

```powershell
aws lambda invoke `
  --function-name $MarketsFunctionName `
  --payload '{"market_ticker":"KXTEST","trade_fetch_mode":"backfill","trade_backfill_start_time":"2026-05-13T00:00:00Z","trade_backfill_end_time":"2026-05-14T00:00:00Z"}' `
  --cli-binary-format raw-in-base64-out `
  --region $Region `
  kalshi-markets-response.json
```

To reset scheduled incremental state, delete or replace only the relevant
per-market watermark object under `state/kalshi/market_trades/`. Do not delete
landed JSONL files under `raw/kalshi/market_trades/`; those files are Snowpipe
inputs.

Snowflake RAW landing setup for the Markets, market orderbook, and market trade
prefixes lives in [`docs/kalshi_markets_snowpipe.md`](./kalshi_markets_snowpipe.md).

## Scheduled Kalshi Payloads

The Kalshi EventBridge schedules invoke their matching Lambda only. The scheduler IAM policy for each schedule is scoped to the corresponding Lambda ARN, and the target payload is generated from Terraform variables.

The default Events schedule payload is:

```json
{
  "s3_bucket": "snowflake-kalshi-project",
  "s3_prefix": "raw/kalshi/events",
  "status": "open",
  "series_tickers": ["KXMLBSPREAD", "KXMLBTOTAL", "KXMLBGAME"]
}
```

If `kalshi_events_event_ticker` is set, Terraform sends `event_ticker` instead of `series_tickers`.

The default Series schedule payload is:

```json
{
  "s3_bucket": "snowflake-kalshi-project",
  "s3_prefix": "raw/kalshi/series",
  "tags": ["BaseBall"]
}
```

If `kalshi_series_ticker` is set, Terraform sends `series_ticker` instead of `tags`.

The default Markets schedule payload is:

```json
{
  "s3_bucket": "snowflake-kalshi-project",
  "markets_s3_prefix": "raw/kalshi/markets",
  "market_orderbooks_s3_prefix": "raw/kalshi/market_orderbooks",
  "market_trades_s3_prefix": "raw/kalshi/market_trades",
  "market_trades_state_prefix": "state/kalshi/market_trades",
  "trade_fetch_mode": "incremental",
  "trade_first_run_lookback_hours": 24,
  "trade_watermark_overlap_seconds": 60,
  "read_requests_per_second": 10,
  "event_query_file": "src/market_data_platform/queries/kalshi/markets_mlb_events.sql"
}
```

If `kalshi_markets_market_ticker`, `kalshi_markets_event_ticker`, or
`kalshi_markets_event_query_file` is set, Terraform uses that configured
Markets scope instead of the packaged query-file fallback. The query-file scope
requires the `kalshi_markets_snowflake_*` settings because the Lambda runs the
SQL in Snowflake before calling Kalshi for markets.
The packaged query is bounded to the current Eastern MLB game day across
`KXMLBTOTAL`, `KXMLBSPREAD`, and `KXMLBGAME`; keep
`read_requests_per_second` below Kalshi's advertised read cap when broadening
scope further.

## Updating The Function

For code changes, repeat the image build and push with a new tag, then re-run Terraform:

```powershell
$ImageTag = git rev-parse --short HEAD
$ImageUri = "${RepositoryUrl}:${ImageTag}"
docker buildx build --platform linux/amd64 -f aws/docker/Dockerfile.lambda -t $ImageUri --push .
terraform -chdir=infra/terraform apply -var "lambda_image_tag=$ImageTag"
```
