import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TERRAFORM_DIR = REPO_ROOT / "infra" / "terraform"
S3_NOTIFICATIONS_PATH = TERRAFORM_DIR / "s3_notifications.tf"
VARIABLES_PATH = TERRAFORM_DIR / "variables.tf"
TFVARS_EXAMPLE_PATH = TERRAFORM_DIR / "terraform.tfvars.example"
NOTIFICATION_RUNBOOK_PATH = REPO_ROOT / "docs" / "snowpipe_s3_notifications.md"
MLB_RUNBOOK_PATH = REPO_ROOT / "docs" / "mlb_teams_snowpipe.md"
KALSHI_RUNBOOK_PATH = REPO_ROOT / "docs" / "kalshi_events_series_snowpipe.md"
KALSHI_MARKETS_RUNBOOK_PATH = REPO_ROOT / "docs" / "kalshi_markets_snowpipe.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class SnowpipeS3NotificationTerraformTests(unittest.TestCase):
    def test_pipe_notification_channel_variables_are_declared_and_documented(self):
        variables = _read(VARIABLES_PATH)
        tfvars_example = _read(TFVARS_EXAMPLE_PATH)

        for name in (
            "mlb_teams_pipe_notification_channel",
            "kalshi_events_pipe_notification_channel",
            "kalshi_series_pipe_notification_channel",
            "kalshi_markets_pipe_notification_channel",
            "kalshi_market_orderbooks_pipe_notification_channel",
            "kalshi_market_trades_pipe_notification_channel",
        ):
            self.assertIn(f'variable "{name}"', variables)
            self.assertRegex(tfvars_example, rf"{name}\s*=\s*null")

        self.assertIn("Set the base Snowpipe notification channel ARNs together", variables)
        self.assertIn("set all three market channel ARNs together", variables)
        self.assertIn("Terraform owns the bucket's full notification configuration", variables)

    def test_bucket_notification_resource_manages_all_snowpipe_queues(self):
        terraform = _read(S3_NOTIFICATIONS_PATH)

        self.assertIn('resource "aws_s3_bucket_notification" "snowpipe"', terraform)
        self.assertIn("count = local.manage_snowpipe_bucket_notifications ? 1 : 0", terraform)
        self.assertIn("prevent_destroy = true", terraform)
        self.assertIn('events        = ["s3:ObjectCreated:*"]', terraform)
        self.assertIn('filter_suffix = ".jsonl"', terraform)

        self.assertIn('id            = "snowpipe-mlb-teams"', terraform)
        self.assertIn('id            = "snowpipe-kalshi-events"', terraform)
        self.assertIn('id            = "snowpipe-kalshi-series"', terraform)
        self.assertIn('id            = "snowpipe-kalshi-markets"', terraform)
        self.assertIn('id            = "snowpipe-kalshi-market-orderbooks"', terraform)
        self.assertIn('id            = "snowpipe-kalshi-market-trades"', terraform)
        self.assertIn('filter_prefix = "${local.s3_prefix}/"', terraform)
        self.assertIn('filter_prefix = "${local.kalshi_events_s3_prefix}/"', terraform)
        self.assertIn('filter_prefix = "${local.kalshi_series_s3_prefix}/"', terraform)
        self.assertIn('filter_prefix = "${local.kalshi_markets_s3_prefix}/"', terraform)
        self.assertIn('filter_prefix = "${local.kalshi_market_orderbooks_s3_prefix}/"', terraform)
        self.assertIn('filter_prefix = "${local.kalshi_market_trades_s3_prefix}/"', terraform)

    def test_bucket_notification_resource_is_all_or_none(self):
        terraform = _read(S3_NOTIFICATIONS_PATH)

        self.assertIn("provided_snowpipe_notification_channels", terraform)
        self.assertIn("provided_base_snowpipe_notification_channels", terraform)
        self.assertIn("provided_kalshi_market_snowpipe_notification_channels", terraform)
        self.assertIn("manage_snowpipe_bucket_notifications = length(local.provided_base_snowpipe_notification_channels) == 3", terraform)
        self.assertIn("manage_kalshi_market_snowpipe_bucket_notifications", terraform)
        self.assertIn("snowpipe_bucket_notifications = local.manage_snowpipe_bucket_notifications ?", terraform)
        self.assertIn("local.manage_kalshi_market_snowpipe_bucket_notifications ? local.kalshi_market_snowpipe_bucket_notifications : {}", terraform)

    def test_runbooks_explain_notification_adoption_and_full_bucket_ownership(self):
        notification_runbook = _read(NOTIFICATION_RUNBOOK_PATH)
        mlb_runbook = _read(MLB_RUNBOOK_PATH)
        kalshi_runbook = _read(KALSHI_RUNBOOK_PATH)
        kalshi_markets_runbook = _read(KALSHI_MARKETS_RUNBOOK_PATH)

        for text in (mlb_runbook, kalshi_runbook, kalshi_markets_runbook):
            self.assertIn("snowpipe_s3_notifications.md", text)

        self.assertIn("terraform -chdir=infra/terraform import", notification_runbook)
        self.assertIn("aws_s3_bucket_notification.snowpipe[0]", notification_runbook)
        self.assertIn("snowflake-kalshi-project", notification_runbook)
        self.assertIn("owns the bucket's full notification configuration", notification_runbook)
        self.assertIn("Set the MLB Teams, Kalshi Events, and Kalshi Series Snowpipe notification", notification_runbook)
        self.assertIn("leave all three null until those pipes exist", notification_runbook)
        self.assertIn("all three together", notification_runbook)
        self.assertIn("prevent_destroy", notification_runbook)

        for pipe_name in (
            "PIPE_MLB_TEAMS",
            "PIPE_KALSHI_EVENTS",
            "PIPE_KALSHI_SERIES",
            "PIPE_KALSHI_MARKETS",
            "PIPE_KALSHI_MARKET_ORDERBOOKS",
            "PIPE_KALSHI_MARKET_TRADES",
        ):
            self.assertIn(pipe_name, notification_runbook)

        for prefix in (
            "raw/mlb/teams/",
            "raw/kalshi/events/",
            "raw/kalshi/series/",
            "raw/kalshi/markets/",
            "raw/kalshi/market_orderbooks/",
            "raw/kalshi/market_trades/",
        ):
            self.assertIn(prefix, notification_runbook)


if __name__ == "__main__":
    unittest.main()
