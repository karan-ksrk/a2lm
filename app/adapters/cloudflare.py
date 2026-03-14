import json
from app.adapters.base import BaseProviderAdapter
from app.models.schemas import (
    NormalizedRequest, ChatCompletionResponse,
    ChatCompletionChunk, Choice, ChoiceDelta, Usage
)


class CloudflareAdapter(BaseProviderAdapter):
    provider_id = "cloudflare"
    # base_url built dynamically using account_id + model
    base_url = "https://api.cloudflare.com/client/v4/accounts"

    # Gateway alias -> Cloudflare native model string
    model_map = {
        "llama-70b":    "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
        "llama-8b":     "@cf/meta/llama-3.2-3b-instruct",
        "llama-11b-v":  "@cf/meta/llama-3.2-11b-vision-instruct",
        "gemma-12b":    "@cf/google/gemma-3-12b-it",
        "qwen-32b":     "@cf/qwen/qwen3-30b-a3b-fp8",
        "qwq-32b":      "@cf/qwen/qwq-32b",
        "deepseek-r1":  "@cf/deepseek-ai/deepseek-r1-distill-qwen-32b",
        "mistral-7b":   "@cf/mistral/mistral-7b-instruct-v0.2",
        "phi-4-mini":   "@cf/microsoft/phi-4-mini-instruct",
        "fast":         "@cf/meta/llama-3.2-3b-instruct",
        "auto":         "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
        "smart":        "@cf/qwen/qwq-32b",
    }

    def __init__(self, api_key: str, account_id: str):
        super().__init__(api_key)
        self.account_id = account_id

    def _get_url(self, native_model: str, stream: bool) -> str:
        return (
            f"{self.base_url}/{self.account_id}/ai/run/{native_model}"
        )

    def build_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def get_chat_url(self) -> str:
        # Not used directly — URL is built per-request in complete/stream
        return ""

    def translate_request(self, req: NormalizedRequest) -> dict:
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

    def translate_response(self, raw: dict, req: NormalizedRequest) -> ChatCompletionResponse:
        # Cloudflare wraps response in {"success": true, "result": {...}}
        result = raw.get("result", raw)
        response_text = result.get("response", "")
        return ChatCompletionResponse(
            id=f"chatcmpl-cf-{req.request_id}",
            model=req.model,
            choices=[Choice(
                index=0,
                message={"role": "assistant", "content": response_text},
                finish_reason="stop",
            )],
            usage=Usage(),  # CF doesn't return token counts
        )

    def translate_stream_chunk(self, raw_data: str) -> ChatCompletionChunk | None:
        try:
            raw = json.loads(raw_data)
        except json.JSONDecodeError:
            return None
        # Cloudflare stream: {"response": "token"} per chunk
        result = raw.get("result", raw)
        text = result.get("response", "")
        if not text:
            return None
        return ChatCompletionChunk(
            id=f"chatcmpl-cf",
            model=self.provider_id,
            choices=[Choice(
                index=0,
                delta=ChoiceDelta(content=text),
                finish_reason=None,
            )],
        )

    # ── Override complete/stream to use dynamic URL ───────────────────────────

    async def complete(self, req: NormalizedRequest) -> ChatCompletionResponse:
        native = self.map_model(req.model)
        url = self._get_url(native, stream=False)
        payload = self.translate_request(req)
        response = await self._client.post(url, headers=self.build_headers(), json=payload)
        response.raise_for_status()
        return self.translate_response(response.json(), req)

    async def stream(self, req: NormalizedRequest):
        native = self.map_model(req.model)
        url = self._get_url(native, stream=True)
        payload = self.translate_request(req)
        async with self._client.stream(
            "POST", url, headers=self.build_headers(), json=payload
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.strip():
                    continue
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        yield "data: [DONE]\n\n"
                        return
                    chunk = self.translate_stream_chunk(data)
                    if chunk:
                        yield f"data: {chunk.model_dump_json()}\n\n"
