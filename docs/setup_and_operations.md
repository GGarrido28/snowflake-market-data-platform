# Setup and Operations

This guide keeps the operational details out of the root README while preserving the setup notes needed to run, scrape, transform, and deploy the project.

## Local dbt Setup

This repo includes a dbt project in [`../dbt`](../dbt) for modeling Kalshi data in Snowflake.

### Install dbt for Snowflake

Use the same virtual environment you use for this repo, then install:

```bash
pip install dbt-core dbt-snowflake
```

### Configure the dbt Profile

Copy [`../dbt/profiles.yml.example`](../dbt/profiles.yml.example) to `dbt/profiles.yml` and set the environment variables it references.

This project uses a single root `.env` file for shared Snowflake/dbt configuration. At minimum, dbt expects:

```bash
SNOWFLAKE_ACCOUNT=...
SNOWFLAKE_USER=...
SNOWFLAKE_PRIVATE_KEY_PATH=...
SNOWFLAKE_PRIVATE_KEY_PASSPHRASE=
SNOWFLAKE_ROLE=...
SNOWFLAKE_WAREHOUSE=...
DBT_DATABASE=PROD
DBT_SCHEMA=STAGE
DBT_SOURCE_DATABASE=PROD
DBT_SOURCE_SCHEMA=RAW
```

The `SNOWFLAKE_*` settings match the Python connection code in `market_data_platform.config.settings`. Snowflake requires key-pair auth here because account-wide MFA enforcement blocks password logins for human users. Generate an RSA keypair, register the public key on your Snowflake user with:

```sql
ALTER USER <you> SET RSA_PUBLIC_KEY='...';
```

Point `SNOWFLAKE_PRIVATE_KEY_PATH` at the `.p8` private key file. Leave `SNOWFLAKE_PRIVATE_KEY_PASSPHRASE` blank if the key is unencrypted.

### Run dbt Locally

From the repo root, first load the root `.env` into your PowerShell session:

```powershell
. .\scripts\load_dbt_env.ps1
```

Then run:

```bash
dbt debug --project-dir dbt --profiles-dir dbt
dbt run --project-dir dbt --profiles-dir dbt
dbt test --project-dir dbt --profiles-dir dbt
dbt docs generate --project-dir dbt --profiles-dir dbt
```

## Starter Model Layout

The scaffold assumes you land raw Kalshi tables in Snowflake with the current Python scraper and then transform them in dbt:

- `source('kalshi_raw', 'markets')` -> `stg_kalshi_markets`
- `source('kalshi_raw', 'market_orderbooks')` -> `stg_kalshi_market_orderbooks`
- `source('kalshi_raw', 'market_trades')` -> `stg_kalshi_market_trades`
- `int_kalshi_markets` gives you a clean starting relation for downstream marts
- `source('mlb_raw', 'teams')` -> `stg_mlb_teams` -> `dim_mlb_teams`

If your physical raw table names or schema differ, update [`../dbt/models/sources.yml`](../dbt/models/sources.yml).

## Markets Scraper Scope

The markets scraper is intentionally scoped so it does not crawl every Kalshi market.

Set exactly one of these in your root `.env` before running the market scraper:

```bash
KALSHI_EVENT_TICKER=KXMLBTOTAL-26APR111310MIADET
```

or:

```bash
KALSHI_MARKET_TICKER=KXMLBTOTAL-26APR111310MIADET-14
```

To backfill markets for multiple events at once, point at a SQL file whose result set returns an `event_ticker` column, one row per event to scrape:

```bash
KALSHI_MARKETS_EVENT_QUERY_FILE=src/market_data_platform/queries/kalshi/markets_mlb_events.sql
```

The scraper runs the query against Snowflake, then fetches markets, orderbooks, and trades for each returned event ticker. The packaged MLB query stays bounded to the current Eastern game day for `KXMLBTOTAL`, `KXMLBSPREAD`, and `KXMLBGAME`. On a 15-game MLB slate, expect roughly 15 event tickers before market fan-out.

