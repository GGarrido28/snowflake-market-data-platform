# Kalshi Market Data Platform

A data pipeline that ingests Kalshi MLB prediction market data into Snowflake and transforms it with dbt. The output answers a specific question: across MLB market types (totals, spreads, moneylines), how does price drift between market-open and market-close differ, and how does liquidity, measured by trade volume and orderbook depth, correlate with that drift? Stack: Python, Snowflake, dbt.

# Project Structure
- `src/market_data_platform`: Main Python package for sources, ingestion pipelines, Snowflake loading, configuration, and orchestration.
- `src/market_data_platform/sources`: Source-specific API client code, currently Kalshi with MLB scaffolding ready for the next source.
- `src/market_data_platform/pipelines`: Source-specific ingestion workflows that load raw Snowflake tables.
- `src/market_data_platform/warehouse`: Snowflake connection and loading utilities.
- `kalshi` and `snow_py`: Compatibility wrappers for older imports and script paths.
- `dbt`: Local dbt project for Snowflake transformations and analytics models.
- `analysis`: Jupyter notebooks for EDA and visualizations. See [`analysis/README.md`](./analysis/README.md).
- `ai`: Public AI-facing artifacts, including a display copy of the Codex skill used for repo change workflows.
- `docs`: Lightweight project documentation, including a Kalshi entity map and join-key cheat sheet.
- `README.md`: This file, providing an overview of the project and its purpose.

# Tech Stack
The lead covers the core stack (Python, Snowflake, dbt). Additional tooling:
- **Data Analysis**: Jupyter Notebooks
- **LLMs**: Cursor, Claude Code, Copilot

# Kalshi Glossary
## As defined by Kalshi
For those unfamiliar with Kalshi's terminology, this section provides definitions based on https://docs.kalshi.com/getting_started/terms

**Market**: A single binary market. This is a low level object which rarely will need to be exposed on its own to members. The usage of the term “market” here is consistent with how it’s used in the backend and API.
**Event**: An event is a collection of markets and the basic unit that members should interact with on Kalshi.
**Series**: A series is a collection of related events. The following should hold true for events that make up a series:
* Each event should look at similar data for determination, but translated over another, disjoint time period.
* Series should never have a logical outcome dependency between events.
* Events in a series should have the same ticker prefix.

## Additions and Clarifications

**Order Book**: The order book displays all the resting orders available on the market. It displays the quantity of resting orders available as well as their corresponding prices. A resting order is an offer to purchase contracts at a certain price that is not matched immediately.

**Pricing Mechanics**: If you are new to prediction markets and find yourself wondering things like "why would anyone buy NO if NO pays $0?" or "are prices in cents or dollars?", read the [`docs/kalshi_pricing_primer.md`](./docs/kalshi_pricing_primer.md) walkthrough before digging into the data. It covers how YES/NO contracts work, why prices sum to $1, what the `_fp` vs `_dollars` column suffixes mean, and how to compute the dollar value of any trade row.

## Examples of Terms
**Market**: Will the S&P 500 close above 4000 on December 31, 2024?

# dbt Setup
This repo now includes a starter dbt project in [`dbt`](./dbt) for modeling Kalshi data in Snowflake.

## 1. Install dbt for Snowflake
Use the same virtual environment you use for this repo, then install:

```bash
pip install dbt-core dbt-snowflake
```

## 2. Configure your dbt profile
Copy [`dbt/profiles.yml.example`](./dbt/profiles.yml.example) to `dbt/profiles.yml` and set the environment variables it references.

This project uses a single root `.env` file for shared Snowflake/dbt configuration.

At minimum, dbt expects:

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

The `SNOWFLAKE_*` settings match the Python connection code in `market_data_platform.config.settings`. Snowflake requires key-pair auth here because account-wide MFA enforcement blocks password logins for human users; generate an RSA keypair, register the public key on your Snowflake user with `ALTER USER <you> SET RSA_PUBLIC_KEY='...'`, and point `SNOWFLAKE_PRIVATE_KEY_PATH` at the `.p8` private key file. Leave `SNOWFLAKE_PRIVATE_KEY_PASSPHRASE` blank if the key is unencrypted.

