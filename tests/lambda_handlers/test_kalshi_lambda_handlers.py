import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from aws.lambdas.kalshi_events import handler as legacy_events_handler
from aws.lambdas.kalshi_series import handler as legacy_series_handler
from market_data_platform.lambda_handlers import kalshi_events as events_handler
from market_data_platform.lambda_handlers import kalshi_series as series_handler


REPO_ROOT = Path(__file__).resolve().parents[2]
TERRAFORM_LAMBDA_PATH = REPO_ROOT / "infra" / "terraform" / "lambda.tf"


class KalshiLambdaHandlerTests(unittest.TestCase):
    def test_events_lambda_handler_dispatches_to_pipeline(self):
        context = Mock()

        with patch.object(events_handler, "run", return_value={"row_count": 2}) as mock_run:
            result = events_handler.lambda_handler({"series_ticker": "KXMLBSPREAD"}, context)

        self.assertEqual(result, {"row_count": 2})
        mock_run.assert_called_once_with({"series_ticker": "KXMLBSPREAD"})

    def test_series_lambda_handler_dispatches_to_pipeline(self):
        context = Mock()

        with patch.object(series_handler, "run", return_value={"row_count": 1}) as mock_run:
            result = series_handler.lambda_handler({"series_ticker": "KXMLBSPREAD"}, context)

        self.assertEqual(result, {"row_count": 1})
        mock_run.assert_called_once_with({"series_ticker": "KXMLBSPREAD"})

    def test_handlers_use_empty_event_for_none(self):
        with patch.object(events_handler, "run", return_value={"row_count": 0}) as mock_events_run:
            events_handler.lambda_handler(None, Mock())

        with patch.object(series_handler, "run", return_value={"row_count": 0}) as mock_series_run:
            series_handler.lambda_handler(None, Mock())

        mock_events_run.assert_called_once_with({})
        mock_series_run.assert_called_once_with({})

    def test_legacy_handler_modules_delegate_to_packaged_entrypoints(self):
        self.assertIs(legacy_events_handler.run, events_handler.run)
        self.assertIs(legacy_series_handler.run, series_handler.run)

        with patch.object(legacy_events_handler, "run", return_value={"row_count": 3}) as mock_events_run:
            result = legacy_events_handler.lambda_handler({"series_ticker": "KXMLBTOTAL"}, Mock())

        self.assertEqual(result, {"row_count": 3})
        mock_events_run.assert_called_once_with({"series_ticker": "KXMLBTOTAL"})

        with patch.object(legacy_series_handler, "run", return_value={"row_count": 4}) as mock_series_run:
            result = legacy_series_handler.lambda_handler({"series_ticker": "KXMLBGAME"}, Mock())

        self.assertEqual(result, {"row_count": 4})
        mock_series_run.assert_called_once_with({"series_ticker": "KXMLBGAME"})

    def test_terraform_uses_packaged_kalshi_entrypoints(self):
        terraform = TERRAFORM_LAMBDA_PATH.read_text(encoding="utf-8")

        self.assertIn(
            'command = ["market_data_platform.lambda_handlers.kalshi_events.lambda_handler"]',
            terraform,
        )
        self.assertIn(
            'command = ["market_data_platform.lambda_handlers.kalshi_series.lambda_handler"]',
            terraform,
        )
        self.assertNotIn("aws.lambdas.kalshi_events.handler.lambda_handler", terraform)
        self.assertNotIn("aws.lambdas.kalshi_series.handler.lambda_handler", terraform)


if __name__ == "__main__":
    unittest.main()
