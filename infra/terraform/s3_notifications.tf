locals {
  base_snowpipe_notification_channels = {
    mlb_teams     = trimspace(coalesce(var.mlb_teams_pipe_notification_channel, ""))
    kalshi_events = trimspace(coalesce(var.kalshi_events_pipe_notification_channel, ""))
    kalshi_series = trimspace(coalesce(var.kalshi_series_pipe_notification_channel, ""))
  }

  kalshi_market_snowpipe_notification_channels = {
    kalshi_markets           = trimspace(coalesce(var.kalshi_markets_pipe_notification_channel, ""))
    kalshi_market_orderbooks = trimspace(coalesce(var.kalshi_market_orderbooks_pipe_notification_channel, ""))
    kalshi_market_trades     = trimspace(coalesce(var.kalshi_market_trades_pipe_notification_channel, ""))
  }

  provided_base_snowpipe_notification_channels = [
    for channel in values(local.base_snowpipe_notification_channels) : channel
    if channel != ""
  ]

  provided_kalshi_market_snowpipe_notification_channels = [
    for channel in values(local.kalshi_market_snowpipe_notification_channels) : channel
    if channel != ""
  ]

  provided_snowpipe_notification_channels = concat(
    local.provided_base_snowpipe_notification_channels,
    local.provided_kalshi_market_snowpipe_notification_channels,
  )

  manage_snowpipe_bucket_notifications = length(local.provided_base_snowpipe_notification_channels) == 3
  manage_kalshi_market_snowpipe_bucket_notifications = (
    local.manage_snowpipe_bucket_notifications
    && length(local.provided_kalshi_market_snowpipe_notification_channels) == 3
  )

  base_snowpipe_bucket_notifications = {
    mlb_teams = {
      id            = "snowpipe-mlb-teams"
      queue_arn     = local.base_snowpipe_notification_channels.mlb_teams
      filter_prefix = "${local.s3_prefix}/"
    }
    kalshi_events = {
      id            = "snowpipe-kalshi-events"
      queue_arn     = local.base_snowpipe_notification_channels.kalshi_events
      filter_prefix = "${local.kalshi_events_s3_prefix}/"
    }
    kalshi_series = {
      id            = "snowpipe-kalshi-series"
      queue_arn     = local.base_snowpipe_notification_channels.kalshi_series
      filter_prefix = "${local.kalshi_series_s3_prefix}/"
    }
  }

  kalshi_market_snowpipe_bucket_notifications = {
    kalshi_markets = {
      id            = "snowpipe-kalshi-markets"
      queue_arn     = local.kalshi_market_snowpipe_notification_channels.kalshi_markets
      filter_prefix = "${local.kalshi_markets_s3_prefix}/"
    }
    kalshi_market_orderbooks = {
      id            = "snowpipe-kalshi-market-orderbooks"
      queue_arn     = local.kalshi_market_snowpipe_notification_channels.kalshi_market_orderbooks
      filter_prefix = "${local.kalshi_market_orderbooks_s3_prefix}/"
    }
    kalshi_market_trades = {
      id            = "snowpipe-kalshi-market-trades"
      queue_arn     = local.kalshi_market_snowpipe_notification_channels.kalshi_market_trades
      filter_prefix = "${local.kalshi_market_trades_s3_prefix}/"
    }
  }

  snowpipe_bucket_notifications = local.manage_snowpipe_bucket_notifications ? merge(
    local.base_snowpipe_bucket_notifications,
    local.manage_kalshi_market_snowpipe_bucket_notifications ? local.kalshi_market_snowpipe_bucket_notifications : {},
  ) : {}
}

resource "aws_s3_bucket_notification" "snowpipe" {
  count = local.manage_snowpipe_bucket_notifications ? 1 : 0

  bucket = data.aws_s3_bucket.landing.id

  lifecycle {
    prevent_destroy = true
  }

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
