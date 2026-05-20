variable "aws_region" {
  description = "AWS region for ECR, Lambda, IAM, and CloudWatch resources."
  type        = string
  default     = "us-east-2"
}

variable "project_name" {
  description = "Short project name used in resource names."
  type        = string
  default     = "snowflake-kalshi"
}

variable "environment" {
  description = "Deployment environment suffix used in resource names."
  type        = string
  default     = "dev"
}

variable "s3_bucket_name" {
  description = "Existing S3 bucket used as the Snowflake landing area."
  type        = string
  default     = "snowflake-kalshi-project"
}

variable "s3_prefix" {
  description = "S3 key prefix the MLB teams Lambda can write under."
  type        = string
  default     = "raw/mlb/teams"
}

variable "kalshi_events_s3_prefix" {
  description = "S3 key prefix the Kalshi events Lambda can write under."
  type        = string
  default     = "raw/kalshi/events"
}

variable "kalshi_series_s3_prefix" {
  description = "S3 key prefix the Kalshi series Lambda can write under."
  type        = string
  default     = "raw/kalshi/series"
}

variable "kalshi_markets_s3_prefix" {
  description = "S3 key prefix the Kalshi markets Lambda can write market payloads under."
  type        = string
  default     = "raw/kalshi/markets"
}

variable "kalshi_market_orderbooks_s3_prefix" {
  description = "S3 key prefix the Kalshi markets Lambda can write market orderbook snapshots under."
  type        = string
  default     = "raw/kalshi/market_orderbooks"
}

variable "kalshi_market_trades_s3_prefix" {
  description = "S3 key prefix the Kalshi markets Lambda can write recent market trade payloads under."
  type        = string
  default     = "raw/kalshi/market_trades"
}

variable "kalshi_market_trades_state_prefix" {
  description = "S3 key prefix where the Kalshi markets Lambda stores non-secret market trade watermark state."
  type        = string
  default     = "state/kalshi/market_trades"
}

variable "mlb_teams_pipe_notification_channel" {
  description = "Snowflake PIPE_MLB_TEAMS notification_channel SQS ARN. Set the MLB Teams, Kalshi Events, and Kalshi Series channels together before Terraform manages bucket notifications. Set the three Kalshi market channels together when those pipes are ready."
  type        = string
  default     = null

  validation {
    condition = (
      (
        length(compact([
          trimspace(var.mlb_teams_pipe_notification_channel != null ? var.mlb_teams_pipe_notification_channel : ""),
          trimspace(var.kalshi_events_pipe_notification_channel != null ? var.kalshi_events_pipe_notification_channel : ""),
          trimspace(var.kalshi_series_pipe_notification_channel != null ? var.kalshi_series_pipe_notification_channel : ""),
        ])) == 0
        && length(compact([
          trimspace(var.kalshi_markets_pipe_notification_channel != null ? var.kalshi_markets_pipe_notification_channel : ""),
          trimspace(var.kalshi_market_orderbooks_pipe_notification_channel != null ? var.kalshi_market_orderbooks_pipe_notification_channel : ""),
          trimspace(var.kalshi_market_trades_pipe_notification_channel != null ? var.kalshi_market_trades_pipe_notification_channel : ""),
        ])) == 0
      )
      || (
        length(compact([
          trimspace(var.mlb_teams_pipe_notification_channel != null ? var.mlb_teams_pipe_notification_channel : ""),
          trimspace(var.kalshi_events_pipe_notification_channel != null ? var.kalshi_events_pipe_notification_channel : ""),
          trimspace(var.kalshi_series_pipe_notification_channel != null ? var.kalshi_series_pipe_notification_channel : ""),
        ])) == 3
        && contains(
          [0, 3],
          length(compact([
            trimspace(var.kalshi_markets_pipe_notification_channel != null ? var.kalshi_markets_pipe_notification_channel : ""),
            trimspace(var.kalshi_market_orderbooks_pipe_notification_channel != null ? var.kalshi_market_orderbooks_pipe_notification_channel : ""),
            trimspace(var.kalshi_market_trades_pipe_notification_channel != null ? var.kalshi_market_trades_pipe_notification_channel : ""),
          ]))
        )
      )
    )
    error_message = "Set the base Snowpipe notification channel ARNs together, or leave all channels null. When adding Kalshi market Snowpipe notifications, set all three market channel ARNs together. Terraform owns the bucket's full notification configuration."
  }
}

