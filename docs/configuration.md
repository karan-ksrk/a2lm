# Configuration

Configuration is loaded from environment variables (via `pydantic-settings`) and `.env`.

## Required variables

- `GATEWAY_API_KEY`
  - Bearer token used by clients when calling gateway endpoints.

- At least one provider key (single-key or multi-key form):
  - `GROQ_API_KEY` or `GROQ_API_KEYS`
  - `OPENROUTER_API_KEY` or `OPENROUTER_API_KEYS`
  - `GOOGLE_AI_STUDIO_API_KEY` or `GOOGLE_AI_STUDIO_API_KEYS`
  - `CEREBRAS_API_KEY` or `CEREBRAS_API_KEYS`

- `REDIS_URL`
  - Required for quota checks and readiness endpoint.

## Optional variables

- `SECRET_KEY` (default: `change-me`)
- `DATABASE_URL` (present but not currently used in active runtime paths)
- `LOG_LEVEL` (default: `INFO`)

## Single vs multi-key behavior

The gateway supports token rotation for each provider.

For each provider:

1. If `*_API_KEYS` (comma-separated) is set and non-empty, those keys are used.
2. Otherwise, fallback to single `*_API_KEY`.

Example:

```env
GROQ_API_KEYS=gsk_a,gsk_b,gsk_c
OPENROUTER_API_KEY=sk-or-single
GOOGLE_AI_STUDIO_API_KEYS=AIza_a,AIza_b
CEREBRAS_API_KEYS=csk_a,csk_b
```

Token pools are built as indexed IDs like:

- `groq:0`, `groq:1`
- `openrouter:0`
- `google_ai_studio:0`
- `cerebras:0`

These IDs namespace Redis quota keys.

## Notes on provider-specific auth

- Groq/OpenRouter/Cerebras: API key in `Authorization: Bearer <key>`
- Google AI Studio: API key passed in query string (`?key=<key>`)

