from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime, timezone

from service_schema.models.schema import SchemaDocument, TableMetadata
from service_schema.util import tokenize


class SchemaStore:
    def __init__(self, tables: list[TableMetadata]) -> None:
        self.tables = {table.name: table for table in tables}
        self.documents: dict[str, SchemaDocument] = {}
        self.table_name_index: dict[str, set[str]] = defaultdict(set)
        self.column_name_index: dict[str, set[str]] = defaultdict(set)
        self.keyword_index: dict[str, set[str]] = defaultdict(set)
        self.relationship_graph: dict[str, set[str]] = defaultdict(set)
        self.version = 1
        self.last_sync_time = datetime.now(timezone.utc)
        self.schema_hash = self._compute_schema_hash(tables)
        self._build_indexes()

    def _build_indexes(self) -> None:
        for table in self.tables.values():
            # Build multiple narrow indexes instead of one heavy search structure so the
            # MVP stays fast, transparent, and easy to tune.
            searchable_parts = [table.name, *table.aliases, *table.business_tags]
            prompt_parts = [f"table {table.name}"]

            self.table_name_index[table.name.lower()].add(table.name)
            for token in tokenize(table.name):
                self.keyword_index[token].add(table.name)

            for alias in table.aliases:
                for token in tokenize(alias):
                    self.keyword_index[token].add(table.name)
            for tag in table.business_tags:
                for token in tokenize(tag):
                    self.keyword_index[token].add(table.name)

            for column in sorted(table.columns, key=lambda item: item.ordinal_position):
                searchable_parts.append(column.name)
                self.column_name_index[column.name.lower()].add(table.name)
                for token in tokenize(column.name):
                    self.keyword_index[token].add(table.name)
                pk_marker = " PK" if column.is_primary_key else ""
                prompt_parts.append(f"- {column.name}: {column.data_type}{pk_marker}")

            for foreign_key in table.foreign_keys:
                searchable_parts.extend(
                    [
                        foreign_key.source_column,
                        foreign_key.target_table,
                        foreign_key.target_column,
                    ]
                )
                self.relationship_graph[foreign_key.source_table].add(foreign_key.target_table)
                self.relationship_graph[foreign_key.target_table].add(foreign_key.source_table)

            for index in table.indexes:
                searchable_parts.append(index.name)
                searchable_parts.extend(index.columns)

            self.documents[table.name] = SchemaDocument(
                table_name=table.name,
                searchable_text=" ".join(searchable_parts),
                prompt_text="\n".join(prompt_parts),
                aliases=table.aliases,
                business_tags=table.business_tags,
            )

    @staticmethod
    def _compute_schema_hash(tables: list[TableMetadata]) -> str:
        payload = []
        for table in sorted(tables, key=lambda item: item.name):
            payload.append(
                {
                    "name": table.name,
                    "columns": [asdict(column) for column in table.columns],
                    "foreign_keys": [asdict(foreign_key) for foreign_key in table.foreign_keys],
                    "indexes": [asdict(index) for index in table.indexes],
                    "aliases": sorted(table.aliases),
                    "business_tags": sorted(table.business_tags),
                }
            )
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
