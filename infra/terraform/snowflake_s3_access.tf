data "aws_caller_identity" "current" {}

locals {
  snowflake_s3_read_trusted_principal = (
    var.snowflake_storage_aws_iam_user_arn != null && var.snowflake_storage_aws_iam_user_arn != ""
    ? var.snowflake_storage_aws_iam_user_arn
    : "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
  )
  snowflake_s3_read_external_id = (
    var.snowflake_storage_aws_external_id != null && var.snowflake_storage_aws_external_id != ""
    ? var.snowflake_storage_aws_external_id
    : "0000"
  )
}

data "aws_iam_policy_document" "snowflake_s3_read_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = [local.snowflake_s3_read_trusted_principal]
    }

    actions = ["sts:AssumeRole"]

    condition {
      test     = "StringEquals"
      variable = "sts:ExternalId"
      values   = [local.snowflake_s3_read_external_id]
    }
  }
}

resource "aws_iam_role" "snowflake_s3_read" {
  name               = "${local.name_prefix}-snowflake-s3-read-role"
  assume_role_policy = data.aws_iam_policy_document.snowflake_s3_read_assume_role.json

  tags = merge(var.tags, {
    Purpose = "snowflake-s3-stage-read"
  })
}

data "aws_iam_policy_document" "snowflake_s3_read" {
  statement {
    sid    = "ReadLandingObjects"
    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:GetObjectVersion",
    ]

    resources = [
      for prefix in local.snowflake_s3_read_prefixes : "${data.aws_s3_bucket.landing.arn}/${prefix}/*"
    ]
  }

  statement {
    sid    = "ListLandingPrefixes"
    effect = "Allow"

    actions = [
      "s3:GetBucketLocation",
      "s3:ListBucket",
    ]

    resources = [data.aws_s3_bucket.landing.arn]

    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values = flatten([
        for prefix in local.snowflake_s3_read_prefixes : [
          prefix,
          "${prefix}/*",
        ]
      ])
    }
  }
}

resource "aws_iam_policy" "snowflake_s3_read" {
  name        = "${local.name_prefix}-snowflake-s3-read"
  description = "Allows Snowflake to read managed S3 landing prefixes."
  policy      = data.aws_iam_policy_document.snowflake_s3_read.json

  tags = merge(var.tags, {
    Purpose = "snowflake-s3-stage-read"
  })
}

resource "aws_iam_role_policy_attachment" "snowflake_s3_read" {
  role       = aws_iam_role.snowflake_s3_read.name
  policy_arn = aws_iam_policy.snowflake_s3_read.arn
}
