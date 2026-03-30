# service-schema

`service-schema` is a FastAPI service that synchronizes PostgreSQL metadata, builds an in-memory schema index, and returns compact schema context for `agent-core`.

## Phase 1 status

- PostgreSQL schema sync for tables, columns, primary keys, foreign keys, and indexes
- In-memory lexical retrieval with FK expansion
- Compact schema context builder
- Health, reindex, table detail, and search endpoints
- Qdrant configuration surface only; vector retrieval is intentionally optional and disabled by default

## Run locally

```bash
cd .\apps\service-schema
python -m venv .venv
.venv\Scripts\Activate
pip install -r requirements.txt
copy .env.example .env
python main.py
```

`SCHEMA_ALIAS_OVERRIDES` and `SCHEMA_TAG_OVERRIDES` expect JSON objects in `.env`.
When Qdrant is running locally from Docker Compose, set `QDRANT_ENABLED=true` and keep `QDRANT_URL=http://127.0.0.1:6333`.
Search logs print the query and returned table names in the service console.

## Endpoints

- `POST /schema/reindex`
- `POST /schema/search`
- `GET /schema/tables/{table_name}`
- `GET /schema/health`

## Query rewrite

`service-schema` now supports hybrid query rewrite before lexical retrieval:

- local normalization plus a small Vietnamese synonym dictionary
- optional Azure OpenAI fallback rewrite when lexical search returns no tables or a weak score
- lexical retrieval remains the source of truth
- FK neighbor expansion can be forced after a successful rewrite so queries like `sản phẩm` can surface related tables such as `categories`

Set these env vars to enable Azure rewrite with a small deployment such as `gpt-4o-mini`:

- `SCHEMA_QUERY_REWRITE_ENABLED=true`
- `AZURE_OPENAI_ENDPOINT=...`
- `AZURE_OPENAI_API_KEY=...`
- `AZURE_OPENAI_DEPLOYMENT=...`
- optional: `AZURE_OPENAI_API_VERSION=2024-10-21`
