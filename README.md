<p align="center">
  <img src="logo.png" alt="A2LM Logo" width="180" />
</p>

# A2LM Gateway — MVP

Single OpenAI-compatible endpoint that routes across **Groq**, **OpenRouter**, **Google AI Studio**, and **Cerebras** with automatic fallback and rate-limit tracking.

---

## Quick Start

### Step 1 — Get your free API keys

| Provider | URL | Notes |
|---|---|---|
| **Groq** | https://console.groq.com | Free, instant signup |
| **OpenRouter** | https://openrouter.ai | Free tier: 50 req/day |
| **Google AI Studio** | https://aistudio.google.com | Click "Get API Key" top-right |
| **Cerebras** | https://cloud.cerebras.ai | Get API key from account settings |

### Step 2 — Configure environment

```bash
cp .env.example .env
# Edit .env and paste your keys:
#   GROQ_API_KEY=gsk_...
#   OPENROUTER_API_KEY=sk-or-...
#   GOOGLE_AI_STUDIO_API_KEY=AIza...
#   CEREBRAS_API_KEY=csk_...
#   GATEWAY_API_KEY=pick-any-secret-key
```

### Step 3 — Start the gateway

```bash
docker compose up --build
```

Gateway starts at **http://localhost:8080**

---

## Documentation

Complete project documentation is available in:

- [docs/README.md](docs/README.md)

---

## Usage

### With OpenAI Python SDK (drop-in replacement)

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8080/v1",
    api_key="your-gateway-key",   # matches GATEWAY_API_KEY in .env
)

response = client.chat.completions.create(
    model="auto",       # gateway picks best available provider
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response.choices[0].message.content)
```

### With curl

```bash
curl http://localhost:8080/v1/chat/completions \
  -H "Authorization: Bearer your-gateway-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama-70b",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

### Streaming

```python
stream = client.chat.completions.create(
    model="fast",
    messages=[{"role": "user", "content": "Count to 10"}],
    stream=True,
)
for chunk in stream:
    print(chunk.choices[0].delta.content or "", end="")
```

---

## Available Models (Aliases)

| Alias | Routes to | Notes |
|---|---|---|
| `auto` | Groq Llama 70B → Cerebras Llama 8B → Google Gemma 27B → OpenRouter | Best available |
| `fast` | Groq Llama 8B → Cerebras Llama 8B → Google Gemma 4B | Lowest latency |
| `smart` | Cerebras GPT-OSS 120B → Groq Kimi K2 → OpenRouter 405B → Gemini Flash | Highest capability |
| `llama-8b` | Groq Llama 3.1 8B | |
| `llama-70b` | Groq Llama 3.3 70B | |
| `llama-405b` | OpenRouter Llama 3.1 405B (free) | |
| `deepseek-r1` | OpenRouter DeepSeek R1 (free) | Reasoning model |
| `gemini-flash` | Google Gemini 2.5 Flash | 1M context |
| `gemma-27b` | Google Gemma 3 27B | |
| `qwen-32b` | Groq Qwen3 32B | |
| `cerebras-llama-8b` | Cerebras Llama 3.1 8B | |
| `cerebras-gpt-oss-120b` | Cerebras GPT-OSS 120B | High-capability model |
| `cerebras-qwen-32b` | Cerebras Qwen3 32B | |

---

## Endpoints

```
POST /v1/chat/completions   — Main inference endpoint (OpenAI-compatible)
GET  /v1/models             — List all available model aliases
GET  /v1/providers          — Current quota status per provider token
GET  /health                — Liveness check
GET  /health/ready          — Readiness check (Redis connectivity)
```

---

## Run smoke tests

```bash
pip install httpx
python test_gateway.py
```

---

## Multi-key rotation (optional, for higher throughput)

Add multiple API keys as comma-separated values to multiply your free quota:

```env
GROQ_API_KEYS=gsk_key1,gsk_key2,gsk_key3
OPENROUTER_API_KEYS=sk-or-key1,sk-or-key2
GOOGLE_AI_STUDIO_API_KEYS=AIza_key1,AIza_key2
CEREBRAS_API_KEYS=csk_key1,csk_key2
```

The gateway will distribute requests across all tokens and track each separately.

---

## Debug: inspect Redis keys

```bash
docker compose --profile debug up -d redis-commander
# Open http://localhost:8081 — shows all rl:* rate limit keys live
```

---

## Contributing

Contributions are welcome. Please read the contribution guide before opening a PR:

- [CONTRIBUTING.md](CONTRIBUTING.md)
