# mcp-query-server

PostgreSQL MCP Tool Server built with FastMCP. This service is intentionally read-only and only exposes schema/query/explain tools.

## Run locally

```bash
cd .\apps\mcp-query-server
python -m venv .venv
.venv\Scripts\Activate
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

## Tracing

This service emits OpenTelemetry traces when `OTEL_EXPORTER_OTLP_ENDPOINT` is set.

Recommended values:

```env
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
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
