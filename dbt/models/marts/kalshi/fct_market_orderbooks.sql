with orderbooks as (
    select *
    from {{ ref('stg_kalshi_market_orderbooks') }}
),
markets as (
    select *
    from {{ ref('stg_kalshi_markets') }}
),
events as (
    select *
    from {{ ref('stg_kalshi_events') }}
)

select
    orderbooks.market_ticker,
    markets.event_ticker,
    events.category,
    events.series_ticker,
    events.event_title,
    events.event_subtitle,
    markets.market_status,
    markets.market_title,
    markets.market_subtitle,
    markets.yes_subtitle,
    markets.no_subtitle,
    markets.response_price_units,
    markets.tick_size,
    markets.last_price_dollars,
    markets.liquidity_dollars,
    markets.no_ask_dollars,
    markets.no_bid_dollars,
    markets.yes_ask_dollars,
    markets.yes_bid_dollars,
    markets.yes_ask_size_fp,
    markets.yes_bid_size_fp,
    coalesce(array_size(orderbooks.orderbook:"yes_dollars"), 0) as yes_level_count,
    coalesce(array_size(orderbooks.orderbook:"no_dollars"), 0) as no_level_count,
    coalesce(array_size(orderbooks.orderbook:"yes_dollars"), 0) > 0 as has_yes_orders,
    coalesce(array_size(orderbooks.orderbook:"no_dollars"), 0) > 0 as has_no_orders,
    orderbooks.orderbook
from orderbooks
left join markets
    on orderbooks.market_ticker = markets.market_ticker
left join events
    on markets.event_ticker = events.event_ticker
