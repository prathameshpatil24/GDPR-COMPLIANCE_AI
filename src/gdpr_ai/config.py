"""Application settings loaded from environment variables."""

from pathlib import Path

from pydantic import Field, field_validator
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
    sqlite_path: Path = Field(
        default=Path("./data/app.db"),
        validation_alias="SQLITE_PATH",
        description="SQLite database for projects, analyses, and generated documents.",
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
        description=(
            "Dense-score multiplier for chunks with no topic-tag overlap when some overlap exists."
        ),
    )
    max_tokens: int = Field(default=16384, validation_alias="MAX_TOKENS")
    max_tokens_validate: int = Field(default=12288, validation_alias="MAX_TOKENS_VALIDATE")

    @field_validator("max_tokens", "max_tokens_validate")
    @classmethod
    def _floor_reasoning_max_tokens(cls, v: int) -> int:
        """Avoid truncated JSON when env sets MAX_TOKENS too low for v4-sized reports."""
        return max(v, 8192)

    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    chroma_collection: str = Field(default="gdpr_ai_chunks", validation_alias="CHROMA_COLLECTION")

    chroma_collection_dpia: str = Field(
        default="dpia_guidance", validation_alias="CHROMA_COLLECTION_DPIA"
    )
    chroma_collection_ropa: str = Field(
        default="ropa_templates", validation_alias="CHROMA_COLLECTION_ROPA"
    )
    chroma_collection_tom: str = Field(
        default="tom_catalog", validation_alias="CHROMA_COLLECTION_TOM"
    )
    chroma_collection_consent: str = Field(
        default="consent_guidance", validation_alias="CHROMA_COLLECTION_CONSENT"
    )
    chroma_collection_ai_act: str = Field(
        default="ai_act",
        validation_alias="CHROMA_COLLECTION_AI_ACT",
    )

    deterministic_retrieval_enabled: bool = Field(
        default=True,
        validation_alias="DETERMINISTIC_RETRIEVAL",
        description="Use article map + cross-ref + full-text assembly as primary retrieval (v4).",
    )
    deterministic_max_supplement_violation: int = Field(
        default=5,
        validation_alias="DETERMINISTIC_MAX_SUPPLEMENT_VIOLATION",
        ge=0,
        le=50,
        description=(
            "Violation mode: max extra GDPR articles from map/graph not already in semantic chunks."
        ),
    )
    deterministic_graph_depth_violation: int = Field(
        default=1,
        validation_alias="DETERMINISTIC_GRAPH_DEPTH_VIOLATION",
        ge=0,
        le=3,
        description="Violation mode: cross-reference expansion depth (0 = map only).",
    )
    deterministic_max_supplement_compliance: int = Field(
        default=5,
        validation_alias="DETERMINISTIC_MAX_SUPPLEMENT_COMPLIANCE",
        ge=0,
        le=50,
        description=(
            "Compliance mode: max extra GDPR articles from map/graph not already "
            "in semantic chunks."
        ),
    )
    deterministic_graph_depth_compliance: int = Field(
        default=0,
        validation_alias="DETERMINISTIC_GRAPH_DEPTH_COMPLIANCE",
        ge=0,
        le=3,
        description=(
            "Compliance mode: cross-reference depth; 0 disables expansion (map-only deterministic)."
        ),
    )
    deterministic_graph_depth: int = Field(
        default=1,
        validation_alias="DETERMINISTIC_GRAPH_DEPTH",
        ge=0,
        le=3,
        description=(
            "Legacy global default; v4 uses deterministic_graph_depth_violation or _compliance."
        ),
    )
    deterministic_max_context_tokens: int = Field(
        default=30000,
        validation_alias="DETERMINISTIC_MAX_CONTEXT_TOKENS",
        ge=2000,
    )
    max_deterministic_supplement_articles: int = Field(
        default=5,
        validation_alias="MAX_DETERMINISTIC_ARTICLES",
        ge=0,
        le=50,
        description=(
            "Legacy cap; v4 uses DETERMINISTIC_MAX_SUPPLEMENT_VIOLATION / "
            "DETERMINISTIC_MAX_SUPPLEMENT_COMPLIANCE."
        ),
    )
    deterministic_semantic_fallback: bool = Field(
        default=True,
        validation_alias="DETERMINISTIC_SEMANTIC_FALLBACK",
        description=(
            "Deprecated: ignored. Hybrid semantic search is always merged when "
            "DETERMINISTIC_RETRIEVAL is enabled. Set DETERMINISTIC_RETRIEVAL=false "
            "for semantic-only."
        ),
    )
    verification_enabled: bool = Field(
        default=True,
        validation_alias="VERIFICATION_ENABLED",
        description="Run completeness verification pass after primary reasoning (v4).",
    )
    supplementary_reasoning_enabled: bool = Field(
        default=True,
        validation_alias="SUPPLEMENTARY_REASONING",
        description="If verification reports gaps, merge extra chunks and re-run reasoning once.",
    )

    gdpr_article_map_path: Path = Field(
        default=Path("data/gdpr_article_map.yaml"),
        validation_alias="GDPR_ARTICLE_MAP_PATH",
    )
    gdpr_cross_references_path: Path = Field(
        default=Path("data/gdpr_cross_references.yaml"),
        validation_alias="GDPR_CROSS_REFERENCES_PATH",
    )
    gdpr_articles_fulltext_path: Path = Field(
        default=Path("data/gdpr_articles_fulltext.yaml"),
        validation_alias="GDPR_ARTICLES_FULLTEXT_PATH",
    )
    gdpr_recitals_fulltext_path: Path = Field(
        default=Path("data/gdpr_recitals_fulltext.yaml"),
        validation_alias="GDPR_RECITALS_FULLTEXT_PATH",
    )
    gdpr_raw_articles_json_path: Path = Field(
        default=Path("data/raw/gdpr_articles.json"),
        validation_alias="GDPR_RAW_ARTICLES_JSON_PATH",
    )
    gdpr_raw_recitals_json_path: Path = Field(
        default=Path("data/raw/gdpr_recitals.json"),
        validation_alias="GDPR_RAW_RECITALS_JSON_PATH",
    )


settings = Settings()
