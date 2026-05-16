output "ecr_repository_url" {
  description = "ECR repository URL for the MLB teams Lambda image."
  value       = aws_ecr_repository.mlb_teams.repository_url
}

output "lambda_function_name" {
  description = "MLB teams Lambda function name."
  value       = aws_lambda_function.mlb_teams.function_name
}

output "lambda_image_uri" {
  description = "Container image URI Terraform expects Lambda to use."
  value       = local.image_uri
}

output "landing_s3_uri" {
  description = "S3 prefix where the MLB teams Lambda writes NDJSON files."
  value       = "s3://${var.s3_bucket_name}/${local.s3_prefix}/"
}

output "kalshi_events_lambda_function_name" {
  description = "Kalshi events Lambda function name for manual invocation."
  value       = aws_lambda_function.kalshi_events.function_name
}

output "kalshi_series_lambda_function_name" {
  description = "Kalshi series Lambda function name for manual invocation."
  value       = aws_lambda_function.kalshi_series.function_name
}

output "kalshi_events_landing_s3_uri" {
  description = "S3 prefix where the Kalshi events Lambda writes NDJSON files."
  value       = "s3://${var.s3_bucket_name}/${local.kalshi_events_s3_prefix}/"
}

output "kalshi_series_landing_s3_uri" {
  description = "S3 prefix where the Kalshi series Lambda writes NDJSON files."
  value       = "s3://${var.s3_bucket_name}/${local.kalshi_series_s3_prefix}/"
}

output "mlb_teams_schedule_name" {
  description = "EventBridge Scheduler schedule name for the MLB teams Lambda."
  value       = aws_scheduler_schedule.mlb_teams.name
}

output "kalshi_events_schedule_name" {
  description = "EventBridge Scheduler schedule name for the Kalshi events Lambda."
  value       = aws_scheduler_schedule.kalshi_events.name
}

output "kalshi_series_schedule_name" {
  description = "EventBridge Scheduler schedule name for the Kalshi series Lambda."
  value       = aws_scheduler_schedule.kalshi_series.name
}

output "snowflake_s3_read_role_arn" {
  description = "IAM role ARN to use in Snowflake storage integrations for managed landing prefixes."
  value       = aws_iam_role.snowflake_s3_read.arn
}

output "kalshi_api_secret_read_policy_arn" {
  description = "Optional IAM policy ARN that grants read access to the configured Kalshi API secret."
  value = (
    length(local.kalshi_api_secret_resource_arns) == 0
    ? null
    : aws_iam_policy.kalshi_api_secret_read[0].arn
  )
}
