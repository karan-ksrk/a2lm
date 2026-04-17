<p align="center">
  <img src="logo.png" alt="A2LM Logo" width="320" />
</p>

# A2LM Gateway

OpenAI-compatible LLM gateway with priority-based automatic provider fallback.

Send a request to one endpoint — gateway tries providers in priority order until one succeeds.

## Features

- Single OpenAI-compatible endpoint: `POST /v1/chat/completions`
- 4 model aliases: `auto`, `fast`, `smart`, `coding`
- Automatic fallback: if provider fails or times out (10s), tries next in list
- 8 providers: Groq, Cerebras, Google AI Studio, Mistral, OpenRouter, Cohere, NVIDIA NIM, Cloudflare
- Streaming and non-streaming responses
- API key auth on all `/v1/*` endpoints
- No database, no Redis — just env vars and one config file

## Quick Start (Docker)

```bash
cp .env.example .env
# fill in at least one provider key + GATEWAY_API_KEY
docker compose up --build
```

Gateway: `http://localhost:8080`

## Local Run

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

## Authentication

All `/v1/*` routes require:
```
Authorization: Bearer <GATEWAY_API_KEY>
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/chat/completions` | Chat inference (OpenAI-compatible) |
| `GET`  | `/v1/models` | List available aliases |
| `GET`  | `/health` | Liveness check |

Returns `503` if all providers for an alias fail.

## Model Aliases

Each alias has an ordered candidate list. Gateway picks the first provider that responds successfully.

### `auto` — general purpose
1. Groq `llama-3.3-70b-versatile`
2. Cerebras `llama3.1-8b`
3. Google `gemini-2.5-flash`
4. Mistral `mistral-small-latest`
5. Cloudflare `@cf/meta/llama-3.3-70b-instruct-fp8-fast`
6. Cohere `command-a-03-2025`
7. OpenRouter `meta-llama/llama-3.3-70b-instruct:free`
8. NVIDIA `meta/llama-3.3-70b-instruct`

### `fast` — speed first
1. Groq `llama-3.1-8b-instant`
2. Cerebras `llama3.1-8b`
3. Google `gemma-3-4b-it`
4. Mistral `mistral-small-latest`
5. Cloudflare `@cf/meta/llama-3.2-3b-instruct`
6. Cohere `command-r7b-12-2024`

### `smart` — capability first
1. Groq `moonshotai/kimi-k2-instruct`
2. Google `gemini-2.5-flash`
3. Mistral `mistral-large-latest`
4. NVIDIA `deepseek-ai/deepseek-r1`
5. Cloudflare `@cf/qwen/qwq-32b`
6. Cohere `command-a-03-2025`
7. OpenRouter `meta-llama/llama-3.1-405b-instruct:free`

### `coding` — code tasks
1. Mistral `codestral-latest`
2. Groq `moonshotai/kimi-k2-instruct`
3. NVIDIA `qwen/qwen2.5-coder-32b-instruct`
4. Google `gemini-2.5-flash`
5. Cloudflare `@cf/deepseek-ai/deepseek-r1-distill-qwen-32b`
6. OpenRouter `deepseek/deepseek-coder-v2-lite-instruct:free`

To change routing: edit [`app/priorities/aliases.py`](app/priorities/aliases.py) — no other files need to change.

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
    messages=[{"role": "user", "content": "Hello"}],
)
print(response.choices[0].message.content)
```

### curl

```bash
curl http://localhost:8080/v1/chat/completions \
  -H "Authorization: Bearer your-gateway-api-key" \
  -H "Content-Type: application/json" \
  -d '{"model": "fast", "messages": [{"role": "user", "content": "Say hello"}]}'
```

### Streaming

```python
stream = client.chat.completions.create(
    model="coding",
    messages=[{"role": "user", "content": "Write a binary search in Python"}],
    stream=True,
)
for chunk in stream:
    print(chunk.choices[0].delta.content or "", end="")
```

### Open WebUI / other tools

Set base URL to `http://localhost:8080/v1` and API key to your `GATEWAY_API_KEY`.

From another Docker container on the same host:
```
http://host.docker.internal:8080/v1
```

## Configuration

### `.env`

```env
GATEWAY_API_KEY=your-personal-gateway-key

# Add keys for any providers you want active
GROQ_API_KEY=
CEREBRAS_API_KEY=
GOOGLE_AI_STUDIO_API_KEY=
MISTRAL_API_KEY=
OPENROUTER_API_KEY=
COHERE_API_KEY=
NVIDIA_API_KEY=
CLOUDFLARE_API_KEY=
CLOUDFLARE_ACCOUNT_ID=
```

At least one provider key required. Providers with no key are skipped automatically.

### Provider key sources

| Provider | Get key |
|----------|---------|
| Groq | https://console.groq.com |
| Cerebras | https://cloud.cerebras.ai |
| Google AI Studio | https://aistudio.google.com |
| Mistral | https://console.mistral.ai |
| OpenRouter | https://openrouter.ai |
| Cohere | https://dashboard.cohere.com |
| NVIDIA NIM | https://build.nvidia.com (phone verification required) |
| Cloudflare | https://dash.cloudflare.com — needs API key + Account ID |

## Smoke Tests

With gateway running:

```bash
python test_gateway.py
```

Tests: health, auth, all 4 aliases, streaming, invalid alias rejection.

## Project Structure

```
app/
  main.py               # FastAPI app + provider setup
  config.py             # env var settings
  schemas.py            # OpenAI-compatible request/response types
  router.py             # fallback loop logic
  priorities/
    aliases.py          # ← edit this to change routing
  providers/
    base.py             # shared httpx client
    groq.py
    cerebras.py
    google.py
    mistral.py
    openrouter.py
    cohere.py
    nvidia.py
    cloudflare.py
  api/
    auth.py
    routes.py
```
