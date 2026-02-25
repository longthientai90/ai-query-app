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

## Required MCP Tools

- Preferred fully qualified name: `mcp-query-server:postgres_query`
- Supporting tool: `mcp-query-server:postgres_get_schema`
- If runtime exposes local aliases, `postgres_query` and `postgres_get_schema` are acceptable

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
   - If needed, call `postgres_get_schema` first
3. Build PostgreSQL SQL that is read-only and minimal:
   - Prefer explicit columns over `SELECT *`
   - Use predicates and joins that match schema keys
   - Add `ORDER BY` and `LIMIT` where appropriate
4. Call `postgres_query` with generated SQL and params.
5. Convert raw rows into a direct user answer.

## Feedback Loop

- If query returns validation/db error, revise SQL and retry once.
- If results are empty, verify filters and time range before concluding no data.
- If schema is unclear, fetch schema first instead of guessing columns.

## SQL Safety Rules

- Only generate `SELECT` or `WITH ... SELECT`.
- Never generate `DROP`, `DELETE`, `INSERT`, `UPDATE`, `ALTER`, or DDL/DML.
- Avoid comments and trailing semicolons.
- Keep queries bounded with a practical `LIMIT` for large datasets.

## Performance Guidelines

- Select only needed columns.
- Filter as early as possible.
- Avoid cartesian joins.
- Use indexed columns in `WHERE` and join predicates when possible.
