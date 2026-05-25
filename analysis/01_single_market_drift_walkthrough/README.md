# Single-Market Drift Walkthrough

This notebook is the first technical walkthrough for the analysis layer. It uses one Kalshi MLB spread contract to establish the basic data shape and price-drift primitives before scaling to broader slates.

Notebook: [01_single_market_drift_walkthrough.ipynb](01_single_market_drift_walkthrough.ipynb)

## Scope

The walkthrough focuses on one market:

- Event: Detroit Tigers at Kansas City Royals, May 10, 2026
- Contract: `KXMLBSPREAD-26MAY101920DETKC-DET2`
- Meaning: YES resolves true if Detroit wins by 2 or more runs
- Sample size: one contract

Because this is an N=1 walkthrough, it should not be read as a public market-level finding. Its purpose is to make the analysis mechanics visible.

## What It Establishes

The notebook demonstrates how to:

- load market metadata, orderbook snapshots, and trade history from the dbt staging/mart layer;
- convert Kalshi timestamps into Eastern time for game-aligned analysis;
- plot executed YES prices through pregame and live trading;
- split the trade path around first pitch;
- compute simple drift and liquidity diagnostics;
- cache notebook inputs to parquet so rendered output remains usable without a live Snowflake warehouse.

## Relationship to Later Analysis

This walkthrough sets up the vocabulary and data handling used by later notebooks. The broader public findings begin in [02 MLB Game Repricing Analysis](../02_mlb_game_repricing_analysis/README.md), which scales the question to a full `KXMLBGAME` slate.
