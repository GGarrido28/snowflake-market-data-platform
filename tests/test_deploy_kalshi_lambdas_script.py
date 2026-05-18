import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "deploy_kalshi_lambdas.ps1"


def _script() -> str:
    return SCRIPT_PATH.read_text(encoding="utf-8")


class DeployKalshiLambdasScriptTests(unittest.TestCase):
    def test_script_includes_markets_lambda_outputs_and_smoke_invoke(self):
        script = _script()

        self.assertIn("[string]$MarketsMarketTicker", script)
        self.assertIn("[string]$MarketsEventTicker", script)
        self.assertIn("[string]$MarketsEventQueryFile", script)
        self.assertIn("[switch]$MarketsPaginateTrades", script)
        self.assertIn("[switch]$SkipMarketsInvoke", script)
        self.assertIn("kalshi_markets_lambda_function_name", script)
        self.assertIn("Deployed Kalshi Markets Lambda", script)
        self.assertIn("kalshi-markets-response.json", script)

    def test_script_requires_at_most_one_markets_scope(self):
        script = _script()

        self.assertIn("$MarketsScopeCount", script)
        self.assertIn("Use only one of -MarketsMarketTicker", script)
        self.assertIn("MarketsEventTicker", script)
        self.assertIn("MarketsEventQueryFile", script)

    def test_script_skips_markets_smoke_invoke_without_scope(self):
        script = _script()

        self.assertIn("Skipping Kalshi Markets smoke invoke because no Markets scope was provided", script)
        self.assertIn('market_ticker"] = $MarketsMarketTicker', script)
        self.assertIn('event_ticker"] = $MarketsEventTicker', script)
        self.assertIn('event_query_file"] = $MarketsEventQueryFile', script)
        self.assertIn("paginate_trades = [bool]$MarketsPaginateTrades", script)


if __name__ == "__main__":
    unittest.main()
