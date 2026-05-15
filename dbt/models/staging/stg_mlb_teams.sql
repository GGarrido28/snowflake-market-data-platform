with source as (
    select *
    from {{ source('mlb_raw', 'teams') }}
),

ranked as (
    select
        team_id,
        name as full_team_name,
        team_code,
        abbreviation,
        team_name,
        location_name,
        first_year_of_play,
        sport_id,
        sport_name,
        league_id,
        league_name,
        division_id,
        division_name,
        venue_id,
        venue_name,
        active as is_active,
        ingested_at,
        raw_payload,
        source_file,
        source_row_number,
        snowpipe_loaded_at,
        row_number() over (
            partition by team_id
            order by ingested_at desc, snowpipe_loaded_at desc, source_file desc, source_row_number desc
        ) as row_number_latest
    from source
)

select
    team_id,
    full_team_name,
    team_code,
    abbreviation,
    team_name,
    location_name,
    first_year_of_play,
    sport_id,
    sport_name,
    league_id,
    league_name,
    division_id,
    division_name,
    venue_id,
    venue_name,
    is_active,
    ingested_at,
    raw_payload,
    source_file,
    source_row_number,
    snowpipe_loaded_at
from ranked
where row_number_latest = 1
