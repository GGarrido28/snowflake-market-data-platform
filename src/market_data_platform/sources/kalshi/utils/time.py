from datetime import datetime, timezone


def utc_to_local(value) -> datetime:
    """Convert a UTC timestamp to the local timezone. Accepts ISO 8601 strings or Unix timestamps (int/float)."""
    if isinstance(value, (int, float)):
        dt = datetime.fromtimestamp(value, tz=timezone.utc)
    elif isinstance(value, str):
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        raise TypeError(f"Expected str, int, or float, got {type(value).__name__}")
    return dt.astimezone()
