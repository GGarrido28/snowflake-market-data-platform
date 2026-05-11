{{ config(materialized='table') }}

{% set raw_markets_relation = source('kalshi_raw', 'markets') %}
{% set raw_markets_columns = adapter.get_columns_in_relation(raw_markets_relation) %}
{% set raw_markets_column_names = raw_markets_columns | map(attribute='name') | map('lower') | list %}

with source as (
    select *
    from {{ raw_markets_relation }}
)

select
    "ticker" as market_ticker,
    "event_ticker" as event_ticker,
    "market_type" as market_type,
    "status" as market_status,
    "result" as market_result,
    "title" as market_title,
    {% if 'subtitle' in raw_markets_column_names %}
    "subtitle" as market_subtitle,
    {% else %}
    iff("yes_sub_title" = "no_sub_title", "yes_sub_title", cast(null as varchar)) as market_subtitle,
    {% endif %}
    "yes_sub_title" as yes_subtitle,
    "no_sub_title" as no_subtitle,
    "rules_primary" as primary_rules,
    "rules_secondary" as secondary_rules,
    "response_price_units" as response_price_units,
    "price_level_structure" as price_level_structure,
    "strike_type" as strike_type,
    "expiration_value" as expiration_value,
    "early_close_condition" as early_close_condition,
    {% if 'primary_participant_key' in raw_markets_column_names %}
    "primary_participant_key" as primary_participant_key,
    {% else %}
    cast(null as varchar) as primary_participant_key,
    {% endif %}
    "can_close_early" as can_close_early,
    "fractional_trading_enabled" as is_fractional_trading_enabled,
    try_to_timestamp_ntz("created_time") as created_at,
    try_to_timestamp_ntz("open_time") as open_at,
    try_to_timestamp_ntz("close_time") as close_at,
    try_to_timestamp_ntz("expected_expiration_time") as expected_expiration_at,
    try_to_timestamp_ntz("expiration_time") as expiration_at,
    try_to_timestamp_ntz("latest_expiration_time") as latest_expiration_at,
    try_to_timestamp_ntz("updated_time") as updated_at,
    {% if 'fee_waiver_expiration_time' in raw_markets_column_names %}
    try_to_timestamp_ntz("fee_waiver_expiration_time") as fee_waiver_expiration_at,
    {% else %}
    cast(null as timestamp_ntz) as fee_waiver_expiration_at,
    {% endif %}
    try_to_decimal("last_price_dollars", 18, 4) as last_price_dollars,
    try_to_decimal("liquidity_dollars", 18, 4) as liquidity_dollars,
    try_to_decimal("no_ask_dollars", 18, 4) as no_ask_dollars,
    try_to_decimal("no_bid_dollars", 18, 4) as no_bid_dollars,
    try_to_decimal("notional_value_dollars", 18, 4) as notional_value_dollars,
    try_to_decimal("previous_price_dollars", 18, 4) as previous_price_dollars,
    try_to_decimal("previous_yes_ask_dollars", 18, 4) as previous_yes_ask_dollars,
    try_to_decimal("previous_yes_bid_dollars", 18, 4) as previous_yes_bid_dollars,
    try_to_decimal("yes_ask_dollars", 18, 4) as yes_ask_dollars,
    try_to_decimal("yes_bid_dollars", 18, 4) as yes_bid_dollars,
    try_to_decimal("open_interest_fp", 38, 6) as open_interest_fp,
    try_to_decimal("volume_24h_fp", 38, 6) as volume_24h_fp,
    try_to_decimal("volume_fp", 38, 6) as volume_fp,
    try_to_decimal("yes_ask_size_fp", 38, 6) as yes_ask_size_fp,
    try_to_decimal("yes_bid_size_fp", 38, 6) as yes_bid_size_fp,
    "settlement_timer_seconds" as settlement_timer_seconds,
    "tick_size" as tick_size,
    {% if 'floor_strike' in raw_markets_column_names %}
    try_to_decimal("floor_strike", 18, 4) as floor_strike,
    {% else %}
    cast(null as number(18, 4)) as floor_strike,
    {% endif %}
    {% if 'cap_strike' in raw_markets_column_names %}
    try_to_decimal("cap_strike", 18, 4) as cap_strike,
    {% else %}
    cast(null as number(18, 4)) as cap_strike,
    {% endif %}
    "custom_strike" as custom_strike,
    "price_ranges" as price_ranges
from source
