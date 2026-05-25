# MLB Game Repricing Analysis

## Overview

This analysis asks a narrow question:

> Does pregame `KXMLBGAME` pricing differ meaningfully from live pricing?

For the May 20, 2026 MLB slate, the answer is yes. Pregame prices showed little systematic improvement before first pitch, while live prices repriced sharply toward the eventual winner after games began.

The notebook caches the full MLB market universe for the day: 45 event tickers across `KXMLBGAME`, `KXMLBSPREAD`, and `KXMLBTOTAL`. The actual repricing analysis is scoped to `KXMLBGAME` only: 15 game events and 30 complementary team contracts.

See [02_mlb_game_repricing_analysis.ipynb](02_mlb_game_repricing_analysis.ipynb) for the full notebook.

## Why `KXMLBGAME`

`KXMLBGAME` is the cleanest MLB market type for apples-to-apples comparison across games. Each contract is a binary "Will Team X win?" market, so the YES price can be interpreted as an implied win probability for that team.

The spread and total markets (`KXMLBSPREAD` and `KXMLBTOTAL`) use strike ladders through `floor_strike`. Their raw YES prices are not directly comparable across games without a moneyness or implied-line normalization step. For example:

| market_ticker | floor_strike | YES meaning |
| --- | ---: | --- |
| KXMLBTOTAL-26MAY201305CINPHI-7 | 6.5 | Over 6.5 runs scored |
| KXMLBTOTAL-26MAY201305CINPHI-8 | 7.5 | Over 7.5 runs scored |
| KXMLBTOTAL-26MAY201305CINPHI-9 | 8.5 | Over 8.5 runs scored |

Those markets are useful, but they need a separate normalization layer before their price discovery paths can be compared cleanly.

## Questions

The analysis splits each game into two windows:

- **Pregame:** from first observed trade until first pitch.
- **Live:** from first pitch until the last observed live trade.

The main questions are:

- Does the pregame market move toward the eventual winner before first pitch?
- Does pregame forecast quality improve from first observed price to first pitch?
- Is any pregame improvement gradual, or concentrated near first pitch?
- How much does the live market reprice toward the eventual winner after first pitch?
- Are live paths smooth, or do they move through large jumps?
- How does liquidity relate to live path efficiency?

## Key Findings

### 1. Pregame Price Discovery Was Flat

Pregame forecast quality was measured with Brier score:

```text
Brier score = (predicted_probability - actual_outcome)^2
```

Lower is better. A winner probability that moves from 0.55 to 0.65 before first pitch improves the Brier score; a move from 0.55 to 0.45 worsens it.

For the May 20 `KXMLBGAME` slate:

- Mean Brier score moved from 0.241 to 0.239 from first observed price to first pitch.
- 15 of 30 contracts moved toward the eventual winner.
- 15 of 30 contracts improved Brier score.
- 5 of 15 games moved toward the eventual winner on average.
- 6 of 15 games improved mean Brier score.
- Among contracts with positive pregame Brier improvement, the median share of improvement in the final hour was 0%.
- Median pregame path efficiency was 2.38%, meaning prices wandered roughly 40x more than their net directional movement.

The important interpretation is not that the pregame market was wrong. It is that this market did not show meaningful systematic improvement between the first observed price and first pitch.

Two explanations remain plausible:

- Pregame information arrived but was not incorporated efficiently.
- Opening prices were already close to fair, and available pregame information was not strong enough to move the prior.

This analysis cannot distinguish those explanations without a timeline of pregame information events such as lineup locks, injury news, weather changes, or pitching updates.

### 2. Live Repricing Was Strong

Live behavior was very different from pregame behavior. The live analysis collapses each pair of team contracts into one winner-normalized game path:

```text
winner_probability = mean(winner_team_yes_price, 1 - loser_team_yes_price)
```

For the 15 `KXMLBGAME` games:

- All 15 games had live trades.
- All 15 games had at least 15 observed live minutes.
- All 15 games repriced toward the eventual winner.
- Mean winner probability moved from 0.517 at first pitch to 0.990 at the last observed live trade.
- Mean live repricing toward the winner was +0.473.
- All 15 games reached 0.99 winner probability by the last observed live trade.

The central finding is timing: nearly all observed information incorporation happened after first pitch, not before.

### 3. Live Paths Were Choppy, Not Smooth

The live market did not simply drift toward the final outcome in a straight line.

Across the 15 analyzable games:

- Mean live path efficiency was 18.9%.
- Median live path efficiency was 19.1%.
- Every game had at least one one-minute move of 5 cents or more.
- Every game had at least one one-minute move of 10 cents or more.
- The mean largest one-minute move was 24.2 cents.

This is consistent with live repricing that reacts to changing game state in chunks. The trade data shows executed price jumps, but it does not identify the baseball events that caused them.

### 4. More Liquid Games Had Less Efficient Live Paths

One surprising diagnostic was the relationship between live trade count and path efficiency:

- Spearman correlation between live trade count and live path efficiency: -0.875.
- Spearman correlation between live volume and live path efficiency: -0.764.

A naive expectation might be that more liquidity produces smoother convergence. This single-day sample showed the opposite: more actively traded games had more price movement relative to their final net move.

The leading explanation is confounding by game competitiveness. Close or volatile games can produce both more trading activity and more price reversals. Blowouts can produce fewer trades and more monotonic paths. Without independent game-state data, this remains a hypothesis, not a causal conclusion.

## Scope and Limitations

This analysis is conducted entirely from Kalshi market data:

- trade prints
- prices
- volumes
- orderbook snapshots

No external MLB game-state data is used.

Important limitations:

- The sample is one day: May 20, 2026.
- The repricing analysis covers 15 `KXMLBGAME` events and 30 team contracts.
- The notebook caches 45 MLB event tickers, but `KXMLBSPREAD` and `KXMLBTOTAL` are excluded from the findings because they require normalization that is not built here.
- Trade data was backfilled for the May 20 slate, but orderbook collection still has a partial-day outage after roughly 6:45 PM CDT.
- Findings are observational and correlational, not causal.
- Live convergence toward the eventual winner is not the same thing as market efficiency. Evaluating efficiency requires an independent game-state benchmark.

## What Would Improve the Analysis

The next layer of analysis should add external baseball context:

- **Pitch-by-pitch or play-by-play data** to map the largest price jumps to run-scoring plays, pitching changes, errors, or high-leverage situations.
- **Pregame information timelines** to test whether flat pregame Brier reflects market failure or an already-efficient prior.
- **Independent win-probability models** to evaluate whether Kalshi prices were efficient relative to game state, not just whether they eventually converged to the winner.

That enrichment would move the analysis from "what did the market do?" to "was the market right, and when?"
