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

RPC_URL = os.environ.get("PROJECTK_RPC_URL", "").strip()
WATCHER_POLL_SECONDS = int(os.environ.get("PROJECTK_WATCHER_POLL_SECONDS", "10"))
WATCHER_CONFIRMATIONS = int(os.environ.get("PROJECTK_WATCHER_CONFIRMATIONS", "2"))
WATCHER_MAX_BLOCK_RANGE = int(os.environ.get("PROJECTK_WATCHER_MAX_BLOCK_RANGE", "200"))
WATCHER_MAX_LAG_BLOCKS = int(os.environ.get("PROJECTK_WATCHER_MAX_LAG_BLOCKS", "600"))
WATCHER_POLL_MIN_SECONDS = int(os.environ.get("PROJECTK_WATCHER_POLL_MIN_SECONDS", "5"))
WATCHER_POLL_MAX_SECONDS = int(os.environ.get("PROJECTK_WATCHER_POLL_MAX_SECONDS", "10"))
WATCHER_BACKOFF_ERROR_STREAK = int(os.environ.get("PROJECTK_WATCHER_BACKOFF_ERROR_STREAK", "2"))
WATCHER_BACKOFF_SLOW_TICK_MS = int(os.environ.get("PROJECTK_WATCHER_BACKOFF_SLOW_TICK_MS", "4000"))
WATCHER_RECOVERY_HEALTHY_TICKS = int(os.environ.get("PROJECTK_WATCHER_RECOVERY_HEALTHY_TICKS", "6"))
WATCHER_EXCHANGES = os.environ.get(
    "PROJECTK_WATCHER_EXCHANGES",
    ",".join(
        [
            "0xC5d563A36AE78145C45a50134d48A1215220f80a",
            "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E",
        ]
    ),
).strip()
