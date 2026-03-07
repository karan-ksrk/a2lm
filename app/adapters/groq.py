import json
from app.adapters.base import BaseProviderAdapter
from app.models.schemas import (
    NormalizedRequest, ChatCompletionResponse,
    ChatCompletionChunk, Choice, ChoiceDelta, Usage
)


class GroqAdapter(BaseProviderAdapter):
    provider_id = "groq"
    base_url = "https://api.groq.com/openai/v1"

    # Gateway alias → Groq native model ID
    model_map = {
        "llama-8b":     "llama-3.1-8b-instant",
        "llama-70b":    "llama-3.3-70b-versatile",
        "llama-70b-s":  "llama-3.3-70b-specdec",
        "kimi-k2":      "moonshotai/kimi-k2-instruct",
        "qwen-32b":     "qwen/qwen3-32b",
        "fast":         "llama-3.1-8b-instant",
        "auto":         "llama-3.3-70b-versatile",
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
            "messages": [m for m in req.messages],
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
            id=raw.get("id", f"chatcmpl-groq"),
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
            model=raw.get("model", "groq"),
            choices=choices,
        )
