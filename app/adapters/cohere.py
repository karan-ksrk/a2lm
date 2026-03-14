import json
import uuid
from app.adapters.base import BaseProviderAdapter
from app.models.schemas import (
    NormalizedRequest, ChatCompletionResponse,
    ChatCompletionChunk, Choice, ChoiceDelta, Usage, RateLimitInfo
)


class CohereAdapter(BaseProviderAdapter):
    provider_id = "cohere"
    base_url = "https://api.cohere.com/v2"

    model_map = {
        "command-a":     "command-a-03-2025",
        "command-r":     "command-r-08-2024",
        "command-r-plus": "command-r-plus-08-2024",
        "command-r7b":   "command-r7b-12-2024",
        "aya-32b":       "c4ai-aya-expanse-32b",
        "aya-8b":        "c4ai-aya-expanse-8b",
        "auto":          "command-a-03-2025",
        "fast":          "command-r7b-12-2024",
        "smart":         "command-a-03-2025",
    }

    def build_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def get_chat_url(self) -> str:
        return f"{self.base_url}/chat"

    def translate_request(self, req: NormalizedRequest) -> dict:
        # Cohere v2 separates system prompt from messages
        messages = []
        for msg in req.messages:
            role = msg["role"]
            content = msg["content"]
            # Cohere uses "user" and "assistant" — same as OpenAI
            # but "system" is a top-level field, not a message role
            if role == "system":
                # Will be handled separately below
                continue
            messages.append({"role": role, "content": content})

        payload: dict = {
            "model": self.map_model(req.model),
            "messages": messages,
            "max_tokens": req.max_tokens,
            "temperature": req.temperature,
            "stream": req.stream,
        }

        # Extract system prompt if present
        system_msgs = [m["content"] for m in req.messages if m["role"] == "system"]
        if system_msgs:
            payload["system"] = " ".join(system_msgs)

        if req.top_p is not None:
            payload["p"] = req.top_p  # Cohere calls it "p" not "top_p"

        if req.stop:
            payload["stop_sequences"] = (
                [req.stop] if isinstance(req.stop, str) else req.stop
            )

        return payload

    def translate_response(self, raw: dict, req: NormalizedRequest) -> ChatCompletionResponse:
        # Cohere v2 response structure:
        # {"id": "...", "message": {"role": "assistant", "content": [{"type": "text", "text": "..."}]},
        #  "finish_reason": "COMPLETE", "usage": {...}}
        message = raw.get("message", {})
        content_blocks = message.get("content", [])
        text = "".join(
            block.get("text", "") for block in content_blocks
            if block.get("type") == "text"
        )

        finish_reason = raw.get("finish_reason", "COMPLETE").lower()
        # Normalize Cohere finish reasons to OpenAI format
        finish_map = {"complete": "stop", "max_tokens": "length", "error": "stop"}
        finish_reason = finish_map.get(finish_reason, "stop")

        usage = None
        if u := raw.get("usage", {}):
            billed = u.get("billed_units", {})
            usage = Usage(
                prompt_tokens=billed.get("input_tokens", 0),
                completion_tokens=billed.get("output_tokens", 0),
                total_tokens=billed.get("input_tokens", 0) + billed.get("output_tokens", 0),
            )

        return ChatCompletionResponse(
            id=raw.get("id", f"chatcmpl-{uuid.uuid4().hex[:12]}"),
            model=self.map_model(req.model),
            choices=[Choice(
                index=0,
                message={"role": "assistant", "content": text},
                finish_reason=finish_reason,
            )],
            usage=usage,
        )

    def translate_stream_chunk(self, raw_data: str) -> ChatCompletionChunk | None:
        try:
            raw = json.loads(raw_data)
        except json.JSONDecodeError:
            return None

        event_type = raw.get("type")

        # Cohere stream events:
        # "content-delta" → actual token
        # "message-end"   → finish
        # "message-start" → metadata, skip
        if event_type == "content-delta":
            delta = raw.get("delta", {})
            message = delta.get("message", {})
            content_blocks = message.get("content", {})
            text = content_blocks.get("text", "") if isinstance(content_blocks, dict) else ""
            return ChatCompletionChunk(
                id=f"chatcmpl-co-{uuid.uuid4().hex[:8]}",
                model=self.provider_id,
                choices=[Choice(
                    index=0,
                    delta=ChoiceDelta(content=text),
                    finish_reason=None,
                )],
            )

        if event_type == "message-end":
            finish = raw.get("delta", {}).get("finish_reason", "COMPLETE").lower()
            finish_map = {"complete": "stop", "max_tokens": "length"}
            return ChatCompletionChunk(
                id=f"chatcmpl-co",
                model=self.provider_id,
                choices=[Choice(
                    index=0,
                    delta=ChoiceDelta(),
                    finish_reason=finish_map.get(finish, "stop"),
                )],
            )

        return None  # skip message-start and other metadata events

    def parse_rate_limit_headers(self, headers: dict) -> RateLimitInfo:
        # Cohere uses X-RateLimit-* headers
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
