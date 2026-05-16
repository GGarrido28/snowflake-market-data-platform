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


def _resolve_series_ticker(event: dict[str, Any]) -> str | None:
    ticker = event_value(event, "series_ticker", "ticker") or os.getenv("KALSHI_SERIES_TICKER")
    return str(ticker) if ticker else None


def _validate_scope(series_ticker: str | None) -> None:
    if not series_ticker:
        raise ValueError("Set series_ticker or KALSHI_SERIES_TICKER before running the Kalshi series Lambda.")


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
    _validate_scope(series_ticker)
    s3_key = build_s3_key(prefix, "series", run_started_at)

    series_client = series_client or Series()
    s3_writer = s3_writer or S3JsonLinesWriter()

    logging.info("Fetching scoped Kalshi series: %s.", series_ticker)
    series_row = series_client.get_series(series_ticker)
    raw_series = [series_row] if series_row else []
    rows = normalize_series(raw_series, ingested_at=ingested_at)
    logging.info("Writing %s Kalshi series row(s) to s3://%s/%s.", len(rows), bucket, s3_key)
    write_result = s3_writer.put_json_lines(bucket=bucket, key=s3_key, rows=rows)

    return {
        "source": "kalshi",
        "entity": "series",
        "series_ticker": series_ticker,
        "row_count": len(rows),
        **write_result,
    }


if __name__ == "__main__":
    print(run())
