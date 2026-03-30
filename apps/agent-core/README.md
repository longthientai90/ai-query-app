# agent-core

Runtime orchestration layer for:

- Loading declarative skills from `apps/agent-core/agent-skills`
- Routing user question to the right skill
- Calling `service-schema` for schema retrieval and MCP tools for query/explain
- Returning a structured response for API gateway

## Run as CLI

```bash
cd apps/agent-core
pip install -r requirements.txt
python -m venv .venv
.venv\Scripts\Activate
# copy .env.example to .env and fill Azure values first
python main.py "Thong ke doanh thu thang nay"
```

## Run as HTTP service (independent)

```bash
cd apps/agent-core
.venv\Scripts\Activate
pip install -r requirements.txt
# copy .env.example to .env and fill Azure values first
uvicorn http_app:app --host 0.0.0.0 --port 8100 --reload
```

Or:

```bash
python http_app.py
```

## Run with Docker

```bash
docker build -t agent-core ./apps/agent-core
docker run --rm -p 8100:8100 --env-file ./apps/agent-core/.env agent-core
```

### Endpoints

- `GET /health`
- `GET /skills`
- `POST /agent/handle`
- `POST /api/chat` (alias for gateway compatibility)

Example request:

```bash
curl -X POST "http://127.0.0.1:8100/agent/handle" ^
  -H "Content-Type: application/json" ^
  -d "{\"question\":\"Thống kê doanh thu tháng này\",\"max_rows\":100}"
```

## Environment variables

- Config file location is fixed at `apps/agent-core/.env`.
- Create `.env` from `.env.example` and fill your Azure credentials.
- `MCP_SERVER_URL` (default: `http://127.0.0.1:8000/mcp`)
- `SERVICE_SCHEMA_BASE_URL` (default: `http://127.0.0.1:8200`)
- `SERVICE_SCHEMA_TIMEOUT_SEC` (default: `60`)
- `AGENT_CORE_HOST` (default: `0.0.0.0`)
- `AGENT_CORE_PORT` (default: `8100`)
- `LLM_PROVIDER` (default: `azure`)
- `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_ROUTER_DEPLOYMENT`, `AZURE_OPENAI_SQL_DEPLOYMENT`, `AZURE_OPENAI_SUMMARY_DEPLOYMENT`
- Optional fallback: `AZURE_OPENAI_DEPLOYMENT`
- `OTEL_EXPORTER_OTLP_ENDPOINT` (example: `http://otel-collector:4318`)
- `OTEL_EXPORTER_OTLP_PROTOCOL` (recommended: `http/protobuf`)
