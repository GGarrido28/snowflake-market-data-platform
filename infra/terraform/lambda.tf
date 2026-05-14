resource "aws_lambda_function" "mlb_teams" {
  function_name = local.mlb_teams_name
  role          = aws_iam_role.mlb_teams_lambda.arn
  package_type  = "Image"
  image_uri     = local.image_uri

  architectures = ["x86_64"]
  memory_size   = var.lambda_memory_mb
  timeout       = var.lambda_timeout_seconds

  environment {
    variables = {
      MLB_TEAMS_S3_BUCKET = var.s3_bucket_name
      MLB_TEAMS_S3_PREFIX = local.s3_prefix
      MLB_TEAMS_SPORT_ID  = var.mlb_teams_sport_id
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.mlb_teams_lambda,
    aws_iam_role_policy_attachment.mlb_teams_lambda_basic,
    aws_iam_role_policy_attachment.mlb_teams_s3_write,
  ]
}
