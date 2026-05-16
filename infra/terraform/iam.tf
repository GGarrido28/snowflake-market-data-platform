data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "mlb_teams_lambda" {
  name               = "${local.mlb_teams_name}-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

resource "aws_iam_role_policy_attachment" "mlb_teams_lambda_basic" {
  role       = aws_iam_role.mlb_teams_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "mlb_teams_s3_write" {
  statement {
    sid    = "WriteMlbTeamsLandingObjects"
    effect = "Allow"

    actions = [
      "s3:AbortMultipartUpload",
      "s3:PutObject",
    ]

    resources = [
      "${data.aws_s3_bucket.landing.arn}/${local.s3_prefix}/*",
    ]
  }
}

resource "aws_iam_policy" "mlb_teams_s3_write" {
  name        = "${local.mlb_teams_name}-s3-write"
  description = "Allows the MLB teams Lambda to write landing files to S3."
  policy      = data.aws_iam_policy_document.mlb_teams_s3_write.json
}

resource "aws_iam_role_policy_attachment" "mlb_teams_s3_write" {
  role       = aws_iam_role.mlb_teams_lambda.name
  policy_arn = aws_iam_policy.mlb_teams_s3_write.arn
}

resource "aws_iam_role" "kalshi_events_lambda" {
  name               = "${local.kalshi_events_name}-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

resource "aws_iam_role_policy_attachment" "kalshi_events_lambda_basic" {
  role       = aws_iam_role.kalshi_events_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "kalshi_events_s3_write" {
  statement {
    sid    = "WriteKalshiEventsLandingObjects"
    effect = "Allow"

    actions = [
      "s3:AbortMultipartUpload",
      "s3:PutObject",
    ]

    resources = [
      "${data.aws_s3_bucket.landing.arn}/${local.kalshi_events_s3_prefix}/*",
    ]
  }
}

resource "aws_iam_policy" "kalshi_events_s3_write" {
  name        = "${local.kalshi_events_name}-s3-write"
  description = "Allows the Kalshi events Lambda to write landing files to S3."
  policy      = data.aws_iam_policy_document.kalshi_events_s3_write.json
}

resource "aws_iam_role_policy_attachment" "kalshi_events_s3_write" {
  role       = aws_iam_role.kalshi_events_lambda.name
  policy_arn = aws_iam_policy.kalshi_events_s3_write.arn
}

resource "aws_iam_role" "kalshi_series_lambda" {
  name               = "${local.kalshi_series_name}-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

resource "aws_iam_role_policy_attachment" "kalshi_series_lambda_basic" {
  role       = aws_iam_role.kalshi_series_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "kalshi_series_s3_write" {
  statement {
    sid    = "WriteKalshiSeriesLandingObjects"
    effect = "Allow"

    actions = [
      "s3:AbortMultipartUpload",
      "s3:PutObject",
    ]

    resources = [
      "${data.aws_s3_bucket.landing.arn}/${local.kalshi_series_s3_prefix}/*",
    ]
  }
}

resource "aws_iam_policy" "kalshi_series_s3_write" {
  name        = "${local.kalshi_series_name}-s3-write"
  description = "Allows the Kalshi series Lambda to write landing files to S3."
  policy      = data.aws_iam_policy_document.kalshi_series_s3_write.json
}

resource "aws_iam_role_policy_attachment" "kalshi_series_s3_write" {
  role       = aws_iam_role.kalshi_series_lambda.name
  policy_arn = aws_iam_policy.kalshi_series_s3_write.arn
}

data "aws_iam_policy_document" "scheduler_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "mlb_teams_scheduler" {
  name               = "${local.mlb_teams_name}-scheduler-role"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume_role.json
}

data "aws_iam_policy_document" "mlb_teams_scheduler_invoke" {
  statement {
    sid    = "InvokeMlbTeamsLambda"
    effect = "Allow"

    actions = ["lambda:InvokeFunction"]

    resources = [aws_lambda_function.mlb_teams.arn]
  }
}

resource "aws_iam_policy" "mlb_teams_scheduler_invoke" {
  name        = "${local.mlb_teams_name}-scheduler-invoke"
  description = "Allows EventBridge Scheduler to invoke the MLB teams Lambda."
  policy      = data.aws_iam_policy_document.mlb_teams_scheduler_invoke.json
}

resource "aws_iam_role_policy_attachment" "mlb_teams_scheduler_invoke" {
  role       = aws_iam_role.mlb_teams_scheduler.name
  policy_arn = aws_iam_policy.mlb_teams_scheduler_invoke.arn
}

data "aws_iam_policy_document" "kalshi_api_secret_read" {
  count = length(local.kalshi_api_secret_resource_arns) > 0 ? 1 : 0

  statement {
    sid    = "ReadKalshiApiSecret"
    effect = "Allow"

    actions = [
      "secretsmanager:GetSecretValue",
    ]

    resources = local.kalshi_api_secret_resource_arns
  }
}

resource "aws_iam_policy" "kalshi_api_secret_read" {
  count = length(local.kalshi_api_secret_resource_arns) > 0 ? 1 : 0

  name        = "${local.name_prefix}-kalshi-api-secret-read"
  description = "Allows a Kalshi ingestion Lambda to read its API credentials from AWS Secrets Manager."
  policy      = data.aws_iam_policy_document.kalshi_api_secret_read[0].json

  tags = merge(var.tags, {
    Purpose = "kalshi-api-secret-read"
  })
}

resource "aws_iam_role_policy_attachment" "kalshi_events_kalshi_api_secret_read" {
  count = length(local.kalshi_api_secret_resource_arns) > 0 ? 1 : 0

  role       = aws_iam_role.kalshi_events_lambda.name
  policy_arn = aws_iam_policy.kalshi_api_secret_read[0].arn
}

resource "aws_iam_role_policy_attachment" "kalshi_series_kalshi_api_secret_read" {
  count = length(local.kalshi_api_secret_resource_arns) > 0 ? 1 : 0

  role       = aws_iam_role.kalshi_series_lambda.name
  policy_arn = aws_iam_policy.kalshi_api_secret_read[0].arn
}
