import json
from app.adapters.base import BaseProviderAdapter
from app.models.schemas import (
    NormalizedRequest, ChatCompletionResponse,
    ChatCompletionChunk, Choice, ChoiceDelta, Usage, RateLimitInfo
)


class NvidiaAdapter(BaseProviderAdapter):
    provider_id = "nvidia"
    base_url = "https://integrate.api.nvidia.com/v1"

    model_map = {
        "llama-70b":        "meta/llama-3.3-70b-instruct",
        "llama-8b":         "meta/llama-3.1-8b-instruct",
        "llama-405b":       "meta/llama-3.1-405b-instruct",
        "deepseek-r1":      "deepseek-ai/deepseek-r1",
        "qwen-72b":         "qwen/qwen2.5-72b-instruct",
        "qwen-coder-32b":   "qwen/qwen2.5-coder-32b-instruct",
        "mistral-nemo":     "mistralai/mistral-nemo-12b-instruct",
        "phi-4-mini":       "microsoft/phi-4-mini-instruct",
        "gemma-27b":        "google/gemma-3-27b-it",
        "nemotron-70b":     "nvidia/llama-3.1-nemotron-70b-instruct",
        "fast":             "meta/llama-3.1-8b-instruct",
        "auto":             "meta/llama-3.3-70b-instruct",
        "smart":            "deepseek-ai/deepseek-r1",
    }

    def build_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
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
            payload["stop"] = req.stop if isinstance(req.stop, list) else [req.stop]
        return payload

    def translate_response(self, raw: dict, req: NormalizedRequest) -> ChatCompletionResponse:
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
            id=raw.get("id", "chatcmpl-nvidia"),
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
            model=raw.get("model", "nvidia"),
            choices=choices,
        )

    def parse_rate_limit_headers(self, headers: dict) -> RateLimitInfo:
        return RateLimitInfo(
            rpm_limit=_safe_int(headers.get("x-ratelimit-limit-requests")),
            rpm_remaining=_safe_int(headers.get("x-ratelimit-remaining-requests")),
            reset_requests=headers.get("x-ratelimit-reset-requests"),
        )


def _safe_int(val) -> int | None:
    try:
        return int(val)
    except (TypeError, ValueError):
        return None
