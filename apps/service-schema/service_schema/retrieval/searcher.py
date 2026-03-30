from __future__ import annotations

from collections import defaultdict

from service_schema.indexing.store import SchemaStore
from service_schema.models.schema import RankedColumn, RankedTable, SchemaSearchResult, SuggestedRelationship
from service_schema.retrieval.context_builder import build_compact_context
from service_schema.util import tokenize


class SchemaSearcher:
    def __init__(
        self,
        *,
        low_signal_patterns: list[str],
        max_columns_per_table: int,
        max_context_chars: int,
    ) -> None:
        self.low_signal_patterns = low_signal_patterns
        self.max_columns_per_table = max_columns_per_table
        self.max_context_chars = max_context_chars

    def search(
        self,
        *,
        store: SchemaStore,
        query: str,
        max_tables: int,
        include_indexes: bool,
        include_relationships: bool,
        query_tokens: list[str] | None = None,
        force_expand_relationships: bool = False,
    ) -> SchemaSearchResult:
        normalized_tokens = query_tokens or tokenize(query)
        if not normalized_tokens:
            raise RuntimeError("Search query does not contain usable tokens")

        table_scores: dict[str, float] = defaultdict(float)
        table_reasons: dict[str, list[str]] = defaultdict(list)
        column_scores: list[RankedColumn] = []

        # Score direct evidence first so lexical retrieval stays deterministic even
        # without vector search. Table, alias, tag, and column signals all contribute.
        for token in normalized_tokens:
            for table_name, table in store.tables.items():
                lower_table_name = table_name.lower()
                if token == lower_table_name:
                    table_scores[table_name] += 8.0
                    table_reasons[table_name].append(f"exact_table:{token}")
                elif token in lower_table_name:
                    table_scores[table_name] += 4.0
                    table_reasons[table_name].append(f"table:{token}")

                for alias in table.aliases:
                    alias_lower = alias.lower()
                    if token == alias_lower:
                        table_scores[table_name] += 3.5
                        table_reasons[table_name].append(f"alias:{token}")
                    elif token in alias_lower:
                        table_scores[table_name] += 2.0
                        table_reasons[table_name].append(f"alias_partial:{token}")

                for tag in table.business_tags:
                    tag_lower = tag.lower()
                    if token == tag_lower:
                        table_scores[table_name] += 2.5
                        table_reasons[table_name].append(f"tag:{token}")

                for column in table.columns:
                    column_lower = column.name.lower()
                    column_score = 0.0
                    reason = ""
                    if token == column_lower:
                        column_score = 4.0
                        reason = f"exact_column:{token}"
                    elif token in column_lower:
                        column_score = 1.5
                        reason = f"column:{token}"
                    if column_score > 0:
                        boost = 1.0 if column.is_primary_key else 0.0
                        total = column_score + boost
                        table_scores[table_name] += total
                        table_reasons[table_name].append(reason)
                        column_scores.append(
                            RankedColumn(
                                table_name=table_name,
                                column_name=column.name,
                                score=round(total, 4),
                                match_reasons=[reason],
                            )
                        )

            for candidate in store.keyword_index.get(token, set()):
                table_scores[candidate] += 1.25
                table_reasons[candidate].append(f"keyword:{token}")

        # Penalize operational tables that often match generic terms but are rarely
        # useful for end-user analytics unless the query is very explicit.
        for table_name in list(table_scores):
            if any(pattern in table_name.lower() for pattern in self.low_signal_patterns):
                table_scores[table_name] -= 1.5
                table_reasons[table_name].append("low_signal_penalty")

        ranked_table_names = [
            table_name
            for table_name, _ in sorted(
                table_scores.items(),
                key=lambda item: (-item[1], item[0]),
            )
            if table_scores[table_name] > 0
        ]

        strong_direct_hits = self._select_strong_direct_hits(
            ranked_table_names=ranked_table_names,
            table_scores=table_scores,
            table_reasons=table_reasons,
            max_tables=max_tables,
        )

        if include_relationships and self._should_expand_relationships(
            query_tokens=normalized_tokens,
            direct_hits=strong_direct_hits,
            table_reasons=table_reasons,
            force_expand_relationships=force_expand_relationships,
        ):
            ranked_table_names = self._expand_related_tables(
                store,
                strong_direct_hits,
                max_tables=max_tables,
            )
        else:
            ranked_table_names = strong_direct_hits

        ranked_tables: list[RankedTable] = []
        for table_name in ranked_table_names[:max_tables]:
            # Surface only the strongest matched columns so prompt context stays compact.
            top_columns = [
                column.column_name
                for column in sorted(
                    [item for item in column_scores if item.table_name == table_name],
                    key=lambda item: (-item.score, item.column_name),
                )[: self.max_columns_per_table]
            ]
            ranked_tables.append(
                RankedTable(
                    table_name=table_name,
                    score=round(table_scores.get(table_name, 0.0), 4),
                    match_reasons=sorted(set(table_reasons.get(table_name, []))),
                    selected_columns=top_columns,
                )
            )

        relationships = self._collect_relationships(store, [item.table_name for item in ranked_tables])
        compact_context = build_compact_context(
            store=store,
            table_names=[item.table_name for item in ranked_tables],
            include_indexes=include_indexes,
            include_relationships=include_relationships,
            max_columns_per_table=self.max_columns_per_table,
            max_chars=self.max_context_chars,
        )

        warnings: list[str] = []
        if not ranked_tables:
            warnings.append("No relevant tables found; consider reindexing or using broader aliases.")
        if len(compact_context) >= self.max_context_chars:
            warnings.append("Compact context was truncated to stay within size limits.")

        selected_tables = {table.table_name for table in ranked_tables}
        # Deduplicate repeated column hits from multiple matching tokens before returning.
        unique_columns = sorted(
            {
                (item.table_name, item.column_name): item
                for item in column_scores
                if item.table_name in selected_tables
            }.values(),
            key=lambda item: (-item.score, item.table_name, item.column_name),
        )

        return SchemaSearchResult(
            query=query,
            schema_hash=store.schema_hash,
            version=store.version,
            used_vector_search=False,
            used_llm_query_rewrite=False,
            rewritten_query_tokens=normalized_tokens,
            compact_context=compact_context,
            ranked_tables=ranked_tables,
            ranked_columns=unique_columns[: max_tables * self.max_columns_per_table],
            suggested_relationships=relationships,
            warnings=warnings,
        )

    def _select_strong_direct_hits(
        self,
        *,
        ranked_table_names: list[str],
        table_scores: dict[str, float],
        table_reasons: dict[str, list[str]],
        max_tables: int,
    ) -> list[str]:
        if not ranked_table_names:
            return []

        top_score = table_scores[ranked_table_names[0]]
        minimum_score = max(3.0, top_score * 0.35)
        selected: list[str] = []
        for table_name in ranked_table_names:
            reasons = table_reasons.get(table_name, [])
            has_direct_signal = any(
                reason.startswith(("exact_table:", "table:", "alias:", "alias_partial:", "tag:", "exact_column:", "column:"))
                for reason in reasons
            )
            if not has_direct_signal:
                continue
            if table_scores[table_name] < minimum_score:
                continue
            selected.append(table_name)
            if len(selected) >= max_tables:
                break
        return selected

    def _should_expand_relationships(
        self,
        *,
        query_tokens: list[str],
        direct_hits: list[str],
        table_reasons: dict[str, list[str]],
        force_expand_relationships: bool,
    ) -> bool:
        if len(direct_hits) >= 2:
            return True

        if not direct_hits:
            return False

        if force_expand_relationships:
            return True

        # Expand a single strong table only when the question language suggests
        # crossing entities such as "products bought by user", not for simple
        # single-table filters like status or counts.
        relation_tokens = {
            "theo",
            "cua",
            "thuoc",
            "mua",
            "bought",
            "buyer",
            "customer",
            "user",
            "product",
            "category",
            "brand",
        }
        if not any(token in relation_tokens for token in query_tokens):
            return False

        reasons = table_reasons.get(direct_hits[0], [])
        has_exact_column = any(reason.startswith("exact_column:") for reason in reasons)
        return has_exact_column

    def _expand_related_tables(self, store: SchemaStore, ranked_table_names: list[str], *, max_tables: int) -> list[str]:
        # Preserve top lexical hits first, then spend any remaining budget on FK-adjacent
        # tables so relationship expansion cannot evict stronger direct matches.
        direct_hits = ranked_table_names[:max_tables]
        expanded = list(direct_hits)
        seen = set(direct_hits)
        if len(expanded) >= max_tables:
            return expanded

        for table_name in direct_hits:
            for neighbor in sorted(store.relationship_graph.get(table_name, set())):
                if len(expanded) >= max_tables:
                    break
                if neighbor not in seen:
                    expanded.append(neighbor)
                    seen.add(neighbor)
        return expanded

    def _collect_relationships(self, store: SchemaStore, table_names: list[str]) -> list[SuggestedRelationship]:
        selected = set(table_names)
        relationships: list[SuggestedRelationship] = []
        for table_name in table_names:
            table = store.tables.get(table_name)
            if table is None:
                continue
            for foreign_key in table.foreign_keys:
                if foreign_key.target_table in selected:
                    relationships.append(
                        SuggestedRelationship(
                            from_table=foreign_key.source_table,
                            from_column=foreign_key.source_column,
                            to_table=foreign_key.target_table,
                            to_column=foreign_key.target_column,
                        )
                    )
        return relationships
