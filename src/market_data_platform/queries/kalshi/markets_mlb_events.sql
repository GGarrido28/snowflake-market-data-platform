-- SQL scope for the scheduled markets scraper.
-- Returns every MLB event whose ticker encodes the current Eastern game date.
--
-- Keep this bounded to the active MLB game day: the markets scraper calls the
-- Kalshi markets endpoint for every event returned here, then calls orderbook
-- and trades endpoints for every market under those events.
with mlb_events as (
    select
        "event_ticker" as event_ticker,
        try_to_date(
            upper(substr(split_part("event_ticker", '-', 2), 1, 7)),
            'YYMONDD'
        ) as game_date
    from raw_events
    where "series_ticker" in (
        'KXMLBTOTAL',
        'KXMLBSPREAD',
        'KXMLBGAME'
    )
),
active_game_day as (
    select cast(convert_timezone('America/New_York', current_timestamp()) as date) as game_date
)

select event_ticker
from mlb_events
where game_date = (select game_date from active_game_day)
order by event_ticker
