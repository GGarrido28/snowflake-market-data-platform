import json
from typing import Any, Iterable


class S3JsonLinesWriter:
    """Writes row dictionaries as newline-delimited JSON objects to S3."""

    def __init__(self, client: Any | None = None):
        self.client = client or self._build_client()

    def _build_client(self) -> Any:
        import boto3

        return boto3.client("s3")

    def put_json_lines(
        self,
        *,
        bucket: str,
        key: str,
        rows: Iterable[dict[str, Any]],
    ) -> dict[str, Any]:
        body = "".join(
            json.dumps(row, sort_keys=True, default=str, separators=(",", ":")) + "\n"
            for row in rows
        )
        body_bytes = body.encode("utf-8")

        self.client.put_object(
            Bucket=bucket,
            Key=key,
            Body=body_bytes,
            ContentType="application/x-ndjson",
        )
        return {
            "bucket": bucket,
            "key": key,
            "s3_uri": f"s3://{bucket}/{key}",
            "bytes": len(body_bytes),
            "content_type": "application/x-ndjson",
        }
