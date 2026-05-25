# Kalshi Market Data Platform

Ingests Kalshi MLB prediction market data into Snowflake via scheduled AWS Lambda pipelines, transforms it with dbt, and analyzes it through notebook-driven writeups.

> Across MLB market types, how does price drift differ between pregame and live trading, and how does liquidity relate to that drift?

## Featured Analysis

- [MLB Game Repricing Analysis](./analysis/02_mlb_game_repricing_analysis/README.md): public writeup answering whether pregame `KXMLBGAME` pricing differs meaningfully from live pricing for the May 20, 2026 MLB slate.

## Architecture

```text
Kalshi API + MLB Stats API
        |
        v
Python ingestion package
        |
        v
EventBridge Scheduler (cron)
        |
        v
AWS Lambda container jobs
        |
        v
S3 JSONL landing files
        |
        v
Snowpipe + Snowflake RAW tables
        |
        v
dbt staging and mart models
        |
        v
Jupyter notebook analysis
```

The same Python package supports local ingestion and AWS-deployed Lambda entrypoints. The deployed path uses Terraform-managed AWS infrastructure, S3 landing prefixes, Snowpipe ingestion, Snowflake warehouse tables, and dbt transformations before the analysis layer reads from marts.

Kalshi organizes data as `series -> events -> markets -> trades`. See the [Kalshi entity map](./docs/kalshi_entity_map.md) for join keys and the [pricing primer](./docs/kalshi_pricing_primer.md) for YES/NO contract mechanics.

## Stack

- **Ingestion:** Python, Kalshi API, MLB Stats API
- **Cloud:** AWS Lambda, ECR, EventBridge Scheduler, S3, Secrets Manager
- **Warehouse:** Snowflake, Snowpipe
- **Transformations:** dbt
- **Analysis:** Jupyter, pandas, matplotlib
- **CI:** GitHub Actions for Python unittest and dbt parse; Dependabot for pip and Actions updates
- **Infrastructure:** Terraform

## Repository Map

| Path | Purpose |
| --- | --- |
| [`src/market_data_platform`](./src/market_data_platform) | Python package for source clients, ingestion workflows, warehouse loading, and orchestration. |
| [`aws/lambdas`](./aws/lambdas) | Thin Lambda handlers that dispatch into shared package pipeline code. |
| [`infra/terraform`](./infra/terraform) | AWS infrastructure for Lambda, S3, EventBridge, IAM, and deployment support. |
| [`infra/snowflake`](./infra/snowflake) | Snowflake/Snowpipe setup SQL. |
| [`dbt`](./dbt) | Snowflake staging, intermediate, and mart models. |
| [`analysis`](./analysis/README.md) | Notebook analyses and public writeups. |
| [`docs`](./docs) | Setup, runbooks, entity maps, and operational notes. |

## Key Documentation

| Document | Use |
| --- | --- |
| [Setup and operations](./docs/setup_and_operations.md) | Local setup, dbt configuration, scraper scopes, credentials, and Lambda landing notes. |
| [Analysis index](./analysis/README.md) | Notebook layout, cache pattern, and analysis writeups. |
| [Kalshi pricing primer](./docs/kalshi_pricing_primer.md) | Explanation of YES/NO pricing, payout mechanics, and `_fp` vs `_dollars` fields. |
| [Kalshi entity map](./docs/kalshi_entity_map.md) | Join keys and raw/staging table mental model. |
| [AWS Lambda deployment](./docs/aws_lambda_deploy.md) | Container-image Lambda deployment path. |
| [Kalshi markets Snowpipe runbook](./docs/kalshi_markets_snowpipe.md) | S3/Snowpipe path for Kalshi market entities. |
| [Snowflake billing pause runbook](./docs/snowflake_billing_pause.md) | Cost-control procedure for pausing Snowpipe/tasks. |
| [PR conventions](./docs/pr-conventions.md) | Branch naming, PR title, and label conventions. |
| [AI workflow docs](./ai/README.md) | Public display copy of the Codex workflow skill used for repo changes. |

## Current Analytical Scope

The current public analysis focuses on MLB Kalshi markets, especially `KXMLBGAME` winner contracts. The broader warehouse also supports totals, spreads, market trades, orderbook snapshots, Kalshi event metadata, and MLB team reference data.

Future analysis can extend the current market-only work by adding external MLB game-state data, such as play-by-play events and independent win-probability models.
