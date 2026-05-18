from market_data_platform.pipelines.kalshi.markets_landing import run


def lambda_handler(event, context):
    return run(event or {})
