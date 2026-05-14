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
