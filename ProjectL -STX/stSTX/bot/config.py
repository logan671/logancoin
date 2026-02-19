from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _read_env_file(path: Path) -> None:
    """Load KEY=VALUE pairs from a local .env file if it exists."""
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _require_str(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required env var: {name}")
    return value


def _get_str(name: str, default: str) -> str:
    return os.getenv(name, default).strip()


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw.strip())
    except ValueError as exc:
        raise ValueError(f"Invalid int for {name}: {raw}") from exc


def _get_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw.strip())
    except ValueError as exc:
        raise ValueError(f"Invalid float for {name}: {raw}") from exc


def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    norm = raw.strip().lower()
    if norm in {"1", "true", "yes", "y", "on"}:
        return True
    if norm in {"0", "false", "no", "n", "off"}:
        return False
    raise ValueError(f"Invalid bool for {name}: {raw}")


@dataclass(frozen=True)
class Settings:
    environment: str
    log_level: str
    dry_run: bool

    # Strategy and risk parameters
    max_order_usd: float
    entry_threshold_pct: float
    min_liquidity_usd: float
    execution_buffer_pct: float
    max_daily_loss_pct: float
    max_consecutive_losses: int

    # Network fee policy
    network_fee_cap_stx: float
    min_fee_floor_stx: float
    fee_multiplier: float

    # Public APIs
    hiro_api_base: str
    bitflow_ticker_url: str
    bitflow_ststx_pool_id: str
    bitflow_quotes_base: str
    coingecko_api_base: str
    stx_coingecko_id: str
    ststx_coingecko_id: str

    # Runtime loop
    poll_interval_sec: int
    dex_fee_pct: float
    daily_start_equity_stx: float
    db_path: str
    tx_estimated_bytes: int

    # Telegram
    tg_enabled: bool
    tg_bot_token: str
    tg_chat_id: str
    tg_parse_mode: str

    # Trading signer
    trading_private_key: str
    trading_address: str
    ststx_token_contract: str
    executor_command: str
    executor_timeout_sec: int

    # Rebalance
    rebalance_enabled: bool
    rebalance_check_interval_sec: int
    rebalance_target_stx_weight: float
    rebalance_drift_pct: float
    rebalance_min_order_usd: float
    rebalance_max_order_usd: float
    rebalance_max_per_day: int
    rebalance_buffer_pct: float


