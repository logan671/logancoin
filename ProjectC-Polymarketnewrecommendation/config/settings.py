from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # OpenAI
    openai_api_key: str = Field(default="")

    # Perplexity
    perplexity_api_key: str = Field(default="")

    # Telegram
    telegram_bot_token: str = Field(default="")
    telegram_chat_id: str = Field(default="")

    # Polymarket API (no auth needed for reading)
    polymarket_base_url: str = "https://gamma-api.polymarket.com"
    polymarket_clob_url: str = "https://clob.polymarket.com"

    # Scanner Settings
    scan_interval_minutes: int = 5
    alpha_threshold: int = 50  # 일반 알림
    high_alpha_threshold: int = 80  # 긴급 알림

    # Database
    database_url: str = "sqlite+aiosqlite:///data/markets.db"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
