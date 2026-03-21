select *
from {{ source('kalshi_raw', 'market_trades') }}
