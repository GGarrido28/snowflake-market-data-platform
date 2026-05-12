# Kalshi Entity Map

This project is easiest to reason about if you remember one hierarchy:

`series` -> `events` -> `markets` -> `trades`

There is also a current orderbook snapshot at the market level.

## Warehouse Join Keys

| From | To | Join key | Notes |
| --- | --- | --- | --- |
| `stg_kalshi_series` | `stg_kalshi_events` | `series_ticker` | One series can contain many events. |
| `stg_kalshi_events` | `stg_kalshi_markets` | `event_ticker` | One event can contain many markets. |
| `stg_kalshi_markets` | `stg_kalshi_market_trades` | `market_ticker = ticker` | Trades are market-grain executions keyed by market ticker in the API payload. |
| `stg_kalshi_markets` | `stg_kalshi_market_orderbooks` | `market_ticker` | Orderbooks are keyed by the Kalshi market ticker. |

## Mental Model

- `series`: a recurring template like a monthly report or daily weather contract family.
- `event`: one dated or otherwise scoped instance within a series.
- `market`: one tradable yes/no contract within an event.
- `trade`: one completed execution in a market.
- `orderbook`: the current bid ladder for a market, not a historical trade.

## Raw Source Cheat Sheet

| Raw table | API endpoint | Main key(s) | Important fields | API field types |
| --- | --- | --- | --- | --- |
| `RAW_SERIES` | `GET /series` | `ticker` | `category`, `title`, `tags`, `frequency`, `fee_type`, `fee_multiplier`, `volume_fp`, `last_updated_ts` | string, array<string>, integer, decimal string, timestamp string |
| `RAW_EVENTS` | `GET /events` | `event_ticker`, `series_ticker` | `category`, `title`, `sub_title`, `product_metadata`, `last_updated_ts` | string, object, timestamp string |
| `RAW_MARKETS` | `GET /markets` | `ticker`, `event_ticker` | `status`, `title`, `subtitle`, `created_time`, `updated_time`, `last_price_dollars`, `volume_fp` | string, timestamp string, decimal string |
| `RAW_MARKET_TRADES` | `GET /markets/trades` | `trade_id`, `ticker` | `count_fp`, `yes_price_dollars`, `no_price_dollars`, `taker_side`, `created_time` | string, decimal string, timestamp string |
| `RAW_MARKET_ORDERBOOKS` | `GET /markets/{ticker}/orderbook` | `market_ticker` | `orderbook` | string, object |

## Staging Conventions

- `stg_kalshi_series.series_ticker` comes from `RAW_SERIES.ticker`
- `stg_kalshi_events.event_ticker` comes from `RAW_EVENTS.event_ticker`
- `stg_kalshi_events.series_ticker` links events back to series
- `stg_kalshi_markets.market_ticker` comes from `RAW_MARKETS.ticker`
- `stg_kalshi_market_orderbooks.market_ticker` comes from `RAW_MARKET_ORDERBOOKS.market_ticker`
- `stg_kalshi_markets.event_ticker` links markets back to events

## Quick SQL Joins

```sql
select *
from {{ ref('stg_kalshi_events') }} events
left join {{ ref('stg_kalshi_series') }} series
  on events.series_ticker = series.series_ticker
```

```sql
select *
from {{ ref('stg_kalshi_markets') }} markets
left join {{ ref('stg_kalshi_events') }} events
  on markets.event_ticker = events.event_ticker
```

```sql
select *
from {{ ref('stg_kalshi_market_trades') }} trades
left join {{ ref('stg_kalshi_markets') }} markets
  on trades.ticker = markets.market_ticker
```

## References

- New to prediction-market pricing? Start with [`kalshi_pricing_primer.md`](./kalshi_pricing_primer.md) — it explains the YES/NO contract structure, the $1 payout, and what the `_fp` vs `_dollars` suffixes mean.
- Kalshi glossary: https://docs.kalshi.com/getting_started/terms
- Get Series List: https://docs.kalshi.com/api-reference/market/get-series-list
- Get Events: https://docs.kalshi.com/api-reference/events/get-events
- Get Markets: https://docs.kalshi.com/api-reference/market/get-markets
- Get Trades: https://docs.kalshi.com/api-reference/market/get-trades
- Get Market Orderbook: https://docs.kalshi.com/api-reference/market/get-market-orderbook
