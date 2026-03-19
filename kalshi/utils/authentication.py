import base64
import os
from pathlib import Path
from dotenv import load_dotenv

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

_env_path = Path(__file__).parent.parent / '.env'
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)


def load_private_key_from_file() -> rsa.RSAPrivateKey:
    private_key_path = os.getenv("KALSHI_API_KEY")
    if private_key_path is None:
        raise ValueError("KALSHI_API_KEY environment variable not set")
    with open(private_key_path, "rb") as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None,
            backend=default_backend()
        )
    return private_key


def load_key_id_from_file() -> str:
    key_id = os.getenv("KALSHI_API_KEY_ID")
    if key_id is None:
        raise ValueError("KALSHI_API_KEY_ID environment variable not set")
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
