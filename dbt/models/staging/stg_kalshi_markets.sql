select *
from {{ source('kalshi_raw', 'markets') }}
