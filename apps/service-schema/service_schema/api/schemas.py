from __future__ import annotations

from pydantic import BaseModel, Field


class ReindexRequest(BaseModel):
    include_indexes: bool = True


class ReindexResponse(BaseModel):
    status: str
    indexed_tables: int
    schema_hash: str | None = None
    version: int
    duration_ms: float
    warnings: list[str] = Field(default_factory=list)


class SchemaSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    max_tables: int = Field(default=5, ge=1, le=12)
    include_indexes: bool = False
    include_relationships: bool = True


class RankedColumnResponse(BaseModel):
    table_name: str
    column_name: str
    score: float
    match_reasons: list[str]


class RankedTableResponse(BaseModel):
    table_name: str
    score: float
    match_reasons: list[str]
    selected_columns: list[str]


class SuggestedRelationshipResponse(BaseModel):
    from_table: str
    from_column: str
    to_table: str
    to_column: str


class SchemaSearchResponse(BaseModel):
    query: str
    schema_hash: str | None = None
    version: int
    used_vector_search: bool = False
    used_llm_query_rewrite: bool = False
    rewritten_query_tokens: list[str] = Field(default_factory=list)
    compact_context: str
    ranked_tables: list[RankedTableResponse]
    ranked_columns: list[RankedColumnResponse]
    suggested_relationships: list[SuggestedRelationshipResponse]
    warnings: list[str] = Field(default_factory=list)


class TableColumnResponse(BaseModel):
    name: str
    data_type: str
    nullable: bool
    is_primary_key: bool


class ForeignKeyResponse(BaseModel):
    name: str
    source_column: str
    target_table: str
    target_column: str


class IndexResponse(BaseModel):
    name: str
    definition: str
    columns: list[str]


class TableDetailResponse(BaseModel):
    name: str
    schema_name: str
    aliases: list[str]
    business_tags: list[str]
    columns: list[TableColumnResponse]
    foreign_keys: list[ForeignKeyResponse]
    indexes: list[IndexResponse]
    prompt_text: str


class HealthResponse(BaseModel):
    status: str
    indexed_tables: int
    schema_hash: str | None = None
    version: int
    qdrant_enabled: bool
    cache_age_seconds: float | None = None
    last_sync_time: str | None = None
    warnings: list[str] = Field(default_factory=list)
