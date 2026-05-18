import datetime as dt
import logging
import os
from dataclasses import dataclass
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
from market_data_platform.warehouse.s3 import S3JsonLinesWriter, S3JsonStore


logging.basicConfig(level=logging.INFO)

DEFAULT_MARKETS_S3_PREFIX = "raw/kalshi/markets"
DEFAULT_MARKET_ORDERBOOKS_S3_PREFIX = "raw/kalshi/market_orderbooks"
DEFAULT_MARKET_TRADES_S3_PREFIX = "raw/kalshi/market_trades"
DEFAULT_MARKET_TRADES_STATE_PREFIX = "state/kalshi/market_trades"
DEFAULT_TRADE_FIRST_RUN_LOOKBACK_HOURS = 24
DEFAULT_TRADE_WATERMARK_OVERLAP_SECONDS = 60
PROJECT_ROOT = Path(__file__).resolve().parents[4]
PACKAGE_ROOT = Path(__file__).resolve().parents[2]

EventTickerLoader = Callable[[str], list[str]]


@dataclass(frozen=True)
class TradeFetchConfig:
    mode: str
    paginate_trades: bool
    state_bucket: str
    state_prefix: str
    state_key: str
    first_run_lookback_hours: float
    watermark_overlap_seconds: int
    backfill_min_ts: int | None
    backfill_max_ts: int | None
    update_watermark: bool


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


def _coerce_float(value: Any, *, name: str, default: float) -> float:
    if value in (None, ""):
        return default
    try:
        resolved = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric, got {value!r}.") from exc
    if resolved <= 0:
        raise ValueError(f"{name} must be greater than zero.")
    return resolved


def _coerce_nonnegative_int(value: Any, *, name: str, default: int) -> int:
    if value in (None, ""):
        return default
    try:
        resolved = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer, got {value!r}.") from exc
    if resolved < 0:
        raise ValueError(f"{name} must be greater than or equal to zero.")
    return resolved


def _coerce_epoch_seconds(value: Any, *, name: str) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, dt.datetime):
        resolved = value
    elif isinstance(value, (int, float)):
        epoch_seconds = int(value)
        if epoch_seconds < 0:
            raise ValueError(f"{name} must be greater than or equal to zero.")
        return epoch_seconds
    else:
        text = str(value).strip()
        if text.isdigit():
            return int(text)
        try:
            resolved = dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"{name} must be a Unix timestamp or ISO-8601 timestamp, got {value!r}.") from exc

    if resolved.tzinfo is None:
        resolved = resolved.replace(tzinfo=dt.timezone.utc)
    epoch_seconds = int(resolved.astimezone(dt.timezone.utc).timestamp())
    if epoch_seconds < 0:
        raise ValueError(f"{name} must be greater than or equal to zero.")
    return epoch_seconds


