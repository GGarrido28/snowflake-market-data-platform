# Snowpipe S3 Notification Terraform Runbook

Terraform manages the S3 `ObjectCreated` notifications that route landed JSONL
files from `snowflake-kalshi-project` to Snowflake-managed Snowpipe SQS queues.

## Managed Notifications

| Source | S3 prefix | Suffix | Snowflake pipe |
| --- | --- | --- | --- |
| MLB Teams | `raw/mlb/teams/` | `.jsonl` | `PIPE_MLB_TEAMS` |
| Kalshi Events | `raw/kalshi/events/` | `.jsonl` | `PIPE_KALSHI_EVENTS` |
| Kalshi Series | `raw/kalshi/series/` | `.jsonl` | `PIPE_KALSHI_SERIES` |

## Deployment Sequence

1. Run the Snowflake pipe SQL for MLB Teams and Kalshi Events/Series.
2. In Snowflake, run:

   ```sql
   SHOW PIPES LIKE 'PIPE_MLB_TEAMS';
   SHOW PIPES LIKE 'PIPE_KALSHI_EVENTS';
   SHOW PIPES LIKE 'PIPE_KALSHI_SERIES';
   ```

3. Copy each pipe's `notification_channel` value into
   `infra/terraform/terraform.tfvars`:

   ```hcl
   mlb_teams_pipe_notification_channel     = "arn:aws:sqs:..."
   kalshi_events_pipe_notification_channel = "arn:aws:sqs:..."
   kalshi_series_pipe_notification_channel = "arn:aws:sqs:..."
   ```

4. Import the existing manual bucket notification configuration before the first
   Terraform apply that manages it:

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
Set all three Snowpipe notification channel ARNs together. A partial
configuration would be unsafe because Terraform could remove working manual
notifications that are not declared in configuration.

The Terraform resource is disabled while all three notification channel
variables are `null`, so unrelated infrastructure deploys can still run before
Snowflake pipes exist. If any channel is set, all three must be set.
