from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ColumnMetadata:
    name: str
    data_type: str
    nullable: bool
    is_primary_key: bool
    ordinal_position: int


@dataclass(slots=True)
class ForeignKeyMetadata:
    name: str
    source_table: str
    source_column: str
    target_table: str
    target_column: str


@dataclass(slots=True)
class IndexMetadata:
    name: str
    definition: str
    columns: list[str] = field(default_factory=list)


@dataclass(slots=True)
class TableMetadata:
    name: str
    schema_name: str
    aliases: list[str] = field(default_factory=list)
    business_tags: list[str] = field(default_factory=list)
    columns: list[ColumnMetadata] = field(default_factory=list)
    foreign_keys: list[ForeignKeyMetadata] = field(default_factory=list)
    indexes: list[IndexMetadata] = field(default_factory=list)


@dataclass(slots=True)
class SchemaDocument:
    table_name: str
    searchable_text: str
    prompt_text: str
    aliases: list[str] = field(default_factory=list)
    business_tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RankedColumn:
    table_name: str
    column_name: str
    score: float
    match_reasons: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RankedTable:
    table_name: str
    score: float
    match_reasons: list[str] = field(default_factory=list)
    selected_columns: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SuggestedRelationship:
    from_table: str
    from_column: str
    to_table: str
    to_column: str


@dataclass(slots=True)
class SchemaSearchResult:
    query: str
    schema_hash: str | None
    version: int
    used_vector_search: bool
    compact_context: str
    ranked_tables: list[RankedTable]
    ranked_columns: list[RankedColumn]
    suggested_relationships: list[SuggestedRelationship]
    used_llm_query_rewrite: bool = False
    rewritten_query_tokens: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
