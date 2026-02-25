# Docker Deployment

This folder contains a compose setup for:

- `mcp-query-server`
- `agent-core`
- `api-gateway`

PostgreSQL is intentionally not included.

## Prerequisites

- Docker + Docker Compose
- A reachable PostgreSQL instance

## Important database note

`mcp-query-server` reads `DATABASE_URL` from `apps/mcp-query-server/.env`.
If PostgreSQL runs on your host machine (not in Docker), use `host.docker.internal` instead of `localhost`.

Example:

```env
DATABASE_URL=postgresql://user:password@host.docker.internal:5432/db_name
```

## Start

From repo root:

```bash
docker compose -f infra/docker/docker-compose.yml up --build -d
```

## Stop

```bash
docker compose -f infra/docker/docker-compose.yml down
```

## Exposed ports

- `api-gateway`: `8080`
- `agent-core`: `8100`
- `mcp-query-server`: `8000`
