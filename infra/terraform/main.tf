locals {
  name_prefix    = "${var.project_name}-${var.environment}"
  mlb_teams_name = "${local.name_prefix}-mlb-teams"
  s3_prefix      = trim(var.s3_prefix, "/")
  image_uri      = "${aws_ecr_repository.mlb_teams.repository_url}:${var.lambda_image_tag}"
}

data "aws_s3_bucket" "landing" {
  bucket = var.s3_bucket_name
}
