from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ServiceSchemaSettings(BaseSettings):
    SERVICE_SCHEMA_HOST: str = "0.0.0.0"
    SERVICE_SCHEMA_PORT: int = 8200
    SERVICE_SCHEMA_LOG_LEVEL: str = "INFO"

    DATABASE_URL: str = "postgresql://postgres:postgres@127.0.0.1:5432/postgres"
    DB_POOL_MIN: int = 1
    DB_POOL_MAX: int = 5
    DB_STATEMENT_TIMEOUT_MS: int = 15000
    DB_SCHEMA_NAME: str = "public"

    AUTO_REINDEX_ON_STARTUP: bool = True
    REINDEX_INCLUDE_INDEXES: bool = True
    DEFAULT_MAX_TABLES: int = 5
    MAX_SEARCH_TABLES: int = 12
    MAX_COLUMNS_PER_TABLE: int = 8
    MAX_CONTEXT_CHARS: int = 6000
    LOW_SIGNAL_TABLE_PATTERNS: str = "log,logs,audit,audits,event,events,config,configs,temp,tmp"
    SCHEMA_ALIAS_OVERRIDES: dict[str, list[str]] = Field(default_factory=dict)
    SCHEMA_TAG_OVERRIDES: dict[str, list[str]] = Field(default_factory=dict)

    QDRANT_ENABLED: bool = False
    QDRANT_URL: str | None = None
    QDRANT_COLLECTION: str = "schema-documents"

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().with_name(".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def low_signal_patterns(self) -> list[str]:
        # Keep pattern parsing explicit so operators can tune noisy utility tables from env.
        return [item.strip().lower() for item in self.LOW_SIGNAL_TABLE_PATTERNS.split(",") if item.strip()]


settings = ServiceSchemaSettings()
