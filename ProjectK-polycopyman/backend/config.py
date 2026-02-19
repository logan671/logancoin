import os


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get("PROJECTK_DB_PATH", "/tmp/projectk_local.db")
API_HOST = os.environ.get("PROJECTK_API_HOST", "127.0.0.1")
API_PORT = int(os.environ.get("PROJECTK_API_PORT", "8081"))

TELEGRAM_BOT_TOKEN = os.environ.get("PROJECTK_TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.environ.get("PROJECTK_TELEGRAM_CHAT_ID", "").strip()
TELEGRAM_MAX_RETRIES = int(os.environ.get("PROJECTK_TELEGRAM_MAX_RETRIES", "3"))
TELEGRAM_OWNER_CHAT_ID = os.environ.get("PROJECTK_TELEGRAM_OWNER_CHAT_ID", "").strip()

VAULT_PASSPHRASE = os.environ.get("PROJECTK_VAULT_PASSPHRASE", "").strip()

EXECUTOR_MODE = os.environ.get("PROJECTK_EXECUTOR_MODE", "stub").strip().lower()
EXECUTOR_POLL_SECONDS = int(os.environ.get("PROJECTK_EXECUTOR_POLL_SECONDS", "10"))
POLYMARKET_HOST = os.environ.get("PROJECTK_POLYMARKET_HOST", "https://clob.polymarket.com").strip()
POLYMARKET_CHAIN_ID = int(os.environ.get("PROJECTK_POLYMARKET_CHAIN_ID", "137"))
POLYMARKET_SIGNATURE_TYPE = int(os.environ.get("PROJECTK_POLYMARKET_SIGNATURE_TYPE", "0"))
