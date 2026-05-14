import datetime as dt
import unittest
from zoneinfo import ZoneInfo

import pandas as pd

from market_data_platform.utils.timezone import utc_to_eastern


EASTERN = ZoneInfo("America/New_York")


class UtcToEasternTests(unittest.TestCase):
    def test_naive_datetime_is_treated_as_utc(self):
        # 23:20 UTC on a May (EDT) day is 19:20 ET.
        result = utc_to_eastern(dt.datetime(2026, 5, 10, 23, 20))

        self.assertEqual(result.tzinfo, EASTERN)
        self.assertEqual((result.year, result.month, result.day), (2026, 5, 10))
        self.assertEqual((result.hour, result.minute), (19, 20))

    def test_aware_datetime_is_converted_from_its_tz(self):
        # 14:00 in Berlin (CEST, UTC+2) on the same day is 08:00 ET (EDT, UTC-4).
        berlin = ZoneInfo("Europe/Berlin")
        result = utc_to_eastern(dt.datetime(2026, 5, 10, 14, 0, tzinfo=berlin))

        self.assertEqual(result.tzinfo, EASTERN)
        self.assertEqual((result.hour, result.minute), (8, 0))

    def test_winter_date_uses_eastern_standard_time(self):
        # 23:20 UTC on a January day is 18:20 ET (EST, UTC-5), not 19:20.
        result = utc_to_eastern(dt.datetime(2026, 1, 10, 23, 20))

        self.assertEqual((result.hour, result.minute), (18, 20))

    def test_pandas_timestamp_naive_treated_as_utc(self):
        result = utc_to_eastern(pd.Timestamp("2026-05-10 23:20:00"))

        self.assertEqual(result.tz, EASTERN)
        self.assertEqual((result.hour, result.minute), (19, 20))

    def test_pandas_series_naive_treated_as_utc(self):
        series = pd.Series(pd.to_datetime(["2026-05-10 23:20:00", "2026-01-10 23:20:00"]))

        result = utc_to_eastern(series)

        # Output is tz-aware America/New_York, length preserved.
        self.assertEqual(str(result.dt.tz), "America/New_York")
        self.assertEqual(len(result), 2)
        # DST-aware: May entry shifts -4h, January entry shifts -5h.
        self.assertEqual(result.dt.hour.tolist(), [19, 18])

    def test_unsupported_type_raises_type_error(self):
        with self.assertRaisesRegex(TypeError, "utc_to_eastern accepts"):
            utc_to_eastern("2026-05-10T23:20:00Z")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
