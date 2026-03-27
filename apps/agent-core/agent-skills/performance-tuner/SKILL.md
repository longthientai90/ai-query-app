---
name: performance-tuner
description: Analyzes PostgreSQL EXPLAIN plans, diagnoses slow SQL access patterns, and proposes safer/faster rewrites. Use when users ask to optimize a slow query, compare alternatives, or investigate bottlenecks.
---

# Performance Tuner

## When To Activate

Activate when the request mentions:

- Slow query symptoms
- SQL optimization or tuning
- EXPLAIN plan analysis or index/join performance

## Runtime Inputs

- Schema context is retrieved by `service-schema`
- SQL inspection is performed by `mcp-query-server:postgres_explain`
- Optional verification queries use `mcp-query-server:postgres_query`

## Workflow Checklist

```text
Performance Tuning Progress:
- [ ] Step 1: Capture target SQL and context
- [ ] Step 2: Run EXPLAIN (JSON) baseline
- [ ] Step 3: Detect dominant cost drivers
- [ ] Step 4: Propose rewrite
- [ ] Step 5: Re-check plan and summarize tradeoffs
```

1. Collect the target SQL from context or synthesize a candidate query from the question.
2. Call `postgres_explain` first:
   - Start with `analyze: false`
   - Use `analyze: true` only when deeper runtime evidence is needed
3. Inspect the plan for anti-patterns:
   - Sequential scan on large tables where indexes should apply
   - Join explosion or poor join order
   - Late filter application
   - Expensive sort/hash steps
4. Propose a rewrite:
   - Narrow selected columns
   - Push down filters
   - Improve join predicates
   - Consider CTE/subquery restructuring if it improves plan shape
5. If needed, re-run `postgres_explain` on rewritten SQL and summarize improvements.

## Feedback Loop

- If rewritten SQL changes business semantics, reject rewrite and keep original logic.
- If plan does not improve, report that no safe optimization was found yet.
- Optionally run `postgres_query` on both versions with limited rows to verify equivalent outputs.

## Constraints

- Keep all SQL read-only.
- Do not claim measurable speedup unless plan evidence supports it.
- If no meaningful optimization is possible, state that explicitly.
