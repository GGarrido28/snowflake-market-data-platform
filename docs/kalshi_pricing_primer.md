# Kalshi Pricing Primer

A beginner-friendly walkthrough of how Kalshi binary contracts price and trade. If you are coming to this data without a prediction-markets or financial-markets background, **read this before the entity map** — most of the confusion people have with Kalshi data is conceptual, not structural.

## TL;DR

- Each binary market has **two contracts**, YES and NO. Both exist at the same time and trade independently.
- Each contract **pays $1.00 if its side wins** and **$0.00 if its side loses**.
- Prices live between **$0.01 and $0.99** and move in **one-cent ticks** by default.
- `yes_price + no_price ≈ $1.00` always. The price *is* the implied probability.
- "Buying NO" doesn't mean receiving $0 — it means buying the coupon that pays $1 if NO wins.

## The two-contracts model

Every Kalshi market is a yes/no question (e.g., "Detroit wins by 1.5+ runs?"). The market has **two distinct, simultaneously-tradeable contracts**:

| Contract | Costs | Pays $1 if... | Pays $0 if... | Column in data |
| --- | --- | --- | --- | --- |
| YES | `yes_price_dollars` | YES outcome happens | NO outcome happens | `yes_bid_dollars` / `yes_ask_dollars` |
| NO  | `no_price_dollars`  | NO outcome happens  | YES outcome happens | `no_bid_dollars` / `no_ask_dollars`  |

You can buy either one. You can sell either one. Most retail platforms hide this complexity behind a "back this side" button, but **both contracts are real and have their own orderbooks**.

## Why prices sum to ~$1.00 (the no-arbitrage identity)

If you hold one YES contract *and* one NO contract, you are guaranteed exactly $1.00 at settlement no matter which side wins — one of them pays $1, the other pays $0. So the combined cost of those two contracts must be very close to $1.00, otherwise someone could buy both for less than $1.00 and pocket the difference risk-free.

That means **the YES price and the NO price are mirror images**: if YES is $0.86, NO is $0.14. The fact that they sum to $1 isn't a coincidence — it's enforced by arbitrage.

Practical consequence: **the YES price is literally the market's estimated probability that YES happens.** $0.86 means the market thinks 86% YES, 14% NO. This is one of the most powerful properties of prediction markets — you don't need to translate odds; the price *is* the probability.

## Worked example

Suppose `yes_price = $0.86, no_price = $0.14` for "Detroit wins by 1.5+ runs?". Two traders each have $100.

**Trader A buys YES at $0.86:**
- Spends $86 to buy 100 contracts.
- Detroit wins by 2+ runs → A collects 100 × $1 = $100. **Profit: $14 (≈16% return).**
- Detroit doesn't cover → A collects $0. **Loss: $86.**

**Trader B buys NO at $0.14:**
- Spends $14 to buy 100 contracts.
- Detroit doesn't cover → B collects 100 × $1 = $100. **Profit: $86 (≈614% return).**
- Detroit wins by 2+ → B collects $0. **Loss: $14.**

This is the same risk/reward shape as horse racing odds: longshots cost little and pay big, favorites cost more and pay less. Both sides are real bets that real people make.

## So why would anyone buy NO?

Three real reasons:

1. **They disagree with the market.** If you think Detroit has only a 70% chance of covering (not 86%), buying NO at $0.14 has positive expected value: `0.30 × $1 − 0.70 × $0.14 = $0.22` per contract.
2. **They're hedging.** If you already hold YES and want to lock in a profit, buying NO neutralizes the position.
3. **They want leverage on a tail outcome.** "If Detroit blows this, I want to be paid handsomely." NO at $0.14 returns ~7x if it hits.

A liquid market needs both sides actively pricing each other — that's how the YES/NO identity gets enforced and how the price stays close to the true probability.

## Connecting back to the data

| You will see in the data... | Read it as... |
| --- | --- |
| `yes_price_dollars = 0.86` | Market's implied probability of YES is 86%. One YES contract costs 86 cents. |
| `no_price_dollars = 0.14` | One NO contract costs 14 cents. (Should ≈ `1.00 − yes_price`.) |
| `count_fp = 25` | 25 contracts traded on this execution. |
| `taker_side = yes` | The aggressing trader was buying YES (paid the ask). |
| `taker_side = no` | The aggressing trader was buying NO (paid the ask on the NO side). |
| `tick_size = 0.01` | Prices move in 1-cent increments. Some markets use larger ticks; check this column per market. |
| `notional_value_dollars = 1` | Each contract pays $1 at settlement if it wins. |
| `market_result = 'yes'` | Settled: YES holders got $1, NO holders got $0. |

## Two unit systems: `_dollars` vs `_fp`

Kalshi columns use two suffix conventions to tell you what kind of number you are looking at:

- **`_dollars`** — a dollar-denominated price (e.g., `yes_bid_dollars`, `last_price_dollars`). Returned as a decimal string like `"0.86"`. Read it as dollars.
- **`_fp`** — a quantity (contracts, volume, open interest), e.g., `count_fp`, `volume_fp`, `open_interest_fp`. The `fp` stands for **fixed-point**: Kalshi stores these as precise integers internally (to avoid floating-point rounding errors) and serializes them as decimal strings. By the time the value reaches you through the dbt staging layer, it is cast to a normal decimal — you can `sum`, `avg`, and chart it like any other number. The suffix is informational; you don't need to scale anything.

In short: `_dollars` = a price; `_fp` = a quantity. Both are decimals by the time they hit SQL.

## Computing the dollar value of a trade

When you see a row like `yes_price_dollars = 0.86, count_fp = 25, taker_side = yes`:

- **25 contracts** changed hands.
- The price per contract was **$0.86**.
- Total dollars exchanged: `25 × $0.86 = $21.50`.

If YES eventually wins, that trade's buyer collects `25 × $1.00 = $25.00` — a $3.50 profit. If NO wins, the buyer collects $0 and is out $21.50.

## Two everyday confusions, resolved

1. **"NO pays $0, so why would anyone ever buy it?"** — NO pays **$1 if NO wins**. It only pays $0 if YES wins (which is the same as YES paying $0 when NO wins — the contracts are symmetric).
2. **"Are prices in cents or dollars?"** — Both descriptions are correct. Prices live in `[0.01, 0.99]` *dollars*, but they move in *one-cent* increments (the `tick_size` is typically $0.01). The contract pays $1 at settlement, not 1 cent — keep "price unit" (cents) and "contract face value" ($1) as separate ideas.

## Where to go next

- For how series → events → markets → trades connect, see [`kalshi_entity_map.md`](./kalshi_entity_map.md).
- For Kalshi's own glossary (series, event, market, order book), see <https://docs.kalshi.com/getting_started/terms>.
