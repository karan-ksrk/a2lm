import json
import uuid
from app.adapters.base import BaseProviderAdapter
from app.models.schemas import (
    NormalizedRequest, ChatCompletionResponse,
    ChatCompletionChunk, Choice, ChoiceDelta, Usage, RateLimitInfo
)


class GoogleAIStudioAdapter(BaseProviderAdapter):
    provider_id = "google_ai_studio"
    base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    model_map = {
        "gemini-flash":     "gemini-2.5-flash",
        "gemini-flash-lite":"gemini-2.5-flash-lite",
        "gemma-27b":        "gemma-3-27b-it",
        "gemma-12b":        "gemma-3-12b-it",
        "gemma-4b":         "gemma-3-4b-it",
        "gemma-1b":         "gemma-3-1b-it",
        "auto":             "gemma-3-27b-it",
        "smart":            "gemini-2.5-flash",
        "fast":             "gemma-3-4b-it",
    }

    def build_headers(self) -> dict:
        # Google AI Studio uses API key as query param, not header
        return {"Content-Type": "application/json"}

    def get_chat_url(self) -> str:
        # placeholder — overridden per-request
        return ""

    def _get_url(self, model_alias: str, stream: bool) -> str:
        native = self.map_model(model_alias)
        action = "streamGenerateContent" if stream else "generateContent"
        suffix = "?alt=sse" if stream else ""
        return f"{self.base_url}/{native}:{action}?key={self.api_key}{suffix.replace('?', '&')}"

    def translate_request(self, req: NormalizedRequest) -> dict:
        contents = []
        system_instruction = None

        for msg in req.messages:
            role = msg["role"]
            content = msg["content"]
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
            }
        }
        if system_instruction:
            payload["systemInstruction"] = system_instruction
        if req.top_p is not None:
            payload["generationConfig"]["topP"] = req.top_p
        if req.stop:
            stops = [req.stop] if isinstance(req.stop, str) else req.stop
            payload["generationConfig"]["stopSequences"] = stops

        return payload

    def translate_response(self, raw: dict, req: NormalizedRequest) -> ChatCompletionResponse:
        candidates = raw.get("candidates", [])
        choices = []
        for i, c in enumerate(candidates):
            parts = c.get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts)
            finish = c.get("finishReason", "stop").lower()
            choices.append(Choice(
                index=i,
                message={"role": "assistant", "content": text},
                finish_reason=finish,
            ))
        usage_meta = raw.get("usageMetadata", {})
        usage = Usage(
            prompt_tokens=usage_meta.get("promptTokenCount", 0),
            completion_tokens=usage_meta.get("candidatesTokenCount", 0),
            total_tokens=usage_meta.get("totalTokenCount", 0),
        )
        return ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:12]}",
            model=self.map_model(req.model),
            choices=choices,
            usage=usage,
        )

    def translate_stream_chunk(self, raw_data: str) -> ChatCompletionChunk | None:
        try:
            raw = json.loads(raw_data)
        except json.JSONDecodeError:
            return None
        candidates = raw.get("candidates", [])
        choices = []
        for i, c in enumerate(candidates):
            parts = c.get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts)
            finish = c.get("finishReason")
            choices.append(Choice(
                index=i,
                delta=ChoiceDelta(content=text),
                finish_reason=finish.lower() if finish else None,
            ))
        return ChatCompletionChunk(
            id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
            model=self.provider_id,
            choices=choices,
        )

    def parse_rate_limit_headers(self, headers: dict) -> RateLimitInfo:
        # Google doesn't expose RL headers — we track limits manually
        return RateLimitInfo()

    # ── Override complete/stream to use dynamic URL ──

    async def complete(self, req: NormalizedRequest):
        import httpx
        payload = self.translate_request(req)
        url = self._get_url(req.model, stream=False)
        response = await self._client.post(url, headers=self.build_headers(), json=payload)
        response.raise_for_status()
        return self.translate_response(response.json(), req)

    async def stream(self, req: NormalizedRequest):
        import httpx
        payload = self.translate_request(req)
        url = self._get_url(req.model, stream=True)
        async with self._client.stream("POST", url, headers=self.build_headers(), json=payload) as response:
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
