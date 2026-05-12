-- Walkthrough query: one MLB market, from spec to trade timeline.
--
-- Market: KXMLBTOTAL-26APR111310MIADET-14
--   Series: KXMLBTOTAL  (Pro Baseball Total Runs)
--   Event:  26APR111310MIADET  (Miami @ Detroit, 2026-04-11, 13:10 ET)
--   Strike: -14  (yes = combined runs strictly above 14)
--
-- The query has three parts you can run as a unit or comment out:
--   1) market_spec  -> the static "spec sheet" row (one row)
--   2) trade_path   -> every trade in chronological order (the price path)
--   3) summary      -> a few summary metrics across the trade stream
--
-- Run via: dbt compile --select one_market_price_path --project-dir dbt --profiles-dir dbt
--          then paste target/compiled/.../one_market_price_path.sql into a Snowflake worksheet.

{% set target_market = 'KXMLBSPREAD-26MAY101920DETKC-DET2' %}

with market_spec as (
    select
        market_ticker,
        event_ticker,
        event_title,
        market_title,
        yes_subtitle,
        no_subtitle,
        market_status,
        market_result,
        open_at,
        close_at,
        expiration_at,
        last_price_dollars,
        yes_bid_dollars,
        yes_ask_dollars,
        volume_fp,
        open_interest_fp
    from {{ ref('fct_markets') }}
    where market_ticker = '{{ target_market }}'
),

trades as (
    select
        trade_id,
        market_ticker,
        trade_time,
        taker_side,
        yes_price_dollars,
        no_price_dollars,
        count_fp as trade_size
    from {{ ref('stg_kalshi_market_trades') }}
    where market_ticker = '{{ target_market }}'
),

trade_path as (
    -- The price path: every execution in order, with derived columns to help
    -- you "see" the market move. yes_price_dollars is the market's implied
    -- probability of YES (combined runs > 14) at the moment of the trade.
    select
        trade_time,
        yes_price_dollars                                      as implied_yes_probability,
        no_price_dollars                                       as implied_no_probability,
        taker_side,
        trade_size,
        -- price change vs the previous trade (positive = market got more bullish on YES)
        yes_price_dollars
            - lag(yes_price_dollars) over (order by trade_time) as yes_price_delta,
        -- seconds since the previous trade (a rough "activity" proxy)
        datediff(
            'second',
            lag(trade_time) over (order by trade_time),
            trade_time
        )                                                       as seconds_since_prev_trade,
        -- cumulative contracts traded so far
        sum(trade_size) over (order by trade_time
                              rows between unbounded preceding and current row)
                                                                as cumulative_volume
    from trades
),

summary as (
    select
        count(*)                          as total_trades,
        sum(trade_size)                   as total_contracts_traded,
        min(trade_time)                   as first_trade_at,
        max(trade_time)                   as last_trade_at,
        min(yes_price_dollars)            as min_yes_price,
        max(yes_price_dollars)            as max_yes_price,
        avg(yes_price_dollars)            as avg_yes_price,
        -- a crude "how volatile was this market" metric
        stddev(yes_price_dollars)         as stddev_yes_price
    from trades
)

-- Pick ONE of the three selects below depending on what you want to see.
-- Default: the trade path, since that's the most useful view for learning.

-- 1) Static spec sheet (one row):
-- select * from market_spec;

-- 2) The price path (one row per trade, chronological):
select * from trade_path order by trade_time;

-- 3) Summary metrics across the whole market (one row):
-- select * from summary;
