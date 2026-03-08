# Models and Routing

## Routing strategy

For each request:

1. Resolve requested model alias into ordered candidates.
2. For each candidate provider/model:
  - iterate configured API keys for that provider
  - check RPM and daily quota in Redis
3. Use first available token/candidate.
4. If no candidates are available, return HTTP 503.

## Generic aliases

Generic aliases route by priority, not by single provider ownership.

### `auto`

1. Groq `llama-3.3-70b-versatile`
2. Cerebras `llama3.1-8b`
3. Google AI Studio `gemma-3-27b-it`
4. OpenRouter `meta-llama/llama-3.3-70b-instruct:free`

### `fast`

1. Groq `llama-3.1-8b-instant`
2. Cerebras `llama3.1-8b`
3. Google AI Studio `gemma-3-4b-it`
4. OpenRouter `meta-llama/llama-3.2-3b-instruct:free`

### `smart`

1. Cerebras `gpt-oss-120b`
2. Groq `moonshotai/kimi-k2-instruct`
3. OpenRouter `meta-llama/llama-3.1-405b-instruct:free`
4. Google AI Studio `gemini-2.5-flash`

## Registered model IDs

The `GET /v1/models` endpoint is driven by static entries in `app/registry/models.py`.

Current provider-owned IDs include:

- Groq: `llama-8b`, `llama-70b`, `kimi-k2`, `qwen-32b`
- OpenRouter: `llama-405b`, `deepseek-r1`, `gemma-27b-or`
- Google AI Studio: `gemini-flash`, `gemma-27b`, `gemma-12b`, `gemma-4b`
- Cerebras: `cerebras-llama-8b`, `cerebras-gpt-oss-120b`, `cerebras-qwen-32b`
- Gateway aliases: `auto`, `fast`, `smart`

## Rate-limit policy

Rate limits are hard-coded in `app/ratelimit/manager.py` using provider/model defaults:

- RPM: 60-second sliding window (Redis sorted set)
- Daily: counter expiring at next UTC midnight

Quota is consumed after successful dispatch in routing execution paths.

## Unknown model behavior

If a model alias is not registered and not a generic alias, the registry fallback candidate order is:

1. `groq` with the raw model string
2. `openrouter` with the raw model string

This allows passing provider-native IDs directly in some cases.

