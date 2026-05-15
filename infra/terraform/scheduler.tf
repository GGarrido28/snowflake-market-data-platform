resource "aws_scheduler_schedule" "mlb_teams" {
  name        = "${local.mlb_teams_name}-schedule"
  description = "Runs ${local.mlb_teams_name} on the configured schedule."
  state       = var.mlb_teams_schedule_state

  schedule_expression          = var.mlb_teams_schedule_expression
  schedule_expression_timezone = var.mlb_teams_schedule_timezone

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.mlb_teams.arn
    role_arn = aws_iam_role.mlb_teams_scheduler.arn

    input = jsonencode({
      sport_id  = var.mlb_teams_sport_id
      s3_bucket = var.s3_bucket_name
      s3_prefix = local.s3_prefix
    })
  }

  depends_on = [
    aws_iam_role_policy_attachment.mlb_teams_scheduler_invoke,
  ]
}
