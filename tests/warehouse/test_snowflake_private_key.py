import base64
import json
import sys
import types
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from market_data_platform.warehouse.snowflake import SnowflakeManager


def _private_key_pem() -> str:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")


class SnowflakePrivateKeyTests(unittest.TestCase):
    def _manager_for_private_key(self) -> SnowflakeManager:
        manager = SnowflakeManager.__new__(SnowflakeManager)
        manager.private_key_path = None
        manager.private_key_pem = None
        manager.private_key_secret_arn = None
        manager.private_key_secret_name = None
        manager.private_key_passphrase = None
        return manager

    def test_load_private_key_from_pem_env_config(self):
        manager = self._manager_for_private_key()
        manager.private_key_pem = _private_key_pem()

        key_bytes = manager._load_private_key()

        self.assertIsInstance(key_bytes, bytes)
        self.assertGreater(len(key_bytes), 0)

    def test_load_private_key_from_secret_json_payload(self):
        private_key_pem = _private_key_pem()
        manager = self._manager_for_private_key()
        manager.private_key_secret_arn = "arn:aws:secretsmanager:us-east-2:123:secret:snowflake"

        class FakeSecretsClient:
            def get_secret_value(self, *, SecretId):
                return {
                    "SecretString": json.dumps(
                        {
                            "snowflake_private_key_pem": private_key_pem,
                        }
                    )
                }

        fake_boto3 = types.SimpleNamespace(client=lambda service: FakeSecretsClient())
        with patch.dict(sys.modules, {"boto3": fake_boto3}):
            key_bytes = manager._load_private_key()

        self.assertIsInstance(key_bytes, bytes)
        self.assertGreater(len(key_bytes), 0)

    def test_decode_private_key_secret_accepts_binary_raw_pem(self):
        private_key_pem = _private_key_pem()
        manager = self._manager_for_private_key()

        payload = manager._decode_private_key_secret_response(
            {
                "SecretBinary": base64.b64encode(private_key_pem.encode("utf-8")),
            }
        )

        self.assertEqual(payload["private_key_pem"], private_key_pem)

    def test_missing_private_key_source_raises_clear_error(self):
        manager = self._manager_for_private_key()

        with self.assertRaisesRegex(ValueError, "SNOWFLAKE_PRIVATE_KEY_PATH"):
            manager._load_private_key()


if __name__ == "__main__":
    unittest.main()
