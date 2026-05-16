import unittest
from unittest.mock import Mock, patch

from aws.lambdas.kalshi_events import handler as events_handler
from aws.lambdas.kalshi_series import handler as series_handler


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


if __name__ == "__main__":
    unittest.main()
