select distinct
    category
from {{ ref('stg_kalshi_events') }}
where category is not null
