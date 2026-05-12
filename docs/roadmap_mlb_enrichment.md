# MLB Game-State Enrichment Roadmap

> **Status:** Planned, deferred. Tracked in [issue #17](https://github.com/GGarrido28/snowflake-market-data-platform/issues/17). This document captures the *why* behind the scope; the issue captures the *what* and the build order.

## Why this matters

The Kalshi data alone tells you **when** a trade happened and **at what price**. It does not tell you whether the underlying game was live, what the score was, who was at bat, or whether the play that just happened was a scoring play.

Every interesting question about market efficiency requires that ground truth:

- How fast does the market reprice after a scoring play?
- Are trades happening *before* publicly-broadcast events (a signal of information asymmetry)?
- Are pre-game and in-game markets calibrated differently?
- Does the orderbook thin out at high-information moments?

Without joining MLB game data, those questions can be narrated but not measured. Today's analyses (`one_market_price_path.sql`, `which_trades_moved_price.sql`) can show that the market moved; they cannot show *why* it moved.

## The "is it live?" gap

There is no field anywhere in the current warehouse that classifies a Kalshi trade as **pre-game**, **in-game**, **post-final-pitch**, or **settlement-floor** liquidity. All trades sit in one undifferentiated timeline. The only timestamps available as reference points are the market's `open_at` / `close_at` / `expiration_at`, and those are *scheduled*, not *observed* — they do not reflect postponements, early closes, or extra innings.

This gap is the single biggest reason that analyses on this dataset can drift toward post-hoc storytelling. Closing it converts narrative-flavored claims ("this trade was probably a reaction to a KC scoring play") into measurable ones ("this trade happened 8 seconds after a KC RBI single, in the bottom of the 7th").

## Architecture

The smallest unit of value is **`dim_mlb_games`**. It alone closes the "is it live?" gap:

- Join key: a `game_pk` resolved from the Kalshi `event_ticker` (parsed from strings like `KXMLBSPREAD-26MAY101920DETKC`).
- Fields: scheduled first pitch, actual first pitch, final time, game status, home/away abbreviations.
- Once it exists, every Kalshi trade can be regime-tagged in a single SQL join.

Built on top, **`stg_mlb_plays`** adds the time-resolved play stream. Now trades can be aligned to discrete game events at the pitch level.

Optionally, a **lineup observation poller** captures the only pre-game information event large enough to move price — but lineup *posting timestamps* are not in the public MLB Stats API; they require us to be the timestamp authority by polling and recording first-appearance. That makes lineups a real engineering project rather than an ingestion exercise.

## Why pitch-by-pitch is "easier" than lineups, despite sounding harder

Pitch-by-pitch data is **ready-made**: the MLB Stats API serves it; `pybaseball` wraps it; bulk fetch and load is a clean ingestion exercise.

Lineup-posting timestamps are **not served anywhere**: the public APIs report the current lineup state, not the time at which each state first appeared. To use lineup-news as a time-stamped event you have to *be* the timestamping system — stand up a recurring poller, record first-appearance, retain history. That's a separate engineering scope.

Both belong in the project eventually. The order is "ingest what already exists first, build what's missing second."

## Why this is deferred

The project is currently being used as a portfolio reference point for `dbt` / `Snowflake` data-engineering experience while job applications are out. Opening enrichment scope (a new scraper, a new league of raw tables, a new dimensional model, new analyses) before that review cycle completes would leave a half-built scope visible in the repo. The right move is to capture the design and pick it up after the project's resume role stabilizes.

If you (or anyone reading this) wants to pick up the work, start with **Phase 1** in [issue #17](https://github.com/GGarrido28/snowflake-market-data-platform/issues/17) — `dim_mlb_games` alone delivers the largest single jump in analytical capability.

## Related

- [`kalshi_entity_map.md`](./kalshi_entity_map.md) — how the Kalshi entities currently connect.
- [`kalshi_pricing_primer.md`](./kalshi_pricing_primer.md) — pricing mechanics for the binary contracts being analyzed.
- [`../dbt/analyses/one_market_price_path.sql`](../dbt/analyses/one_market_price_path.sql) — the analysis whose limitations motivated this enrichment.
- [`../dbt/analyses/which_trades_moved_price.sql`](../dbt/analyses/which_trades_moved_price.sql) — the information-score ranking that would benefit most from regime-bucketing.
