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

resource "aws_lambda_function" "kalshi_events" {
  function_name = local.kalshi_events_name
  role          = aws_iam_role.kalshi_events_lambda.arn
  package_type  = "Image"
  image_uri     = local.image_uri

  architectures = ["x86_64"]
  memory_size   = var.lambda_memory_mb
  timeout       = var.lambda_timeout_seconds

  image_config {
    command = ["aws.lambdas.kalshi_events.handler.lambda_handler"]
  }

  environment {
    variables = merge(
      {
        KALSHI_EVENTS_S3_BUCKET = var.s3_bucket_name
        KALSHI_EVENTS_S3_PREFIX = local.kalshi_events_s3_prefix
        KALSHI_EVENTS_STATUS    = var.kalshi_events_status
      },
      local.kalshi_secret_environment,
      local.kalshi_events_scope_environment,
    )
  }

  depends_on = [
    aws_cloudwatch_log_group.kalshi_events_lambda,
    aws_iam_role_policy_attachment.kalshi_events_lambda_basic,
    aws_iam_role_policy_attachment.kalshi_events_s3_write,
    aws_iam_role_policy_attachment.kalshi_events_kalshi_api_secret_read,
  ]
}

resource "aws_lambda_function" "kalshi_series" {
  function_name = local.kalshi_series_name
  role          = aws_iam_role.kalshi_series_lambda.arn
  package_type  = "Image"
  image_uri     = local.image_uri

  architectures = ["x86_64"]
  memory_size   = var.lambda_memory_mb
  timeout       = var.lambda_timeout_seconds

  image_config {
    command = ["aws.lambdas.kalshi_series.handler.lambda_handler"]
  }

  environment {
    variables = merge(
      {
        KALSHI_SERIES_S3_BUCKET = var.s3_bucket_name
        KALSHI_SERIES_S3_PREFIX = local.kalshi_series_s3_prefix
      },
      local.kalshi_secret_environment,
      local.kalshi_series_scope_environment,
    )
  }

  depends_on = [
    aws_cloudwatch_log_group.kalshi_series_lambda,
    aws_iam_role_policy_attachment.kalshi_series_lambda_basic,
    aws_iam_role_policy_attachment.kalshi_series_s3_write,
    aws_iam_role_policy_attachment.kalshi_series_kalshi_api_secret_read,
  ]
}
