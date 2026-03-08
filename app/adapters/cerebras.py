import json
from app.adapters.base import BaseProviderAdapter
from app.models.schemas import (
    NormalizedRequest, ChatCompletionResponse,
    ChatCompletionChunk, Choice, ChoiceDelta, Usage
)


class CerebrasAdapter(BaseProviderAdapter):
    provider_id = "cerebras"
    base_url = "https://api.cerebras.ai/v1"

    model_map = {
        "llama-70b":    "llama-3.3-70b",
        "llama-8b":     "llama-3.1-8b",
        "qwen-235b":    "qwen-3-235b",
        "qwen-32b":     "qwen-3-32b",
        "fast":         "llama-3.1-8b",
        "auto":         "llama-3.3-70b",
        "smart":        "qwen-3-235b",
    }

    def build_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/a2lm-gateway",
            "X-Title": "A2LM Gateway",
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
            id=raw.get("id", "chatcmpl-cerebras"),
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
            model=raw.get("model", "cerebras"),
            choices=choices,
        )
