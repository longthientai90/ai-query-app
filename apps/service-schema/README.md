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

## Endpoints

- `POST /schema/reindex`
- `POST /schema/search`
- `GET /schema/tables/{table_name}`
- `GET /schema/health`
