# API Reference

All protected endpoints require:

- Header: `Authorization: Bearer <GATEWAY_API_KEY>`

Base URL examples:

- Local: `http://localhost:8080`
- OpenAI-compatible namespace: `http://localhost:8080/v1`

## POST /v1/chat/completions

OpenAI-compatible chat completion endpoint with provider routing and fallback.

### Request body

```json
{
  "model": "auto",
  "messages": [
    { "role": "user", "content": "Hello" }
  ],
  "temperature": 0.7,
  "max_tokens": 1024,
  "stream": false,
  "top_p": 0.9,
  "stop": ["END"]
}
```

### Fields

- `model` (string, default `auto`)
- `messages` (array, required)
- `temperature` (number, optional)
- `max_tokens` (integer, optional)
- `stream` (boolean, optional)
- `top_p` (number, optional)
- `stop` (string or string array, optional)
- `x-latency-hint` (optional alias field in schema; currently not used by routing)

### Success responses

- Non-streaming: OpenAI-like `chat.completion` JSON object
- Streaming: Server-Sent Events (`text/event-stream`) with `data: {...}` chunks and terminal `data: [DONE]`

### Error responses

- `401`: invalid/missing gateway key
- `503`: all providers exhausted for selected model alias
- `502`: upstream provider call failed

## GET /v1/models

Returns gateway model aliases and provider-owned models in OpenAI list format.

### Response shape

```json
{
  "object": "list",
  "data": [
    {
      "id": "llama-8b",
      "object": "model",
      "owned_by": "groq",
      "context_length": 131072
    }
  ]
}
```

## GET /v1/providers

Returns per-token provider quota status from Redis and static limits table.

### Response shape

```json
{
  "providers": [
    {
      "provider": "groq",
      "token": "groq:0",
      "rpm_remaining": 29,
      "rpm_limit": 30,
      "daily_remaining": 999,
      "daily_limit": 1000,
      "available": true
    }
  ]
}
```

## GET /health

Liveness endpoint.

### Response

```json
{ "status": "ok" }
```

## GET /health/ready

Readiness endpoint. Checks Redis connectivity through the initialized routing engine.

### Response

```json
{
  "status": "ready",
  "checks": {
    "redis": "ok"
  }
}
```

If Redis is unavailable, status becomes `degraded` and `checks.redis` contains error text.

