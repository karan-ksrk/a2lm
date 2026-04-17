import json
from app.providers.base import BaseProvider
from app.schemas import NormalizedRequest, ChatCompletionResponse, ChatCompletionChunk, Choice, ChoiceDelta, Usage

URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqProvider(BaseProvider):
    def _headers(self):
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _payload(self, req: NormalizedRequest) -> dict:
        payload: dict = {
            "model": req.model,
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

    async def complete(self, req: NormalizedRequest) -> ChatCompletionResponse:
        r = await self._client.post(URL, headers=self._headers(), json=self._payload(req))
        r.raise_for_status()
        raw = r.json()
        choices = [
            Choice(index=c["index"], message=c.get("message"), finish_reason=c.get("finish_reason"))
            for c in raw.get("choices", [])
        ]
        usage = None
        if u := raw.get("usage"):
            usage = Usage(prompt_tokens=u["prompt_tokens"], completion_tokens=u["completion_tokens"], total_tokens=u["total_tokens"])
        return ChatCompletionResponse(id=raw.get("id", "chatcmpl-groq"), model=raw.get("model", req.model), choices=choices, usage=usage)

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
                choices = []
                for c in raw.get("choices", []):
                    delta = c.get("delta", {})
                    choices.append(Choice(index=c["index"], delta=ChoiceDelta(role=delta.get("role"), content=delta.get("content")), finish_reason=c.get("finish_reason")))
                chunk = ChatCompletionChunk(id=raw.get("id", "chunk"), model=raw.get("model", req.model), choices=choices)
                yield chunk.to_sse()
