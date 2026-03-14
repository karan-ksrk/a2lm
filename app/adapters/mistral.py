import json
from app.adapters.base import BaseProviderAdapter
from app.models.schemas import (
    NormalizedRequest, ChatCompletionResponse,
    ChatCompletionChunk, Choice, ChoiceDelta, Usage, RateLimitInfo
)


class MistralAdapter(BaseProviderAdapter):
    provider_id = "mistral"
    base_url = "https://api.mistral.ai/v1"

    model_map = {
        "mistral-small":    "mistral-small-latest",
        "mistral-medium":   "mistral-medium-latest",
        "mistral-large":    "mistral-large-latest",
        "codestral":        "codestral-latest",
        "mixtral-8x7b":     "open-mixtral-8x7b",
        "mixtral-8x22b":    "open-mixtral-8x22b",
        "mistral-7b":       "open-mistral-7b",
        "mistral-nemo":     "open-mistral-nemo",
        "fast":             "mistral-small-latest",
        "auto":             "mistral-small-latest",
        "smart":            "mistral-large-latest",
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
            id=raw.get("id", "chatcmpl-mistral"),
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
            model=raw.get("model", "mistral"),
            choices=choices,
        )

    def parse_rate_limit_headers(self, headers: dict) -> RateLimitInfo:
        # Mistral returns standard ratelimit headers
        return RateLimitInfo(
            rpm_limit=_safe_int(headers.get("ratelimit-limit")),
            rpm_remaining=_safe_int(headers.get("ratelimit-remaining")),
            reset_requests=headers.get("ratelimit-reset"),
        )


def _safe_int(val) -> int | None:
    try:
        return int(val)
    except (TypeError, ValueError):
        return None