variable "kalshi_events_pipe_notification_channel" {
  description = "Snowflake PIPE_KALSHI_EVENTS notification_channel SQS ARN. Set with mlb_teams_pipe_notification_channel and kalshi_series_pipe_notification_channel before Terraform manages bucket notifications."
  type        = string
  default     = null
}

variable "kalshi_series_pipe_notification_channel" {
  description = "Snowflake PIPE_KALSHI_SERIES notification_channel SQS ARN. Set with mlb_teams_pipe_notification_channel and kalshi_events_pipe_notification_channel before Terraform manages bucket notifications."
  type        = string
  default     = null
}

variable "kalshi_markets_pipe_notification_channel" {
  description = "Snowflake PIPE_KALSHI_MARKETS notification_channel SQS ARN. Optional until market Snowpipes exist; set all three Kalshi market pipe channels together."
  type        = string
  default     = null
}

variable "kalshi_market_orderbooks_pipe_notification_channel" {
  description = "Snowflake PIPE_KALSHI_MARKET_ORDERBOOKS notification_channel SQS ARN. Optional until market Snowpipes exist; set all three Kalshi market pipe channels together."
  type        = string
  default     = null
}

variable "kalshi_market_trades_pipe_notification_channel" {
  description = "Snowflake PIPE_KALSHI_MARKET_TRADES notification_channel SQS ARN. Optional until market Snowpipes exist; set all three Kalshi market pipe channels together."
  type        = string
  default     = null
}

variable "lambda_image_tag" {
  description = "Container image tag to deploy from the managed ECR repository."
  type        = string
  default     = "latest"
}

variable "mlb_teams_sport_id" {
  description = "MLB Stats API sportId used by the teams Lambda."
  type        = string
  default     = "1"
}

variable "mlb_teams_schedule_expression" {
  description = "EventBridge Scheduler expression for the MLB teams Lambda."
  type        = string
  default     = "cron(0 6 * * ? *)"
}

variable "mlb_teams_schedule_timezone" {
  description = "Time zone used to evaluate the MLB teams schedule expression."
  type        = string
  default     = "America/Chicago"
}

variable "mlb_teams_schedule_state" {
  description = "Whether the MLB teams EventBridge Scheduler schedule is enabled. Defaults disabled because MLB teams is low-change dimension data."
  type        = string
  default     = "DISABLED"

  validation {
    condition     = contains(["ENABLED", "DISABLED"], var.mlb_teams_schedule_state)
    error_message = "mlb_teams_schedule_state must be ENABLED or DISABLED."
  }
}

variable "kalshi_events_schedule_expression" {
  description = "Hourly EventBridge Scheduler expression for the Kalshi events Lambda."
  type        = string
  default     = "cron(0 * * * ? *)"
}

variable "kalshi_events_schedule_timezone" {
  description = "Time zone used to evaluate the Kalshi events schedule expression."
  type        = string
  default     = "America/Chicago"
}

variable "kalshi_events_schedule_state" {
  description = "Whether the Kalshi events EventBridge Scheduler schedule is enabled."
  type        = string
  default     = "ENABLED"

  validation {
    condition     = contains(["ENABLED", "DISABLED"], var.kalshi_events_schedule_state)
    error_message = "kalshi_events_schedule_state must be ENABLED or DISABLED."
  }
}

