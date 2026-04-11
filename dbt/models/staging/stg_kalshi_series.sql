{{ config(materialized='table') }}

with source as (
    select *
    from {{ source('kalshi_raw', 'series') }}
)

select
    "ticker" as series_ticker,
    "category" as category,
    "title" as series_title,
    "tags" as tags,
    "frequency" as frequency,
    "fee_multiplier" as fee_multiplier,
    "fee_type" as fee_type,
    try_to_timestamp_ntz("last_updated_ts") as updated_at
from source