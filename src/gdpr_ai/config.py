"""Central configuration loaded from environment variables."""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    anthropic_api_key: str
    claude_model_fast: str = "claude-haiku-4-5-20251001"
    claude_model_smart: str = "claude-sonnet-4-6"

    chroma_path: Path = Path("./data/chroma")
    sqlite_path: Path = Path("./data/gdpr_ai.db")
    embedding_model: str = "BAAI/bge-m3"

    log_level: str = "INFO"


settings = Settings()
