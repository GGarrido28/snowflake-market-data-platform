# Analysis

Notebook-driven exploratory analysis and visualizations for the Kalshi market data platform. Each notebook answers (or starts to answer) a piece of the project's headline question: **across MLB market types (totals, spreads, moneylines), how does price drift between market-open and market-close differ, and how does liquidity, measured by trade volume and orderbook depth, correlate with that drift?**

## Why notebooks (and not a live dashboard, for now)

The Snowflake warehouse backing this project may be paused between active work periods. A live-query dashboard (Streamlit, Evidence.dev, dbt-docs) would go dark every time the warehouse is cold, which is exactly the wrong failure mode for a portfolio piece. Jupyter notebooks retain executed cell output (charts, dataframe previews) in the `.ipynb` file itself, so a reader landing on GitHub sees the analysis regardless of warehouse state.

Streamlit and friends are on the post-MVP roadmap — once the notebook-based analysis is shipped and the subscription situation is clearer.

## Layout

```
analysis/
├── README.md                              <- this file
├── 01_single_market_drift_walkthrough.ipynb
├── 02_...                                  (future)
└── data/                                   <- gitignored; per-notebook parquet cache
```

Notebooks are numbered for sort order and to make it obvious which builds on which. They are intended to be readable top-to-bottom.

## Data cache pattern

Every notebook follows the same shape:

1. Query Snowflake **once** at the top of the notebook.
2. Persist each pulled dataframe to `analysis/data/<notebook_slug>/<table>.parquet`.
3. Wrap the pull in a helper that loads from the parquet cache when present, otherwise queries Snowflake and writes the cache.

This means a notebook can be re-executed without Snowflake creds as long as someone has the cached data on disk. The cache directory is **gitignored**, so each contributor pulls their own copy. The rendered cell output in the `.ipynb` is what survives in git for everyone else.

## Running a notebook

Activate the project's conda env. `requirements.txt` covers everything the notebooks need (pandas, matplotlib, pyarrow); only `jupyterlab` is added on top because it's a dev tool, not a runtime dep:

```bash
conda activate snowflake-kalshi
pip install -r requirements.txt
pip install jupyterlab
jupyter lab
```

To pull fresh data, also have a `.env` configured with the same `SNOWFLAKE_*` vars the dbt and Python ingest paths already use (see the root README for setup). If you've just scraped new markets, run `dbt run` first so the marts pick up the new rows — the notebooks read from `fct_*` and `stg_*`, not from `RAW`.
