from market_data_platform.lambda_handlers.kalshi_markets import run


def lambda_handler(event, context):
    return run(event or {})
