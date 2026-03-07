from abc import ABC, abstractmethod
from typing import AsyncIterator
import httpx

from app.models.schemas import (
    NormalizedRequest, ChatCompletionResponse,
    ChatCompletionChunk, RateLimitInfo
)


class BaseProviderAdapter(ABC):
    provider_id: str
    base_url: str
    # Maps gateway model aliases → provider-native model strings
    model_map: dict[str, str] = {}

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = httpx.AsyncClient(timeout=60.0)

    async def close(self):
        await self._client.aclose()

    # ── Must implement ────────────────────────

    @abstractmethod
    def build_headers(self) -> dict:
        """Return auth + content-type headers for this provider."""
        pass

    @abstractmethod
    def translate_request(self, req: NormalizedRequest) -> dict:
        """Convert NormalizedRequest → provider-specific payload dict."""
        pass

    @abstractmethod
    def translate_response(self, raw: dict, req: NormalizedRequest) -> ChatCompletionResponse:
        """Convert provider raw JSON response → ChatCompletionResponse."""
        pass

    @abstractmethod
    def translate_stream_chunk(self, raw_data: str) -> ChatCompletionChunk | None:
        """Parse one SSE data line → ChatCompletionChunk (or None to skip)."""
        pass

    @abstractmethod
    def get_chat_url(self) -> str:
        """Return the full URL for chat completions."""
        pass

    # ── Optional override ─────────────────────

    def parse_rate_limit_headers(self, headers: dict) -> RateLimitInfo:
        """Default: parse standard x-ratelimit-* headers (Groq/OpenAI style)."""
        return RateLimitInfo(
            rpm_limit=_int(headers.get("x-ratelimit-limit-requests")),
            rpm_remaining=_int(headers.get("x-ratelimit-remaining-requests")),
            tpm_limit=_int(headers.get("x-ratelimit-limit-tokens")),
            tpm_remaining=_int(headers.get("x-ratelimit-remaining-tokens")),
            reset_requests=headers.get("x-ratelimit-reset-requests"),
            reset_tokens=headers.get("x-ratelimit-reset-tokens"),
        )

    def map_model(self, alias: str) -> str:
        """Resolve a model alias to the provider's native model string."""
        return self.model_map.get(alias, alias)

    # ── Shared execution logic ────────────────

    async def complete(self, req: NormalizedRequest) -> ChatCompletionResponse:
        payload = self.translate_request(req)
        response = await self._client.post(
            self.get_chat_url(),
            headers=self.build_headers(),
            json=payload,
        )
        response.raise_for_status()
        return self.translate_response(response.json(), req)

    async def stream(self, req: NormalizedRequest) -> AsyncIterator[str]:
        payload = self.translate_request(req)
        async with self._client.stream(
            "POST",
            self.get_chat_url(),
            headers=self.build_headers(),
            json=payload,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.strip():
                    continue
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        yield "data: [DONE]\n\n"
                        return
                    chunk = self.translate_stream_chunk(data)
                    if chunk:
                        yield f"data: {chunk.model_dump_json()}\n\n"


def _int(val) -> int | None:
    try:
        return int(val)
    except (TypeError, ValueError):
        return None
