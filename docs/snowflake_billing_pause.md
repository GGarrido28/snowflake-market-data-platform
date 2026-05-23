# Pausing Snowflake Billing For Cost Savings

Use this procedure when active ingestion and warehouse-backed processing are not
needed for a short pause, such as stopping work overnight or for a day. The goal
is to reduce Snowflake credit usage by pausing both the serverless Snowpipe
ingestion layer and the task/warehouse layer.

This procedure does not stop files from landing in S3. It stops Snowpipe from
processing those files and stops Snowflake tasks from using the configured task
warehouse for merge and cleanup work.

## What This Pauses

- Snowpipes use Snowflake's serverless Snowpipe processing and are billed
  separately from the named virtual warehouse.
- Merge and cleanup tasks run with the configured Snowflake warehouse, so they
  can resume warehouse usage if they are left active.
- The warehouse should be suspended after tasks are suspended to stop active
  warehouse credit consumption.

## Pause Snowpipes

Run these statements first to pause serverless Snowpipe ingestion for the active
repo-managed landing paths:

```sql
ALTER PIPE PROD.RAW.PIPE_KALSHI_EVENTS SET PIPE_EXECUTION_PAUSED = TRUE;
ALTER PIPE PROD.RAW.PIPE_KALSHI_SERIES SET PIPE_EXECUTION_PAUSED = TRUE;
ALTER PIPE PROD.RAW.PIPE_KALSHI_MARKETS SET PIPE_EXECUTION_PAUSED = TRUE;
ALTER PIPE PROD.RAW.PIPE_KALSHI_MARKET_ORDERBOOKS SET PIPE_EXECUTION_PAUSED = TRUE;
ALTER PIPE PROD.RAW.PIPE_KALSHI_MARKET_TRADES SET PIPE_EXECUTION_PAUSED = TRUE;
ALTER PIPE PROD.RAW.PIPE_MLB_TEAMS SET PIPE_EXECUTION_PAUSED = TRUE;
```

Files can still land in S3 while pipes are paused. Snowflake retains
auto-ingest event notifications for a limited period while a pipe is paused,
commonly 14 days, so keep this procedure to short-term pauses unless you have a
separate backfill plan.

## Suspend Warehouse-Backed Tasks

Run these statements after pausing the pipes. Suspending the tasks is important
because these merge and cleanup tasks are the part of the pipeline that can use
the configured Snowflake warehouse:

```sql
ALTER TASK PROD.RAW.TASK_MERGE_KALSHI_EVENTS SUSPEND;
ALTER TASK PROD.RAW.TASK_MERGE_KALSHI_SERIES SUSPEND;
ALTER TASK PROD.RAW.TASK_MERGE_KALSHI_MARKETS SUSPEND;
ALTER TASK PROD.RAW.TASK_MERGE_KALSHI_MARKET_ORDERBOOKS SUSPEND;
ALTER TASK PROD.RAW.TASK_MERGE_KALSHI_MARKET_TRADES SUSPEND;

ALTER TASK PROD.RAW.TASK_CLEANUP_KALSHI_EVENTS_LOAD SUSPEND;
ALTER TASK PROD.RAW.TASK_CLEANUP_KALSHI_SERIES_LOAD SUSPEND;
ALTER TASK PROD.RAW.TASK_CLEANUP_KALSHI_MARKETS_LOAD SUSPEND;
ALTER TASK PROD.RAW.TASK_CLEANUP_KALSHI_MARKET_ORDERBOOKS_LOAD SUSPEND;
ALTER TASK PROD.RAW.TASK_CLEANUP_KALSHI_MARKET_TRADES_LOAD SUSPEND;
```

## Suspend Warehouse

Replace `<your_warehouse_name>` with the actual warehouse configured for the
environment, such as the value in `SNOWFLAKE_WAREHOUSE` or the `<task_warehouse>`
placeholder used in the Snowpipe setup SQL.

```sql
ALTER WAREHOUSE <your_warehouse_name> SUSPEND;
```

## Operator Notes

- This is intended for short-term cost control when stopping active work for the
  day.
- Pause pipes to reduce Snowpipe/serverless ingestion charges.
- Suspend tasks before suspending the warehouse so task runs do not immediately
  resume or consume the configured warehouse.
- If the pause extends beyond Snowflake's retained auto-ingest notification
  window, use the relevant Snowpipe runbook to refresh or backfill files that
  landed while the pipes were paused.
