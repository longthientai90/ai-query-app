from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from openai import AsyncAzureOpenAI

from service_schema.indexing.store import SchemaStore
from service_schema.util import tokenize

logger = logging.getLogger(__name__)

LOCAL_SYNONYM_MAP: dict[str, list[str]] = {
    "san pham": ["product"],
    "hang hoa": ["product"],
    "mat hang": ["product"],
    "danh muc": ["category"],
    "nhom san pham": ["category"],
    "loai san pham": ["category"],
    "don hang": ["order"],
    "hoa don": ["order"],
    "khach hang": ["customer"],
    "nguoi dung": ["user", "customer"],
    "bao nhieu": ["count"],
    "tong bao nhieu": ["count"],
    "tong so": ["count"],
    "so luong": ["count"],
    "doanh thu": ["revenue", "sum"],
}


@dataclass(slots=True)
class QueryRewriteResult:
    tokens: list[str] = field(default_factory=list)
    used_llm: bool = False
    force_expand_relationships: bool = False
    warnings: list[str] = field(default_factory=list)


class SchemaQueryRewriter:
    def __init__(
        self,
        *,
        enabled: bool,
        azure_endpoint: str | None,
        api_key: str | None,
        api_version: str,
        deployment: str | None,
        max_keywords: int,
        client: AsyncAzureOpenAI | None = None,
    ) -> None:
        self.max_keywords = max_keywords
        self.client = client
        self.deployment = deployment
        if self.client is None and enabled and azure_endpoint and api_key and deployment:
            self.client = AsyncAzureOpenAI(
                azure_endpoint=azure_endpoint,
                api_key=api_key,
                api_version=api_version,
            )

    @property
    def enabled(self) -> bool:
        return self.client is not None and self.deployment is not None

    def rewrite_locally(self, query: str) -> QueryRewriteResult:
        tokens = tokenize(query)
        normalized_text = " ".join(tokens)
        expanded = list(tokens)
        matched_phrases = 0
        # Keep the local layer cheap and predictable: map only a few high-value
        # Vietnamese business phrases into canonical English schema terms.
        for phrase, mapped_terms in LOCAL_SYNONYM_MAP.items():
            if phrase in normalized_text:
                matched_phrases += 1
                expanded.extend(mapped_terms)

        deduped = self._dedupe_tokens(expanded)
        return QueryRewriteResult(
            tokens=deduped,
            used_llm=False,
            force_expand_relationships=matched_phrases > 0,
        )

    async def rewrite_with_llm(self, *, query: str, store: SchemaStore) -> QueryRewriteResult:
        if not self.enabled or self.client is None or self.deployment is None:
            return QueryRewriteResult(tokens=[])

        # Give the model a compact catalog instead of raw DDL so it can anchor
        # keyword extraction to real table names without paying a large token cost.
        schema_catalog = self._build_schema_catalog(store)
        logger.info(
            "schema_query_rewrite_llm_started query=%r deployment=%s catalog_table_count=%s",
            query,
            self.deployment,
            len(store.tables),
        )
        messages = [
            {
                "role": "system",
                "content": (
                    "You rewrite multilingual analytics questions into compact English schema lookup keywords. "
                    "Return JSON only with shape: "
                    "{\"keywords\": [\"...\"], \"expand_relationships\": true|false}. "
                    "Choose up to 8 short keywords. Prefer singular English nouns and SQL-like intents such as "
                    "count, sum, revenue, category, product, customer, order. "
                    "Use terms grounded in the schema catalog when possible."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Query: {query}\n\n"
                    f"Schema catalog:\n{schema_catalog}\n\n"
                    "Return JSON only."
                ),
            },
        ]
        try:
            completion = await self.client.chat.completions.create(
                model=self.deployment,
                messages=messages,
                temperature=0,
                max_completion_tokens=180,
                response_format={"type": "json_object"},
            )
        except Exception as exc:
            logger.warning("schema_query_rewrite_llm_failed error=%s", exc)
            return QueryRewriteResult(tokens=[], warnings=[f"query_rewrite_llm_failed:{exc}"])

        if not completion.choices or not completion.choices[0].message.content:
            return QueryRewriteResult(tokens=[], warnings=["query_rewrite_llm_empty"])

        try:
            payload = json.loads(completion.choices[0].message.content)
        except json.JSONDecodeError:
            return QueryRewriteResult(tokens=[], warnings=["query_rewrite_llm_invalid_json"])

        raw_keywords = payload.get("keywords") or []
        expand_relationships = bool(payload.get("expand_relationships", False))
        if not isinstance(raw_keywords, list):
            return QueryRewriteResult(tokens=[], warnings=["query_rewrite_llm_invalid_keywords"])

        llm_tokens: list[str] = []
        for keyword in raw_keywords[: self.max_keywords]:
            if isinstance(keyword, str):
                llm_tokens.extend(tokenize(keyword))

        result = QueryRewriteResult(
            tokens=self._dedupe_tokens(llm_tokens),
            used_llm=bool(llm_tokens),
            # A rewritten token such as "category" is usually a signal that the
            # caller expects joinable business context, not only one anchor table.
            force_expand_relationships=expand_relationships or any(
                token in {"category", "brand", "customer", "user"} for token in llm_tokens
            ),
        )
        logger.info(
            "schema_query_rewrite_llm_completed query=%r used_llm=%s rewritten_tokens=%s force_expand_relationships=%s",
            query,
            result.used_llm,
            result.tokens,
            result.force_expand_relationships,
        )
        return result

    @staticmethod
    def _build_schema_catalog(store: SchemaStore) -> str:
        lines: list[str] = []
        for table_name in sorted(store.tables):
            table = store.tables[table_name]
            aliases = ", ".join(table.aliases[:6])
            tags = ", ".join(table.business_tags[:6])
            neighbors = ", ".join(sorted(store.relationship_graph.get(table_name, set()))[:4])
            parts = [f"table={table_name}"]
            if aliases:
                parts.append(f"aliases=[{aliases}]")
            if tags:
                parts.append(f"tags=[{tags}]")
            if neighbors:
                parts.append(f"neighbors=[{neighbors}]")
            lines.append(" ".join(parts))
        return "\n".join(lines[:80])

    @staticmethod
    def _dedupe_tokens(tokens: list[str]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for token in tokens:
            if token and token not in seen:
                ordered.append(token)
                seen.add(token)
        return ordered
