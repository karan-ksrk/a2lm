#!/usr/bin/env python3
"""Smoke tests for A2LM Gateway. Run after gateway is up: python test_gateway.py"""

import os
import json
import httpx

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8080")


def _read_dotenv(key: str, path: str = ".env") -> str | None:
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() == key:
                return v.split("#")[0].strip().strip('"').strip("'") or None
    return None


GATEWAY_KEY = os.getenv("GATEWAY_API_KEY") or _read_dotenv("GATEWAY_API_KEY") or "dev-key"
HEADERS = {"Authorization": f"Bearer {GATEWAY_KEY}", "Content-Type": "application/json"}

PASS = "✓"
FAIL = "✗"


def sep(title):
    print(f"\n{'─' * 55}\n  {title}\n{'─' * 55}")


def test_health():
    sep("1. Health")
    r = httpx.get(f"{GATEWAY_URL}/health", timeout=5)
    print(f"  {PASS if r.status_code == 200 else FAIL} {r.status_code} → {r.json()}")
    assert r.status_code == 200


def test_auth():
    sep("2. Auth — bad key should 401")
    r = httpx.get(f"{GATEWAY_URL}/v1/models", headers={"Authorization": "Bearer wrong"})
    ok = r.status_code == 401
    print(f"  {PASS if ok else FAIL} got {r.status_code} (expected 401)")
    assert ok


def test_models():
    sep("3. List models")
    r = httpx.get(f"{GATEWAY_URL}/v1/models", headers=HEADERS)
    assert r.status_code == 200, f"Auth failed: {r.text}"
    aliases = [m["id"] for m in r.json()["data"]]
    print(f"  {PASS} aliases: {aliases}")
    return aliases


def test_all_aliases(aliases: list[str]):
    sep("4. Chat — all aliases")
    results = {}
    for alias in aliases:
        try:
            r = httpx.post(
                f"{GATEWAY_URL}/v1/chat/completions",
                headers=HEADERS,
                json={"model": alias, "messages": [{"role": "user", "content": "reply: ok"}], "max_tokens": 20},
                timeout=45,
            )
            if r.status_code == 200:
                content = r.json()["choices"][0]["message"]["content"].strip()
                served = r.json().get("model", "?")
                print(f"  {PASS} {alias:10s} → {content[:30]!r}  (served by: {served})")
                results[alias] = True
            else:
                print(f"  {FAIL} {alias:10s} → HTTP {r.status_code}: {r.text[:80]}")
                results[alias] = False
        except Exception as e:
            print(f"  {FAIL} {alias:10s} → {e}")
            results[alias] = False
    return results


def test_streaming():
    sep("5. Streaming — alias: fast")
    payload = {
        "model": "fast",
        "messages": [{"role": "user", "content": "count 1 to 5"}],
        "max_tokens": 40,
        "stream": True,
    }
    chunks = []
    with httpx.stream("POST", f"{GATEWAY_URL}/v1/chat/completions",
                      headers=HEADERS, json=payload, timeout=45) as r:
        assert r.status_code == 200, f"HTTP {r.status_code}"
        for line in r.iter_lines():
            if not line.startswith("data: ") or line == "data: [DONE]":
                continue
            try:
                data = json.loads(line[6:])
                if "error" in data:
                    print(f"  {FAIL} stream error: {data['error']}")
                    return
                text = data["choices"][0].get("delta", {}).get("content", "")
                if text:
                    chunks.append(text)
            except Exception:
                pass
    print(f"  {PASS} received {len(chunks)} chunks → {''.join(chunks)[:60]!r}")


def test_invalid_alias():
    sep("6. Invalid alias — should 400")
    r = httpx.post(
        f"{GATEWAY_URL}/v1/chat/completions",
        headers=HEADERS,
        json={"model": "nonexistent", "messages": [{"role": "user", "content": "hi"}]},
        timeout=10,
    )
    ok = r.status_code == 400
    print(f"  {PASS if ok else FAIL} got {r.status_code} (expected 400)")


if __name__ == "__main__":
    print(f"\nA2LM Gateway Smoke Tests")
    print(f"Target: {GATEWAY_URL}")
    test_health()
    test_auth()
    aliases = test_models()
    results = test_all_aliases(aliases)
    test_streaming()
    test_invalid_alias()

    passed = sum(results.values())
    total = len(results)
    print(f"\n{'─' * 55}")
    print(f"Alias results: {passed}/{total} passed")
    if passed < total:
        failed = [k for k, v in results.items() if not v]
        print(f"Failed: {failed}")
    print()
