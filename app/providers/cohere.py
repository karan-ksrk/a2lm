import json
import uuid
from app.providers.base import BaseProvider
from app.schemas import NormalizedRequest, ChatCompletionResponse, ChatCompletionChunk, Choice, ChoiceDelta, Usage

URL = "https://api.cohere.com/v2/chat"

_FINISH_MAP = {"complete": "stop", "max_tokens": "length", "error": "stop"}


class CohereProvider(BaseProvider):
    def _headers(self):
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _payload(self, req: NormalizedRequest) -> dict:
        messages = [m for m in req.messages if m["role"] != "system"]
        system_parts = [m["content"] for m in req.messages if m["role"] == "system"]

        payload: dict = {
            "model": req.model,
            "messages": messages,
            "max_tokens": req.max_tokens,
            "temperature": req.temperature,
            "stream": req.stream,
        }
        if system_parts:
            payload["system"] = " ".join(system_parts)
        if req.top_p is not None:
            payload["p"] = req.top_p
        if req.stop:
            payload["stop_sequences"] = [req.stop] if isinstance(req.stop, str) else req.stop
        return payload

    async def complete(self, req: NormalizedRequest) -> ChatCompletionResponse:
        r = await self._client.post(URL, headers=self._headers(), json=self._payload(req))
        r.raise_for_status()
        raw = r.json()
        content_blocks = raw.get("message", {}).get("content", [])
        text = "".join(b.get("text", "") for b in content_blocks if b.get("type") == "text")
        finish = _FINISH_MAP.get(raw.get("finish_reason", "COMPLETE").lower(), "stop")
        usage = None
        if u := raw.get("usage", {}).get("billed_units"):
            usage = Usage(prompt_tokens=u.get("input_tokens", 0), completion_tokens=u.get("output_tokens", 0), total_tokens=u.get("input_tokens", 0) + u.get("output_tokens", 0))
        return ChatCompletionResponse(
            id=raw.get("id", f"chatcmpl-{uuid.uuid4().hex[:12]}"),
            model=req.model,
            choices=[Choice(index=0, message={"role": "assistant", "content": text}, finish_reason=finish)],
            usage=usage,
        )

    async def stream(self, req: NormalizedRequest):
        async with self._client.stream("POST", URL, headers=self._headers(), json=self._payload(req)) as r:
            r.raise_for_status()
            async for line in r.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data == "[DONE]":
                    yield "data: [DONE]\n\n"
                    return
                try:
                    raw = json.loads(data)
                except json.JSONDecodeError:
                    continue
                event = raw.get("type")
                if event == "content-delta":
                    content = raw.get("delta", {}).get("message", {}).get("content", {})
                    text = content.get("text", "") if isinstance(content, dict) else ""
                    chunk = ChatCompletionChunk(
                        id=f"chatcmpl-co-{uuid.uuid4().hex[:8]}",
                        model=req.model,
                        choices=[Choice(index=0, delta=ChoiceDelta(content=text))],
                    )
                    yield chunk.to_sse()
                elif event == "message-end":
                    finish = _FINISH_MAP.get(raw.get("delta", {}).get("finish_reason", "COMPLETE").lower(), "stop")
                    chunk = ChatCompletionChunk(
                        id="chatcmpl-co",
                        model=req.model,
                        choices=[Choice(index=0, delta=ChoiceDelta(), finish_reason=finish)],
                    )
                    yield chunk.to_sse()
                    yield "data: [DONE]\n\n"
                    return
