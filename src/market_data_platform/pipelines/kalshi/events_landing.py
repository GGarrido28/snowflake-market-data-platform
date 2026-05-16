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
from market_data_platform.sources.kalshi.events import Events
from market_data_platform.warehouse.s3 import S3JsonLinesWriter


logging.basicConfig(level=logging.INFO)

DEFAULT_S3_PREFIX = "raw/kalshi/events"
DEFAULT_EVENT_STATUS = "open"
DEFAULT_SERIES_TICKERS = ("KXMLBSPREAD", "KXMLBTOTAL", "KXMLBGAME")


def _resolve_status(event: dict[str, Any]) -> str | None:
    configured_status = (
        event_value(event, "status", "event_status")
        or os.getenv("KALSHI_EVENTS_STATUS")
        or DEFAULT_EVENT_STATUS
    )
    status = str(configured_status).strip().lower()
    if status in {"", "all"}:
        return None
    return status


def _coerce_series_tickers(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, str):
        raw_tickers = value.split(",")
    elif isinstance(value, list | tuple | set):
        raw_tickers = list(value)
    else:
        raw_tickers = [value]
    return [str(ticker).strip() for ticker in raw_tickers if str(ticker).strip()]


def _resolve_scope(event: dict[str, Any]) -> tuple[str | None, list[str]]:
    event_ticker = event_value(event, "event_ticker") or os.getenv("KALSHI_EVENTS_EVENT_TICKER")
    event_series_value = event_value(event, "series_tickers") or event_value(event, "series_ticker")
    env_series_value = os.getenv("KALSHI_EVENTS_SERIES_TICKERS") or os.getenv("KALSHI_EVENTS_SERIES_TICKER")

    if event_ticker:
        if event_series_value:
            raise ValueError("Set either event_ticker or series_tickers for Kalshi events, not both.")
        return str(event_ticker), []

    series_tickers = _coerce_series_tickers(
        event_series_value or env_series_value or list(DEFAULT_SERIES_TICKERS)
    )
    return None, series_tickers


def _validate_scope(status: str | None, event_ticker: str | None, series_tickers: list[str]) -> None:
    if status is None and not (event_ticker or series_tickers):
        raise ValueError("Set event_ticker or series_tickers when requesting all Kalshi event statuses.")


def normalize_events(rows: list[dict[str, Any]], *, ingested_at: str) -> list[dict[str, Any]]:
    return normalize_payloads(rows, ingested_at=ingested_at)


def run(
    event: dict[str, Any] | None = None,
    *,
    events_client: Events | None = None,
    s3_writer: S3JsonLinesWriter | None = None,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    event = event or {}
    run_started_at = now or dt.datetime.now(dt.timezone.utc)
    ingested_at = ingestion_timestamp(run_started_at)
    bucket = resolve_bucket(event, env_var="KALSHI_EVENTS_S3_BUCKET")
    prefix = resolve_prefix(event, env_var="KALSHI_EVENTS_S3_PREFIX", default=DEFAULT_S3_PREFIX)
    status = _resolve_status(event)
    event_ticker, series_tickers = _resolve_scope(event)
    _validate_scope(status, event_ticker, series_tickers)
    s3_key = build_s3_key(prefix, "events", run_started_at)

    events_client = events_client or Events()
    s3_writer = s3_writer or S3JsonLinesWriter()

    logging.info(
        "Fetching Kalshi events with status=%s event_ticker=%s series_tickers=%s.",
        status,
        event_ticker,
        series_tickers,
    )
    if event_ticker:
        raw_events = events_client.get_target_events(
            event_ticker=event_ticker,
            status=status,
        )
    else:
        raw_events = []
        for series_ticker in series_tickers:
            raw_events.extend(
                events_client.get_target_events(
                    series_ticker=series_ticker,
                    status=status,
                )
            )
    rows = normalize_events(raw_events, ingested_at=ingested_at)
    logging.info("Writing %s Kalshi event row(s) to s3://%s/%s.", len(rows), bucket, s3_key)
    write_result = s3_writer.put_json_lines(bucket=bucket, key=s3_key, rows=rows)

    return {
        "source": "kalshi",
        "entity": "events",
        "status": status,
        "event_ticker": event_ticker,
        "series_tickers": series_tickers,
        "row_count": len(rows),
        **write_result,
    }


if __name__ == "__main__":
    print(run())
