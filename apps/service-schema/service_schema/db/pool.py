from __future__ import annotations

from typing import Any

import asyncpg

from config import ServiceSchemaSettings

_pool: asyncpg.Pool | None = None


async def init_pool(settings: ServiceSchemaSettings) -> asyncpg.Pool:
    global _pool
    if _pool is not None:
        return _pool

    create_pool_kwargs: dict[str, Any] = {
        "dsn": settings.DATABASE_URL,
        "min_size": settings.DB_POOL_MIN,
        "max_size": settings.DB_POOL_MAX,
    }
    if settings.DB_STATEMENT_TIMEOUT_MS > 0:
        create_pool_kwargs["server_settings"] = {
            "statement_timeout": str(settings.DB_STATEMENT_TIMEOUT_MS)
        }
    _pool = await asyncpg.create_pool(**create_pool_kwargs)
    return _pool


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database pool is not initialized")
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
    _pool = None
