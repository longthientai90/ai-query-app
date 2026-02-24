from __future__ import annotations

from sqlglot import exp, parse_one


class LimitExceededError(ValueError):
    pass


def enforce_limit(
    sql: str,
    default_limit: int,
    max_limit: int,
    max_rows: int | None = None,
) -> str:
    """Ensure every query has a bounded LIMIT and never exceeds max_limit."""
    if max_rows is not None and max_rows <= 0:
        raise LimitExceededError("max_rows must be greater than 0")

    parsed = parse_one(sql, read="postgres")
    target_limit = default_limit

    if max_rows is not None:
        target_limit = min(max_rows, max_limit)

    limit_expr = parsed.args.get("limit")
    if limit_expr is None:
        # Add default/user limit when query has no LIMIT clause.
        parsed.set("limit", exp.Limit(expression=exp.Literal.number(target_limit)))
        return parsed.sql(dialect="postgres")

    current_expr = limit_expr.expression if isinstance(limit_expr, exp.Limit) else None
    if isinstance(current_expr, exp.Literal) and current_expr.is_int:
        current_limit = int(current_expr.this)
        clamped = min(current_limit, max_limit)
        if max_rows is not None:
            clamped = min(clamped, target_limit)
        limit_expr.set("expression", exp.Literal.number(clamped))
        return parsed.sql(dialect="postgres")

    # For non-literal LIMIT expressions, replace with the safer bounded value.
    limit_expr.set("expression", exp.Literal.number(target_limit))
    return parsed.sql(dialect="postgres")
