# api-gateway

User-facing HTTP layer for the AI query system.

## Responsibilities

- Accept REST requests from clients
- Validate request schema
- Forward chat request to standalone `agent-core` HTTP service
- Return structured response (`question`, `answer`, `sql`, `result`, ...)

## Run

Start `agent-core` first (default `http://127.0.0.1:8100`), then run gateway:

```bash
cd apps/api-gateway
python -m venv .venv
.venv\Scripts\Activate
pip install -r requirements.txt
# copy .env.example to .env if you need custom URLs/ports
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

## Environment variables

- `AGENT_CORE_BASE_URL` (default: `http://127.0.0.1:8100`)
- `AGENT_CORE_HANDLE_PATH` (default: `/agent/handle`)
- `AGENT_CORE_TIMEOUT_SEC` (default: `120`)
- `API_GATEWAY_HOST` (default: `0.0.0.0`)
- `API_GATEWAY_PORT` (default: `8000`)
- `API_GATEWAY_CORS_ORIGINS` (default: `*`)

## Endpoint

- `POST /api/chat`

Request:

```json
{
  "question": "Thong ke doanh thu thang nay",
  "max_rows": 100
}
```
