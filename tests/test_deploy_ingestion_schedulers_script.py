import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "deploy_ingestion_schedulers.ps1"


def _script() -> str:
    return SCRIPT_PATH.read_text(encoding="utf-8")


class DeployIngestionSchedulersScriptTests(unittest.TestCase):
    def test_script_verifies_kalshi_markets_schedule_output(self):
        script = _script()

        self.assertIn("kalshi_markets_schedule_name", script)
        self.assertIn("Verifying EventBridge Scheduler schedule", script)


if __name__ == "__main__":
    unittest.main()