variable "kalshi_series_schedule_expression" {
  description = "Hourly EventBridge Scheduler expression for the Kalshi series Lambda."
  type        = string
  default     = "cron(0 * * * ? *)"
}

variable "kalshi_series_schedule_timezone" {
  description = "Time zone used to evaluate the Kalshi series schedule expression."
  type        = string
  default     = "America/Chicago"
}

variable "kalshi_series_schedule_state" {
  description = "Whether the Kalshi series EventBridge Scheduler schedule is enabled."
  type        = string
  default     = "ENABLED"

  validation {
    condition     = contains(["ENABLED", "DISABLED"], var.kalshi_series_schedule_state)
    error_message = "kalshi_series_schedule_state must be ENABLED or DISABLED."
  }
}

variable "kalshi_markets_schedule_expression" {
  description = "Half-hour EventBridge Scheduler expression for the Kalshi markets Lambda, offset from the hourly events and series schedules."
  type        = string
  default     = "cron(15,45 * * * ? *)"
}

variable "kalshi_markets_schedule_timezone" {
  description = "Time zone used to evaluate the Kalshi markets schedule expression."
  type        = string
  default     = "America/Chicago"
}

variable "kalshi_markets_schedule_state" {
  description = "Whether the Kalshi markets EventBridge Scheduler schedule is enabled. The schedule defaults to the packaged MLB event-query SQL file when no exact market or event scope is configured."
  type        = string
  default     = "ENABLED"

  validation {
    condition     = contains(["ENABLED", "DISABLED"], var.kalshi_markets_schedule_state)
    error_message = "kalshi_markets_schedule_state must be ENABLED or DISABLED."
  }
}

variable "snowflake_storage_aws_iam_user_arn" {
  description = "Snowflake STORAGE_AWS_IAM_USER_ARN from DESC INTEGRATION. Leave null until the storage integration exists."
  type        = string
  default     = null
}

variable "snowflake_storage_aws_external_id" {
  description = "Snowflake STORAGE_AWS_EXTERNAL_ID from DESC INTEGRATION. Leave null until the storage integration exists."
  type        = string
  default     = null
}

variable "kalshi_api_secret_arn" {
  description = "Optional AWS Secrets Manager secret ARN containing the Kalshi API key id and private key PEM. When set, Terraform passes KALSHI_SECRET_ARN to the Kalshi Lambdas and grants read access to that ARN."
  type        = string
  default     = null

  validation {
    condition = !(
      var.kalshi_api_secret_arn != null && var.kalshi_api_secret_arn != ""
      && var.kalshi_api_secret_name != null && var.kalshi_api_secret_name != ""
    )
    error_message = "Set only one of kalshi_api_secret_arn or kalshi_api_secret_name."
  }
}

variable "kalshi_api_secret_name" {
  description = "Optional AWS Secrets Manager secret name containing the Kalshi API key id and private key PEM. When set, Terraform passes KALSHI_SECRET_NAME to the Kalshi Lambdas and grants read access to the resolved secret ARN."
  type        = string
  default     = null
}

variable "kalshi_events_status" {
  description = "Default Kalshi events status filter. Use all only with an event or series scope."
  type        = string
  default     = "open"
}

variable "kalshi_events_event_ticker" {
  description = "Optional exact Kalshi event ticker scope for the events Lambda."
  type        = string
  default     = null
}

variable "kalshi_events_series_tickers" {
  description = "Kalshi series tickers the events Lambda fetches when no exact event ticker is supplied."
  type        = list(string)
  default     = ["KXMLBSPREAD", "KXMLBTOTAL", "KXMLBGAME"]
}

variable "kalshi_series_ticker" {
  description = "Optional exact Kalshi series ticker scope for the series Lambda. When unset, the Lambda fetches all series pages and filters by kalshi_series_tags."
  type        = string
  default     = null
}

variable "kalshi_series_tags" {
  description = "Kalshi series tags to match when kalshi_series_ticker is unset."
  type        = list(string)
  default     = ["BaseBall"]
}

