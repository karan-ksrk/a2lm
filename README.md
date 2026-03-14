<p align="center">
  <img src="logo.png" alt="A2LM Logo" width="320" />
</p>

# A2LM Gateway

OpenAI-compatible LLM gateway with quota-aware and health-aware routing across multiple providers.

## Features

- Single OpenAI-compatible endpoint: `POST /v1/chat/completions`
- Multi-provider routing with fallback across 8 providers
- Provider health and latency aware scoring (not just static priority)
- Redis-backed per-token RPM and daily quota tracking
- Circuit breaker for unstable providers
- Streaming and non-streaming responses
- Gateway model aliases: `auto`, `fast`, `smart`
- API key auth for all `/v1/*` endpoints

## Supported Providers

- Groq
- OpenRouter
- Google AI Studio
- Cerebras
- Cloudflare Workers AI
- Cohere
- Mistral
- NVIDIA NIM

## Quick Start (Docker)

### 1) Configure environment

```bash
cp .env.example .env
```

Set these in `.env`:

- `GATEWAY_API_KEY` (required)
- At least one provider key (required)
- `REDIS_URL` (required, default in `.env.example` works with docker compose)
- `CLOUDFLARE_ACCOUNT_ID` (required only if using Cloudflare)

### 2) Start services

```bash
docker compose up --build
```

Gateway: `http://localhost:8080`

Optional Redis UI:

```bash
docker compose --profile debug up -d redis-commander
```

Redis Commander: `http://localhost:8081`

## Local Run (Without Docker)

Redis must be running and reachable by `REDIS_URL`.

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

## Authentication and Base URL

- Base URL: `http://localhost:8080/v1`
- Header: `Authorization: Bearer <GATEWAY_API_KEY>`

All `/v1/*` routes require the gateway API key.

## Endpoints

- `POST /v1/chat/completions` - main inference endpoint (OpenAI-compatible)
- `GET /v1/models` - list exposed model IDs
- `GET /v1/providers` - per-token provider quota/health/latency status
- `GET /health` - liveness
- `GET /health/ready` - readiness (includes Redis connectivity check)

If no provider is currently available for a request, the gateway returns `503` with `Retry-After: 60`.

## Usage

### OpenAI Python SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8080/v1",
    api_key="your-gateway-api-key",
)

response = client.chat.completions.create(
    model="auto",
    messages=[{"role": "user", "content": "Hello from A2LM"}],
)

print(response.choices[0].message.content)
print("served_model:", response.model)
```

### curl

```bash
curl http://localhost:8080/v1/chat/completions \
  -H "Authorization: Bearer your-gateway-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "fast",
    "messages": [{"role": "user", "content": "Say hello in one line"}]
  }'
```

### Streaming

```python
stream = client.chat.completions.create(
    model="fast",
    messages=[{"role": "user", "content": "Count from 1 to 5"}],
    stream=True,
)
for chunk in stream:
    print(chunk.choices[0].delta.content or "", end="")
```

## Routing Aliases

These aliases map to ordered candidate lists. The scorer then picks the best currently available candidate based on quota, latency, health, and weight.

### `auto` priority list

1. Groq `llama-3.3-70b-versatile`
2. Cerebras `llama3.1-8b`
3. Mistral `mistral-small-latest`
4. NVIDIA `meta/llama-3.3-70b-instruct`
5. Cloudflare `@cf/meta/llama-3.3-70b-instruct-fp8-fast`
6. Google AI Studio `gemma-3-27b-it`
7. OpenRouter `meta-llama/llama-3.3-70b-instruct:free`
8. Cohere `command-a-03-2025`

### `fast` priority list

1. Groq `llama-3.1-8b-instant`
2. Cerebras `llama3.1-8b`
3. Mistral `mistral-small-latest`
4. NVIDIA `meta/llama-3.3-70b-instruct`
5. Cloudflare `@cf/meta/llama-3.2-3b-instruct`
6. Google AI Studio `gemma-3-4b-it`
7. OpenRouter `meta-llama/llama-3.2-3b-instruct:free`
8. Cohere `command-r7b-12-2024`

### `smart` priority list

1. Cerebras `gpt-oss-120b`
2. Cloudflare `@cf/qwen/qwq-32b`
3. NVIDIA `deepseek-ai/deepseek-r1`
4. Mistral `mistral-large-latest`
5. Groq `moonshotai/kimi-k2-instruct`
6. OpenRouter `meta-llama/llama-3.1-405b-instruct:free`
7. Google AI Studio `gemini-2.5-flash`
8. Cohere `command-a-03-2025`

## Current Model IDs

Exposed by `GET /v1/models`.

- Gateway aliases: `auto`, `fast`, `smart`
- Groq: `llama-8b`, `llama-70b`, `kimi-k2`, `qwen-32b`
- OpenRouter: `llama-405b`, `deepseek-r1`, `gemma-27b-or`
- Google AI Studio: `gemini-flash`, `gemma-27b`, `gemma-12b`, `gemma-4b`
- Cerebras: `cerebras-llama-8b`, `cerebras-gpt-oss-120b`, `cerebras-qwen-32b`
- Cloudflare: `cf-llama-70b`, `cf-llama-8b`, `cf-qwq-32b`, `cf-deepseek-r1`, `cf-gemma-12b`
- Cohere: `command-a`, `command-r-plus`, `command-r`, `command-r7b`, `aya-32b`
- Mistral: `mistral-small`, `mistral-large`, `mistral-nemo`, `mixtral-8x7b`, `codestral`
- NVIDIA: `nvidia-llama-70b`, `nvidia-llama-405b`, `nvidia-qwen-coder`, `nvidia-phi-4-mini`

## Multi-Key Rotation

You can configure multiple API keys per provider (comma-separated) for higher throughput and better quota distribution.

Supported multi-key vars:

- `GROQ_API_KEYS`
- `OPENROUTER_API_KEYS`
- `GOOGLE_AI_STUDIO_API_KEYS`
- `CEREBRAS_API_KEYS`
- `CLOUDFLARE_API_KEYS`
- `MISTRAL_API_KEYS`
- `NVIDIA_API_KEYS`

Single-key vars are also supported and used as fallback:

- `GROQ_API_KEY`, `OPENROUTER_API_KEY`, `GOOGLE_AI_STUDIO_API_KEY`, `CEREBRAS_API_KEY`
- `CLOUDFLARE_API_KEY`, `COHERE_API_KEY`, `MISTRAL_API_KEY`, `NVIDIA_API_KEY`

Example:

```env
GROQ_API_KEYS=gsk_key1,gsk_key2
OPENROUTER_API_KEYS=sk-or-key1,sk-or-key2
GOOGLE_AI_STUDIO_API_KEYS=AIza_key1,AIza_key2
CEREBRAS_API_KEYS=csk_key1,csk_key2
MISTRAL_API_KEYS=mis_key1,mis_key2
NVIDIA_API_KEYS=nv_key1,nv_key2
```

## Smoke Tests

With gateway running:

```bash
python test_gateway.py
```

Quick manual script:

```bash
python test.py
```

## Notes

- Redis is required for runtime routing/quota checks.
- `DATABASE_URL` is currently configured but not used in active request paths.
- CORS is currently open to all origins (`*`).

## Documentation

- [docs/README.md](docs/README.md)
- [docs/api.md](docs/api.md)
- [docs/models-and-routing.md](docs/models-and-routing.md)
- [docs/configuration.md](docs/configuration.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)
