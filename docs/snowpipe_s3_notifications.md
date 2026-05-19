# Snowpipe S3 Notification Terraform Runbook

Terraform manages the S3 `ObjectCreated` notifications that route landed JSONL
files from `snowflake-kalshi-project` to Snowflake-managed Snowpipe SQS queues.

## Managed Notifications

| Source | S3 prefix | Suffix | Snowflake pipe |
| --- | --- | --- | --- |
| MLB Teams | `raw/mlb/teams/` | `.jsonl` | `PIPE_MLB_TEAMS` |
| Kalshi Events | `raw/kalshi/events/` | `.jsonl` | `PIPE_KALSHI_EVENTS` |
| Kalshi Series | `raw/kalshi/series/` | `.jsonl` | `PIPE_KALSHI_SERIES` |
| Kalshi Markets | `raw/kalshi/markets/` | `.jsonl` | `PIPE_KALSHI_MARKETS` |
| Kalshi Market Orderbooks | `raw/kalshi/market_orderbooks/` | `.jsonl` | `PIPE_KALSHI_MARKET_ORDERBOOKS` |
| Kalshi Market Trades | `raw/kalshi/market_trades/` | `.jsonl` | `PIPE_KALSHI_MARKET_TRADES` |

## Deployment Sequence

1. Run the Snowflake pipe SQL for MLB Teams, Kalshi Events/Series, and Kalshi
   Markets/Orderbooks/Trades.
2. In Snowflake, run:

   ```sql
   SHOW PIPES LIKE 'PIPE_MLB_TEAMS';
   SHOW PIPES LIKE 'PIPE_KALSHI_EVENTS';
   SHOW PIPES LIKE 'PIPE_KALSHI_SERIES';
   SHOW PIPES LIKE 'PIPE_KALSHI_MARKETS';
   SHOW PIPES LIKE 'PIPE_KALSHI_MARKET_ORDERBOOKS';
   SHOW PIPES LIKE 'PIPE_KALSHI_MARKET_TRADES';
   ```

3. Copy each pipe's `notification_channel` value into
   `infra/terraform/terraform.tfvars`:

   ```hcl
   mlb_teams_pipe_notification_channel                = "arn:aws:sqs:..."
   kalshi_events_pipe_notification_channel            = "arn:aws:sqs:..."
   kalshi_series_pipe_notification_channel            = "arn:aws:sqs:..."
   kalshi_markets_pipe_notification_channel           = "arn:aws:sqs:..."
   kalshi_market_orderbooks_pipe_notification_channel = "arn:aws:sqs:..."
   kalshi_market_trades_pipe_notification_channel     = "arn:aws:sqs:..."
   ```

   The Kalshi market pipe ARNs can remain `null` while only the first three
   pipe notifications are active. When adding market notifications, set all
   three market pipe ARNs together.

4. Import the existing manual bucket notification configuration before the
   first Terraform apply that manages it:

   ```powershell
   terraform -chdir=infra/terraform import 'aws_s3_bucket_notification.snowpipe[0]' snowflake-kalshi-project
   ```

5. Review the plan before applying:

   ```powershell
   terraform -chdir=infra/terraform plan
   terraform -chdir=infra/terraform apply
   ```

## Safety Notes

`aws_s3_bucket_notification` owns the bucket's full notification configuration.
Set the MLB Teams, Kalshi Events, and Kalshi Series Snowpipe notification
channel ARNs together. The Kalshi market-related notification channels are a
second all-or-none group: leave all three null until those pipes exist, then set
all three together. A partial configuration would be unsafe because Terraform
could remove working manual notifications that are not declared in
configuration.

The Terraform resource is disabled while all notification channel variables are
`null`, so unrelated infrastructure deploys can still run before Snowflake
pipes exist. If the base three channels are set and the market channels are
still null, Terraform continues to manage only the existing MLB Teams, Kalshi
Events, and Kalshi Series notifications without destroying them.

After the resource is imported or applied, `prevent_destroy` blocks accidental
removal of the bucket notification configuration if a later Terraform run omits
the notification channel variables.
