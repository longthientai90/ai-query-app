from __future__ import annotations

import time
from dataclasses import asdict
from datetime import datetime, timezone

from config import ServiceSchemaSettings
from service_schema.db.loader import SchemaLoader
from service_schema.db.pool import close_pool, init_pool
from service_schema.indexing.store import SchemaStore
from service_schema.retrieval.searcher import SchemaSearcher


class ServiceSchemaRuntime:
    def __init__(self, settings: ServiceSchemaSettings) -> None:
        self.settings = settings
        self.loader = SchemaLoader(
            schema_name=settings.DB_SCHEMA_NAME,
            alias_overrides=settings.SCHEMA_ALIAS_OVERRIDES,
            tag_overrides=settings.SCHEMA_TAG_OVERRIDES,
        )
        self.searcher = SchemaSearcher(
            low_signal_patterns=settings.low_signal_patterns,
            max_columns_per_table=settings.MAX_COLUMNS_PER_TABLE,
            max_context_chars=settings.MAX_CONTEXT_CHARS,
        )
        self.store: SchemaStore | None = None
        self.last_sync_error: str | None = None
        self.last_sync_duration_ms: float | None = None

    async def start(self) -> None:
        # Load the DB pool once at startup so sync/search requests reuse connections.
        await init_pool(self.settings)
        if self.settings.AUTO_REINDEX_ON_STARTUP:
            await self.reindex(include_indexes=self.settings.REINDEX_INCLUDE_INDEXES)

    async def stop(self) -> None:
        await close_pool()

    async def reindex(self, *, include_indexes: bool) -> dict[str, object]:
        started_at = time.perf_counter()
        warnings: list[str] = []
        try:
            tables = await self.loader.load(include_indexes=include_indexes)
            new_store = SchemaStore(tables)
            # Version increments only after a successful rebuild so callers can detect
            # fresh index generations without diffing the entire schema payload.
            if self.store is not None:
                new_store.version = self.store.version + 1
            self.store = new_store
            self.last_sync_error = None
        except Exception as exc:
            self.last_sync_error = str(exc)
            warnings.append(f"reindex_failed:{exc}")
            if self.store is None:
                raise
        duration_ms = round((time.perf_counter() - started_at) * 1000.0, 2)
        self.last_sync_duration_ms = duration_ms
        return {
            "status": "ok" if self.last_sync_error is None else "degraded",
            "indexed_tables": len(self.store.tables) if self.store is not None else 0,
            "schema_hash": self.store.schema_hash if self.store is not None else None,
            "version": self.store.version if self.store is not None else 0,
            "duration_ms": duration_ms,
            "warnings": warnings,
        }

    def search(
        self,
        *,
        query: str,
        max_tables: int,
        include_indexes: bool,
        include_relationships: bool,
    ) -> dict[str, object]:
        store = self._require_store()
        max_tables = min(max_tables, self.settings.MAX_SEARCH_TABLES)
        result = self.searcher.search(
            store=store,
            query=query,
            max_tables=max_tables,
            include_indexes=include_indexes,
            include_relationships=include_relationships,
        )
        return {
            "query": result.query,
            "schema_hash": result.schema_hash,
            "version": result.version,
            "used_vector_search": result.used_vector_search,
            "compact_context": result.compact_context,
            "ranked_tables": [asdict(item) for item in result.ranked_tables],
            "ranked_columns": [asdict(item) for item in result.ranked_columns],
            "suggested_relationships": [asdict(item) for item in result.suggested_relationships],
            "warnings": result.warnings,
        }

    def get_table(self, table_name: str) -> dict[str, object] | None:
        store = self._require_store()
        table = store.tables.get(table_name)
        document = store.documents.get(table_name)
        if table is None or document is None:
            return None
        return {
            "name": table.name,
            "schema_name": table.schema_name,
            "aliases": table.aliases,
            "business_tags": table.business_tags,
            "columns": [
                {
                    "name": column.name,
                    "data_type": column.data_type,
                    "nullable": column.nullable,
                    "is_primary_key": column.is_primary_key,
                }
                for column in sorted(table.columns, key=lambda item: item.ordinal_position)
            ],
            "foreign_keys": [
                {
                    "name": foreign_key.name,
                    "source_column": foreign_key.source_column,
                    "target_table": foreign_key.target_table,
                    "target_column": foreign_key.target_column,
                }
                for foreign_key in table.foreign_keys
            ],
            "indexes": [
                {
                    "name": index.name,
                    "definition": index.definition,
                    "columns": index.columns,
                }
                for index in table.indexes
            ],
            "prompt_text": document.prompt_text,
        }

    def health_response(self) -> dict[str, object]:
        status = "ok"
        warnings: list[str] = []
        cache_age_seconds: float | None = None
        last_sync_time: str | None = None
        indexed_tables = 0
        schema_hash: str | None = None
        version = 0

        if self.store is not None:
            indexed_tables = len(self.store.tables)
            schema_hash = self.store.schema_hash
            version = self.store.version
            cache_age_seconds = round(
                (datetime.now(timezone.utc) - self.store.last_sync_time).total_seconds(),
                3,
            )
            last_sync_time = self.store.last_sync_time.isoformat()
        else:
            status = "degraded"
            warnings.append("Schema store is empty.")

        if self.last_sync_error is not None:
            status = "degraded"
            warnings.append(self.last_sync_error)

        return {
            "status": status,
            "indexed_tables": indexed_tables,
            "schema_hash": schema_hash,
            "version": version,
            "qdrant_enabled": self.settings.QDRANT_ENABLED,
            "cache_age_seconds": cache_age_seconds,
            "last_sync_time": last_sync_time,
            "warnings": warnings,
        }

    def _require_store(self) -> SchemaStore:
        if self.store is None:
            raise RuntimeError("Schema store is empty. Run /schema/reindex first.")
        return self.store
