"""Timezone helpers for analysis code.

The dbt staging layer uses `try_to_timestamp_ntz` on Kalshi's UTC timestamps,
which strips the offset and stores naive Python datetimes. Downstream notebooks
and queries therefore receive naive values that should be interpreted as
**UTC wall-clock**, and need to be converted to a viewer-friendly timezone
(US Eastern) for display.

This module is intentionally narrow: one converter, three accepted input
shapes (`datetime`, `pandas.Timestamp`, `pandas.Series` of either). If a
caller needs a different target timezone, swap the `ZoneInfo` constant rather
than overload the API.
"""

from __future__ import annotations

import datetime as _dt
from typing import Union
from zoneinfo import ZoneInfo

import pandas as pd

_UTC = _dt.timezone.utc
_EASTERN = ZoneInfo("America/New_York")

_DatetimeLike = Union[_dt.datetime, pd.Timestamp, pd.Series]


def utc_to_eastern(ts: _DatetimeLike) -> _DatetimeLike:
    """Convert a UTC value to US Eastern time, handling DST automatically.

    Accepted inputs:

    - `datetime.datetime` — naive treated as UTC; aware converted from its tz.
    - `pandas.Timestamp` — same semantics as datetime.
    - `pandas.Series` of datetime-like values — vectorised; naive treated as UTC.

    Returns a tz-aware `America/New_York` value of the same shape as the input.
    Strip the timezone afterwards with `.dt.tz_localize(None)` (Series) or
    `.replace(tzinfo=None)` (scalar) if a downstream consumer wants naive ET.
    """
    if isinstance(ts, pd.Series):
        coerced = pd.to_datetime(ts)
        if coerced.dt.tz is None:
            coerced = coerced.dt.tz_localize("UTC")
        return coerced.dt.tz_convert(_EASTERN)

    if isinstance(ts, pd.Timestamp):
        if ts.tz is None:
            ts = ts.tz_localize("UTC")
        return ts.tz_convert(_EASTERN)

    if isinstance(ts, _dt.datetime):
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=_UTC)
        return ts.astimezone(_EASTERN)

    raise TypeError(
        f"utc_to_eastern accepts datetime, pandas.Timestamp, or pandas.Series; "
        f"got {type(ts).__name__}"
    )
