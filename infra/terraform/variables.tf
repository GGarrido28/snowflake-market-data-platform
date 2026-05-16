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

variable "lambda_timeout_seconds" {
  description = "Timeout for managed Lambda functions."
  type        = number
  default     = 60
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
