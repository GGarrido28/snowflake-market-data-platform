resource "aws_cloudwatch_log_group" "mlb_teams_lambda" {
  name              = "/aws/lambda/${local.mlb_teams_name}"
  retention_in_days = var.log_retention_days
}
