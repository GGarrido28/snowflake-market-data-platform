import unittest
from unittest.mock import Mock, patch

from aws.lambdas.mlb_teams import handler


class MlbTeamsLambdaHandlerTests(unittest.TestCase):
    def test_lambda_handler_dispatches_to_pipeline(self):
        context = Mock()

        with patch.object(handler, "run", return_value={"row_count": 30}) as mock_run:
            result = handler.lambda_handler({"s3_bucket": "snowflake-landing"}, context)

        self.assertEqual(result, {"row_count": 30})
        mock_run.assert_called_once_with({"s3_bucket": "snowflake-landing"})

    def test_lambda_handler_uses_empty_event_for_none(self):
        with patch.object(handler, "run", return_value={"row_count": 30}) as mock_run:
            handler.lambda_handler(None, Mock())

        mock_run.assert_called_once_with({})


if __name__ == "__main__":
    unittest.main()
