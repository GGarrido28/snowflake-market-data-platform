"""MLB ingestion pipelines."""

from market_data_platform.pipelines.mlb.teams_pipeline import run as run_teams_pipeline


__all__ = ["run_teams_pipeline"]
