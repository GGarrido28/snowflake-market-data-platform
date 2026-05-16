import datetime as dt
import logging
import os
from typing import Any

from market_data_platform.pipelines.kalshi.s3_landing import (
    build_s3_key,
    event_value,
    ingestion_timestamp,
    normalize_payloads,
    resolve_bucket,
    resolve_prefix,
)
from market_data_platform.sources.kalshi.markets import Series
from market_data_platform.warehouse.s3 import S3JsonLinesWriter


logging.basicConfig(level=logging.INFO)

DEFAULT_S3_PREFIX = "raw/kalshi/series"
DEFAULT_SERIES_TAGS = ("BaseBall",)


def _coerce_tags(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, str):
        raw_tags = value.split(",")
    elif isinstance(value, list | tuple | set):
        raw_tags = list(value)
    else:
        raw_tags = [value]
    return [str(tag).strip() for tag in raw_tags if str(tag).strip()]


def _resolve_series_ticker(event: dict[str, Any]) -> str | None:
    ticker = event_value(event, "series_ticker", "ticker") or os.getenv("KALSHI_SERIES_TICKER")
    return str(ticker) if ticker else None


def _resolve_tags(event: dict[str, Any]) -> list[str]:
    return _coerce_tags(
        event_value(event, "tags", "series_tags")
        or os.getenv("KALSHI_SERIES_TAGS")
        or list(DEFAULT_SERIES_TAGS)
    )


def _row_matches_tags(row: dict[str, Any], tags: list[str]) -> bool:
    row_tags = row.get("tags")
    if not isinstance(row_tags, list):
        return False
    normalized_row_tags = {str(tag).casefold() for tag in row_tags}
    return all(tag.casefold() in normalized_row_tags for tag in tags)


def normalize_series(rows: list[dict[str, Any]], *, ingested_at: str) -> list[dict[str, Any]]:
    return normalize_payloads(rows, ingested_at=ingested_at)


def run(
    event: dict[str, Any] | None = None,
    *,
    series_client: Series | None = None,
    s3_writer: S3JsonLinesWriter | None = None,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    event = event or {}
    run_started_at = now or dt.datetime.now(dt.timezone.utc)
    ingested_at = ingestion_timestamp(run_started_at)
    bucket = resolve_bucket(event, env_var="KALSHI_SERIES_S3_BUCKET")
    prefix = resolve_prefix(event, env_var="KALSHI_SERIES_S3_PREFIX", default=DEFAULT_S3_PREFIX)
    series_ticker = _resolve_series_ticker(event)
    tags = _resolve_tags(event)
    s3_key = build_s3_key(prefix, "series", run_started_at)

    series_client = series_client or Series()
    s3_writer = s3_writer or S3JsonLinesWriter()

    if series_ticker:
        logging.info("Fetching scoped Kalshi series: %s.", series_ticker)
        series_row = series_client.get_series(series_ticker)
        raw_series = [series_row] if series_row else []
    else:
        logging.info("Fetching Kalshi series and filtering for tags=%s.", tags)
        raw_series = [
            row for row in series_client.get_all_series(all_pages=True) if _row_matches_tags(row, tags)
        ]
    rows = normalize_series(raw_series, ingested_at=ingested_at)
    logging.info("Writing %s Kalshi series row(s) to s3://%s/%s.", len(rows), bucket, s3_key)
    write_result = s3_writer.put_json_lines(bucket=bucket, key=s3_key, rows=rows)

    return {
        "source": "kalshi",
        "entity": "series",
        "series_ticker": series_ticker,
        "tags": tags,
        "row_count": len(rows),
        **write_result,
    }


if __name__ == "__main__":
    print(run())
