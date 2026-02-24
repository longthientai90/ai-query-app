# mcp-query-server

PostgreSQL MCP Tool Server built with FastMCP. This service is intentionally read-only and only exposes schema/query/explain tools.

## Run locally

```bash
python -m venv .venv
.venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py
```

## Tests

```bash
pytest tests/ -v
pytest tests/ -v --integration
pytest tests/ --cov=. --cov-report=html
```

## Read-only DB role grants

```sql
CREATE ROLE mcp_readonly LOGIN PASSWORD 'Scuti@12345';
GRANT CONNECT ON DATABASE db_ec TO mcp_readonly;
GRANT USAGE ON SCHEMA public TO mcp_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO mcp_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT ON TABLES TO mcp_readonly;
```

