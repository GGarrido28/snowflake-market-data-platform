import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[3]
_env_path = PROJECT_ROOT / '.env'
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)

SNOWFLAKE_CONFIG = {
    "account": os.environ.get("SNOWFLAKE_ACCOUNT"),
    "user": os.environ.get("SNOWFLAKE_USER"),
    "private_key_path": os.environ.get("SNOWFLAKE_PRIVATE_KEY_PATH"),
    "private_key_pem": os.environ.get("SNOWFLAKE_PRIVATE_KEY_PEM"),
    "private_key_secret_arn": os.environ.get("SNOWFLAKE_PRIVATE_KEY_SECRET_ARN"),
    "private_key_secret_name": os.environ.get("SNOWFLAKE_PRIVATE_KEY_SECRET_NAME"),
    "private_key_passphrase": os.environ.get("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE"),
    "warehouse": os.environ.get("SNOWFLAKE_WAREHOUSE"),
    "role": os.environ.get("SNOWFLAKE_ROLE"),
}
