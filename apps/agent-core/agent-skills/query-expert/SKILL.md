---
name: query-expert
description: Generates secure read-only PostgreSQL SQL and retrieves result rows. Use when users ask to list, filter, aggregate, rank, compare, or compute business metrics from database data.
---

# Query Expert

## When To Activate

Activate when user intent is data retrieval:

- List/search/filter records
- Aggregate metrics (sum, count, avg, revenue, trends)
- Ranking, grouping, time-based summaries

## Runtime Inputs

- Schema context is retrieved by `service-schema`
- SQL execution is performed by `mcp-query-server:postgres_query`

## Workflow Checklist

```text
SQL Execution Progress:
- [ ] Step 1: Parse question intent and target entities
- [ ] Step 2: Confirm schema context
- [ ] Step 3: Draft minimal read-only SQL
- [ ] Step 4: Execute query via MCP
- [ ] Step 5: Validate result shape and answer clearly
```

1. Parse the user question into data requirements:
   - Required fields
   - Filters and time windows
   - Grouping or aggregation rules
2. Ensure schema context is known:
   - The runtime should fetch compact schema context from `service-schema`
   - Prefer schema annotations like `[PK]`, `[IDX]`, and `indexes:` when available
3. Build PostgreSQL SQL that is read-only and minimal:
   - Prefer explicit columns over `SELECT *`
   - Use predicates and joins that match schema keys
   - Prefer `[PK]`/`[IDX]` columns in `WHERE`, `JOIN ON`, and `ORDER BY`
   - Keep predicates sargable (avoid wrapping indexed columns in functions in `WHERE`)
   - Add `ORDER BY` and `LIMIT` where appropriate
4. Call `postgres_query` with generated SQL and params.
5. Convert raw rows into a direct user answer.

## Feedback Loop

- If query returns validation/db error, revise SQL and retry once.
- If query returns timeout, narrow filters and retry once with simpler/sargable predicates.
- If results are empty, verify filters and time range before concluding no data.
- If schema is unclear, ask for refreshed schema context instead of guessing columns.

## SQL Safety Rules

- Only generate `SELECT` or `WITH ... SELECT`.
- Never generate `DROP`, `DELETE`, `INSERT`, `UPDATE`, `ALTER`, or DDL/DML.
- Avoid comments and trailing semicolons.
- Keep queries bounded with a practical `LIMIT` for large datasets.

## Performance Guidelines

- Select only needed columns; never use `SELECT *` unless explicitly required.
- Filter as early as possible in `WHERE`.
- Avoid cartesian joins (always include a correct `ON` predicate).
- Always prefer columns marked `[PK]` or `[IDX]` in `WHERE`, `JOIN ON`, and `ORDER BY`.
- For foreign key filters, prefer filtering directly on indexed FK columns.
- Keep expressions sargable: avoid `date_trunc(col)`, `lower(col)`, or casts on indexed columns inside `WHERE`.
- For time windows, use range predicates (for example `col >= $1 AND col < $2`) instead of wrapping the column with functions.
- Keep result sets bounded with `LIMIT` and stable sort when returning top-N.
