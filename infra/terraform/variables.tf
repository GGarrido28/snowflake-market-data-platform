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
  description = "Optional AWS Secrets Manager secret ARN containing the Kalshi API key id and private key PEM. When set, Terraform creates a least-privilege read policy for future Kalshi ingestion Lambdas."
  type        = string
  default     = null
}

variable "lambda_timeout_seconds" {
  description = "Timeout for the MLB teams Lambda function."
  type        = number
  default     = 60
}

variable "lambda_memory_mb" {
  description = "Memory size for the MLB teams Lambda function."
  type        = number
  default     = 512
}

variable "log_retention_days" {
  description = "CloudWatch log retention for the MLB teams Lambda."
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
