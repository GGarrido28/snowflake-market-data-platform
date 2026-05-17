locals {
  snowpipe_notification_channels = {
    mlb_teams     = trimspace(coalesce(var.mlb_teams_pipe_notification_channel, ""))
    kalshi_events = trimspace(coalesce(var.kalshi_events_pipe_notification_channel, ""))
    kalshi_series = trimspace(coalesce(var.kalshi_series_pipe_notification_channel, ""))
  }

  provided_snowpipe_notification_channels = [
    for channel in values(local.snowpipe_notification_channels) : channel
    if channel != ""
  ]

  manage_snowpipe_bucket_notifications = length(local.provided_snowpipe_notification_channels) == 3

  snowpipe_bucket_notifications = local.manage_snowpipe_bucket_notifications ? {
    mlb_teams = {
      id            = "snowpipe-mlb-teams"
      queue_arn     = local.snowpipe_notification_channels.mlb_teams
      filter_prefix = "${local.s3_prefix}/"
    }
    kalshi_events = {
      id            = "snowpipe-kalshi-events"
      queue_arn     = local.snowpipe_notification_channels.kalshi_events
      filter_prefix = "${local.kalshi_events_s3_prefix}/"
    }
    kalshi_series = {
      id            = "snowpipe-kalshi-series"
      queue_arn     = local.snowpipe_notification_channels.kalshi_series
      filter_prefix = "${local.kalshi_series_s3_prefix}/"
    }
  } : {}
}

resource "aws_s3_bucket_notification" "snowpipe" {
  count = local.manage_snowpipe_bucket_notifications ? 1 : 0

  bucket = data.aws_s3_bucket.landing.id

  dynamic "queue" {
    for_each = local.snowpipe_bucket_notifications

    content {
      id            = queue.value.id
      queue_arn     = queue.value.queue_arn
      events        = ["s3:ObjectCreated:*"]
      filter_prefix = queue.value.filter_prefix
      filter_suffix = ".jsonl"
    }
  }
}
