# Contributing to A2LM Gateway

Thanks for contributing. This document describes the expected workflow for changes in this project.

## Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Git

## Local setup

1. Clone the repository.
2. Create and configure environment variables:

```bash
cp .env.example .env
```

3. Add keys and gateway auth config in `.env`:
- `GATEWAY_API_KEY`
- Provider keys (`GROQ_API_KEY`, `OPENROUTER_API_KEY`, `GOOGLE_AI_STUDIO_API_KEY`) or multi-key variants

## Run the project

Using Docker (recommended):

```bash
docker compose up --build
```

API will be available at `http://localhost:8080`.

## Run tests

Smoke test:

```bash
pip install httpx
python test_gateway.py
```

Optional quick script:

```bash
python test.py
```

## Coding guidelines

- Keep the OpenAI-compatible API behavior stable.
- Prefer small, focused pull requests.
- Follow existing module layout under `app/` (`api`, `adapters`, `routing`, `ratelimit`, `registry`).
- Do not commit secrets or real API keys.
- Update docs when behavior, config, or endpoints change.

## Pull request process

1. Create a feature branch from `main`.
2. Make changes with clear commit messages.
3. Run relevant tests locally.
4. Update `README.md` and/or this file for user-facing changes.
5. Open a pull request with:
- Problem statement
- What changed
- How it was tested
- Any breaking changes or migration notes

## Suggested PR checklist

- [ ] Code builds and starts successfully
- [ ] Existing endpoint behavior is preserved or intentionally documented
- [ ] Tests/smoke checks pass locally
- [ ] No secrets or credentials in commits
- [ ] Documentation updated
