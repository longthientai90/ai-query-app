from __future__ import annotations

import re

from sqlglot import exp, parse_one
from sqlglot.errors import ParseError

DENY_KEYWORDS = {
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "CREATE",
    "TRUNCATE",
    "COPY",
    "GRANT",
    "REVOKE",
    "CALL",
    "DO",
    "EXECUTE",
}

RISKY_FUNCTIONS = {
    "pg_read_file",
    "pg_ls_dir",
    "dblink",
    "dblink_exec",
    "lo_import",
    "lo_export",
    "copy_to",
    "copy_from",
}


class SQLValidationError(ValueError):
    pass


def _contains_comment(sql: str) -> bool:
    # Block comments to reduce hidden payloads and prompt-injected fragments.
    return "--" in sql or "/*" in sql or "*/" in sql


def _contains_multistatement(sql: str) -> bool:
    stripped = sql.strip()
    return bool(re.search(r";\s*\S", stripped))


def _contains_denied_keyword(sql: str) -> str | None:
    upper_sql = sql.upper()
    for keyword in DENY_KEYWORDS:
        if re.search(rf"\b{keyword}\b", upper_sql):
            return keyword
    return None


def _extract_function_name(node: exp.Expression) -> str | None:
    if isinstance(node, exp.Anonymous):
        return node.name.lower()
    if isinstance(node, exp.Func):
        return node.sql_name().lower()
    return None


def validate_sql(sql: str) -> None:
    """Validate SQL as read-only SELECT/CTE SELECT and reject risky patterns."""
    if not sql or not sql.strip():
        raise SQLValidationError("SQL cannot be empty")
    if _contains_comment(sql):
        raise SQLValidationError("SQL comments are not allowed")
    if _contains_multistatement(sql):
        raise SQLValidationError("Multi-statement SQL is not allowed")

    denied = _contains_denied_keyword(sql)
    if denied:
        raise SQLValidationError(f"Disallowed keyword found: {denied}")

    try:
        # Parse to AST so checks are based on SQL structure, not raw string only.
        parsed = parse_one(sql, read="postgres")
    except ParseError as exc:
        raise SQLValidationError(f"Invalid SQL syntax: {exc}") from exc

    if not isinstance(parsed, exp.Select):
        raise SQLValidationError("Only SELECT statements are allowed")

    for node in parsed.walk():
        # Walk the AST to catch blocked function calls anywhere in the query.
        func_name = _extract_function_name(node)
        if func_name and func_name in RISKY_FUNCTIONS:
            raise SQLValidationError(f"Disallowed function found: {func_name}")