Markets scraping is expensive because orderbook and trades are called per market. Keep custom query files date-bounded and set `KALSHI_MARKETS_READ_REQUESTS_PER_SECOND` below Kalshi's advertised read cap if you broaden scope. The three scope env vars are mutually exclusive; set at most one.

## Events Scraper Scope

The events scraper defaults to open events only. To include non-open or historical events in `RAW_EVENTS`, set:

```bash
KALSHI_EVENTS_STATUS=all
```

If you want a specific status instead, set it directly:

```bash
KALSHI_EVENTS_STATUS=open
```

To backfill a single event or a single series without crawling all historical events, scope the scraper with one of:

```bash
KALSHI_EVENTS_EVENT_TICKER=KXMASTERS-25
```

or:

```bash
KALSHI_EVENTS_SERIES_TICKER=KXMASTERS
```

To backfill multiple series at once, point at a SQL file whose result set returns a `ticker` column, one row per series to scrape:

```bash
KALSHI_EVENTS_SERIES_QUERY_FILE=src/market_data_platform/queries/kalshi/events_mlb_series.sql
```

The scraper runs the query against Snowflake, then fetches Kalshi events for each returned series ticker. The three scope env vars are mutually exclusive; set at most one.

## Python Scraper CLI

Install the package in editable mode, then run the orchestration CLI:

```bash
pip install -e .
market-data market --event-ticker KXMLBTOTAL-26APR111310MIADET
market-data events --series-ticker KXMLBTOTAL
market-data series --ticker KXMLBTOTAL
```

## Kalshi API Credentials

Local scraper runs can use `KALSHI_API_KEY_ID` plus `KALSHI_API_KEY`, where `KALSHI_API_KEY` points at the local RSA private key PEM file.

AWS-deployed ingestion should use AWS Secrets Manager instead by setting `KALSHI_SECRET_ARN` or `KALSHI_SECRET_NAME`.

Setup instructions and the expected secret JSON shape live in [`kalshi_secrets_manager.md`](./kalshi_secrets_manager.md).

## MLB Teams Lambda S3 Landing

The first AWS-oriented MLB pipeline fetches public MLB team metadata and lands newline-delimited JSON in the S3 bucket used for Snowflake ingestion.

Configure the target bucket with either a source-specific env var or a shared Snowflake landing var:

```bash
MLB_TEAMS_S3_BUCKET=snowflake-kalshi-project
MLB_TEAMS_S3_PREFIX=raw/mlb/teams
```

`SNOWFLAKE_S3_BUCKET` and `SNOWFLAKE_S3_PREFIX` are also supported fallbacks. S3 folders are object key prefixes, so the pipeline can write under `raw/mlb/teams/...` even if only `raw/mlb` is visible before the first run.

The Lambda entrypoint is [`../aws/lambdas/mlb_teams/handler.py`](../aws/lambdas/mlb_teams/handler.py), which calls `market_data_platform.pipelines.mlb.teams_pipeline.run(event)`.

Deployment instructions live in [`aws_lambda_deploy.md`](./aws_lambda_deploy.md). The EventBridge schedule is intentionally disabled by default because MLB teams is low-change dimension data; Snowpipe setup and the manual refresh runbook live in [`mlb_teams_snowpipe.md`](./mlb_teams_snowpipe.md).

## Additional Reference Docs

- [`kalshi_entity_map.md`](./kalshi_entity_map.md): Kalshi hierarchy, join keys, and raw/staging table map.
- [`kalshi_pricing_primer.md`](./kalshi_pricing_primer.md): YES/NO pricing mechanics and `_fp` vs `_dollars` suffixes.
- [`aws_lambda_deploy.md`](./aws_lambda_deploy.md): Lambda container deployment.
- [`kalshi_markets_snowpipe.md`](./kalshi_markets_snowpipe.md): Kalshi markets Snowpipe runbook.
- [`snowpipe_s3_notifications.md`](./snowpipe_s3_notifications.md): Terraform-managed S3 notification setup.
- [`snowflake_billing_pause.md`](./snowflake_billing_pause.md): Cost-control pause procedure.
