-- Which trades actually moved the price?
--
-- Intuition: a $0.06 price jump caused by a 1-contract trade carries more
-- information than a $0.06 jump that required a 1,000-contract sweep through
-- the orderbook. Big trades "pay for depth" (they consume many resting orders);
-- small trades that move price are usually responding to fresh information
-- (a scoring play, a lineup announcement, a weather change).
--
-- We rank trades by a size-discounted price-move score:
--
--   information_score = |yes_price_delta| / ln(trade_size + 1)
--
-- The +1 keeps ln() well-defined for fractional trade sizes (Kalshi supports
-- fractional contracts on some markets). Log is sublinear: doubling trade size
-- doesn't double the discount.
--
-- The top rows of the output are the moments the market learned something new.
-- The bottom rows (information_score = 0) are trades that didn't move price at
-- all -- volume without price discovery, typical of the settlement-floor phase.
--
-- Run via: dbt show --select which_trades_moved_price --limit 30

{% set target_market = 'KXMLBSPREAD-26MAY101920DETKC-DET2' %}

with trades as (
    select
        trade_id,
        trade_time,
        yes_price_dollars,
        no_price_dollars,
        count_fp as trade_size,
        taker_side
    from {{ ref('stg_kalshi_market_trades') }}
    where market_ticker = '{{ target_market }}'
),

with_lag as (
    select
        trade_id,
        trade_time,
        taker_side,
        trade_size,
        lag(yes_price_dollars) over (order by trade_time, trade_id) as prev_yes_price,
        yes_price_dollars                                            as yes_price,
        yes_price_dollars
            - lag(yes_price_dollars) over (order by trade_time, trade_id)
                                                                     as yes_price_delta
    from trades
),

scored as (
    select
        trade_time,
        taker_side,
        trade_size,
        prev_yes_price,
        yes_price,
        yes_price_delta,
        case
            when yes_price_delta is null then null
            when trade_size <= 0          then null
            else abs(yes_price_delta) / ln(trade_size + 1)
        end as information_score,
        -- mark trades that moved the market against the eventual winner;
        -- these are the "surprises" -- the market briefly believed the wrong thing.
        case
            when yes_price_delta < 0 then 'no-favorable shock'
            when yes_price_delta > 0 then 'yes-favorable shock'
            else                          'no price change'
        end as move_direction
    from with_lag
)

-- Top movers: trades ranked by how much price they shifted per contract.
-- Switch the order-by or filter at the bottom to inspect other slices.
select
    trade_time,
    prev_yes_price,
    yes_price,
    yes_price_delta,
    trade_size,
    taker_side,
    move_direction,
    information_score
from scored
where yes_price_delta is not null
  and yes_price_delta <> 0    -- skip non-moving trades; they live at the bottom of the ranking anyway
order by information_score desc nulls last
