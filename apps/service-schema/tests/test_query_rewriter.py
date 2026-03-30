import pytest

from service_schema.indexing.store import SchemaStore
from service_schema.models.schema import ColumnMetadata, ForeignKeyMetadata, TableMetadata
from service_schema.retrieval.query_rewriter import SchemaQueryRewriter
from service_schema.retrieval.searcher import SchemaSearcher


def make_product_store() -> SchemaStore:
    categories = TableMetadata(
        name="categories",
        schema_name="public",
        aliases=["category"],
        business_tags=["catalog"],
        columns=[
            ColumnMetadata("id", "uuid", False, True, 1),
            ColumnMetadata("name", "text", False, False, 2),
        ],
    )
    products = TableMetadata(
        name="products",
        schema_name="public",
        aliases=["product"],
        business_tags=["catalog"],
        columns=[
            ColumnMetadata("id", "uuid", False, True, 1),
            ColumnMetadata("category_id", "uuid", False, False, 2),
            ColumnMetadata("name", "text", False, False, 3),
        ],
        foreign_keys=[
            ForeignKeyMetadata(
                name="products_category_id_fkey",
                source_table="products",
                source_column="category_id",
                target_table="categories",
                target_column="id",
            )
        ],
    )
    return SchemaStore([products, categories])


def test_local_rewrite_expands_vietnamese_product_query() -> None:
    rewriter = SchemaQueryRewriter(
        enabled=False,
        azure_endpoint=None,
        api_key=None,
        api_version="2024-10-21",
        deployment=None,
        max_keywords=8,
    )

    result = rewriter.rewrite_locally("Co tong bao nhieu san pham?")

    assert "product" in result.tokens
    assert "count" in result.tokens
    assert result.force_expand_relationships is True


def test_search_can_expand_related_categories_after_rewrite() -> None:
    searcher = SchemaSearcher(
        low_signal_patterns=[],
        max_columns_per_table=8,
        max_context_chars=4000,
    )
    rewriter = SchemaQueryRewriter(
        enabled=False,
        azure_endpoint=None,
        api_key=None,
        api_version="2024-10-21",
        deployment=None,
        max_keywords=8,
    )

    rewrite = rewriter.rewrite_locally("Co tong bao nhieu san pham?")
    result = searcher.search(
        store=make_product_store(),
        query="Co tong bao nhieu san pham?",
        max_tables=5,
        include_indexes=False,
        include_relationships=True,
        query_tokens=rewrite.tokens,
        force_expand_relationships=rewrite.force_expand_relationships,
    )

    ranked = [item.table_name for item in result.ranked_tables]
    assert ranked[0] == "products"
    assert "categories" in ranked


class _FakeCompletions:
    async def create(self, **_: object):
        class _Message:
            content = '{"keywords":["product","category","count"],"expand_relationships":true}'

        class _Choice:
            message = _Message()

        class _Response:
            choices = [_Choice()]

        return _Response()


class _FakeChat:
    completions = _FakeCompletions()


class _FakeAzureClient:
    chat = _FakeChat()


@pytest.mark.asyncio
async def test_llm_rewrite_returns_keywords_and_expand_flag() -> None:
    rewriter = SchemaQueryRewriter(
        enabled=True,
        azure_endpoint="https://example.openai.azure.com",
        api_key="test-key",
        api_version="2024-10-21",
        deployment="gpt-4o-mini",
        max_keywords=8,
        client=_FakeAzureClient(),
    )

    result = await rewriter.rewrite_with_llm(
        query="Co tong bao nhieu san pham?",
        store=make_product_store(),
    )

    assert result.used_llm is True
    assert result.force_expand_relationships is True
    assert result.tokens[:3] == ["product", "category", "count"]