## Markets Scraper Scope
The markets scraper is intentionally scoped now so it does not try to crawl every Kalshi market.
Set exactly one of these in your root `.env` before running the market scraper:

```bash
KALSHI_EVENT_TICKER=KXMLBTOTAL-26APR111310MIADET
```

or

```bash
KALSHI_MARKET_TICKER=KXMLBTOTAL-26APR111310MIADET-14
```

To backfill markets for multiple events at once, point at a SQL file (absolute path, or relative to the repo root) whose result set returns an `event_ticker` column — one row per event to scrape:

```bash
KALSHI_MARKETS_EVENT_QUERY_FILE=src/market_data_platform/queries/kalshi/markets_mlb_events.sql
```

The scraper runs the query against Snowflake, then fetches markets + orderbooks + trades for each returned event ticker. Markets scraping is expensive (orderbook and trades are called per market), so keep the query narrow until you know how many markets each event produces. The three scope env vars are mutually exclusive — set at most one.

## Events Scraper Status
The events scraper defaults to open events only. To include non-open or historical events in `RAW_EVENTS`, set:

```bash
KALSHI_EVENTS_STATUS=all
```

If you want a specific status instead, set it directly, for example:

```bash
KALSHI_EVENTS_STATUS=open
```

To backfill a single event or a single series without crawling all historical events, scope the scraper with one of:

```bash
KALSHI_EVENTS_EVENT_TICKER=KXMASTERS-25
```

or

```bash
KALSHI_EVENTS_SERIES_TICKER=KXMASTERS
```

To backfill multiple series at once, point at a SQL file (absolute path, or relative to the repo root) whose result set returns a `ticker` column — one row per series to scrape:

```bash
KALSHI_EVENTS_SERIES_QUERY_FILE=src/market_data_platform/queries/kalshi/events_mlb_series.sql
```

The scraper runs the query against Snowflake, then fetches Kalshi events for each returned series ticker. The three scope env vars are mutually exclusive — set at most one.

## Python Scraper CLI
Install the package in editable mode, then run the orchestration CLI:

```bash
pip install -e .
market-data market --event-ticker KXMLBTOTAL-26APR111310MIADET
market-data events --series-ticker KXMLBTOTAL
market-data series --ticker KXMLBTOTAL
```

The older `python -m snow_py.orchestration ...` entrypoint remains available through compatibility wrappers.

## 3. Run dbt locally
From the repo root, first load the root `.env` into your PowerShell session:

```bash
. .\scripts\load_dbt_env.ps1
```

Then run:

```bash
dbt debug --project-dir dbt --profiles-dir dbt
dbt run --project-dir dbt --profiles-dir dbt
dbt test --project-dir dbt --profiles-dir dbt
dbt docs generate --project-dir dbt --profiles-dir dbt
```

## 4. Starter model layout
The scaffold assumes you land raw Kalshi tables in Snowflake with the current Python scraper and then transform them in dbt:

- `source('kalshi_raw', 'markets')` -> `stg_kalshi_markets`
- `source('kalshi_raw', 'market_orderbooks')` -> `stg_kalshi_market_orderbooks`
- `source('kalshi_raw', 'market_trades')` -> `stg_kalshi_market_trades`
- `int_kalshi_markets` gives you a clean starting relation for downstream marts

If your physical raw table names or schema differ, update [`dbt/models/sources.yml`](./dbt/models/sources.yml).

## Entity Map
If you need a quick reminder of how Kalshi objects connect, see [`docs/kalshi_entity_map.md`](./docs/kalshi_entity_map.md).

## AI Workflow Docs
For the public display copy of the Codex workflow skill, see [`ai/`](./ai).
For repo PR naming and labeling conventions, see [`docs/pr-conventions.md`](./docs/pr-conventions.md).
