with source as (
    select *
    from {{ source('kalshi_raw', 'market_orderbooks') }}
)

select
    "market_ticker" as market_ticker,
    "orderbook" as orderbook
from source
