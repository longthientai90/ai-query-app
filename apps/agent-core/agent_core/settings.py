from __future__ import annotations

"""Configuration model for agent-core runtime and integration endpoints."""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_skills_dir() -> Path:
    # apps/agent-core/agent_core/settings.py -> repo root -> packages/agent-skills
    return Path(__file__).resolve().parents[3] / "packages" / "agent-skills"


def _default_env_file() -> Path:
    # apps/agent-core/agent_core/settings.py -> apps/agent-core/.env
    return Path(__file__).resolve().parents[1] / ".env"


class AgentCoreSettings(BaseSettings):
    """Centralized settings loaded from environment variables."""

    SKILLS_DIR: Path = Field(default_factory=_default_skills_dir)

    MCP_SERVER_URL: str = "http://127.0.0.1:8000/mcp"
    MCP_SERVER_TRANSPORT: Literal["http"] = "http"

    # Default to Azure OpenAI for this project.
    LLM_PROVIDER: Literal["none", "openai", "azure"] = "azure"
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4.1-mini"
    OPENAI_BASE_URL: str | None = None

    AZURE_OPENAI_ENDPOINT: str | None = None
    AZURE_OPENAI_API_KEY: str | None = None
    AZURE_OPENAI_API_VERSION: str = "2024-10-21"
    AZURE_OPENAI_DEPLOYMENT: str | None = None

    AGENT_HISTORY_LIMIT: int = 20
    AGENT_SCHEMA_CACHE_TTL_SEC: int = 300
    AGENT_MAX_ROWS_TO_SUMMARIZE: int = 25
    AGENT_MAX_VALUE_CHARS: int = 200
    AGENT_DEFAULT_MAX_ROWS: int = 100

    model_config = SettingsConfigDict(
        env_file=_default_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )
