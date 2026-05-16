import os
import unittest

from market_data_platform.sources.kalshi.utils.authentication import (
    load_api_key_id,
    load_private_key_from_file,
    sign_pss_text,
)


class KalshiSecretsManagerSmokeTests(unittest.TestCase):
    @unittest.skipUnless(
        os.getenv("RUN_KALSHI_SECRET_SMOKE_TEST") == "1",
        "Set RUN_KALSHI_SECRET_SMOKE_TEST=1 to fetch the real Kalshi secret from AWS.",
    )
    def test_fetches_real_kalshi_secret_and_signs_message(self):
        self.assertTrue(
            os.getenv("KALSHI_SECRET_ARN") or os.getenv("KALSHI_SECRET_NAME"),
            "Set KALSHI_SECRET_ARN or KALSHI_SECRET_NAME before running the smoke test.",
        )

        key_id = load_api_key_id()
        private_key = load_private_key_from_file()
        signature = sign_pss_text(private_key, "kalshi-secret-smoke-test")

        self.assertGreater(len(key_id), 0)
        self.assertGreaterEqual(private_key.key_size, 2048)
        self.assertGreater(len(signature), 0)


if __name__ == "__main__":
    unittest.main()
