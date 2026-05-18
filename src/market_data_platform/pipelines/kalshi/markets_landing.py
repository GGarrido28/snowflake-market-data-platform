import datetime as dt
import logging
import os
from pathlib import Path
from typing import Any, Callable

from market_data_platform.pipelines.kalshi.s3_landing import (
    build_s3_key,
    event_value,
    ingestion_timestamp,
    normalize_payloads,
    resolve_bucket,
)
from market_data_platform.sources.kalshi.markets import Markets
from market_data_platform.warehouse.s3 import S3JsonLinesWriter


logging.basicConfig(level=logging.INFO)

DEFAULT_MARKETS_S3_PREFIX = "raw/kalshi/markets"
DEFAULT_MARKET_ORDERBOOKS_S3_PREFIX = "raw/kalshi/market_orderbooks"
DEFAULT_MARKET_TRADES_S3_PREFIX = "raw/kalshi/market_trades"
PROJECT_ROOT = Path(__file__).resolve().parents[4]
PACKAGE_ROOT = Path(__file__).resolve().parents[2]

EventTickerLoader = Callable[[str], list[str]]


def _configured_string(
    event: dict[str, Any],
    *,
    keys: tuple[str, ...],
    env_vars: tuple[str, ...],
) -> str | None:
    value = event_value(event, *keys)
    if value in (None, ""):
        for env_var in env_vars:
            value = os.getenv(env_var)
            if value not in (None, ""):
                break
    if value in (None, ""):
        return None
    return str(value).strip() or None


def _resolve_entity_prefix(
    event: dict[str, Any],
    *,
    keys: tuple[str, ...],
    env_var: str,
    default: str,
) -> str:
    prefix = event_value(event, *keys) or os.getenv(env_var) or default
    return str(prefix).strip("/")


def _coerce_bool(value: Any, *, default: bool = False) -> bool:
    if value in (None, ""):
        return default
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "f", "no", "n", "off"}:
        return False
    raise ValueError(f"Expected a boolean value, got {value!r}.")


