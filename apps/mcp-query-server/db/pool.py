from __future__ import annotations

from typing import Any

import asyncpg

from config import Settings

_pools: list[asyncpg.Pool] = []
_pool_index = 0


async def init_pool(settings: Settings) -> asyncpg.Pool:
    global _pools
    if not _pools:
        for dsn in _resolve_read_dsns(settings):
            create_pool_kwargs: dict[str, Any] = {
                "dsn": dsn,
                "min_size": settings.DB_POOL_MIN,
                "max_size": settings.DB_POOL_MAX,
            }
            if settings.DB_STATEMENT_TIMEOUT_MS > 0:
                create_pool_kwargs["server_settings"] = {
                    "statement_timeout": str(settings.DB_STATEMENT_TIMEOUT_MS)
                }
            # Create one pool per read endpoint so calls can be balanced across replicas.
            _pools.append(await asyncpg.create_pool(**create_pool_kwargs))
    return _pools[0]


def get_pool() -> asyncpg.Pool:
    global _pool_index
    if not _pools:
        # Tools call this at runtime, so fail fast if startup was skipped.
        raise RuntimeError("Database pool is not initialized")

    pool = _pools[_pool_index % len(_pools)]
    _pool_index = (_pool_index + 1) % len(_pools)
    return pool


async def close_pool() -> None:
    global _pools, _pool_index
    for pool in _pools:
        await pool.close()
    _pools = []
    _pool_index = 0


def _resolve_read_dsns(settings: Settings) -> list[str]:
    dsns = [item.strip() for item in settings.READONLY_DATABASE_URLS.split(",") if item.strip()]
    if not dsns:
        raise RuntimeError("READONLY_DATABASE_URLS must contain at least one replica DSN")
    return dsns
