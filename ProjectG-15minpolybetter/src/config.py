from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # === Secrets (from .env) ===
    PRIVATE_KEY: str = ""
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # === Odds Thresholds ===
    ODDS_CAUTION_MIN: float = 0.85
    ODDS_CAUTION_MAX: float = 0.89
    ODDS_STANDARD_MIN: float = 0.90
    ODDS_STANDARD_MAX: float = 0.94
    ODDS_CONFIDENCE_MIN: float = 0.95

    # === Momentum Thresholds (5min % change) ===
    MOMENTUM_CAUTION: float = 0.005   # 0.5%
    MOMENTUM_STANDARD: float = 0.003  # 0.3%
    # Confidence zone: direction match only (no momentum threshold)

    # === Bet Sizing (% of active buy-in) ===
    BET_PCT_CAUTION: float = 0.05    # 5%
    BET_PCT_STANDARD: float = 0.10   # 10%
    BET_PCT_CONFIDENCE: float = 0.15 # 15%

    # === Bankroll ===
    TOTAL_BANKROLL: float = 300.0
    BUYIN_SIZE: float = 50.0
    TOTAL_BUYINS: int = 6
    BUYIN_BUST_THRESHOLD: float = 25.0    # below this = bust
    BUYIN_GRADUATE_THRESHOLD: float = 75.0 # merge with next
    BUYIN_WITHDRAW_THRESHOLD: float = 100.0 # withdraw $50

    # === Position Limits ===
    MAX_CONCURRENT_BETS: int = 2
    MAX_CONCURRENT_BETS_LOW: int = 1  # when buy-in < $30
    LOW_BUYIN_THRESHOLD: float = 30.0
    MAX_BET_PCT: float = 0.15  # 15% cap

    # === Circuit Breakers ===
    CONSECUTIVE_LOSS_LIMIT: int = 3
    PAUSE_DURATION_SECONDS: int = 3600  # 1 hour
    DAILY_LOSS_LIMIT_PCT: float = 0.30  # 30% of buy-in
    MAX_CONSECUTIVE_BUSTS: int = 3

    # === Liquidity Filter ===
    LIQUIDITY_ASK_MULTIPLIER: float = 3.0  # ask qty >= 3x bet
    MAX_SPREAD: float = 0.02               # $0.02
    RECENT_TRADE_WINDOW: int = 300         # 5 minutes in seconds

    # === Timing ===
    MIN_REMAINING_SECONDS: int = 120  # 2 min buffer before market close
    DATA_FRESHNESS_SECONDS: float = 3.0  # stale if > 3s old

    # === Data Feed URLs ===
    BINANCE_WS_BTC: str = "wss://stream.binance.com:9443/ws/btcusdt@trade"
    BINANCE_WS_ETH: str = "wss://stream.binance.com:9443/ws/ethusdt@trade"
    POLYMARKET_CLOB_WS: str = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
    GAMMA_API_URL: str = "https://gamma-api.polymarket.com"
    CLOB_API_URL: str = "https://clob.polymarket.com"

    # === Reconnect ===
    WS_RECONNECT_DELAY: float = 5.0  # seconds
    API_RETRY_BACKOFF: float = 2.0    # exponential backoff base

    # === Coins ===
    SUPPORTED_COINS: list[str] = Field(default=["BTC", "ETH"])

    # === Modes ===
    # observe / paper / live
    MODE: str = "observe"

    # === SQLite ===
    DB_PATH: str = "data/polybot.db"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
