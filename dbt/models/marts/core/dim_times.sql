with seed as (
    select *
    from {{ ref('dim_times_seed') }}
)

select
    cast(the_minute_of_day as smallint)  as time_key,
    cast(the_time as time)               as the_time,
    cast(the_hour as smallint)           as the_hour,
    cast(the_minute as smallint)         as the_minute,
    cast(the_minute_of_day as smallint)  as the_minute_of_day,
    cast(the_hour_12 as smallint)        as the_hour_12,
    am_pm,
    portion_of_day,
    style_hhmm,
    style_hhmm_12
from seed
