from __future__ import annotations
import httpx
from dataclasses import dataclass, field


@dataclass
class DiscoveredModel:
    provider: str
    model_id: str
    is_free: bool = True
    raw: dict = field(default_factory=dict)


async def fetch_groq(api_key: str, client: httpx.AsyncClient) -> list[DiscoveredModel]:
    try:
        r = await client.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        r.raise_for_status()
        return [
            DiscoveredModel(provider="groq", model_id=m["id"], raw=m)
            for m in r.json().get("data", [])
        ]
    except Exception as e:
        print(f"  [groq] fetch error: {e}")
        return []


async def fetch_cerebras(api_key: str, client: httpx.AsyncClient) -> list[DiscoveredModel]:
    try:
        r = await client.get(
            "https://api.cerebras.ai/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        r.raise_for_status()
        return [
            DiscoveredModel(provider="cerebras", model_id=m["id"], raw=m)
            for m in r.json().get("data", [])
        ]
    except Exception as e:
        print(f"  [cerebras] fetch error: {e}")
        return []


async def fetch_google(api_key: str, client: httpx.AsyncClient) -> list[DiscoveredModel]:
    try:
        r = await client.get(
            f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}",
        )
        r.raise_for_status()
        results = []
        for m in r.json().get("models", []):
            name = m.get("name", "")
            if not name.startswith("models/"):
                continue
            model_id = name[len("models/"):]
            methods = m.get("supportedGenerationMethods", [])
            if "generateContent" not in methods:
                continue
            # skip embedding/aqa/vision-only/image models
            lower = model_id.lower()
            if any(x in lower for x in ("embedding", "aqa", "vision", "image", "tts", "transcrib")):
                continue
            results.append(DiscoveredModel(provider="google", model_id=model_id, raw=m))
        return results
    except Exception as e:
        print(f"  [google] fetch error: {e}")
        return []


async def fetch_mistral(api_key: str, client: httpx.AsyncClient) -> list[DiscoveredModel]:
    try:
        r = await client.get(
            "https://api.mistral.ai/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        r.raise_for_status()
        return [
            DiscoveredModel(provider="mistral", model_id=m["id"], raw=m)
            for m in r.json().get("data", [])
        ]
    except Exception as e:
        print(f"  [mistral] fetch error: {e}")
        return []


async def fetch_openrouter(api_key: str, client: httpx.AsyncClient) -> list[DiscoveredModel]:
    try:
        r = await client.get(
            "https://openrouter.ai/api/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        r.raise_for_status()
        results = []
        for m in r.json().get("data", []):
            pricing = m.get("pricing", {})
            is_free = pricing.get("prompt") == "0" and pricing.get("completion") == "0"
            if not is_free:
                continue
            results.append(DiscoveredModel(provider="openrouter", model_id=m["id"], is_free=True, raw=m))
        return results
    except Exception as e:
        print(f"  [openrouter] fetch error: {e}")
        return []


async def fetch_cohere(api_key: str, client: httpx.AsyncClient) -> list[DiscoveredModel]:
    try:
        r = await client.get(
            "https://api.cohere.com/v2/models",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        r.raise_for_status()
        results = []
        for m in r.json().get("models", []):
            endpoints = m.get("endpoints", [])
            if "chat" not in endpoints:
                continue
            results.append(DiscoveredModel(provider="cohere", model_id=m["name"], raw=m))
        return results
    except Exception as e:
        print(f"  [cohere] fetch error: {e}")
        return []


async def fetch_nvidia(api_key: str, client: httpx.AsyncClient) -> list[DiscoveredModel]:
    try:
        r = await client.get(
            "https://integrate.api.nvidia.com/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        r.raise_for_status()
        return [
            DiscoveredModel(provider="nvidia", model_id=m["id"], raw=m)
            for m in r.json().get("data", [])
        ]
    except Exception as e:
        print(f"  [nvidia] fetch error: {e}")
        return []


async def fetch_cloudflare(api_key: str, account_id: str, client: httpx.AsyncClient) -> list[DiscoveredModel]:
    try:
        r = await client.get(
            f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/models/search",
            headers={"Authorization": f"Bearer {api_key}"},
            params={"per_page": 500},
        )
        r.raise_for_status()
        results = []
        for m in r.json().get("result", []):
            task = m.get("task", {})
            if task.get("name") != "Text Generation":
                continue
            results.append(DiscoveredModel(provider="cloudflare", model_id=m["name"], raw=m))
        return results
    except Exception as e:
        print(f"  [cloudflare] fetch error: {e}")
        return []
