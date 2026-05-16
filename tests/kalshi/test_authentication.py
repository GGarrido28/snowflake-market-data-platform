import json
import os
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from market_data_platform.sources.kalshi.utils import authentication


def _private_key_pem() -> str:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")


class FakeSecretsManagerClient:
    def __init__(self, response: dict):
        self.response = response
        self.secret_ids: list[str] = []

    def get_secret_value(self, *, SecretId: str) -> dict:
        self.secret_ids.append(SecretId)
        return self.response


class AuthenticationTests(unittest.TestCase):
    def setUp(self):
        authentication._clear_secret_cache()

    def tearDown(self):
        authentication._clear_secret_cache()

    def _patch_boto3(self, response: dict):
        secrets_client = FakeSecretsManagerClient(response)
        boto3_client = Mock(return_value=secrets_client)
        boto3_module = types.SimpleNamespace(client=boto3_client)
        return patch.dict(sys.modules, {"boto3": boto3_module}), secrets_client, boto3_client

    def test_loads_api_key_id_and_private_key_from_secrets_manager(self):
        private_key_pem = _private_key_pem()
        response = {
            "SecretString": json.dumps(
                {
                    "kalshi_api_key_id": "kalshi-key-id",
                    "kalshi_private_key_pem": private_key_pem,
                }
            )
        }
        boto3_patch, secrets_client, boto3_client = self._patch_boto3(response)

        with patch.dict(os.environ, {"KALSHI_SECRET_NAME": "kalshi/dev/api"}, clear=True):
            with boto3_patch:
                key_id = authentication.load_api_key_id()
                private_key = authentication.load_private_key_from_file()

        self.assertEqual(key_id, "kalshi-key-id")
        self.assertIsInstance(private_key, rsa.RSAPrivateKey)
        self.assertEqual(secrets_client.secret_ids, ["kalshi/dev/api"])
        boto3_client.assert_called_once_with("secretsmanager")

    def test_uses_secret_arn_before_local_environment_values(self):
        response = {
            "SecretString": json.dumps(
                {
                    "kalshi_api_key_id": "secret-key-id",
                    "kalshi_private_key_pem": _private_key_pem(),
                }
            )
        }
        boto3_patch, _secrets_client, _boto3_client = self._patch_boto3(response)

        env = {
            "KALSHI_SECRET_ARN": "arn:aws:secretsmanager:us-east-2:123456789012:secret:kalshi",
            "KALSHI_API_KEY_ID": "local-key-id",
        }
        with patch.dict(os.environ, env, clear=True):
            with boto3_patch:
                self.assertEqual(authentication.load_api_key_id(), "secret-key-id")

    def test_falls_back_to_local_environment_and_private_key_file(self):
        private_key_pem = _private_key_pem()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False, encoding="utf-8") as fh:
            fh.write(private_key_pem)
            private_key_path = fh.name

        try:
            env = {
                "KALSHI_API_KEY_ID": "local-key-id",
                "KALSHI_API_KEY": private_key_path,
            }
            with patch.dict(os.environ, env, clear=True):
                self.assertEqual(authentication.load_api_key_id(), "local-key-id")
                private_key = authentication.load_private_key_from_file()

            self.assertIsInstance(private_key, rsa.RSAPrivateKey)
        finally:
            os.unlink(private_key_path)

    def test_raises_clear_error_when_no_credential_source_is_configured(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "KALSHI_SECRET_ARN"):
                authentication.load_api_key_id()

        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "KALSHI_SECRET_ARN"):
                authentication.load_private_key_from_file()

    def test_raises_clear_error_when_secret_is_missing_required_fields(self):
        response = {"SecretString": json.dumps({"unexpected": "value"})}
        boto3_patch, _secrets_client, _boto3_client = self._patch_boto3(response)

        with patch.dict(os.environ, {"KALSHI_SECRET_NAME": "kalshi/dev/api"}, clear=True):
            with boto3_patch:
                with self.assertRaisesRegex(ValueError, "API key id"):
                    authentication.load_api_key_id()

    def test_raises_clear_error_when_secret_is_not_json(self):
        response = {"SecretString": "not-json"}
        boto3_patch, _secrets_client, _boto3_client = self._patch_boto3(response)

        with patch.dict(os.environ, {"KALSHI_SECRET_NAME": "kalshi/dev/api"}, clear=True):
            with boto3_patch:
                with self.assertRaisesRegex(ValueError, "valid JSON"):
                    authentication.load_api_key_id()


if __name__ == "__main__":
    unittest.main()
