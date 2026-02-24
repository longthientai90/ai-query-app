# mcp-query-client

FastAPI client app for testing `mcp-query-server` through the official MCP Python SDK.

## Setup

```bash
python -m venv .venv
.venv\Scripts\Activate

pip install -r requirements.txt
cp .env.example .env
```

## Run

```bash
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

## Environment variables (`.env`)

- `MCP_SERVER_TRANSPORT` (use `http`)
- `MCP_SERVER_URL` (example: `http://127.0.0.1:8000/mcp`)
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_API_VERSION`
- `AZURE_OPENAI_DEPLOYMENT`

## APIs

- `GET /health`
- `GET /tools`
- `POST /query`
- `POST /schema`
- `POST /explain`
- `POST /chat` (question -> Azure OpenAI generates SQL -> calls MCP `postgres_query`)
