with source as (
    select *
    from {{ source('kalshi_raw', 'market_trades') }}
)

select
    "trade_id" as trade_id,
    "ticker" as market_ticker,
    try_to_decimal(cast("count_fp" as varchar), 38, 6) as count_fp,
    "taker_side" as taker_side,
    try_to_decimal(cast("no_price_dollars" as varchar), 18, 4) as no_price_dollars,
    try_to_decimal(cast("yes_price_dollars" as varchar), 18, 4) as yes_price_dollars,
    try_to_timestamp_ntz("created_time") as trade_time
from source
