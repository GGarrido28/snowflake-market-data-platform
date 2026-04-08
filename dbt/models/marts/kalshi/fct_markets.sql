with markets as (
    select *
    from {{ ref('stg_kalshi_markets') }}
),
events as (
    select *
    from {{ ref('stg_kalshi_events') }}
)

select
    markets.market_ticker,
    markets.event_ticker,
    events.category,
    events.series_ticker,
    events.event_title,
    events.event_subtitle,
    events.is_available_on_brokers,
    events.is_mutually_exclusive,
    events.collateral_return_type,
    markets.market_type,
    markets.market_status,
    markets.market_result,
    markets.market_title,
    markets.market_subtitle,
    markets.yes_subtitle,
    markets.no_subtitle,
    markets.primary_rules,
    markets.secondary_rules,
    markets.response_price_units,
    markets.price_level_structure,
    markets.strike_type,
    markets.expiration_value,
    markets.early_close_condition,
    markets.primary_participant_key,
    markets.can_close_early,
    markets.is_fractional_trading_enabled,
    markets.created_at,
    markets.open_at,
    markets.close_at,
    markets.expected_expiration_at,
    markets.expiration_at,
    markets.latest_expiration_at,
    markets.updated_at,
    markets.fee_waiver_expiration_at,
    markets.last_price_dollars,
    markets.liquidity_dollars,
    markets.no_ask_dollars,
    markets.no_bid_dollars,
    markets.notional_value_dollars,
    markets.previous_price_dollars,
    markets.previous_yes_ask_dollars,
    markets.previous_yes_bid_dollars,
    markets.yes_ask_dollars,
    markets.yes_bid_dollars,
    markets.open_interest_fp,
    markets.volume_24h_fp,
    markets.volume_fp,
    markets.yes_ask_size_fp,
    markets.yes_bid_size_fp,
    markets.settlement_timer_seconds,
    markets.tick_size,
    markets.floor_strike,
    markets.cap_strike,
    markets.custom_strike,
    markets.price_ranges
from markets
left join events
    on markets.event_ticker = events.event_ticker
