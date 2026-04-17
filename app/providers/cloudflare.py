import json
from app.providers.base import BaseProvider
from app.schemas import NormalizedRequest, ChatCompletionResponse, ChatCompletionChunk, Choice, ChoiceDelta, Usage

BASE = "https://api.cloudflare.com/client/v4/accounts"


class CloudflareProvider(BaseProvider):
    def __init__(self, api_key: str, account_id: str):
        super().__init__(api_key)
        self.account_id = account_id

    def _url(self, model: str) -> str:
        return f"{BASE}/{self.account_id}/ai/run/{model}"

    def _headers(self):
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _payload(self, req: NormalizedRequest) -> dict:
        payload: dict = {
            "messages": req.messages,
            "max_tokens": req.max_tokens,
            "temperature": req.temperature,
            "stream": req.stream,
        }
        if req.top_p is not None:
            payload["top_p"] = req.top_p
        if req.stop:
            payload["stop"] = req.stop if isinstance(req.stop, list) else [req.stop]
        return payload

    async def complete(self, req: NormalizedRequest) -> ChatCompletionResponse:
        r = await self._client.post(self._url(req.model), headers=self._headers(), json=self._payload(req))
        r.raise_for_status()
        result = r.json().get("result", r.json())
        text = result.get("response", "")
        return ChatCompletionResponse(
            id=f"chatcmpl-cf",
            model=req.model,
            choices=[Choice(index=0, message={"role": "assistant", "content": text}, finish_reason="stop")],
            usage=Usage(),
        )

    async def stream(self, req: NormalizedRequest):
        async with self._client.stream("POST", self._url(req.model), headers=self._headers(), json=self._payload(req)) as r:
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
                result = raw.get("result", raw)
                text = result.get("response", "")
                if not text:
                    continue
                chunk = ChatCompletionChunk(
                    id="chatcmpl-cf",
                    model=req.model,
                    choices=[Choice(index=0, delta=ChoiceDelta(content=text))],
                )
                yield chunk.to_sse()
