from market_data_platform.pipelines.kalshi.events_landing import run


def lambda_handler(event, context):
    return run(event or {})
