{{ config(materialized='table') }}

with source as (
    select *
    from {{ source('kalshi_raw', 'market_trades') }}
)

SELECT
    "trade_id" as trade_id,
    "ticker" as market_ticker,
    "count_fp" as count_fp,
    "taker_side" as taker_side,
    "no_price_dollars" as no_price_dollars,
    "yes_price_dollars" as yes_price_dollars,
    try_to_timestamp_ntz("created_time") as trade_time
FROM source