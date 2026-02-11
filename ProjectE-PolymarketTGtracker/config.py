import os

BASE_DIR = os.environ.get(
    "PROJECTE_BASE_DIR",
    os.path.dirname(os.path.abspath(__file__)),
)

LOG_DIR = os.environ.get(
    "PROJECTE_LOG_DIR",
    os.path.join(BASE_DIR, "logs"),
)
TRACKER_LOG_PATH = os.environ.get(
    "PROJECTE_TRACKER_LOG_PATH",
    os.path.join(LOG_DIR, "tracker.log"),
)

DB_PATH = os.environ.get(
    "PROJECTE_DB_PATH",
    os.path.join(BASE_DIR, "tracker.db"),
)

BOT_TOKEN = os.environ.get("PROJECTE_BOT_TOKEN", "").strip()
CHANNEL_ID = os.environ.get("PROJECTE_CHANNEL_ID", "").strip()
OWNER_CHAT_ID = os.environ.get("PROJECTE_OWNER_CHAT_ID", "").strip()

RPC_URL = os.environ.get("PROJECTE_RPC_URL", "").strip()
POLL_SECONDS = int(os.environ.get("PROJECTE_POLL_SECONDS", "10"))
CONFIRMATIONS = int(os.environ.get("PROJECTE_CONFIRMATIONS", "2"))
MAX_BLOCK_RANGE = int(os.environ.get("PROJECTE_MAX_BLOCK_RANGE", "200"))
MAX_LAG_BLOCKS = int(os.environ.get("PROJECTE_MAX_LAG_BLOCKS", "300"))

CTF_EXCHANGE = os.environ.get(
    "PROJECTE_CTF_EXCHANGE",
    ",".join(
        [
            "0xC5d563A36AE78145C45a50134d48A1215220f80a",
            "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E",
        ]
    ),
)

GAMMA_API_BASE = os.environ.get(
    "PROJECTE_GAMMA_API_BASE",
    "https://gamma-api.polymarket.com",
)
MARKET_CACHE_TTL_SECONDS = int(
    os.environ.get("PROJECTE_MARKET_CACHE_TTL_SECONDS", "3600")
)

MAX_RETRIES = int(os.environ.get("PROJECTE_MAX_RETRIES", "3"))

MIN_USDC_ALERT = float(os.environ.get("PROJECTE_MIN_USDC_ALERT", "100"))
MIN_USDC_EXEMPT = os.environ.get(
    "PROJECTE_MIN_USDC_EXEMPT",
    "0x811192618fb0c7fcc678a81bb7c796a554bcb832",
).strip().lower()
