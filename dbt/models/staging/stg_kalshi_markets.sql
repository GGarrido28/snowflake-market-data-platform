{{ config(materialized='table') }}

{# Kalshi's market response shape varies by market type (Spread, Total, Hits, etc.),
   so anything beyond the merge keys (ticker, event_ticker) may legitimately be absent.
   The optional_* macros emit a passthrough/try_cast when the source column exists and
   a typed NULL otherwise. See dbt/macros/optional_column.sql. #}

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
    "title" as market_title,
    {{ optional_string(raw_markets_column_names, 'market_type', 'market_type') }},
    {{ optional_string(raw_markets_column_names, 'status', 'market_status') }},
    {{ optional_string(raw_markets_column_names, 'result', 'market_result') }},
    {# Prefer the explicit `subtitle` field when present; otherwise derive from the
       yes/no sides (Kalshi binary markets often share a subtitle across both sides).
       If neither shape is available the subtitle silently becomes NULL rather than
       failing the build — same defensive philosophy as the rest of this model. #}
    {% if 'subtitle' in raw_markets_column_names %}
    "subtitle" as market_subtitle,
    {% elif 'yes_sub_title' in raw_markets_column_names and 'no_sub_title' in raw_markets_column_names %}
    iff("yes_sub_title" = "no_sub_title", "yes_sub_title", cast(null as varchar)) as market_subtitle,
    {% else %}
    cast(null as varchar) as market_subtitle,
    {% endif %}
    {{ optional_string(raw_markets_column_names, 'yes_sub_title', 'yes_subtitle') }},
    {{ optional_string(raw_markets_column_names, 'no_sub_title', 'no_subtitle') }},
    {{ optional_string(raw_markets_column_names, 'rules_primary', 'primary_rules') }},
    {{ optional_string(raw_markets_column_names, 'rules_secondary', 'secondary_rules') }},
    {{ optional_string(raw_markets_column_names, 'response_price_units', 'response_price_units') }},
    {{ optional_string(raw_markets_column_names, 'price_level_structure', 'price_level_structure') }},
    {{ optional_string(raw_markets_column_names, 'strike_type', 'strike_type') }},
    {{ optional_string(raw_markets_column_names, 'expiration_value', 'expiration_value') }},
    {{ optional_string(raw_markets_column_names, 'early_close_condition', 'early_close_condition') }},
    {{ optional_string(raw_markets_column_names, 'primary_participant_key', 'primary_participant_key') }},
    {{ optional_boolean(raw_markets_column_names, 'can_close_early', 'can_close_early') }},
    {{ optional_boolean(raw_markets_column_names, 'fractional_trading_enabled', 'is_fractional_trading_enabled') }},
    {{ optional_timestamp(raw_markets_column_names, 'created_time', 'created_at') }},
    {{ optional_timestamp(raw_markets_column_names, 'open_time', 'open_at') }},
    {{ optional_timestamp(raw_markets_column_names, 'close_time', 'close_at') }},
    {{ optional_timestamp(raw_markets_column_names, 'expected_expiration_time', 'expected_expiration_at') }},
    {{ optional_timestamp(raw_markets_column_names, 'expiration_time', 'expiration_at') }},
    {{ optional_timestamp(raw_markets_column_names, 'latest_expiration_time', 'latest_expiration_at') }},
    {{ optional_timestamp(raw_markets_column_names, 'updated_time', 'updated_at') }},
    {{ optional_timestamp(raw_markets_column_names, 'fee_waiver_expiration_time', 'fee_waiver_expiration_at') }},
    {{ optional_decimal(raw_markets_column_names, 'last_price_dollars', 'last_price_dollars', 18, 4) }},
    {{ optional_decimal(raw_markets_column_names, 'liquidity_dollars', 'liquidity_dollars', 18, 4) }},
    {{ optional_decimal(raw_markets_column_names, 'no_ask_dollars', 'no_ask_dollars', 18, 4) }},
    {{ optional_decimal(raw_markets_column_names, 'no_bid_dollars', 'no_bid_dollars', 18, 4) }},
    {{ optional_decimal(raw_markets_column_names, 'notional_value_dollars', 'notional_value_dollars', 18, 4) }},
    {{ optional_decimal(raw_markets_column_names, 'previous_price_dollars', 'previous_price_dollars', 18, 4) }},
    {{ optional_decimal(raw_markets_column_names, 'previous_yes_ask_dollars', 'previous_yes_ask_dollars', 18, 4) }},
    {{ optional_decimal(raw_markets_column_names, 'previous_yes_bid_dollars', 'previous_yes_bid_dollars', 18, 4) }},
    {{ optional_decimal(raw_markets_column_names, 'yes_ask_dollars', 'yes_ask_dollars', 18, 4) }},
    {{ optional_decimal(raw_markets_column_names, 'yes_bid_dollars', 'yes_bid_dollars', 18, 4) }},
    {{ optional_decimal(raw_markets_column_names, 'open_interest_fp', 'open_interest_fp', 38, 6) }},
    {{ optional_decimal(raw_markets_column_names, 'volume_24h_fp', 'volume_24h_fp', 38, 6) }},
    {{ optional_decimal(raw_markets_column_names, 'volume_fp', 'volume_fp', 38, 6) }},
    {{ optional_decimal(raw_markets_column_names, 'yes_ask_size_fp', 'yes_ask_size_fp', 38, 6) }},
    {{ optional_decimal(raw_markets_column_names, 'yes_bid_size_fp', 'yes_bid_size_fp', 38, 6) }},
    {{ optional_integer(raw_markets_column_names, 'settlement_timer_seconds', 'settlement_timer_seconds') }},
    {{ optional_string(raw_markets_column_names, 'tick_size', 'tick_size') }},
    {{ optional_decimal(raw_markets_column_names, 'floor_strike', 'floor_strike', 18, 4) }},
    {{ optional_decimal(raw_markets_column_names, 'cap_strike', 'cap_strike', 18, 4) }},
    {{ optional_string(raw_markets_column_names, 'custom_strike', 'custom_strike') }},
    {{ optional_string(raw_markets_column_names, 'price_ranges', 'price_ranges') }}
from source
