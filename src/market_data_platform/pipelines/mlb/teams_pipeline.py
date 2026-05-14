import datetime as dt
import logging
import os
from typing import Any

from market_data_platform.sources.mlb import Teams
from market_data_platform.warehouse.s3 import S3JsonLinesWriter


logging.basicConfig(level=logging.INFO)

DEFAULT_S3_PREFIX = "raw/mlb/teams"


def _event_value(event: dict[str, Any], *keys: str) -> Any | None:
    for key in keys:
        value = event.get(key)
        if value not in (None, ""):
            return value
    return None


def _resolve_sport_id(event: dict[str, Any]) -> int:
    value = _event_value(event, "sport_id", "sportId") or os.getenv("MLB_TEAMS_SPORT_ID") or "1"
    return int(value)


def _resolve_bucket(event: dict[str, Any]) -> str:
    bucket = (
        _event_value(event, "s3_bucket", "bucket")
        or os.getenv("MLB_TEAMS_S3_BUCKET")
        or os.getenv("SNOWFLAKE_S3_BUCKET")
    )
    if not bucket:
        raise ValueError("Set MLB_TEAMS_S3_BUCKET or SNOWFLAKE_S3_BUCKET before running the MLB teams pipeline.")
    return str(bucket)


def _resolve_prefix(event: dict[str, Any]) -> str:
    prefix = (
        _event_value(event, "s3_prefix", "prefix")
        or os.getenv("MLB_TEAMS_S3_PREFIX")
        or os.getenv("SNOWFLAKE_S3_PREFIX")
        or DEFAULT_S3_PREFIX
    )
    return str(prefix).strip("/")


def _timestamp_for_key(value: dt.datetime) -> str:
    return (
        value.astimezone(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
        .replace("-", "")
        .replace(":", "")
    )


def build_s3_key(prefix: str, run_started_at: dt.datetime) -> str:
    run_started_at = run_started_at.astimezone(dt.timezone.utc)
    partition_date = run_started_at.date().isoformat()
    timestamp = _timestamp_for_key(run_started_at)
    return f"{prefix}/ingested_date={partition_date}/mlb_teams_{timestamp}.jsonl"


def _nested_value(row: dict[str, Any], parent: str, child: str) -> Any | None:
    value = row.get(parent)
    if isinstance(value, dict):
        return value.get(child)
    return None


def normalize_team(row: dict[str, Any], *, ingested_at: str) -> dict[str, Any]:
    return {
        "team_id": row.get("id"),
        "name": row.get("name"),
        "team_code": row.get("teamCode"),
        "abbreviation": row.get("abbreviation"),
        "team_name": row.get("teamName"),
        "location_name": row.get("locationName"),
        "first_year_of_play": row.get("firstYearOfPlay"),
        "sport_id": _nested_value(row, "sport", "id"),
        "sport_name": _nested_value(row, "sport", "name"),
        "league_id": _nested_value(row, "league", "id"),
        "league_name": _nested_value(row, "league", "name"),
        "division_id": _nested_value(row, "division", "id"),
        "division_name": _nested_value(row, "division", "name"),
        "venue_id": _nested_value(row, "venue", "id"),
        "venue_name": _nested_value(row, "venue", "name"),
        "active": row.get("active"),
        "ingested_at": ingested_at,
        "raw_payload": row,
    }


def normalize_teams(rows: list[dict[str, Any]], *, ingested_at: str) -> list[dict[str, Any]]:
    return [normalize_team(row, ingested_at=ingested_at) for row in rows]


def run(
    event: dict[str, Any] | None = None,
    *,
    teams_client: Teams | None = None,
    s3_writer: S3JsonLinesWriter | None = None,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    event = event or {}
    run_started_at = now or dt.datetime.now(dt.timezone.utc)
    ingested_at = run_started_at.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    sport_id = _resolve_sport_id(event)
    bucket = _resolve_bucket(event)
    prefix = _resolve_prefix(event)
    s3_key = build_s3_key(prefix, run_started_at)

    teams_client = teams_client or Teams()
    s3_writer = s3_writer or S3JsonLinesWriter()

    logging.info("Fetching MLB teams for sport_id=%s.", sport_id)
    raw_teams = teams_client.fetch_teams(sport_id=sport_id)
    rows = normalize_teams(raw_teams, ingested_at=ingested_at)
    logging.info("Writing %s MLB team row(s) to s3://%s/%s.", len(rows), bucket, s3_key)
    write_result = s3_writer.put_json_lines(bucket=bucket, key=s3_key, rows=rows)

    return {
        "source": "mlb",
        "entity": "teams",
        "sport_id": sport_id,
        "row_count": len(rows),
        **write_result,
    }


if __name__ == "__main__":
    print(run())
