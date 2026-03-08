# Troubleshooting

## 401 Unauthorized on `/v1/*`

Cause:

- missing or wrong `Authorization` bearer token

Checks:

- verify request header is `Authorization: Bearer <GATEWAY_API_KEY>`
- verify `.env` `GATEWAY_API_KEY` matches your client value

## 503 No provider available

Cause:

- all candidate providers/tokens for selected model are out of RPM or daily quota

Checks:

- call `GET /v1/providers` and inspect `available`, `rpm_remaining`, `daily_remaining`
- wait for RPM window reset (up to 60 seconds)
- wait for daily quota reset (next UTC midnight)
- add additional provider keys using `*_API_KEYS` rotation

## 502 Bad gateway from chat endpoint

Cause:

- upstream provider error
- invalid provider API key
- model unsupported by upstream for selected provider

Checks:

- verify provider keys in `.env`
- test with another model alias (`fast`, `auto`, `smart`)
- inspect service logs for provider error message

## `/health/ready` is degraded

Cause:

- Redis connection failed

Checks:

- verify `REDIS_URL`
- ensure Redis container/service is running
- verify network reachability from gateway to Redis host

## Streaming not working

Checks:

- set `stream: true` in request body
- ensure client is reading SSE lines from `text/event-stream`
- confirm reverse proxy does not buffer streaming responses

## CORS issues in browser clients

Current default is permissive CORS. If you hardened CORS settings:

- ensure frontend origin is included in `allow_origins`
- ensure `Authorization` is allowed in headers
- verify preflight `OPTIONS` requests are accepted