def _resolve_scope(event: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    payload_market_ticker = event_value(event, "market_ticker", "ticker")
    payload_event_ticker = event_value(event, "event_ticker")
    payload_event_query_file = event_value(event, "event_query_file", "event_tickers_query_file")

    if any(value not in (None, "") for value in (payload_market_ticker, payload_event_ticker, payload_event_query_file)):
        market_ticker = str(payload_market_ticker).strip() if payload_market_ticker not in (None, "") else None
        event_ticker = str(payload_event_ticker).strip() if payload_event_ticker not in (None, "") else None
        event_query_file = str(payload_event_query_file).strip() if payload_event_query_file not in (None, "") else None
    else:
        market_ticker = _configured_string(
            event,
            keys=("market_ticker", "ticker"),
            env_vars=("KALSHI_MARKET_TICKER", "KALSHI_MARKETS_MARKET_TICKER"),
        )
        event_ticker = _configured_string(
            event,
            keys=("event_ticker",),
            env_vars=("KALSHI_EVENT_TICKER", "KALSHI_MARKETS_EVENT_TICKER"),
        )
        event_query_file = _configured_string(
            event,
            keys=("event_query_file", "event_tickers_query_file"),
            env_vars=("KALSHI_MARKETS_EVENT_QUERY_FILE",),
        )

    set_count = sum(1 for value in (market_ticker, event_ticker, event_query_file) if value)
    if set_count > 1:
        raise ValueError("Set only one of market_ticker, event_ticker, or event_query_file.")
    if set_count == 0:
        raise ValueError("Set market_ticker, event_ticker, or event_query_file before running Kalshi markets landing.")
    return market_ticker, event_ticker, event_query_file


def _resolve_paginate_trades(event: dict[str, Any]) -> bool:
    value = event_value(event, "paginate_trades", "trades_all_pages")
    if value in (None, ""):
        value = os.getenv("KALSHI_MARKETS_PAGINATE_TRADES")
    return _coerce_bool(value, default=False)


def _resolve_query_path(query_file: str) -> Path:
    raw_path = Path(query_file).expanduser()
    if raw_path.is_absolute() and raw_path.exists():
        return raw_path

    candidates = [
        Path.cwd() / raw_path,
        PROJECT_ROOT / raw_path,
        PACKAGE_ROOT / raw_path,
        PACKAGE_ROOT.parent / raw_path,
    ]
    normalized = str(raw_path).replace("\\", "/")
    if normalized.startswith("src/market_data_platform/"):
        candidates.append(PACKAGE_ROOT / normalized.removeprefix("src/market_data_platform/"))
    if normalized.startswith("market_data_platform/"):
        candidates.append(PACKAGE_ROOT.parent / normalized)

    seen: set[Path] = set()
    for candidate in candidates:
        candidate = candidate.resolve()
        if candidate in seen:
            continue
        seen.add(candidate)
        if candidate.exists():
            return candidate

    checked = ", ".join(str(path) for path in seen)
    raise FileNotFoundError(f"Event query file not found at {query_file}. Checked: {checked}")


def _dedupe_event_tickers(rows: list[dict[str, Any]], *, query_path: Path) -> list[str]:
    raw_tickers = [row.get("event_ticker") for row in rows if row.get("event_ticker")]
    tickers = list(dict.fromkeys(str(ticker) for ticker in raw_tickers))
    if not tickers:
        logging.warning("Event query returned 0 tickers: %s", query_path)
    else:
        dropped = len(raw_tickers) - len(tickers)
        if dropped:
            logging.info(
                "Event query returned %s ticker(s) from %s (%s duplicate(s) dropped).",
                len(tickers),
                query_path,
                dropped,
            )
        else:
            logging.info("Event query returned %s ticker(s) from %s.", len(tickers), query_path)
    return tickers


def load_event_tickers_from_query(query_file: str) -> list[str]:
    query_path = _resolve_query_path(query_file)
    sql = query_path.read_text(encoding="utf-8")

    from market_data_platform.warehouse import SnowflakeManager

    snowflake_manager = SnowflakeManager("PROD", "RAW")
    try:
        rows = snowflake_manager.execute(sql, raise_exc=True)
    finally:
        snowflake_manager.close()
    return _dedupe_event_tickers(rows, query_path=query_path)


def _fetch_markets_for_event_list(
    markets_client: Markets,
    event_tickers: list[str],
) -> list[dict[str, Any]]:
    all_markets: list[dict[str, Any]] = []
    for event_ticker in event_tickers:
        try:
            markets_for_event = markets_client.get_target_markets(event_ticker=event_ticker)
            logging.info("Fetched %s markets for event %s.", len(markets_for_event), event_ticker)
            all_markets.extend(markets_for_event)
        except Exception as e:
            logging.warning("Failed to fetch markets for event %s: %s", event_ticker, e)
    return all_markets


def normalize_markets(rows: list[dict[str, Any]], *, ingested_at: str) -> list[dict[str, Any]]:
    return normalize_payloads(rows, ingested_at=ingested_at)


def normalize_market_orderbooks(rows: list[dict[str, Any]], *, ingested_at: str) -> list[dict[str, Any]]:
    return normalize_payloads(rows, ingested_at=ingested_at)


def normalize_market_trades(rows: list[dict[str, Any]], *, ingested_at: str) -> list[dict[str, Any]]:
    return normalize_payloads(rows, ingested_at=ingested_at)


def _write_entity(
    *,
    bucket: str,
    prefix: str,
    entity: str,
    rows: list[dict[str, Any]],
    ingested_at: str,
    run_started_at: dt.datetime,
    s3_writer: S3JsonLinesWriter,
) -> dict[str, Any]:
    normalized_rows = normalize_payloads(rows, ingested_at=ingested_at)
    s3_key = build_s3_key(prefix, entity, run_started_at)
    logging.info("Writing %s Kalshi %s row(s) to s3://%s/%s.", len(normalized_rows), entity, bucket, s3_key)
    write_result = s3_writer.put_json_lines(bucket=bucket, key=s3_key, rows=normalized_rows)
    return {
        "row_count": len(normalized_rows),
        **write_result,
    }


def run(
    event: dict[str, Any] | None = None,
    *,
    markets_client: Markets | None = None,
    s3_writer: S3JsonLinesWriter | None = None,
    now: dt.datetime | None = None,
    event_ticker_loader: EventTickerLoader | None = None,
) -> dict[str, Any]:
    event = event or {}
    run_started_at = now or dt.datetime.now(dt.timezone.utc)
    ingested_at = ingestion_timestamp(run_started_at)
    bucket = resolve_bucket(event, env_var="KALSHI_MARKETS_S3_BUCKET")
    markets_prefix = _resolve_entity_prefix(
        event,
        keys=("markets_s3_prefix", "market_s3_prefix", "s3_prefix", "prefix"),
        env_var="KALSHI_MARKETS_S3_PREFIX",
        default=DEFAULT_MARKETS_S3_PREFIX,
    )
    orderbooks_prefix = _resolve_entity_prefix(
        event,
        keys=("market_orderbooks_s3_prefix", "orderbooks_s3_prefix"),
        env_var="KALSHI_MARKET_ORDERBOOKS_S3_PREFIX",
        default=DEFAULT_MARKET_ORDERBOOKS_S3_PREFIX,
    )
    trades_prefix = _resolve_entity_prefix(
        event,
        keys=("market_trades_s3_prefix", "trades_s3_prefix"),
        env_var="KALSHI_MARKET_TRADES_S3_PREFIX",
        default=DEFAULT_MARKET_TRADES_S3_PREFIX,
    )
    market_ticker, event_ticker, event_query_file = _resolve_scope(event)
    paginate_trades = _resolve_paginate_trades(event)

    markets_client = markets_client or Markets()
    s3_writer = s3_writer or S3JsonLinesWriter()

    event_tickers: list[str] = []
    if event_query_file:
        event_ticker_loader = event_ticker_loader or load_event_tickers_from_query
        event_tickers = event_ticker_loader(event_query_file)
        market_rows = _fetch_markets_for_event_list(markets_client, event_tickers)
    elif market_ticker:
        logging.info("Fetching scoped Kalshi market: %s.", market_ticker)
        market_rows = markets_client.get_target_markets(market_ticker=market_ticker)
    else:
        logging.info("Fetching scoped Kalshi event markets: %s.", event_ticker)
        market_rows = markets_client.get_target_markets(event_ticker=event_ticker)

    logging.info(
        "Fetching orderbooks and recent trades for %s market(s); paginate_trades=%s.",
        len(market_rows),
        paginate_trades,
    )
    detail_data = markets_client.get_market_details(market_rows, paginate_trades=paginate_trades)

    writes = {
        "markets": _write_entity(
            bucket=bucket,
            prefix=markets_prefix,
            entity="markets",
            rows=market_rows,
            ingested_at=ingested_at,
            run_started_at=run_started_at,
            s3_writer=s3_writer,
        ),
        "market_orderbooks": _write_entity(
            bucket=bucket,
            prefix=orderbooks_prefix,
            entity="market_orderbooks",
            rows=detail_data["orderbook"],
            ingested_at=ingested_at,
            run_started_at=run_started_at,
            s3_writer=s3_writer,
        ),
        "market_trades": _write_entity(
            bucket=bucket,
            prefix=trades_prefix,
            entity="market_trades",
            rows=detail_data["trades"],
            ingested_at=ingested_at,
            run_started_at=run_started_at,
            s3_writer=s3_writer,
        ),
    }

    return {
        "source": "kalshi",
        "entity": "markets",
        "market_ticker": market_ticker,
        "event_ticker": event_ticker,
        "event_query_file": event_query_file,
        "event_tickers": event_tickers,
        "paginate_trades": paginate_trades,
        "row_counts": {
            entity: result["row_count"]
            for entity, result in writes.items()
        },
        "writes": writes,
    }


if __name__ == "__main__":
    print(run())
