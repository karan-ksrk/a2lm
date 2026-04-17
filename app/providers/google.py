import json
import uuid
from app.providers.base import BaseProvider
from app.schemas import NormalizedRequest, ChatCompletionResponse, ChatCompletionChunk, Choice, ChoiceDelta, Usage

BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GoogleProvider(BaseProvider):
    def _url(self, model: str, stream: bool) -> str:
        action = "streamGenerateContent" if stream else "generateContent"
        suffix = "&alt=sse" if stream else ""
        return f"{BASE}/{model}:{action}?key={self.api_key}{suffix}"

    def _payload(self, req: NormalizedRequest) -> dict:
        contents = []
        system_instruction = None
        for msg in req.messages:
            role, content = msg["role"], msg["content"]
            if role == "system":
                system_instruction = {"parts": [{"text": content}]}
            elif role == "user":
                contents.append({"role": "user", "parts": [{"text": content}]})
            elif role == "assistant":
                contents.append({"role": "model", "parts": [{"text": content}]})

        payload: dict = {
            "contents": contents,
            "generationConfig": {
                "temperature": req.temperature,
                "maxOutputTokens": req.max_tokens,
            },
        }
        if system_instruction:
            payload["systemInstruction"] = system_instruction
        if req.top_p is not None:
            payload["generationConfig"]["topP"] = req.top_p
        if req.stop:
            stops = [req.stop] if isinstance(req.stop, str) else req.stop
            payload["generationConfig"]["stopSequences"] = stops
        return payload

    async def complete(self, req: NormalizedRequest) -> ChatCompletionResponse:
        r = await self._client.post(
            self._url(req.model, stream=False),
            headers={"Content-Type": "application/json"},
            json=self._payload(req),
        )
        r.raise_for_status()
        raw = r.json()
        choices = []
        for i, c in enumerate(raw.get("candidates", [])):
            text = "".join(p.get("text", "") for p in c.get("content", {}).get("parts", []))
            finish = c.get("finishReason", "stop").lower()
            choices.append(Choice(index=i, message={"role": "assistant", "content": text}, finish_reason=finish))
        u = raw.get("usageMetadata", {})
        usage = Usage(prompt_tokens=u.get("promptTokenCount", 0), completion_tokens=u.get("candidatesTokenCount", 0), total_tokens=u.get("totalTokenCount", 0))
        return ChatCompletionResponse(id=f"chatcmpl-{uuid.uuid4().hex[:12]}", model=req.model, choices=choices, usage=usage)

    async def stream(self, req: NormalizedRequest):
        async with self._client.stream(
            "POST",
            self._url(req.model, stream=True),
            headers={"Content-Type": "application/json"},
            json=self._payload(req),
        ) as r:
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
                for i, c in enumerate(raw.get("candidates", [])):
                    text = "".join(p.get("text", "") for p in c.get("content", {}).get("parts", []))
                    finish = c.get("finishReason")
                    choices.append(Choice(index=i, delta=ChoiceDelta(content=text), finish_reason=finish.lower() if finish else None))
                chunk = ChatCompletionChunk(id=f"chatcmpl-{uuid.uuid4().hex[:8]}", model=req.model, choices=choices)
                yield chunk.to_sse()
