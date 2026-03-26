from service_schema.indexing.store import SchemaStore
from service_schema.models.schema import ColumnMetadata, ForeignKeyMetadata, TableMetadata
from service_schema.retrieval.searcher import SchemaSearcher


def make_store() -> SchemaStore:
    customers = TableMetadata(
        name="customers",
        schema_name="public",
        aliases=["customer", "client"],
        business_tags=["crm"],
        columns=[
            ColumnMetadata("id", "uuid", False, True, 1),
            ColumnMetadata("email", "text", False, False, 2),
            ColumnMetadata("full_name", "text", False, False, 3),
        ],
    )
    orders = TableMetadata(
        name="orders",
        schema_name="public",
        aliases=["order", "purchase"],
        business_tags=["sales"],
        columns=[
            ColumnMetadata("id", "uuid", False, True, 1),
            ColumnMetadata("customer_id", "uuid", False, False, 2),
            ColumnMetadata("status", "text", False, False, 3),
            ColumnMetadata("total_amount", "numeric", False, False, 4),
        ],
        foreign_keys=[
            ForeignKeyMetadata(
                name="orders_customer_id_fkey",
                source_table="orders",
                source_column="customer_id",
                target_table="customers",
                target_column="id",
            )
        ],
    )
    audit_logs = TableMetadata(
        name="audit_logs",
        schema_name="public",
        aliases=["audit log"],
        business_tags=["ops"],
        columns=[
            ColumnMetadata("id", "uuid", False, True, 1),
            ColumnMetadata("payload", "jsonb", True, False, 2),
        ],
    )
    return SchemaStore([customers, orders, audit_logs])


def test_search_prefers_relevant_domain_tables() -> None:
    searcher = SchemaSearcher(
        low_signal_patterns=["audit", "log", "logs"],
        max_columns_per_table=8,
        max_context_chars=4000,
    )

    result = searcher.search(
        store=make_store(),
        query="customer orders by email",
        max_tables=3,
        include_indexes=False,
        include_relationships=True,
    )

    ranked = [item.table_name for item in result.ranked_tables]
    assert ranked[0] in {"customers", "orders"}
    assert "customers" in ranked
    assert "orders" in ranked
    assert "audit_logs" not in ranked[:2]


def test_search_includes_relationship_expansion() -> None:
    searcher = SchemaSearcher(
        low_signal_patterns=[],
        max_columns_per_table=8,
        max_context_chars=4000,
    )

    result = searcher.search(
        store=make_store(),
        query="purchase status",
        max_tables=2,
        include_indexes=False,
        include_relationships=True,
    )

    ranked = [item.table_name for item in result.ranked_tables]
    assert ranked[0] == "orders"
    assert "customers" in ranked
    assert result.suggested_relationships[0].from_table == "orders"


def test_relationship_expansion_does_not_evict_direct_hits() -> None:
    searcher = SchemaSearcher(
        low_signal_patterns=[],
        max_columns_per_table=8,
        max_context_chars=4000,
    )

    result = searcher.search(
        store=make_store(),
        query="customer status",
        max_tables=2,
        include_indexes=False,
        include_relationships=True,
    )

    ranked = [item.table_name for item in result.ranked_tables]
    assert ranked == ["customers", "orders"]