def load_settings() -> Settings:
    # Allow local env file for development. Real server env vars still override.
    base_dir = Path(__file__).resolve().parent
    env_path = base_dir / ".env"
    _read_env_file(env_path)

    settings = Settings(
        environment=_get_str("ENVIRONMENT", "development"),
        log_level=_get_str("LOG_LEVEL", "INFO"),
        dry_run=_get_bool("DRY_RUN", True),
        max_order_usd=_get_float("MAX_ORDER_USD", 500.0),
        entry_threshold_pct=_get_float("ENTRY_THRESHOLD_PCT", 0.8),
        min_liquidity_usd=_get_float("MIN_LIQUIDITY_USD", 200000.0),
        execution_buffer_pct=_get_float("EXECUTION_BUFFER_PCT", 0.2),
        max_daily_loss_pct=_get_float("MAX_DAILY_LOSS_PCT", 2.0),
        max_consecutive_losses=_get_int("MAX_CONSECUTIVE_LOSSES", 5),
        network_fee_cap_stx=_get_float("NETWORK_FEE_CAP_STX", 0.25),
        min_fee_floor_stx=_get_float("MIN_FEE_FLOOR_STX", 0.001),
        fee_multiplier=_get_float("FEE_MULTIPLIER", 1.2),
        hiro_api_base=_get_str("HIRO_API_BASE", "https://api.hiro.so"),
        bitflow_ticker_url=_get_str(
            "BITFLOW_TICKER_URL",
            "https://bitflow-sdk-api-gateway-7owjsmt8.uc.gateway.dev/ticker",
        ),
        bitflow_ststx_pool_id=_get_str(
            "BITFLOW_STSTX_POOL_ID",
            "SM1793C4R5PZ4NS4VQ4WMP7SKKYVH8JZEWSZ9HCCR.stableswap-pool-stx-ststx-v-1-4",
        ),
        bitflow_quotes_base=_get_str(
            "BITFLOW_QUOTES_BASE", "https://bff.bitflowapis.finance/api/quotes"
        ),
        coingecko_api_base=_get_str(
            "COINGECKO_API_BASE", "https://api.coingecko.com/api/v3"
        ),
        stx_coingecko_id=_get_str("STX_COINGECKO_ID", "blockstack"),
        ststx_coingecko_id=_get_str("STSTX_COINGECKO_ID", "stacking-dao"),
        poll_interval_sec=_get_int("POLL_INTERVAL_SEC", 30),
        dex_fee_pct=_get_float("DEX_FEE_PCT", 0.3),
        daily_start_equity_stx=_get_float("DAILY_START_EQUITY_STX", 1000.0),
        db_path=_get_str("DB_PATH", str(base_dir / "bot.sqlite3")),
        tx_estimated_bytes=_get_int("TX_ESTIMATED_BYTES", 350),
        tg_enabled=_get_bool("TG_ENABLED", True),
        tg_bot_token=_require_str("TG_BOT_TOKEN"),
        tg_chat_id=_require_str("TG_CHAT_ID"),
        tg_parse_mode=_get_str("TG_PARSE_MODE", "Markdown"),
        trading_private_key=_require_str("TRADING_PRIVATE_KEY"),
        trading_address=_get_str("TRADING_ADDRESS", ""),
        ststx_token_contract=_get_str(
            "STSTX_TOKEN_CONTRACT",
            "SP4SZE494VC2YC5JYG7AYFQ44F5Q4PYV7DVMDPBG.ststx-token",
        ),
        executor_command=_get_str("EXECUTOR_COMMAND", ""),
        executor_timeout_sec=_get_int("EXECUTOR_TIMEOUT_SEC", 25),
        rebalance_enabled=_get_bool("REBALANCE_ENABLED", True),
        rebalance_check_interval_sec=_get_int("REBALANCE_CHECK_INTERVAL_SEC", 21600),
        rebalance_target_stx_weight=_get_float("REBALANCE_TARGET_STX_WEIGHT", 0.65),
        rebalance_drift_pct=_get_float("REBALANCE_DRIFT_PCT", 20.0),
        rebalance_min_order_usd=_get_float("REBALANCE_MIN_ORDER_USD", 100.0),
        rebalance_max_order_usd=_get_float("REBALANCE_MAX_ORDER_USD", 200.0),
        rebalance_max_per_day=_get_int("REBALANCE_MAX_PER_DAY", 2),
        rebalance_buffer_pct=_get_float("REBALANCE_BUFFER_PCT", 0.15),
    )

    _validate(settings)
    return settings


def _validate(settings: Settings) -> None:
    if settings.max_order_usd <= 0:
        raise ValueError("MAX_ORDER_USD must be > 0")
    if settings.network_fee_cap_stx <= 0:
        raise ValueError("NETWORK_FEE_CAP_STX must be > 0")
    if settings.fee_multiplier < 1.0:
        raise ValueError("FEE_MULTIPLIER should be >= 1.0")
    if settings.max_daily_loss_pct <= 0:
        raise ValueError("MAX_DAILY_LOSS_PCT must be > 0")
    if settings.max_consecutive_losses <= 0:
        raise ValueError("MAX_CONSECUTIVE_LOSSES must be > 0")
    if settings.poll_interval_sec <= 0:
        raise ValueError("POLL_INTERVAL_SEC must be > 0")
    if settings.daily_start_equity_stx <= 0:
        raise ValueError("DAILY_START_EQUITY_STX must be > 0")
    if settings.tx_estimated_bytes <= 0:
        raise ValueError("TX_ESTIMATED_BYTES must be > 0")
    if settings.executor_timeout_sec <= 0:
        raise ValueError("EXECUTOR_TIMEOUT_SEC must be > 0")
    if not settings.dry_run and not settings.executor_command:
        raise ValueError("EXECUTOR_COMMAND is required when DRY_RUN=false")
    if not (0 < settings.rebalance_target_stx_weight < 1):
        raise ValueError("REBALANCE_TARGET_STX_WEIGHT must be between 0 and 1")
    if settings.rebalance_drift_pct < 0:
        raise ValueError("REBALANCE_DRIFT_PCT must be >= 0")
    if settings.rebalance_min_order_usd <= 0:
        raise ValueError("REBALANCE_MIN_ORDER_USD must be > 0")
    if settings.rebalance_max_order_usd < settings.rebalance_min_order_usd:
        raise ValueError("REBALANCE_MAX_ORDER_USD must be >= REBALANCE_MIN_ORDER_USD")
    if settings.rebalance_max_per_day <= 0:
        raise ValueError("REBALANCE_MAX_PER_DAY must be > 0")
    if settings.rebalance_buffer_pct < 0:
        raise ValueError("REBALANCE_BUFFER_PCT must be >= 0")
