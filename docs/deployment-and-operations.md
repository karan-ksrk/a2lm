# Deployment and Operations

## Local development with Docker Compose

From repository root:

```bash
docker compose up --build
```

Services:

- `gateway` on `:8080`
- `redis` internal service for quota tracking
- optional `redis-commander` on `:8081` using `--profile debug`

Debug profile:

```bash
docker compose --profile debug up -d redis-commander
```

## Container details

`Dockerfile`:

- Base image: `python:3.12-slim`
- Installs `requirements.txt`
- Copies `app/`
- Runs:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

Note: `--reload` is convenient for development but should typically be disabled for production images.

## Health checks

- Liveness: `GET /health`
- Readiness: `GET /health/ready` (includes Redis ping check)

Compose gateway healthcheck currently uses:

```bash
curl -f http://localhost:8080/health
```

## State and persistence

- Redis data is persisted via named volume `redis_data`.
- Quota keys persist across restarts unless volume is removed.

## Logs

- Structured logging via `structlog`.
- Log level configured by `LOG_LEVEL` environment variable.

## Security baseline

- All `/v1/*` endpoints require gateway bearer key.
- CORS is currently permissive (`allow_origins=["*"]`, methods and headers all allowed).
- Avoid exposing gateway publicly without additional controls:
  - stricter CORS
  - TLS termination
  - network-level restrictions
  - key rotation and secrets management

