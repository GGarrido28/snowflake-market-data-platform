with source as (
    select
        "event_ticker" as event_ticker,
        "series_ticker" as series_ticker,
        "category" as category,
        "title" as event_title,
        "sub_title" as event_subtitle,
        "available_on_brokers" as is_available_on_brokers,
        "mutually_exclusive" as is_mutually_exclusive,
        "collateral_return_type" as collateral_return_type,
        try_to_timestamp_ntz("last_updated_ts") as updated_at,
        "product_metadata" as product_metadata
    from {{ source('kalshi_raw', 'events') }}
)

select *
from source
