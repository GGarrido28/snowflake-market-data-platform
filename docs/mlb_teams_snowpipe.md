# MLB Teams Snowpipe Runbook

MLB teams is reference data, not a high-churn event stream. The Lambda, S3 landing path, IAM role, and Snowpipe objects are kept in the repo to demonstrate the integration pattern, but the EventBridge schedule is intentionally disabled by default. Refresh the dimension manually when MLB team metadata needs to be reloaded.

## Data Flow

```text
MLB Stats API -> Lambda -> S3 JSON Lines -> Snowpipe -> PROD.RAW.RAW_MLB_TEAMS -> dbt current dimension
```

The Lambda writes newline-delimited JSON under:

```text
s3://snowflake-kalshi-project/raw/mlb/teams/ingested_date=YYYY-MM-DD/mlb_teams_*.jsonl
```

Snowpipe loads every file as an append-only raw snapshot. dbt then selects the latest row per `team_id` in `stg_mlb_teams` and exposes `dim_mlb_teams`.

## Why The Schedule Is Disabled

The EventBridge Scheduler resource remains deployed and visible for portfolio/demo purposes, but `mlb_teams_schedule_state` defaults to `DISABLED`. Running this daily would mostly create duplicate reference snapshots.

This is not a general Snowpipe rule. For high-change feeds, keep the schedule enabled or use event-driven writers. For static or low-change dimensions like MLB teams, manual refreshes are cleaner.

## Why Not Truncate

Snowpipe is built around `COPY INTO` from new files and does not naturally run `TRUNCATE TABLE` before loading. A truncate-and-reload flow would need additional orchestration, such as a Snowflake task or stored procedure, and would obscure the Snowpipe pattern this repo is meant to show.

The chosen pattern is:

- Raw table: append-only snapshots from Snowpipe.
- dbt staging: latest row per `team_id`.
- dbt mart: current `dim_mlb_teams`.

The pipe intentionally omits `ON_ERROR = 'ABORT_STATEMENT'`. Snowpipe pipe definitions do not support that value; the default pipe behavior skips files with load errors. Check `COPY_HISTORY` after each manual refresh to catch skipped files.

## Setup Steps

1. Apply Terraform once to create the AWS IAM role Snowflake will use for S3 reads:

   ```powershell
   terraform -chdir=infra/terraform apply
   terraform -chdir=infra/terraform output -raw snowflake_s3_read_role_arn
   ```

2. Open `infra/snowflake/mlb_teams_snowpipe.sql`, replace `<snowflake_s3_read_role_arn>` with the Terraform output, and run the storage integration section in Snowflake.

3. Run:

   ```sql
   DESC INTEGRATION S3_MLB_TEAMS_INT;
   ```

   Copy `STORAGE_AWS_IAM_USER_ARN` and `STORAGE_AWS_EXTERNAL_ID` into `infra/terraform/terraform.tfvars` as:

   ```hcl
   snowflake_storage_aws_iam_user_arn = "..."
   snowflake_storage_aws_external_id  = "..."
   ```

4. Re-apply Terraform so the IAM role trust policy grants access to Snowflake:

   ```powershell
   terraform -chdir=infra/terraform apply
   ```

5. Run the remaining SQL in `infra/snowflake/mlb_teams_snowpipe.sql` to create the file format, stage, raw table, and pipe.

6. Run `SHOW PIPES LIKE 'PIPE_MLB_TEAMS';`, copy the `notification_channel` ARN, and configure an S3 `ObjectCreated` notification for:

   - Prefix: `raw/mlb/teams/`
   - Suffix: `.jsonl`
   - Destination: the Snowflake-managed SQS ARN from `notification_channel`

7. Invoke the Lambda once to land the initial snapshot:

   ```powershell
   $FunctionName = terraform -chdir=infra/terraform output -raw lambda_function_name
   aws lambda invoke `
     --function-name $FunctionName `
     --payload "{}" `
     --cli-binary-format raw-in-base64-out `
     --region us-east-2 `
     response.json
   ```

8. Validate Snowpipe:

   ```sql
   SELECT SYSTEM$PIPE_STATUS('PROD.RAW.PIPE_MLB_TEAMS');

   SELECT *
   FROM TABLE(PROD.INFORMATION_SCHEMA.COPY_HISTORY(
     TABLE_NAME => 'RAW_MLB_TEAMS',
     START_TIME => DATEADD('hour', -2, CURRENT_TIMESTAMP()),
     PIPE_NAME => 'PIPE_MLB_TEAMS'
   ));

   SELECT COUNT(*) FROM PROD.RAW.RAW_MLB_TEAMS;
   ```

9. Run dbt:

   ```powershell
   dbt run --project-dir dbt --profiles-dir dbt --select stg_mlb_teams dim_mlb_teams
   dbt test --project-dir dbt --profiles-dir dbt --select stg_mlb_teams dim_mlb_teams
   ```

## Manual Refresh

When team metadata needs refreshing:

1. Invoke the Lambda once.
2. Confirm the new S3 URI in `response.json`.
3. Check Snowpipe load history.
4. Run dbt for `stg_mlb_teams` and `dim_mlb_teams`.

If a file is written before S3 notifications are configured, run:

```sql
ALTER PIPE PROD.RAW.PIPE_MLB_TEAMS REFRESH;
```

For files older than Snowpipe's refresh window, run a manual `COPY INTO` from `STG_MLB_TEAMS`.
