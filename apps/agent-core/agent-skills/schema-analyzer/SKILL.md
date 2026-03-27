---
name: schema-analyzer
description: Analyzes PostgreSQL schema metadata and identifies table/column relationships. Use when users ask what data is available, ask about tables/fields/relationships, or when schema context is required before writing SQL.
---

# Schema Analyzer

## When To Activate

Activate when the request includes keywords or intents such as:

- Available tables, fields, or relationships
- What data exists in the database
- Clarifying table structure before query generation

## Runtime Inputs

- Schema retrieval and refresh are performed by `service-schema`

## Workflow Checklist

Copy and track:

```text
Schema Analysis Progress:
- [ ] Step 1: Determine schema scope needed for the user request
- [ ] Step 2: Fetch schema metadata
- [ ] Step 3: Identify key entities and key columns
- [ ] Step 4: Infer likely joins/relationships
- [ ] Step 5: Return concise schema summary with caveats
```

1. Determine whether broad schema discovery or focused schema retrieval is needed.
2. Refresh schema through `service-schema` when the request is about current structure.
3. Inspect the returned ranked tables and compact context:
   - Table names and selected columns
   - Relationship hints
   - Primary/index annotations when present
4. Infer likely entity relationships from key columns:
   - `*_id` patterns and primary keys
   - Natural lookup tables and fact tables
5. Respond with a concise structure summary that helps downstream SQL generation.

## Feedback Loop

- If schema output is empty or incomplete, retry with a narrower, more explicit schema question.
- If keys/relationships are ambiguous, state uncertainty explicitly and avoid inventing ERD links.

## Constraints

- Do not fabricate tables or columns that are not in tool output.
- If schema is empty or the retrieval service reports an error, say that clearly and ask for environment verification.
