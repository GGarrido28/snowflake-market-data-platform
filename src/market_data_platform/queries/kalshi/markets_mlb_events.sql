-- Sample query for the markets scraper.
-- Returns the 5 most recently updated MLB market events from RAW_EVENTS.
--
-- The markets scraper hits the Kalshi orderbook and trades endpoints PER MARKET
-- for every event returned here. Kalshi caps GET requests at ~20/sec, so keep
-- this set narrow until you know how many markets each event produces.
SELECT "event_ticker" AS event_ticker
FROM raw_events
WHERE "series_ticker" IN (
    'KXMLBTOTAL',
    'KXMLBSPREAD',
    'KXMLBGAME'
)
ORDER BY TRY_TO_TIMESTAMP_NTZ("last_updated_ts") DESC NULLS LAST
LIMIT 5
