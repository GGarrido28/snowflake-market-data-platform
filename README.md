# What is this project?
A Snowflake-based data platform that ingests, analyzes, models, and visualizes prediction market data (Kalshi) to evaluate market efficiency, probability calibration, and liquidity dynamics.

# Why this project?
This project aims to provide insights into the efficiency of prediction markets, which are often used for forecasting events. By analyzing Kalshi's data, we can assess how well the market prices reflect actual probabilities, identify potential inefficiencies, and understand liquidity patterns. This can be valuable for traders, researchers, and anyone interested in the dynamics of prediction markets.

For my personal use, this project serves as a practical application of data engineering and analytics skills, allowing me to work with real-world data and derive meaningful insights. It also provides an opportunity to explore the intersection of finance, economics, sports, and data science. I decided to use Snowflake because of its scalability, performance, and ease of use for data warehousing and analytics. Snowflake's ability to handle large volumes of data and its support for SQL make it an ideal choice for this project. 

# Project Structure
- `kalshi`: Contains the main code for data scraping from Kalshi API.
- `snow_py`: Contains the code for data collection, modeling, transformation, and analysis in Snowflake.
- `dbt`: Local dbt project for Snowflake transformations and analytics models.
- `README.md`: This file, providing an overview of the project and its purpose.

# Tech Stack
- **Data Collection**: Python
- **Data Storage**: Snowflake 
- **Data Analysis**: Snowflake + Jupyter Notebooks
- **Data Modeling and Transformation**: DBT (Data Build Tool)
- **Version Control**: GitHub
- **Scheduling**: Airflow (optional for automating data collection and transformation)
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
SNOWFLAKE_PASSWORD=...
SNOWFLAKE_ROLE=...
SNOWFLAKE_WAREHOUSE=...
DBT_DATABASE=PROD
DBT_SCHEMA=STAGE
DBT_SOURCE_DATABASE=PROD
DBT_SOURCE_SCHEMA=RAW
```

The `SNOWFLAKE_*` settings match the Python connection code in `snow_py.connection.config`.

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