variable "kalshi_markets_market_ticker" {
  description = "Optional exact Kalshi market ticker scope for the markets Lambda. Set at most one Kalshi markets scope variable."
  type        = string
  default     = null

  validation {
    condition = length(compact([
      trimspace(var.kalshi_markets_market_ticker != null ? var.kalshi_markets_market_ticker : ""),
      trimspace(var.kalshi_markets_event_ticker != null ? var.kalshi_markets_event_ticker : ""),
      trimspace(var.kalshi_markets_event_query_file != null ? var.kalshi_markets_event_query_file : ""),
    ])) <= 1
    error_message = "Set at most one of kalshi_markets_market_ticker, kalshi_markets_event_ticker, or kalshi_markets_event_query_file."
  }
}

variable "kalshi_markets_event_ticker" {
  description = "Optional exact Kalshi event ticker scope for the markets Lambda."
  type        = string
  default     = null
}

variable "kalshi_markets_event_query_file" {
  description = "Optional SQL file path whose event_ticker column scopes the markets Lambda. Requires the Kalshi markets Snowflake account, user, and private-key secret variables."
  type        = string
  default     = null

  validation {
    condition = (
      trimspace(var.kalshi_markets_event_query_file != null ? var.kalshi_markets_event_query_file : "") == ""
      || (
        trimspace(var.kalshi_markets_snowflake_account != null ? var.kalshi_markets_snowflake_account : "") != ""
        && trimspace(var.kalshi_markets_snowflake_user != null ? var.kalshi_markets_snowflake_user : "") != ""
        && length(compact([
          trimspace(var.kalshi_markets_snowflake_private_key_secret_arn != null ? var.kalshi_markets_snowflake_private_key_secret_arn : ""),
          trimspace(var.kalshi_markets_snowflake_private_key_secret_name != null ? var.kalshi_markets_snowflake_private_key_secret_name : ""),
        ])) == 1
      )
    )
    error_message = "kalshi_markets_event_query_file requires kalshi_markets_snowflake_account, kalshi_markets_snowflake_user, and exactly one Snowflake private-key secret ARN or name."
  }
}

variable "kalshi_markets_paginate_trades" {
  description = "Legacy manual override for full trade-history pagination per market. Keep false for scheduled automation; use kalshi_market_trades_fetch_mode instead."
  type        = bool
  default     = false
}

variable "kalshi_market_trades_fetch_mode" {
  description = "Default market trade fetch mode for the markets Lambda. incremental uses S3 watermarks; recent fetches one latest page; backfill requires explicit payload bounds."
  type        = string
  default     = "incremental"

  validation {
    condition     = contains(["incremental", "recent", "backfill", "full_history"], var.kalshi_market_trades_fetch_mode)
    error_message = "kalshi_market_trades_fetch_mode must be incremental, recent, backfill, or full_history."
  }
}

variable "kalshi_market_trades_first_run_lookback_hours" {
  description = "Bounded lookback window for a market with no existing trade watermark."
  type        = number
  default     = 24

  validation {
    condition     = var.kalshi_market_trades_first_run_lookback_hours > 0
    error_message = "kalshi_market_trades_first_run_lookback_hours must be greater than zero."
  }
}

variable "kalshi_market_trades_watermark_overlap_seconds" {
  description = "Small overlap subtracted from the last checked trade timestamp to avoid missing boundary-second trades."
  type        = number
  default     = 60

  validation {
    condition     = var.kalshi_market_trades_watermark_overlap_seconds >= 0
    error_message = "kalshi_market_trades_watermark_overlap_seconds must be greater than or equal to zero."
  }
}

