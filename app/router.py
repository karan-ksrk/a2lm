import json
import logging
from fastapi import HTTPException

from app.schemas import NormalizedRequest, ChatCompletionResponse
from app.priorities.aliases import PRIORITIES

log = logging.getLogger(__name__)


class Router:
    def __init__(self, providers: dict):
        self._providers = providers  # name → provider instance

    async def complete(self, req: NormalizedRequest) -> ChatCompletionResponse:
        candidates = PRIORITIES.get(req.model)
        if not candidates:
            raise HTTPException(400, f"Unknown alias '{req.model}'. Valid: {list(PRIORITIES)}")

        last_error = None
        for provider_name, native_model in candidates:
            provider = self._providers.get(provider_name)
            if not provider:
                log.debug(f"skip {provider_name} — no key configured")
                continue
            try:
                routed = req.model_copy(update={"model": native_model})
                result = await provider.complete(routed)
                log.info(f"served alias={req.model} via {provider_name}/{native_model}")
                return result
            except Exception as e:
                log.warning(f"provider_failed alias={req.model} provider={provider_name} model={native_model} error={e}")
                last_error = e

        raise HTTPException(503, detail=f"All providers failed for '{req.model}'. Last: {last_error}")

    async def stream(self, req: NormalizedRequest):
        # Caller must pre-validate alias — raising HTTPException inside an async
        # generator breaks StreamingResponse. This generator never raises.
        candidates = PRIORITIES.get(req.model, [])
        last_error = None

        for provider_name, native_model in candidates:
            provider = self._providers.get(provider_name)
            if not provider:
                log.debug(f"skip {provider_name} — no key configured")
                continue
            try:
                routed = req.model_copy(update={"model": native_model, "stream": True})
                async for chunk in provider.stream(routed):
                    yield chunk
                log.info(f"served alias={req.model} via {provider_name}/{native_model} (stream)")
                return
            except Exception as e:
                log.warning(f"provider_failed alias={req.model} provider={provider_name} model={native_model} error={e}")
                last_error = e

        # All failed — yield SSE error so client gets a readable message
        error_payload = json.dumps({"error": {"message": f"All providers failed for '{req.model}'. Last: {last_error}", "type": "gateway_error"}})
        yield f"data: {error_payload}\n\n"
        yield "data: [DONE]\n\n"

    def list_models(self) -> list[dict]:
        import time
        ts = int(time.time())
        return [{"id": alias, "object": "model", "created": ts, "owned_by": "a2lm"} for alias in PRIORITIES]

    async def close(self):
        for provider in self._providers.values():
            await provider.close()
