import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TERRAFORM_DIR = REPO_ROOT / "infra" / "terraform"
MAIN_PATH = TERRAFORM_DIR / "main.tf"
VARIABLES_PATH = TERRAFORM_DIR / "variables.tf"
LAMBDA_PATH = TERRAFORM_DIR / "lambda.tf"
IAM_PATH = TERRAFORM_DIR / "iam.tf"
CLOUDWATCH_PATH = TERRAFORM_DIR / "cloudwatch.tf"
OUTPUTS_PATH = TERRAFORM_DIR / "outputs.tf"
TFVARS_EXAMPLE_PATH = TERRAFORM_DIR / "terraform.tfvars.example"
SCHEDULER_PATH = TERRAFORM_DIR / "scheduler.tf"
LAMBDA_REQUIREMENTS_PATH = REPO_ROOT / "aws" / "docker" / "requirements.lambda.txt"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class KalshiMarketsLambdaTerraformTests(unittest.TestCase):
    def test_markets_prefixes_and_scope_variables_are_declared(self):
        variables = _read(VARIABLES_PATH)
        tfvars_example = _read(TFVARS_EXAMPLE_PATH)
        main = _read(MAIN_PATH)

        for name, default in (
            ("kalshi_markets_s3_prefix", "raw/kalshi/markets"),
            ("kalshi_market_orderbooks_s3_prefix", "raw/kalshi/market_orderbooks"),
            ("kalshi_market_trades_s3_prefix", "raw/kalshi/market_trades"),
            ("kalshi_market_trades_state_prefix", "state/kalshi/market_trades"),
        ):
            self.assertIn(f'variable "{name}"', variables)
            self.assertRegex(tfvars_example, rf'{name}\s*=\s*"{default}"')

        for name in (
            "kalshi_markets_market_ticker",
            "kalshi_markets_event_ticker",
            "kalshi_markets_event_query_file",
            "kalshi_markets_paginate_trades",
            "kalshi_market_trades_fetch_mode",
            "kalshi_market_trades_first_run_lookback_hours",
            "kalshi_market_trades_watermark_overlap_seconds",
            "kalshi_markets_reserved_concurrency",
            "kalshi_markets_snowflake_account",
            "kalshi_markets_snowflake_user",
            "kalshi_markets_snowflake_warehouse",
            "kalshi_markets_snowflake_role",
            "kalshi_markets_snowflake_private_key_secret_arn",
            "kalshi_markets_snowflake_private_key_secret_name",
        ):
            self.assertIn(f'variable "{name}"', variables)
            self.assertRegex(tfvars_example, rf"{name}\s*=")

        self.assertIn("Set at most one of kalshi_markets_market_ticker", variables)
        self.assertIn("kalshi_markets_event_query_file requires", variables)
        self.assertIn("KALSHI_MARKET_TICKER", main)
        self.assertIn("KALSHI_EVENT_TICKER", main)
        self.assertIn("KALSHI_MARKETS_EVENT_QUERY_FILE", main)
        self.assertIn("trade_fetch_mode", main)
        self.assertIn("SNOWFLAKE_ACCOUNT", main)
        self.assertIn("SNOWFLAKE_USER", main)
        self.assertIn("SNOWFLAKE_PRIVATE_KEY_SECRET_ARN", main)

    def test_optional_string_validations_handle_null_values(self):
        variables = _read(VARIABLES_PATH)

        self.assertNotRegex(variables, r'coalesce\(\s*var\.[^,\n]+,\s*""\s*\)')

    def test_markets_lambda_uses_image_command_secret_env_and_prefixes(self):
        terraform = _read(LAMBDA_PATH)

        self.assertIn('resource "aws_lambda_function" "kalshi_markets"', terraform)
        self.assertIn('command = ["market_data_platform.lambda_handlers.kalshi_markets.lambda_handler"]', terraform)
        self.assertNotIn("aws.lambdas.kalshi_markets.handler.lambda_handler", terraform)
        self.assertIn("KALSHI_MARKETS_S3_BUCKET", terraform)
        self.assertIn("KALSHI_MARKETS_S3_PREFIX", terraform)
        self.assertIn("KALSHI_MARKET_ORDERBOOKS_S3_PREFIX", terraform)
        self.assertIn("KALSHI_MARKET_TRADES_S3_PREFIX", terraform)
        self.assertIn("KALSHI_MARKET_TRADES_STATE_PREFIX", terraform)
        self.assertIn("KALSHI_MARKETS_PAGINATE_TRADES", terraform)
        self.assertIn("KALSHI_MARKET_TRADES_FETCH_MODE", terraform)
        self.assertIn("KALSHI_MARKET_TRADES_FIRST_RUN_LOOKBACK_HOURS", terraform)
        self.assertIn("KALSHI_MARKET_TRADES_WATERMARK_OVERLAP_SECONDS", terraform)
        self.assertIn("reserved_concurrent_executions = var.kalshi_markets_reserved_concurrency", terraform)
        self.assertEqual(terraform.count("reserved_concurrent_executions = var.kalshi_markets_reserved_concurrency"), 1)
        self.assertGreater(
            terraform.index("reserved_concurrent_executions = var.kalshi_markets_reserved_concurrency"),
            terraform.index('resource "aws_lambda_function" "kalshi_markets"'),
        )
        self.assertIn("local.kalshi_secret_environment", terraform)
        self.assertIn("local.kalshi_markets_scope_environment", terraform)
        self.assertIn("local.kalshi_markets_snowflake_environment", terraform)

    def test_markets_iam_writes_only_market_landing_prefixes(self):
        terraform = _read(IAM_PATH)

        self.assertIn('resource "aws_iam_role" "kalshi_markets_lambda"', terraform)
        self.assertIn('data "aws_iam_policy_document" "kalshi_markets_s3_write"', terraform)
        self.assertIn('"s3:PutObject"', terraform)
        self.assertIn('"s3:AbortMultipartUpload"', terraform)
        self.assertIn('"s3:GetObject"', terraform)
        self.assertIn('"s3:ListBucket"', terraform)
        self.assertIn("${data.aws_s3_bucket.landing.arn}/${local.kalshi_markets_s3_prefix}/*", terraform)
        self.assertIn(
            "${data.aws_s3_bucket.landing.arn}/${local.kalshi_market_orderbooks_s3_prefix}/*",
            terraform,
        )
        self.assertIn(
            "${data.aws_s3_bucket.landing.arn}/${local.kalshi_market_trades_s3_prefix}/*",
            terraform,
        )
        self.assertIn(
            "${data.aws_s3_bucket.landing.arn}/${local.kalshi_market_trades_state_prefix}/*",
            terraform,
        )
        self.assertIn("data.aws_s3_bucket.landing.arn", terraform)
        self.assertIn('variable = "s3:prefix"', terraform)
        self.assertIn('resource "aws_iam_role_policy_attachment" "kalshi_markets_kalshi_api_secret_read"', terraform)
        self.assertIn(
            'data "aws_iam_policy_document" "kalshi_markets_snowflake_private_key_secret_read"',
            terraform,
        )
        self.assertIn(
            'resource "aws_iam_role_policy_attachment" "kalshi_markets_snowflake_private_key_secret_read"',
            terraform,
        )

    def test_markets_log_group_outputs_and_no_scheduler_are_present(self):
        cloudwatch = _read(CLOUDWATCH_PATH)
        outputs = _read(OUTPUTS_PATH)
        scheduler = _read(SCHEDULER_PATH)

        self.assertIn('resource "aws_cloudwatch_log_group" "kalshi_markets_lambda"', cloudwatch)
        self.assertIn('output "kalshi_markets_lambda_function_name"', outputs)
        self.assertIn('output "kalshi_markets_landing_s3_uri"', outputs)
        self.assertIn('output "kalshi_market_orderbooks_landing_s3_uri"', outputs)
        self.assertIn('output "kalshi_market_trades_landing_s3_uri"', outputs)
        self.assertIn('output "kalshi_market_trades_state_s3_uri"', outputs)
        self.assertIn('output "kalshi_markets_manual_invoke_payload"', outputs)
        self.assertNotIn("kalshi_markets", scheduler)

    def test_lambda_image_includes_snowflake_connector_for_event_query_file_scope(self):
        requirements = _read(LAMBDA_REQUIREMENTS_PATH)

        self.assertIn("snowflake-connector-python", requirements)


if __name__ == "__main__":
    unittest.main()
