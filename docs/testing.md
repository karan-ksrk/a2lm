# Testing

## Smoke test script

Primary smoke test file: `test_gateway.py`

It validates:

- health endpoint
- auth behavior
- model listing
- provider status endpoint
- chat completions
- streaming responses
- optional loop across all listed models

### Run

```bash
pip install httpx
python test_gateway.py
```

By default, script target:

- `GATEWAY_URL` env var if set
- otherwise `http://localhost:8080`

Gateway API key resolution in script:

1. `GATEWAY_API_KEY` environment variable
2. `.env` value
3. fallback `dev-key`

## OpenAI SDK quick test

`test.py` demonstrates OpenAI client compatibility:

- sets `base_url=http://localhost:8080/v1`
- uses gateway API key
- sends a chat completion request

## Manual curl checks

Example model list:

```bash
curl http://localhost:8080/v1/models \
  -H "Authorization: Bearer <GATEWAY_API_KEY>"
```

Example chat completion:

```bash
curl http://localhost:8080/v1/chat/completions \
  -H "Authorization: Bearer <GATEWAY_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "auto",
    "messages": [{"role": "user", "content": "hello"}]
  }'
```

