# api-gateway

User-facing HTTP layer for the AI query system.

## Responsibilities

- Accept REST requests from clients
- Validate request schema
- Delegate query handling to `agent-core`
- Return structured response (`question`, `answer`, `sql`, `result`, ...)

## Run

```bash
cd apps/api-gateway
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Endpoint

- `POST /api/chat`

Request:

```json
{
  "question": "Thong ke doanh thu thang nay",
  "max_rows": 100
}
```
