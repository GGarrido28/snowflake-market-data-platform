with seed as (
    select *
    from {{ ref('dim_dates_seed') }}
)

select
    cast(the_date as date)               as date_key,
    cast(the_date as date)               as the_date,
    cast(the_day as smallint)            as the_day,
    the_day_suffix,
    the_day_name,
    cast(the_day_of_week as smallint)         as the_day_of_week,
    cast(the_day_of_week_in_month as smallint) as the_day_of_week_in_month,
    cast(the_day_of_year as smallint)    as the_day_of_year,
    cast(is_weekend as boolean)          as is_weekend,
    cast(the_week as smallint)           as the_week,
    cast(the_iso_week as smallint)       as the_iso_week,
    cast(the_first_of_week as date)      as the_first_of_week,
    cast(the_last_of_week as date)       as the_last_of_week,
    cast(the_week_of_month as smallint)  as the_week_of_month,
    cast(the_month as smallint)          as the_month,
    the_month_name,
    cast(the_first_of_month as date)     as the_first_of_month,
    cast(the_last_of_month as date)      as the_last_of_month,
    cast(the_first_of_next_month as date) as the_first_of_next_month,
    cast(the_last_of_next_month as date) as the_last_of_next_month,
    cast(the_quarter as smallint)        as the_quarter,
    cast(the_first_of_quarter as date)   as the_first_of_quarter,
    cast(the_last_of_quarter as date)    as the_last_of_quarter,
    cast(the_year as smallint)           as the_year,
    cast(the_iso_year as smallint)       as the_iso_year,
    cast(the_first_of_year as date)      as the_first_of_year,
    cast(the_last_of_year as date)       as the_last_of_year,
    cast(is_leap_year as boolean)        as is_leap_year,
    cast(has_53_weeks as boolean)        as has_53_weeks,
    cast(has_53_iso_weeks as boolean)    as has_53_iso_weeks,
    mmyyyy,
    style_101,
    style_103,
    style_112,
    style_120
from seed