def _format_epoch_seconds(epoch_seconds: int) -> str:
    return (
        dt.datetime.fromtimestamp(epoch_seconds, tz=dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _resolve_trade_fetch_config(
    event: dict[str, Any],
    *,
    bucket: str,
    run_started_at: dt.datetime,
) -> TradeFetchConfig:
    legacy_paginate_trades = _resolve_paginate_trades(event)
    mode = event_value(event, "trade_fetch_mode", "market_trades_fetch_mode")
    if mode in (None, "") and legacy_paginate_trades:
        mode = "full_history"
    if mode in (None, ""):
        mode = os.getenv("KALSHI_MARKET_TRADES_FETCH_MODE")
    if mode in (None, ""):
        mode = "incremental"

    mode = str(mode).strip().lower().replace("-", "_")
    if mode == "full":
        mode = "full_history"
    supported_modes = {"incremental", "recent", "backfill", "full_history"}
    if mode not in supported_modes:
        raise ValueError(f"trade_fetch_mode must be one of {sorted(supported_modes)}, got {mode!r}.")

    state_bucket = _configured_string(
        event,
        keys=("market_trades_state_bucket", "trade_state_bucket", "state_bucket"),
        env_vars=("KALSHI_MARKET_TRADES_STATE_BUCKET",),
    ) or bucket
    state_prefix = _resolve_entity_prefix(
        event,
        keys=("market_trades_state_prefix", "trade_state_prefix"),
        env_var="KALSHI_MARKET_TRADES_STATE_PREFIX",
        default=DEFAULT_MARKET_TRADES_STATE_PREFIX,
    )
    first_run_lookback_hours = _coerce_float(
        event_value(event, "trade_first_run_lookback_hours", "market_trades_first_run_lookback_hours")
        or os.getenv("KALSHI_MARKET_TRADES_FIRST_RUN_LOOKBACK_HOURS"),
        name="trade_first_run_lookback_hours",
        default=DEFAULT_TRADE_FIRST_RUN_LOOKBACK_HOURS,
    )
    watermark_overlap_seconds = _coerce_nonnegative_int(
        event_value(event, "trade_watermark_overlap_seconds", "market_trades_watermark_overlap_seconds")
        or os.getenv("KALSHI_MARKET_TRADES_WATERMARK_OVERLAP_SECONDS"),
        name="trade_watermark_overlap_seconds",
        default=DEFAULT_TRADE_WATERMARK_OVERLAP_SECONDS,
    )

    backfill_min_ts = _coerce_epoch_seconds(
        event_value(event, "trade_backfill_start_ts", "trade_backfill_start_time", "market_trades_min_ts")
        or os.getenv("KALSHI_MARKET_TRADES_BACKFILL_START_TS"),
        name="trade_backfill_start_ts",
    )
    backfill_max_ts = _coerce_epoch_seconds(
        event_value(event, "trade_backfill_end_ts", "trade_backfill_end_time", "market_trades_max_ts")
        or os.getenv("KALSHI_MARKET_TRADES_BACKFILL_END_TS"),
        name="trade_backfill_end_ts",
    )
    if mode == "backfill":
        if backfill_min_ts is None:
            raise ValueError("trade_fetch_mode=backfill requires trade_backfill_start_ts or trade_backfill_start_time.")
        if backfill_max_ts is None:
            backfill_max_ts = int(run_started_at.astimezone(dt.timezone.utc).timestamp())
        if backfill_max_ts < backfill_min_ts:
            raise ValueError("trade_backfill_end_ts must be greater than or equal to trade_backfill_start_ts.")
    elif backfill_min_ts is not None or backfill_max_ts is not None:
        raise ValueError("Set trade_fetch_mode=backfill before using trade backfill bounds.")

    update_watermark_value = event_value(event, "update_trade_watermark", "write_trade_watermark")
    if update_watermark_value in (None, ""):
        update_watermark_value = os.getenv("KALSHI_MARKET_TRADES_UPDATE_WATERMARK")
    update_watermark = _coerce_bool(update_watermark_value, default=(mode == "incremental"))

    return TradeFetchConfig(
        mode=mode,
        paginate_trades=mode in {"incremental", "backfill", "full_history"},
        state_bucket=state_bucket,
        state_prefix=state_prefix,
        state_key=f"{state_prefix}/watermarks.json",
        first_run_lookback_hours=first_run_lookback_hours,
        watermark_overlap_seconds=watermark_overlap_seconds,
        backfill_min_ts=backfill_min_ts,
        backfill_max_ts=backfill_max_ts,
        update_watermark=update_watermark,
    )


def _empty_trade_watermark_state() -> dict[str, Any]:
    return {
        "version": 1,
        "markets": {},
    }


def _load_trade_watermark_state(
    state_store: S3JsonStore,
    *,
    bucket: str,
    key: str,
) -> dict[str, Any]:
    payload = state_store.get_json(bucket=bucket, key=key)
    if not isinstance(payload, dict):
        return _empty_trade_watermark_state()
    markets = payload.get("markets")
    if not isinstance(markets, dict):
        payload = dict(payload)
        payload["markets"] = {}
    payload["version"] = payload.get("version") or 1
    return payload


def _market_tickers(markets: list[dict[str, Any]]) -> list[str]:
    tickers: list[str] = []
    for market in markets:
        ticker = market.get("ticker")
        if ticker not in (None, ""):
            tickers.append(str(ticker))
    return list(dict.fromkeys(tickers))


def _entry_checked_through_ts(entry: dict[str, Any]) -> int | None:
    for key in ("checked_through_ts", "max_created_ts", "last_seen_trade_ts"):
        value = _coerce_epoch_seconds(entry.get(key), name=key)
        if value is not None:
            return value
    return None


def _build_trade_fetch_options(
    *,
    tickers: list[str],
    config: TradeFetchConfig,
    state: dict[str, Any],
    run_started_at: dt.datetime,
) -> dict[str, dict[str, int | bool]]:
    if config.mode == "recent":
        return {}
    if config.mode == "full_history":
        return {ticker: {"all_pages": True} for ticker in tickers}
    if config.mode == "backfill":
        return {
            ticker: {
                "all_pages": True,
                "min_ts": config.backfill_min_ts,
                "max_ts": config.backfill_max_ts,
            }
            for ticker in tickers
        }

    run_ts = int(run_started_at.astimezone(dt.timezone.utc).timestamp())
    first_run_min_ts = max(0, run_ts - int(config.first_run_lookback_hours * 3600))
    state_markets = state.get("markets", {})
    options: dict[str, dict[str, int | bool]] = {}
    for ticker in tickers:
        entry = state_markets.get(ticker, {})
        checked_through_ts = _entry_checked_through_ts(entry) if isinstance(entry, dict) else None
        min_ts = (
            max(0, checked_through_ts - config.watermark_overlap_seconds)
            if checked_through_ts is not None
            else first_run_min_ts
        )
        options[ticker] = {
            "all_pages": True,
            "min_ts": min_ts,
            "max_ts": run_ts,
        }
    return options


def _latest_trade_watermarks(trades: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    watermarks: dict[str, dict[str, Any]] = {}
    for trade in trades:
        ticker = trade.get("ticker") or trade.get("market_ticker")
        created_ts = _coerce_epoch_seconds(trade.get("created_time"), name="created_time")
        if ticker in (None, "") or created_ts is None:
            continue

        ticker = str(ticker)
        current = watermarks.get(ticker)
        if current is None or created_ts >= current["last_seen_trade_ts"]:
            watermarks[ticker] = {
                "last_seen_trade_ts": created_ts,
                "last_seen_trade_time": _format_epoch_seconds(created_ts),
                "last_seen_trade_id": trade.get("trade_id"),
            }
    return watermarks


def _merge_trade_watermark_state(
    *,
    state: dict[str, Any],
    tickers: list[str],
    trades: list[dict[str, Any]],
    checked_through_ts: int,
    ingested_at: str,
) -> dict[str, Any]:
    merged = dict(state)
    state_markets = dict(merged.get("markets", {}))
    latest_by_ticker = _latest_trade_watermarks(trades)

    for ticker in tickers:
        existing = state_markets.get(ticker, {})
        entry = dict(existing) if isinstance(existing, dict) else {}
        latest = latest_by_ticker.get(ticker)
        if latest:
            existing_last_seen = _coerce_epoch_seconds(entry.get("last_seen_trade_ts"), name="last_seen_trade_ts")
            if existing_last_seen is None or latest["last_seen_trade_ts"] >= existing_last_seen:
                entry.update(latest)
        entry.update(
            {
                "checked_through_ts": checked_through_ts,
                "checked_through_time": _format_epoch_seconds(checked_through_ts),
                "updated_at": ingested_at,
            }
        )
        state_markets[ticker] = entry

    merged["version"] = 1
    merged["updated_at"] = ingested_at
    merged["markets"] = state_markets
    return merged


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
    state_store: S3JsonStore | None = None,
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
    trade_fetch_config = _resolve_trade_fetch_config(event, bucket=bucket, run_started_at=run_started_at)

    markets_client = markets_client or Markets()
    s3_writer = s3_writer or S3JsonLinesWriter()
    state_store = state_store or S3JsonStore()

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
        "Fetching orderbooks and trades for %s market(s); trade_fetch_mode=%s.",
        len(market_rows),
        trade_fetch_config.mode,
    )
    tickers = _market_tickers(market_rows)
    trade_watermark_state = _load_trade_watermark_state(
        state_store,
        bucket=trade_fetch_config.state_bucket,
        key=trade_fetch_config.state_key,
    )
    trade_fetch_options_by_ticker = _build_trade_fetch_options(
        tickers=tickers,
        config=trade_fetch_config,
        state=trade_watermark_state,
        run_started_at=run_started_at,
    )
    detail_data = markets_client.get_market_details(
        market_rows,
        paginate_trades=trade_fetch_config.paginate_trades,
        trade_fetch_options_by_ticker=trade_fetch_options_by_ticker or None,
    )

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

    watermark_write: dict[str, Any] | None = None
    if trade_fetch_config.update_watermark and tickers:
        checked_through_ts = (
            trade_fetch_config.backfill_max_ts
            if trade_fetch_config.mode == "backfill" and trade_fetch_config.backfill_max_ts is not None
            else int(run_started_at.astimezone(dt.timezone.utc).timestamp())
        )
        updated_state = _merge_trade_watermark_state(
            state=trade_watermark_state,
            tickers=tickers,
            trades=detail_data["trades"],
            checked_through_ts=checked_through_ts,
            ingested_at=ingested_at,
        )
        watermark_write = state_store.put_json(
            bucket=trade_fetch_config.state_bucket,
            key=trade_fetch_config.state_key,
            payload=updated_state,
        )

    return {
        "source": "kalshi",
        "entity": "markets",
        "market_ticker": market_ticker,
        "event_ticker": event_ticker,
        "event_query_file": event_query_file,
        "event_tickers": event_tickers,
        "paginate_trades": trade_fetch_config.paginate_trades,
        "trade_fetch_mode": trade_fetch_config.mode,
        "trade_fetch_window_count": len(trade_fetch_options_by_ticker),
        "trade_watermark": {
            "state_bucket": trade_fetch_config.state_bucket,
            "state_key": trade_fetch_config.state_key,
            "updated": watermark_write is not None,
            "write": watermark_write,
        },
        "row_counts": {
            entity: result["row_count"]
            for entity, result in writes.items()
        },
        "writes": writes,
    }


if __name__ == "__main__":
    print(run())
