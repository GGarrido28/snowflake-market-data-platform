locals {
  name_prefix              = "${var.project_name}-${var.environment}"
  mlb_teams_name           = "${local.name_prefix}-mlb-teams"
  kalshi_events_name       = "${local.name_prefix}-kalshi-events"
  kalshi_series_name       = "${local.name_prefix}-kalshi-series"
  kalshi_markets_name      = "${local.name_prefix}-kalshi-markets"
  s3_prefix                = trim(var.s3_prefix, "/")
  kalshi_events_s3_prefix  = trim(var.kalshi_events_s3_prefix, "/")
  kalshi_series_s3_prefix  = trim(var.kalshi_series_s3_prefix, "/")
  kalshi_markets_s3_prefix = trim(var.kalshi_markets_s3_prefix, "/")
  kalshi_market_orderbooks_s3_prefix = trim(
    var.kalshi_market_orderbooks_s3_prefix,
    "/",
  )
  kalshi_market_trades_s3_prefix = trim(var.kalshi_market_trades_s3_prefix, "/")
  image_uri                      = "${aws_ecr_repository.mlb_teams.repository_url}:${var.lambda_image_tag}"
  snowflake_s3_read_prefixes = [
    local.s3_prefix,
    local.kalshi_events_s3_prefix,
    local.kalshi_series_s3_prefix,
    local.kalshi_markets_s3_prefix,
    local.kalshi_market_orderbooks_s3_prefix,
    local.kalshi_market_trades_s3_prefix,
  ]
  kalshi_secret_environment = merge(
    var.kalshi_api_secret_arn != null && var.kalshi_api_secret_arn != "" ? { KALSHI_SECRET_ARN = var.kalshi_api_secret_arn } : {},
    var.kalshi_api_secret_name != null && var.kalshi_api_secret_name != "" ? { KALSHI_SECRET_NAME = var.kalshi_api_secret_name } : {}
  )
  kalshi_events_scope_environment = merge(
    var.kalshi_events_event_ticker != null && var.kalshi_events_event_ticker != "" ? { KALSHI_EVENTS_EVENT_TICKER = var.kalshi_events_event_ticker } : {},
    length(var.kalshi_events_series_tickers) > 0 ? { KALSHI_EVENTS_SERIES_TICKERS = join(",", var.kalshi_events_series_tickers) } : {}
  )
  kalshi_series_scope_environment = merge(
    var.kalshi_series_ticker != null && var.kalshi_series_ticker != ""
    ? { KALSHI_SERIES_TICKER = var.kalshi_series_ticker }
    : {},
    length(var.kalshi_series_tags) > 0 ? { KALSHI_SERIES_TAGS = join(",", var.kalshi_series_tags) } : {}
  )
  kalshi_markets_scope_environment = merge(
    var.kalshi_markets_market_ticker != null && var.kalshi_markets_market_ticker != "" ? { KALSHI_MARKET_TICKER = var.kalshi_markets_market_ticker } : {},
    var.kalshi_markets_event_ticker != null && var.kalshi_markets_event_ticker != "" ? { KALSHI_EVENT_TICKER = var.kalshi_markets_event_ticker } : {},
    var.kalshi_markets_event_query_file != null && var.kalshi_markets_event_query_file != "" ? { KALSHI_MARKETS_EVENT_QUERY_FILE = var.kalshi_markets_event_query_file } : {}
  )
  kalshi_markets_manual_invoke_payload = merge(
    {
      s3_bucket                   = var.s3_bucket_name
      markets_s3_prefix           = local.kalshi_markets_s3_prefix
      market_orderbooks_s3_prefix = local.kalshi_market_orderbooks_s3_prefix
      market_trades_s3_prefix     = local.kalshi_market_trades_s3_prefix
      paginate_trades             = var.kalshi_markets_paginate_trades
    },
    var.kalshi_markets_market_ticker != null && var.kalshi_markets_market_ticker != "" ? { market_ticker = var.kalshi_markets_market_ticker } : {},
    var.kalshi_markets_event_ticker != null && var.kalshi_markets_event_ticker != "" ? { event_ticker = var.kalshi_markets_event_ticker } : {},
    var.kalshi_markets_event_query_file != null && var.kalshi_markets_event_query_file != "" ? { event_query_file = var.kalshi_markets_event_query_file } : {}
  )
  kalshi_events_schedule_input = {
    s3_bucket      = var.s3_bucket_name
    s3_prefix      = local.kalshi_events_s3_prefix
    status         = var.kalshi_events_status
    event_ticker   = var.kalshi_events_event_ticker != null && var.kalshi_events_event_ticker != "" ? var.kalshi_events_event_ticker : null
    series_tickers = var.kalshi_events_event_ticker != null && var.kalshi_events_event_ticker != "" ? null : var.kalshi_events_series_tickers
  }
  kalshi_series_schedule_input = {
    s3_bucket     = var.s3_bucket_name
    s3_prefix     = local.kalshi_series_s3_prefix
    series_ticker = var.kalshi_series_ticker != null && var.kalshi_series_ticker != "" ? var.kalshi_series_ticker : null
    tags          = var.kalshi_series_ticker != null && var.kalshi_series_ticker != "" ? null : var.kalshi_series_tags
  }
  kalshi_api_secret_resource_arns = concat(
    var.kalshi_api_secret_arn != null && var.kalshi_api_secret_arn != "" ? [var.kalshi_api_secret_arn] : [],
    var.kalshi_api_secret_name != null && var.kalshi_api_secret_name != "" ? [data.aws_secretsmanager_secret.kalshi_api[0].arn] : []
  )
}

data "aws_s3_bucket" "landing" {
  bucket = var.s3_bucket_name
}

data "aws_secretsmanager_secret" "kalshi_api" {
  count = var.kalshi_api_secret_name != null && var.kalshi_api_secret_name != "" ? 1 : 0

  name = var.kalshi_api_secret_name
}
