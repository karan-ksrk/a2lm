from __future__ import annotations
import httpx
from dataclasses import dataclass
from typing import Optional

from app.providers.base import BaseProvider
from app.schemas import NormalizedRequest

_TEST_MESSAGES = [{"role": "user", "content": "Say hi."}]


@dataclass
class TestResult:
    passed: bool
    skipped: bool = False
    error: Optional[str] = None
    snippet: Optional[str] = None


async def test_model(provider: BaseProvider, model_id: str) -> TestResult:
    req = NormalizedRequest(
        model=model_id,
        messages=_TEST_MESSAGES,
        temperature=0.1,
        max_tokens=10,
        stream=False,
    )
    try:
        result = await provider.complete(req)
        msg = result.choices[0].message if result.choices else None
        content = (msg.get("content") or "") if isinstance(msg, dict) else ""
        if content:
            return TestResult(passed=True, snippet=content[:60])
        return TestResult(passed=False, error="empty response content")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            return TestResult(passed=False, skipped=True, error="rate_limited")
        return TestResult(passed=False, error=f"HTTP {e.response.status_code}: {e.response.text[:120]}")
    except Exception as e:
        return TestResult(passed=False, error=str(e)[:120])
