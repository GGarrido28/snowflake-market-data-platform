import datetime as dt
import os
from typing import Any


def event_value(event: dict[str, Any], *keys: str) -> Any | None:
    for key in keys:
        value = event.get(key)
        if value not in (None, ""):
            return value
    return None


def resolve_bucket(event: dict[str, Any], *, env_var: str) -> str:
    bucket = event_value(event, "s3_bucket", "bucket") or os.getenv(env_var) or os.getenv("SNOWFLAKE_S3_BUCKET")
    if not bucket:
        raise ValueError(f"Set {env_var} or SNOWFLAKE_S3_BUCKET before running the Kalshi S3 landing pipeline.")
    return str(bucket)


def resolve_prefix(event: dict[str, Any], *, env_var: str, default: str) -> str:
    prefix = event_value(event, "s3_prefix", "prefix") or os.getenv(env_var) or default
    return str(prefix).strip("/")


def timestamp_for_key(value: dt.datetime) -> str:
    return (
        value.astimezone(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
        .replace("-", "")
        .replace(":", "")
    )


def ingestion_timestamp(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_s3_key(prefix: str, entity: str, run_started_at: dt.datetime) -> str:
    run_started_at = run_started_at.astimezone(dt.timezone.utc)
    partition_date = run_started_at.date().isoformat()
    timestamp = timestamp_for_key(run_started_at)
    return f"{prefix}/ingested_date={partition_date}/kalshi_{entity}_{timestamp}.jsonl"


def normalize_payload(row: dict[str, Any], *, ingested_at: str) -> dict[str, Any]:
    raw_payload = dict(row)
    return {
        **row,
        "ingested_at": ingested_at,
        "raw_payload": raw_payload,
    }


def normalize_payloads(rows: list[dict[str, Any]], *, ingested_at: str) -> list[dict[str, Any]]:
    return [normalize_payload(row, ingested_at=ingested_at) for row in rows]
