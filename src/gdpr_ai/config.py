"""Application settings loaded from environment variables."""
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for GDPR AI."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    anthropic_api_key: str | None = Field(default=None, validation_alias="ANTHROPIC_API_KEY")
    chroma_path: Path = Field(default=Path("./data/chroma"), validation_alias="CHROMA_PATH")
    log_db_path: Path = Field(
        default=Path("./logs/gdpr_ai.db"),
        validation_alias="LOG_DB_PATH",
    )
    bm25_index_path: Path = Field(
        default=Path("./data/processed/bm25.pkl"),
        validation_alias="BM25_INDEX_PATH",
    )
    processed_dir: Path = Field(default=Path("./data/processed"), validation_alias="PROCESSED_DIR")

    model_reasoning: str = Field(
        default="claude-sonnet-4-6",
        validation_alias="MODEL_REASONING",
    )
    model_translation: str = Field(
        default="claude-haiku-4-5-20251001",
        validation_alias="MODEL_TRANSLATION",
    )
    model_extract_classify: str = Field(
        default="claude-haiku-4-5-20251001",
        validation_alias="MODEL_EXTRACT_CLASSIFY",
    )

    embedding_model: str = Field(default="BAAI/bge-m3", validation_alias="EMBEDDING_MODEL")
    top_k: int = Field(default=25, validation_alias="TOP_K")
    topic_demote_factor: float = Field(
        default=0.82,
        validation_alias="TOPIC_DEMOTE_FACTOR",
        description="Dense-score multiplier for chunks with no topic-tag overlap when some overlap exists.",
    )
    max_tokens: int = Field(default=8192, validation_alias="MAX_TOKENS")
    max_tokens_validate: int = Field(default=12288, validation_alias="MAX_TOKENS_VALIDATE")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    chroma_collection: str = Field(default="gdpr_ai_chunks", validation_alias="CHROMA_COLLECTION")


settings = Settings()
