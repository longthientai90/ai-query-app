from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Connection string should use a dedicated read-only role.
    DATABASE_URL: str
    DB_POOL_MIN: int = 2
    DB_POOL_MAX: int = 10
    # PostgreSQL statement_timeout in milliseconds (0 disables timeout).
    DB_STATEMENT_TIMEOUT_MS: int = 15000
    DEFAULT_LIMIT: int = 100
    MAX_LIMIT: int = 1000
    LOG_LEVEL: str = "INFO"
    LOG_SQL: bool = False
    MCP_HOST: str = "0.0.0.0"
    MCP_PORT: int = 8000
    MCP_TRANSPORT: str = "http"
    MCP_STATELESS_HTTP: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
