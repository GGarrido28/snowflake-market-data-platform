import json
import subprocess
import sys
import textwrap
import unittest
from unittest.mock import Mock

from market_data_platform.warehouse.s3 import S3JsonLinesWriter


class S3JsonLinesWriterTests(unittest.TestCase):
    def test_put_json_lines_writes_ndjson_payload(self):
        client = Mock()
        writer = S3JsonLinesWriter(client=client)

        result = writer.put_json_lines(
            bucket="snowflake-landing",
            key="raw/mlb/teams/file.jsonl",
            rows=[{"team_id": 119, "name": "Dodgers"}, {"team_id": 147, "name": "Yankees"}],
        )

        client.put_object.assert_called_once()
        call = client.put_object.call_args.kwargs
        self.assertEqual(call["Bucket"], "snowflake-landing")
        self.assertEqual(call["Key"], "raw/mlb/teams/file.jsonl")
        self.assertEqual(call["ContentType"], "application/x-ndjson")
        self.assertEqual(
            [json.loads(line) for line in call["Body"].decode("utf-8").splitlines()],
            [{"name": "Dodgers", "team_id": 119}, {"name": "Yankees", "team_id": 147}],
        )
        self.assertEqual(result["s3_uri"], "s3://snowflake-landing/raw/mlb/teams/file.jsonl")
        self.assertEqual(result["content_type"], "application/x-ndjson")

    def test_s3_import_does_not_require_snowflake_connector(self):
        code = textwrap.dedent(
            """
            import builtins

            original_import = builtins.__import__

            def guarded_import(name, *args, **kwargs):
                if name == "snowflake" or name.startswith("snowflake."):
                    raise ModuleNotFoundError("No module named 'snowflake'")
                return original_import(name, *args, **kwargs)

            builtins.__import__ = guarded_import
            from market_data_platform.warehouse.s3 import S3JsonLinesWriter
            from aws.lambdas.mlb_teams import handler

            assert S3JsonLinesWriter is not None
            assert handler.lambda_handler is not None
            """
        )

        result = subprocess.run(
            [sys.executable, "-c", code],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
