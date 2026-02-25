# agent-core

Runtime orchestration layer for:

- Loading declarative skills from `packages/agent-skills`
- Routing user question to the right skill
- Calling MCP tools (`postgres_get_schema`, `postgres_query`, `postgres_explain`)
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
pip install -r requirements.txt
# copy .env.example to .env and fill Azure values first
uvicorn http_app:app --host 0.0.0.0 --port 8100 --reload
```

Or:

```bash
python http_app.py
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
- `AGENT_CORE_HOST` (default: `0.0.0.0`)
- `AGENT_CORE_PORT` (default: `8100`)
- `LLM_PROVIDER` (default: `azure`)
- `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`
