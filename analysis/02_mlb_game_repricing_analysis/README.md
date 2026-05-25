# MLB Game Repricing Analysis

# Overview

This notebook explores price drift and liquidity patterns in the MLB `KXMLBGAME` market type. It builds on the single-market walkthrough in `01_single_market_drift_walkthrough.ipynb` by scaling up to all MLB games over the course of the May 20th, 2026 season. The goal is to see whether the patterns observed in the single-market case hold more generally, and to identify any interesting outliers or trends across the broader market set. There were 15 games on May 20th, so the notebook pulls and analyzes data for 45 markets.

## Why was the focus soley on `KXMLBGAME` and not the other markets?

`KXMLBGAME` is the easiest market to do apples-to-apples comparison between games. The market is a binary "Will Team X win?". The other markets have `floor_strikes` that need to account for normalization and determination of price discovery. For example, some samples of the `KXMLBTOTAL` markets for CIN/PHI:

| market_ticker | floor_strike | YES meaning |
|-----------|-----------|-----------|
| KXMLBTOTAL-26MAY201305CINPHI-7 | 6.5 | Over 6.5 runs scored |
| KXMLBTOTAL-26MAY201305CINPHI-8 | 7.5 | Over 7.5 runs scored |
| KXMLBTOTAL-26MAY201305CINPHI-9 | 8.5 | Over 8.5 runs scored |

This means totals and spreads behave like strike ladders, where attention/liquidity may concentrate around the most relevant threshold. That makes them harder to compare directly without a moneyness or implied-line normalization step.

## Key questions

I decided to split the data into two buckets: pre-game (from market open until the first pitch) and in-game (from first pitch until market close). This allows us to see how the transition from pre-game to in-game affects price drift and liquidity patterns. 

### Pre-game 

The key questions I want to answer are:

* Does the pregame market move toward the eventual winner before first pitch?
* Does forecast quality improve from first observed trade/open to first pitch?
* Is the improvement gradual, or concentrated near first pitch?
* Does liquidity, trade count, volume, or available order book depth correlate with smoother or more accurate pregame price discovery?

### In-game

The key questions I want to answer are:

* How does the market react to in-game events, such as scoring plays or pitching changes?
* Is the improvement gradual, or are there observable jumps and shocks over the course of the game?
* Does liquidity, trade count, volume, or available order book depth correlate with smoother or more accurate in-game price discovery?

# Key Findings

## Pregame price discovery was flat

To assess the "accuracy of the pregame market, I used **Brier** score. A Brier score measures the accuracy of probabilistic predictions, primarily for binary or categorical outcomes (e.g., "win or no win"). It calculates the mean squared difference between the predicted probabilities and the actual outcomes, resulting in a number between \(0\) and \(1\).

```
Brier score = (predicted_probability - actual_outcome)^2
```

Lower is better. For the eventual winner, a price moving from 0.55 to 0.65 before first pitch improves the Brier score; moving from 0.55 to 0.45 worsens it. It punishes confident wrong predictions more than uncertain wrong predictions - the closer the prediction is to 1, and is wrong, the more of a penalty there is to the prediction.

* Brier score 0.241 → 0.239 (first observed → first pitch) — no improvement
* 50% of markets moved toward the eventual winner (coin flip)
* 0% of improvement concentrated in the final hour
* Path efficiency 2.38% — prices wandered ~40x more than net movement
* Two competing hypotheses:
    * Market failed at price discovery — pregame information arrived but was not incorporated
    * Market was already efficient — opening price was already correct; pregame information (lineups, weather, injuries) was not material enough to update the prior

## Pregame-to-live disparity

* Pregame: coin flip forecasting, flat Brier, no systematic improvement
* Live: 100% of games repriced toward the winner, +0.473 mean repricing, all 15 games reached 0.99 winner probability
* Nearly all information incorporation happened after first pitch, not before
* This is the central finding — when does the market incorporate information, and the answer is almost entirely post-first-pitch

## Liquidity-path efficiency correlation

* More liquid games had less efficient price paths (Spearman Correlation Coefficient -0.875)
* My expectations and beliefs was centered that more liquidity would lead to smoother convergence. The opposite was observed — more liquid games had more price wandering relative to net movement.
* Hypothesis: Leading explanation is confounding by game competitiveness — close games produce both more trading activity AND more price reversals (lead changes, shifting momentum). There is more variance in the game because the teams appear to be evenly matched, and game state shows that they are close to one another. This leads to more price wandering as the market reacts to the more volatile game state. In blowouts, the market quickly converges on the winner and there are fewer in-game events that cause price reversals, leading to a more monotonic path.
* Hypothesis: Blowouts produce fewer trades and more monotonic paths. Since we don't have an independent game-state variable in this analysis, we can't disentangle whether liquidity is causing the price path inefficiency, or if both are caused by the underlying game state. This is a key area for future exploration.
* Disentangling liquidity's causal effect from game-state variance requires an independent game-state variable (run differential, win probability model)

# Analysis boundary conditions

This analysis is conducted entirely from market data — trade prints, prices, volumes, and orderbook snapshots from Kalshi's `KXMLBGAME` contracts. No external MLB game-state data is used.

To build deeper hypotheses and move beyond correlation:

* Pitch-by-pitch / play-by-play data would allow mapping the largest price jumps to specific in-game events (run-scoring plays, pitching changes, errors) — separating ordinary live convergence from event-driven repricing
* Pregame information event timelines (lineup locks, injury reports, weather updates) would distinguish whether the flat pregame Brier reflects market failure or an already-efficient prior
* Independent win-probability models (e.g., MLB-level WPA) would provide a benchmark to evaluate whether the market's live path was efficient relative to game-state, not just whether it converged
* MLB enrichment data would push this from "what did the market do?" to "was the market right, and when?" — a fundamentally different tier of analysis.

## Limitations of the current analysis

* Single Day Sample: This analysis focuses on a single day of MLB games (May 20th, 2026). While this allows for a detailed exploration of price drift and liquidity patterns, the findings may not generalize across different days, teams, or market conditions. Future work could expand the sample size to include multiple days or even entire seasons for a more robust analysis.
* Observational Nature: Findings here are observational and correlational, not causal. We can identify patterns and associations in the data, but we can't definitively say that one factor causes another without further experimental or quasi-experimental analysis.
* Enrichment Data: The analysis is limited to the market data available within Kalshi. Incorporating external data sources, such as lineup information, weather conditions, or in-game events, could provide additional context and help explain some of the observed patterns. This is an area for future exploration.