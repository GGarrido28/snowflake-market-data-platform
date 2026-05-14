from market_data_platform.pipelines.mlb.teams_pipeline import run


def lambda_handler(event, context):
    return run(event or {})
