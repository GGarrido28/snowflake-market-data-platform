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

output "mlb_teams_schedule_name" {
  description = "EventBridge Scheduler schedule name for the MLB teams Lambda."
  value       = aws_scheduler_schedule.mlb_teams.name
}

output "snowflake_s3_read_role_arn" {
  description = "IAM role ARN to use in the Snowflake MLB teams storage integration."
  value       = aws_iam_role.snowflake_s3_read.arn
}
