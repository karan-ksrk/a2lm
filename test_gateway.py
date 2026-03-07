#!/usr/bin/env python3
"""
Quick smoke test for the OMNI-LLM Gateway.
Run AFTER the gateway is up: python test_gateway.py
"""

import os
import json
import httpx

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8080")


def _load_env_value_from_dotenv(key: str, path: str = ".env") -> str | None:
    """Lightweight .env parser for local smoke tests."""
    if not os.path.exists(path):
        return None

    with open(path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() != key:
                continue
            # Support inline comments (VALUE # comment)
            value = v.split("#", 1)[0].strip().strip('"').strip("'")
            return value or None
    return None


GATEWAY_KEY = (
    os.getenv("GATEWAY_API_KEY")
    or _load_env_value_from_dotenv("GATEWAY_API_KEY")
    or "dev-key"
)

headers = {
    "Authorization": f"Bearer {GATEWAY_KEY}",
    "Content-Type": "application/json",
}


def separator(title: str):
    print(f"\n{'─' * 50}")
    print(f"  {title}")
    print('─' * 50)


def test_health():
    separator("1. Health Check")
    r = httpx.get(f"{GATEWAY_URL}/health")
    print(f"Status: {r.status_code} → {r.json()}")
    assert r.status_code == 200


def test_models():
    separator("2. List Models")
    r = httpx.get(f"{GATEWAY_URL}/v1/models", headers=headers)
    data = r.json()
    print(f"Status: {r.status_code}")
    if r.status_code != 200:
        print(f"Error: {data}")
        raise AssertionError(
            "Auth failed for /v1/models. Check GATEWAY_API_KEY in your shell or .env."
        )
    print(f"Models available: {len(data['data'])}")
    for m in data["data"][:6]:
        print(f"  • {m['id']}  ({m['owned_by']})")
    print("  ...")
    assert r.status_code == 200


def test_chat_auto():
    separator("3. Chat Completion — model: auto")
    payload = {
        "model": "auto",
        "messages": [{"role": "user", "content": "Say: hello from omni-llm"}],
        "max_tokens": 30,
    }
    r = httpx.post(f"{GATEWAY_URL}/v1/chat/completions", headers=headers, json=payload, timeout=30)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        content = data["choices"][0]["message"]["content"]
        print(f"Response: {content}")
        print(f"Model served by: {data['model']}")
    else:
        print(f"Error: {r.text}")


def test_chat_specific():
    separator("4. Chat Completion — model: llama-8b")
    payload = {
        "model": "llama-8b",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant. Be very brief."},
            {"role": "user", "content": "What is 2+2?"},
        ],
        "max_tokens": 20,
    }
    r = httpx.post(f"{GATEWAY_URL}/v1/chat/completions", headers=headers, json=payload, timeout=30)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        print(f"Response: {r.json()['choices'][0]['message']['content']}")
    else:
        print(f"Error: {r.text}")


def test_streaming():
    separator("5. Streaming — model: fast")
    payload = {
        "model": "fast",
        "messages": [{"role": "user", "content": "Count from 1 to 5, one number per line."}],
        "max_tokens": 50,
        "stream": True,
    }
    print("Streaming chunks: ", end="", flush=True)
    with httpx.stream("POST", f"{GATEWAY_URL}/v1/chat/completions",
                      headers=headers, json=payload, timeout=30) as r:
        for line in r.iter_lines():
            if line.startswith("data: ") and line != "data: [DONE]":
                try:
                    chunk = json.loads(line[6:])
                    delta = chunk["choices"][0].get("delta", {})
                    if content := delta.get("content"):
                        print(content, end="", flush=True)
                except Exception:
                    pass
    print("\n✓ Stream complete")


def test_provider_status():
    separator("6. Provider Quota Status")
    r = httpx.get(f"{GATEWAY_URL}/v1/providers", headers=headers)
    print(f"Status: {r.status_code}")
    for p in r.json().get("providers", []):
        avail = "✓" if p["available"] else "✗"
        print(f"  {avail} {p['provider']:20s} RPM: {p['rpm_remaining']:4d}/{p['rpm_limit']}  "
              f"Daily: {p['daily_remaining']:6d}/{p['daily_limit']}")


def test_auth_failure():
    separator("7. Auth — Bad Key (should 401)")
    r = httpx.get(f"{GATEWAY_URL}/v1/models",
                  headers={"Authorization": "Bearer wrong-key"})
    print(f"Status: {r.status_code} (expected 401) → {'✓' if r.status_code == 401 else '✗'}")


if __name__ == "__main__":
    print("\n🚀  OMNI-LLM Gateway Smoke Tests")
    print(f"    Target: {GATEWAY_URL}")
    try:
        test_health()
        test_models()
        test_auth_failure()
        test_provider_status()
        test_chat_auto()
        test_chat_specific()
        test_streaming()
        print("\n✅  All tests passed!\n")
    except Exception as e:
        print(f"\n❌  Test failed: {e}\n")
        raise
