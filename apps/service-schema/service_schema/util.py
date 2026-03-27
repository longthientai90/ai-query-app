from __future__ import annotations

import re
import unicodedata

TOKEN_PATTERN = re.compile(r"[a-z0-9_]+")


def tokenize(text: str) -> list[str]:
    normalized = _strip_accents(text).lower().replace("-", "_").replace(".", "_").replace("/", "_")
    parts = TOKEN_PATTERN.findall(normalized)
    tokens: list[str] = []
    for part in parts:
        tokens.append(part)
        tokens.extend(item for item in part.split("_") if item and item != part)
    seen: set[str] = set()
    ordered: list[str] = []
    for token in tokens:
        if token not in seen:
            ordered.append(token)
            seen.add(token)
    return ordered


def infer_aliases(table_name: str) -> list[str]:
    tokens = tokenize(table_name)
    aliases = {table_name.lower()}
    if len(tokens) > 1:
        aliases.add(" ".join(tokens))
        aliases.add("".join(tokens))
    singular = _singularize(tokens[-1]) if tokens else table_name.lower()
    if singular:
        aliases.add(singular)
    return sorted(alias for alias in aliases if alias)


def infer_business_tags(table_name: str) -> list[str]:
    tags: set[str] = set()
    for token in tokenize(table_name):
        if token.endswith("id"):
            continue
        tags.add(token)
    return sorted(tags)


def extract_index_columns(index_definition: str) -> list[str]:
    match = re.search(r"\((.+)\)", index_definition)
    if not match:
        return []
    columns: list[str] = []
    for item in [part.strip() for part in match.group(1).split(",") if part.strip()]:
        cleaned = re.sub(
            r"\s+(ASC|DESC|NULLS\s+FIRST|NULLS\s+LAST)\b",
            "",
            item,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(r"\s+COLLATE\s+\S+", "", cleaned, flags=re.IGNORECASE).strip()
        candidate = cleaned.split(".")[-1].strip().strip('"')
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", candidate):
            columns.append(candidate)
    return columns


def _singularize(token: str) -> str:
    if token.endswith("ies") and len(token) > 3:
        return token[:-3] + "y"
    if token.endswith("s") and not token.endswith("ss") and len(token) > 1:
        return token[:-1]
    return token


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(char for char in normalized if not unicodedata.combining(char))
