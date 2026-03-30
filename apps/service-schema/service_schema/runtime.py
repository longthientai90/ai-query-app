from __future__ import annotations

import logging
import time
from dataclasses import asdict
from datetime import datetime, timezone

from config import ServiceSchemaSettings
from service_schema.db.loader import SchemaLoader
from service_schema.db.pool import close_pool, init_pool
from service_schema.indexing.store import SchemaStore
from service_schema.retrieval.query_rewriter import SchemaQueryRewriter
from service_schema.retrieval.searcher import SchemaSearcher

logger = logging.getLogger(__name__)


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
        self.query_rewriter = SchemaQueryRewriter(
            enabled=settings.SCHEMA_QUERY_REWRITE_ENABLED,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            deployment=settings.AZURE_OPENAI_DEPLOYMENT,
            max_keywords=settings.SCHEMA_QUERY_REWRITE_MAX_KEYWORDS,
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
            logger.exception("service_schema_reindex_failed include_indexes=%s", include_indexes)
            if self.store is None:
                raise
        duration_ms = round((time.perf_counter() - started_at) * 1000.0, 2)
        self.last_sync_duration_ms = duration_ms
        if self.store is not None:
            logger.info(
                "service_schema_reindex_completed indexed_tables=%s schema_hash=%s version=%s duration_ms=%s include_indexes=%s",
                len(self.store.tables),
                self.store.schema_hash,
                self.store.version,
                duration_ms,
                include_indexes,
            )
        return {
            "status": "ok" if self.last_sync_error is None else "degraded",
            "indexed_tables": len(self.store.tables) if self.store is not None else 0,
            "schema_hash": self.store.schema_hash if self.store is not None else None,
            "version": self.store.version if self.store is not None else 0,
            "duration_ms": duration_ms,
            "warnings": warnings,
        }

    async def search(
        self,
        *,
        query: str,
        max_tables: int,
        include_indexes: bool,
        include_relationships: bool,
    ) -> dict[str, object]:
        store = self._require_store()
        max_tables = min(max_tables, self.settings.MAX_SEARCH_TABLES)
        # First pass stays fully local so common Vietnamese prompts avoid an LLM round-trip.
        local_rewrite = self.query_rewriter.rewrite_locally(query)
        logger.info(
            "service_schema_search_local_rewrite query=%r local_tokens=%s force_expand_relationships=%s",
            query,
            local_rewrite.tokens,
            local_rewrite.force_expand_relationships,
        )
        result = self.searcher.search(
            store=store,
            query=query,
            max_tables=max_tables,
            include_indexes=include_indexes,
            include_relationships=include_relationships,
            query_tokens=local_rewrite.tokens,
            force_expand_relationships=local_rewrite.force_expand_relationships,
        )
        warnings = list(result.warnings)
        warnings.extend(local_rewrite.warnings)

        used_llm_query_rewrite = False
        rewritten_query_tokens = list(local_rewrite.tokens)
        top_score = result.ranked_tables[0].score if result.ranked_tables else 0.0
        should_retry_with_llm = (
            self.query_rewriter.enabled
            and (not result.ranked_tables or top_score < self.settings.SCHEMA_QUERY_REWRITE_SCORE_THRESHOLD)
        )
        logger.info(
            "service_schema_search_llm_decision query=%r llm_enabled=%s should_retry_with_llm=%s initial_top_score=%s initial_tables=%s threshold=%s",
            query,
            self.query_rewriter.enabled,
            should_retry_with_llm,
            top_score,
            [item.table_name for item in result.ranked_tables],
            self.settings.SCHEMA_QUERY_REWRITE_SCORE_THRESHOLD,
        )
        if should_retry_with_llm:
            llm_rewrite = await self.query_rewriter.rewrite_with_llm(query=query, store=store)
            warnings.extend(llm_rewrite.warnings)
            # Merge local and LLM tokens so the deterministic lexical scorer keeps
            # all cheap matches while adding the model's semantic hints.
            combined_tokens = self._dedupe_tokens([*local_rewrite.tokens, *llm_rewrite.tokens])
            used_llm_query_rewrite = llm_rewrite.used_llm
            rewritten_query_tokens = combined_tokens or rewritten_query_tokens
            logger.info(
                "service_schema_search_llm_result query=%r used_llm_query_rewrite=%s llm_tokens=%s combined_tokens=%s warnings=%s",
                query,
                used_llm_query_rewrite,
                llm_rewrite.tokens,
                combined_tokens,
                llm_rewrite.warnings,
            )
            if combined_tokens and combined_tokens != local_rewrite.tokens:
                retried_result = self.searcher.search(
                    store=store,
                    query=query,
                    max_tables=max_tables,
                    include_indexes=include_indexes,
                    include_relationships=include_relationships,
                    query_tokens=combined_tokens,
                    force_expand_relationships=(
                        local_rewrite.force_expand_relationships or llm_rewrite.force_expand_relationships
                    ),
                )
                if retried_result.ranked_tables:
                    result = retried_result
                    top_score = result.ranked_tables[0].score
                logger.info(
                    "service_schema_search_llm_retry_completed query=%r retried_tables=%s retried_top_score=%s",
                    query,
                    [item.table_name for item in retried_result.ranked_tables],
                    retried_result.ranked_tables[0].score if retried_result.ranked_tables else 0.0,
                )

        ranked_table_names = [item.table_name for item in result.ranked_tables]
        logger.info(
            "service_schema_search_completed query=%r returned_tables=%s table_count=%s include_indexes=%s include_relationships=%s schema_hash=%s version=%s used_llm_query_rewrite=%s rewritten_query_tokens=%s top_score=%s",
            query,
            ranked_table_names,
            len(ranked_table_names),
            include_indexes,
            include_relationships,
            result.schema_hash,
            result.version,
            used_llm_query_rewrite,
            rewritten_query_tokens,
            top_score,
        )
        return {
            "query": result.query,
            "schema_hash": result.schema_hash,
            "version": result.version,
            "used_vector_search": result.used_vector_search,
            "used_llm_query_rewrite": used_llm_query_rewrite,
            "rewritten_query_tokens": rewritten_query_tokens,
            "compact_context": result.compact_context,
            "ranked_tables": [asdict(item) for item in result.ranked_tables],
            "ranked_columns": [asdict(item) for item in result.ranked_columns],
            "suggested_relationships": [asdict(item) for item in result.suggested_relationships],
            "warnings": self._dedupe_tokens(warnings),
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

    @staticmethod
    def _dedupe_tokens(tokens: list[str]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for token in tokens:
            if token not in seen:
                ordered.append(token)
                seen.add(token)
        return ordered
