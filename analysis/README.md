# Analysis

Notebook-driven exploratory analysis and public writeups for the Kalshi market data platform.

The analysis work is organized around the project question: across MLB market types (totals, spreads, and game winner markets), how does price drift differ between pregame and live trading, and how does liquidity relate to that drift?

## Featured Writeups

| Analysis | Status | Summary |
| --- | --- | --- |
| [01 Single-Market Drift Walkthrough](01_single_market_drift_walkthrough/README.md) | Technical walkthrough | Establishes the data shape and drift primitives on one `KXMLBSPREAD` contract. |
| [02 MLB Game Repricing Analysis](02_mlb_game_repricing_analysis/README.md) | Public findings writeup | Answers whether pregame `KXMLBGAME` pricing differs meaningfully from live pricing for the May 20, 2026 MLB slate. |

## Notebook Rendering

Jupyter notebooks retain rendered output in the `.ipynb` file, so GitHub readers can inspect the analysis without live Snowflake warehouse access.

## Layout

```text
analysis/
|-- README.md
|-- 01_single_market_drift_walkthrough/
|   |-- 01_single_market_drift_walkthrough.ipynb
|   `-- README.md
|-- 02_mlb_game_repricing_analysis/
|   |-- 02_mlb_game_repricing_analysis.ipynb
|   `-- README.md
`-- data/
```

Notebooks are numbered for reading order. Each analysis folder contains the notebook and a `README.md` that explains the notebook's role, findings, or current status.

The `analysis/data/` directory is gitignored and stores local parquet caches. Cache paths are notebook-specific; for example:

- `analysis/data/single_market_KXMLBSPREAD-26MAY101920DETKC-DET2/`
- `analysis/data/full_day_2026-05-20/`

## Data Cache Pattern

Every notebook follows the same general pattern:

1. Query Snowflake when a needed parquet cache is missing.
2. Persist pulled dataframes under `analysis/data/`.
3. Load from parquet on later runs when the cache is present.
4. Commit the rendered notebook output, but not the cache files.

This means a notebook can be re-executed without Snowflake access as long as the cache is already on disk. Public readers still see the committed rendered output in GitHub.

## Running a Notebook

Activate the project's conda environment and install the notebook tooling:

```bash
conda activate snowflake-kalshi
pip install -r requirements.txt
pip install jupyterlab
jupyter lab
```

To pull fresh data, configure the root `.env` with the same `SNOWFLAKE_*` variables used by dbt and the Python ingest paths. If you have just scraped new markets, run dbt first so the marts pick up the new rows:

```bash
dbt run --project-dir dbt --profiles-dir dbt
```

The notebooks read from dbt staging and mart tables such as `fct_markets`, `fct_market_orderbooks`, and `stg_kalshi_market_trades`, not directly from `RAW`.
