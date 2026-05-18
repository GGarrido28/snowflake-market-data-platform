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

resource "aws_scheduler_schedule" "kalshi_events" {
  name        = "${local.kalshi_events_name}-schedule"
  description = "Runs ${local.kalshi_events_name} hourly with the configured conservative scope."
  state       = var.kalshi_events_schedule_state

  schedule_expression          = var.kalshi_events_schedule_expression
  schedule_expression_timezone = var.kalshi_events_schedule_timezone

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.kalshi_events.arn
    role_arn = aws_iam_role.kalshi_events_scheduler.arn

    input = jsonencode({
      for key, value in local.kalshi_events_schedule_input : key => value
      if value != null
    })
  }

  depends_on = [
    aws_iam_role_policy_attachment.kalshi_events_scheduler_invoke,
  ]
}

resource "aws_scheduler_schedule" "kalshi_series" {
  name        = "${local.kalshi_series_name}-schedule"
  description = "Runs ${local.kalshi_series_name} hourly with the configured conservative scope."
  state       = var.kalshi_series_schedule_state

  schedule_expression          = var.kalshi_series_schedule_expression
  schedule_expression_timezone = var.kalshi_series_schedule_timezone

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.kalshi_series.arn
    role_arn = aws_iam_role.kalshi_series_scheduler.arn

    input = jsonencode({
      for key, value in local.kalshi_series_schedule_input : key => value
      if value != null
    })
  }

  depends_on = [
    aws_iam_role_policy_attachment.kalshi_series_scheduler_invoke,
  ]
}

resource "aws_scheduler_schedule" "kalshi_markets" {
  name        = "${local.kalshi_markets_name}-schedule"
  description = "Runs ${local.kalshi_markets_name} at 15 and 45 minutes past each hour with a bounded markets scope."
  state       = var.kalshi_markets_schedule_state

  schedule_expression          = var.kalshi_markets_schedule_expression
  schedule_expression_timezone = var.kalshi_markets_schedule_timezone

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.kalshi_markets.arn
    role_arn = aws_iam_role.kalshi_markets_scheduler.arn

    input = jsonencode({
      for key, value in local.kalshi_markets_schedule_input : key => value
      if value != null
    })
  }

  depends_on = [
    aws_iam_role_policy_attachment.kalshi_markets_scheduler_invoke,
  ]
}
