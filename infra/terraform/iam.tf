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

resource "aws_iam_role" "kalshi_markets_lambda" {
  name               = "${local.kalshi_markets_name}-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

resource "aws_iam_role_policy_attachment" "kalshi_markets_lambda_basic" {
  role       = aws_iam_role.kalshi_markets_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "kalshi_markets_s3_write" {
  statement {
    sid    = "WriteKalshiMarketsLandingObjects"
    effect = "Allow"

    actions = [
      "s3:AbortMultipartUpload",
      "s3:PutObject",
    ]

    resources = [
      "${data.aws_s3_bucket.landing.arn}/${local.kalshi_markets_s3_prefix}/*",
      "${data.aws_s3_bucket.landing.arn}/${local.kalshi_market_orderbooks_s3_prefix}/*",
      "${data.aws_s3_bucket.landing.arn}/${local.kalshi_market_trades_s3_prefix}/*",
    ]
  }

  statement {
    sid    = "ReadWriteKalshiMarketTradeState"
    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:PutObject",
    ]

    resources = [
      "${data.aws_s3_bucket.landing.arn}/${local.kalshi_market_trades_state_prefix}/*",
    ]
  }

  statement {
    sid    = "ListKalshiMarketTradeStatePrefix"
    effect = "Allow"

    actions = [
      "s3:ListBucket",
    ]

    resources = [
      data.aws_s3_bucket.landing.arn,
    ]

    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = ["${local.kalshi_market_trades_state_prefix}/*"]
    }
  }
}

resource "aws_iam_policy" "kalshi_markets_s3_write" {
  name        = "${local.kalshi_markets_name}-s3-write"
  description = "Allows the Kalshi markets Lambda to write landing files to S3."
  policy      = data.aws_iam_policy_document.kalshi_markets_s3_write.json
}

resource "aws_iam_role_policy_attachment" "kalshi_markets_s3_write" {
  role       = aws_iam_role.kalshi_markets_lambda.name
  policy_arn = aws_iam_policy.kalshi_markets_s3_write.arn
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

resource "aws_iam_role" "kalshi_events_scheduler" {
  name               = "${local.kalshi_events_name}-scheduler-role"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume_role.json
}

data "aws_iam_policy_document" "kalshi_events_scheduler_invoke" {
  statement {
    sid    = "InvokeKalshiEventsLambda"
    effect = "Allow"

    actions = ["lambda:InvokeFunction"]

    resources = [aws_lambda_function.kalshi_events.arn]
  }
}

resource "aws_iam_policy" "kalshi_events_scheduler_invoke" {
  name        = "${local.kalshi_events_name}-scheduler-invoke"
  description = "Allows EventBridge Scheduler to invoke only the Kalshi events Lambda."
  policy      = data.aws_iam_policy_document.kalshi_events_scheduler_invoke.json
}

resource "aws_iam_role_policy_attachment" "kalshi_events_scheduler_invoke" {
  role       = aws_iam_role.kalshi_events_scheduler.name
  policy_arn = aws_iam_policy.kalshi_events_scheduler_invoke.arn
}

resource "aws_iam_role" "kalshi_series_scheduler" {
  name               = "${local.kalshi_series_name}-scheduler-role"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume_role.json
}

data "aws_iam_policy_document" "kalshi_series_scheduler_invoke" {
  statement {
    sid    = "InvokeKalshiSeriesLambda"
    effect = "Allow"

    actions = ["lambda:InvokeFunction"]

    resources = [aws_lambda_function.kalshi_series.arn]
  }
}

resource "aws_iam_policy" "kalshi_series_scheduler_invoke" {
  name        = "${local.kalshi_series_name}-scheduler-invoke"
  description = "Allows EventBridge Scheduler to invoke only the Kalshi series Lambda."
  policy      = data.aws_iam_policy_document.kalshi_series_scheduler_invoke.json
}

resource "aws_iam_role_policy_attachment" "kalshi_series_scheduler_invoke" {
  role       = aws_iam_role.kalshi_series_scheduler.name
  policy_arn = aws_iam_policy.kalshi_series_scheduler_invoke.arn
}

resource "aws_iam_role" "kalshi_markets_scheduler" {
  name               = "${local.kalshi_markets_name}-scheduler-role"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume_role.json
}

data "aws_iam_policy_document" "kalshi_markets_scheduler_invoke" {
  statement {
    sid    = "InvokeKalshiMarketsLambda"
    effect = "Allow"

    actions = ["lambda:InvokeFunction"]

    resources = [aws_lambda_function.kalshi_markets.arn]
  }
}

resource "aws_iam_policy" "kalshi_markets_scheduler_invoke" {
  name        = "${local.kalshi_markets_name}-scheduler-invoke"
  description = "Allows EventBridge Scheduler to invoke only the Kalshi markets Lambda."
  policy      = data.aws_iam_policy_document.kalshi_markets_scheduler_invoke.json
}

resource "aws_iam_role_policy_attachment" "kalshi_markets_scheduler_invoke" {
  role       = aws_iam_role.kalshi_markets_scheduler.name
  policy_arn = aws_iam_policy.kalshi_markets_scheduler_invoke.arn
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

resource "aws_iam_role_policy_attachment" "kalshi_markets_kalshi_api_secret_read" {
  count = length(local.kalshi_api_secret_resource_arns) > 0 ? 1 : 0

  role       = aws_iam_role.kalshi_markets_lambda.name
  policy_arn = aws_iam_policy.kalshi_api_secret_read[0].arn
}

data "aws_iam_policy_document" "kalshi_markets_snowflake_private_key_secret_read" {
  count = length(local.kalshi_markets_snowflake_private_key_secret_resource_arns) > 0 ? 1 : 0

  statement {
    sid    = "ReadSnowflakePrivateKeySecret"
    effect = "Allow"

    actions = [
      "secretsmanager:GetSecretValue",
    ]

    resources = local.kalshi_markets_snowflake_private_key_secret_resource_arns
  }
}

resource "aws_iam_policy" "kalshi_markets_snowflake_private_key_secret_read" {
  count = length(local.kalshi_markets_snowflake_private_key_secret_resource_arns) > 0 ? 1 : 0

  name        = "${local.kalshi_markets_name}-snowflake-private-key-read"
  description = "Allows the Kalshi markets Lambda to read its Snowflake private key from AWS Secrets Manager."
  policy      = data.aws_iam_policy_document.kalshi_markets_snowflake_private_key_secret_read[0].json

  tags = merge(var.tags, {
    Purpose = "kalshi-markets-snowflake-private-key-read"
  })
}

resource "aws_iam_role_policy_attachment" "kalshi_markets_snowflake_private_key_secret_read" {
  count = length(local.kalshi_markets_snowflake_private_key_secret_resource_arns) > 0 ? 1 : 0

  role       = aws_iam_role.kalshi_markets_lambda.name
  policy_arn = aws_iam_policy.kalshi_markets_snowflake_private_key_secret_read[0].arn
}
