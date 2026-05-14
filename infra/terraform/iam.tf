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
