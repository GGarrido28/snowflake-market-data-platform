SELECT "ticker" AS ticker
FROM raw_series
WHERE "category" = 'Sports'
  AND ARRAY_CONTAINS('Baseball'::VARIANT, "tags")
  AND "ticker" LIKE '%MLB%'
  AND "title" IN (
    'Pro Baseball Spread',
    'Pro Baseball Total Bases',
    'Pro Baseball Hits',
    'Pro Baseball Total Points',
    'First 5 Innings Spread',
    'First 5 Innings Total',
    'First 5 Innings Winner'
  )