variable "kalshi_markets_read_requests_per_second" {
  description = "Conservative client-side GET request cap for the Kalshi markets Lambda. Keep below Kalshi's advertised read limit to leave headroom for account-limit checks and retries."
  type        = number
  default     = 10

  validation {
    condition = (
      var.kalshi_markets_read_requests_per_second == floor(var.kalshi_markets_read_requests_per_second)
      && var.kalshi_markets_read_requests_per_second > 0
      && var.kalshi_markets_read_requests_per_second <= 20
    )
    error_message = "kalshi_markets_read_requests_per_second must be a whole number between 1 and 20."
  }
}

variable "kalshi_markets_reserved_concurrency" {
  description = "Optional reserved concurrency for the Kalshi markets Lambda. Leave null to avoid consuming account-level reserved concurrency; set to 1 or higher only when the AWS account has enough unreserved concurrency headroom."
  type        = number
  default     = null

  validation {
    condition     = var.kalshi_markets_reserved_concurrency == null || var.kalshi_markets_reserved_concurrency >= 1
    error_message = "kalshi_markets_reserved_concurrency must be null or at least 1."
  }
}

variable "kalshi_markets_snowflake_account" {
  description = "Optional Snowflake account identifier used by the markets Lambda when kalshi_markets_event_query_file is configured."
  type        = string
  default     = null
}

variable "kalshi_markets_snowflake_user" {
  description = "Optional Snowflake user used by the markets Lambda when kalshi_markets_event_query_file is configured."
  type        = string
  default     = null
}

variable "kalshi_markets_snowflake_warehouse" {
  description = "Optional Snowflake warehouse used by the markets Lambda event-query-file scope."
  type        = string
  default     = null
}

variable "kalshi_markets_snowflake_role" {
  description = "Optional Snowflake role used by the markets Lambda event-query-file scope."
  type        = string
  default     = null
}

variable "kalshi_markets_snowflake_private_key_secret_arn" {
  description = "Optional Secrets Manager secret ARN containing the Snowflake private key PEM for the markets Lambda event-query-file scope. Use either ARN or name."
  type        = string
  default     = null

  validation {
    condition = length(compact([
      trimspace(var.kalshi_markets_snowflake_private_key_secret_arn != null ? var.kalshi_markets_snowflake_private_key_secret_arn : ""),
      trimspace(var.kalshi_markets_snowflake_private_key_secret_name != null ? var.kalshi_markets_snowflake_private_key_secret_name : ""),
    ])) <= 1
    error_message = "Set only one of kalshi_markets_snowflake_private_key_secret_arn or kalshi_markets_snowflake_private_key_secret_name."
  }
}

variable "kalshi_markets_snowflake_private_key_secret_name" {
  description = "Optional Secrets Manager secret name containing the Snowflake private key PEM for the markets Lambda event-query-file scope. Use either ARN or name."
  type        = string
  default     = null
}

variable "lambda_timeout_seconds" {
  description = "Timeout for managed Lambda functions."
  type        = number
  default     = 60
}

variable "kalshi_markets_lambda_timeout_seconds" {
  description = "Timeout for the Kalshi markets Lambda. Set null to fall back to lambda_timeout_seconds."
  type        = number
  default     = 300

  validation {
    condition = var.kalshi_markets_lambda_timeout_seconds == null ? true : (
      var.kalshi_markets_lambda_timeout_seconds == floor(var.kalshi_markets_lambda_timeout_seconds)
      && var.kalshi_markets_lambda_timeout_seconds >= 1
      && var.kalshi_markets_lambda_timeout_seconds <= 900
    )
    error_message = "kalshi_markets_lambda_timeout_seconds must be null or a whole number between 1 and 900."
  }
}

variable "lambda_memory_mb" {
  description = "Memory size for managed Lambda functions."
  type        = number
  default     = 512
}

variable "log_retention_days" {
  description = "CloudWatch log retention for managed Lambda functions."
  type        = number
  default     = 14
}

variable "tags" {
  description = "Default tags applied to managed AWS resources."
  type        = map(string)
  default = {
    Project   = "snowflake-kalshi-market-data-platform"
    ManagedBy = "terraform"
  }
}
