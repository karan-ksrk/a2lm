# Architecture

## Overview

A2LM Gateway exposes an OpenAI-compatible API and routes requests across multiple providers:

- Groq
- OpenRouter
- Google AI Studio
- Cerebras

It applies provider/model-aware rate-limit checks and falls back to the next candidate provider when quota is exhausted.

## High-level flow

1. Client sends request to `POST /v1/chat/completions`.
2. API key is validated (`Authorization: Bearer <GATEWAY_API_KEY>`).
3. Request is normalized into internal format.
4. Routing engine resolves model alias into ordered provider candidates.
5. RateLimitManager checks Redis-backed RPM and daily quota for each provider token.
6. First available provider token is selected.
7. Request is translated by provider adapter and dispatched upstream.
8. On success, quotas are consumed and response is translated to OpenAI-compatible format.

## Core modules

- `app/main.py`
  - FastAPI app bootstrap
  - CORS middleware
  - startup/shutdown lifecycle
  - shared `RoutingEngine` in `app.state.engine`

- `app/api/routes.py`
  - endpoint handlers
  - streaming and non-streaming dispatch
  - error mapping to HTTP 502/503

- `app/api/auth.py`
  - bearer token validation against `GATEWAY_API_KEY`

- `app/routing/engine.py`
  - model candidate resolution
  - provider token pool construction
  - quota-aware provider selection

- `app/registry/models.py`
  - static model registry
  - alias priorities (`auto`, `fast`, `smart`)
  - adapter factory

- `app/ratelimit/manager.py`
  - Redis-backed RPM sliding window
  - daily quota tracking
  - provider/model limits table

- `app/adapters/*.py`
  - provider-specific request/response translation
  - streaming chunk translation

## Runtime dependencies

- FastAPI + Uvicorn
- Redis (required for readiness and rate-limit state)
- HTTPX async client for upstream provider calls

`database_url` is currently configured but not used by active runtime code.

## Data and state

- Stateless request handling in API layer
- Redis stores quota counters:
  - `rl:<provider:token_index>:rpm` (sorted set, 60-second window)
  - `rl:<provider:token_index>:daily` (counter, expires after next UTC midnight)

## Startup and shutdown

- Startup (`lifespan` in `app/main.py`):
  - initialize `RateLimitManager`
  - initialize `ModelRegistry`
  - initialize `RoutingEngine`

- Shutdown:
  - close Redis async client via `RateLimitManager.close()`

## Error handling model

- `NoProviderAvailableError` -> HTTP 503 with `Retry-After: 60`
- upstream provider/network errors -> HTTP 502
- invalid gateway key -> HTTP 401

