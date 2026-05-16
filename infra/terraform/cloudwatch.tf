resource "aws_cloudwatch_log_group" "mlb_teams_lambda" {
  name              = "/aws/lambda/${local.mlb_teams_name}"
  retention_in_days = var.log_retention_days
}

resource "aws_cloudwatch_log_group" "kalshi_events_lambda" {
  name              = "/aws/lambda/${local.kalshi_events_name}"
  retention_in_days = var.log_retention_days
}

resource "aws_cloudwatch_log_group" "kalshi_series_lambda" {
  name              = "/aws/lambda/${local.kalshi_series_name}"
  retention_in_days = var.log_retention_days
}
