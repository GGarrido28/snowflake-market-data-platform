from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from dotenv import load_dotenv

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

PROJECT_ROOT = Path(__file__).resolve().parents[5]
_env_path = PROJECT_ROOT / '.env'
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)

SECRET_ID_FIELDS = ("kalshi_api_key_id", "api_key_id", "KALSHI_API_KEY_ID")
SECRET_PRIVATE_KEY_FIELDS = (
    "kalshi_private_key_pem",
    "private_key_pem",
    "KALSHI_PRIVATE_KEY_PEM",
)

_cached_secret_identifier: str | None = None
_cached_secret_payload: dict[str, str] | None = None


def _get_secret_identifier() -> str | None:
    return os.getenv("KALSHI_SECRET_ARN") or os.getenv("KALSHI_SECRET_NAME")


def _decode_secret_response(response: dict) -> dict[str, str]:
    if "SecretString" in response and response["SecretString"]:
        raw_secret = response["SecretString"]
    elif "SecretBinary" in response and response["SecretBinary"]:
        secret_binary = response["SecretBinary"]
        if isinstance(secret_binary, str):
            secret_binary = secret_binary.encode("utf-8")
        raw_secret = base64.b64decode(secret_binary).decode("utf-8")
    else:
        raise ValueError("Kalshi secret is missing SecretString or SecretBinary")

    try:
        secret_payload = json.loads(raw_secret)
    except json.JSONDecodeError as e:
        raise ValueError("Kalshi secret must be valid JSON") from e

    if not isinstance(secret_payload, dict):
        raise ValueError("Kalshi secret must be a JSON object")
    return secret_payload


def _load_secret_payload() -> dict[str, str] | None:
    global _cached_secret_identifier, _cached_secret_payload

    secret_identifier = _get_secret_identifier()
    if not secret_identifier:
        return None

    if (
        _cached_secret_payload is not None
        and _cached_secret_identifier == secret_identifier
    ):
        return _cached_secret_payload

    import boto3

    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId=secret_identifier)
    _cached_secret_payload = _decode_secret_response(response)
    _cached_secret_identifier = secret_identifier
    return _cached_secret_payload


def _secret_value(secret_payload: dict[str, str], fields: tuple[str, ...], label: str) -> str:
    for field in fields:
        value = secret_payload.get(field)
        if value:
            if not isinstance(value, str):
                raise ValueError(f"Kalshi secret field {field} for {label} must be a string")
            return value
    raise ValueError(f"Kalshi secret is missing required field for {label}: one of {fields}")


def _load_private_key_from_pem(private_key_pem: str) -> rsa.RSAPrivateKey:
    private_key = serialization.load_pem_private_key(
        private_key_pem.encode("utf-8"),
        password=None,
        backend=default_backend(),
    )
    if not isinstance(private_key, rsa.RSAPrivateKey):
        raise ValueError("Kalshi private key must be an RSA private key")
    return private_key


def _clear_secret_cache() -> None:
    global _cached_secret_identifier, _cached_secret_payload
    _cached_secret_identifier = None
    _cached_secret_payload = None


def load_private_key_from_file() -> rsa.RSAPrivateKey:
    secret_payload = _load_secret_payload()
    if secret_payload is not None:
        private_key_pem = _secret_value(
            secret_payload,
            SECRET_PRIVATE_KEY_FIELDS,
            "private key PEM",
        )
        return _load_private_key_from_pem(private_key_pem)

    private_key_path = os.getenv("KALSHI_API_KEY")
    if private_key_path is None:
        raise ValueError(
            "Set KALSHI_SECRET_ARN, KALSHI_SECRET_NAME, or KALSHI_API_KEY "
            "before loading the Kalshi private key"
        )
    with open(private_key_path, "rb") as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None,
            backend=default_backend()
        )
    return private_key


def load_api_key_id() -> str:
    secret_payload = _load_secret_payload()
    if secret_payload is not None:
        return _secret_value(secret_payload, SECRET_ID_FIELDS, "API key id")

    key_id = os.getenv("KALSHI_API_KEY_ID")
    if key_id is None:
        raise ValueError(
            "Set KALSHI_SECRET_ARN, KALSHI_SECRET_NAME, or KALSHI_API_KEY_ID "
            "before loading the Kalshi API key id"
        )
    return key_id


def sign_pss_text(private_key: rsa.RSAPrivateKey, text: str) -> str:
    message = text.encode('utf-8')
    try:
        signature = private_key.sign(
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.DIGEST_LENGTH
            ),
            hashes.SHA256()
        )
        return base64.b64encode(signature).decode('utf-8')
    except InvalidSignature as e:
        raise ValueError("RSA sign PSS failed") from e
