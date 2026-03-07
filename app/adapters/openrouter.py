import json
from app.adapters.base import BaseProviderAdapter
from app.models.schemas import (
    NormalizedRequest, ChatCompletionResponse,
    ChatCompletionChunk, Choice, ChoiceDelta, Usage
)


class OpenRouterAdapter(BaseProviderAdapter):
    provider_id = "openrouter"
    base_url = "https://openrouter.ai/api/v1"

    model_map = {
        "llama-405b":   "meta-llama/llama-3.1-405b-instruct:free",
        "llama-70b":    "meta-llama/llama-3.3-70b-instruct:free",
        "llama-8b":     "meta-llama/llama-3.2-3b-instruct:free",
        "deepseek-r1":  "deepseek/deepseek-r1-0528:free",
        "gemma-27b":    "google/gemma-3-27b-it:free",
        "gemma-12b":    "google/gemma-3-12b-it:free",
        "qwen-235b":    "qwen/qwen3-next-80b-a3b-instruct:free",
        "smart":        "meta-llama/llama-3.1-405b-instruct:free",
        "auto":         "meta-llama/llama-3.3-70b-instruct:free",
    }

    def build_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/omni-llm-gateway",
            "X-Title": "OMNI-LLM Gateway",
        }

    def get_chat_url(self) -> str:
        return f"{self.base_url}/chat/completions"

    def translate_request(self, req: NormalizedRequest) -> dict:
        payload: dict = {
            "model": self.map_model(req.model),
            "messages": req.messages,
            "temperature": req.temperature,
            "max_tokens": req.max_tokens,
            "stream": req.stream,
        }
        if req.top_p is not None:
            payload["top_p"] = req.top_p
        if req.stop:
            payload["stop"] = req.stop
        return payload

    def translate_response(self, raw: dict, req: NormalizedRequest) -> ChatCompletionResponse:
        # OpenRouter is OpenAI-compatible — almost no translation needed
        choices = []
        for c in raw.get("choices", []):
            choices.append(Choice(
                index=c.get("index", 0),
                message=c.get("message"),
                finish_reason=c.get("finish_reason"),
            ))
        usage = None
        if u := raw.get("usage"):
            usage = Usage(
                prompt_tokens=u.get("prompt_tokens", 0),
                completion_tokens=u.get("completion_tokens", 0),
                total_tokens=u.get("total_tokens", 0),
            )
        return ChatCompletionResponse(
            id=raw.get("id", "chatcmpl-or"),
            model=raw.get("model", req.model),
            choices=choices,
            usage=usage,
        )

    def translate_stream_chunk(self, raw_data: str) -> ChatCompletionChunk | None:
        try:
            raw = json.loads(raw_data)
        except json.JSONDecodeError:
            return None
        choices = []
        for c in raw.get("choices", []):
            delta = c.get("delta", {})
            choices.append(Choice(
                index=c.get("index", 0),
                delta=ChoiceDelta(
                    role=delta.get("role"),
                    content=delta.get("content"),
                ),
                finish_reason=c.get("finish_reason"),
            ))
        return ChatCompletionChunk(
            id=raw.get("id", "chunk"),
            model=raw.get("model", "openrouter"),
            choices=choices,
        )

    def parse_rate_limit_headers(self, headers):
        # OpenRouter uses different header names
        from app.models.schemas import RateLimitInfo
        return RateLimitInfo(
            rpm_limit=None,
            rpm_remaining=None,
        )
