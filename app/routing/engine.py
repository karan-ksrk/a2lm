import structlog
from app.config import get_settings
from app.ratelimit.manager import RateLimitManager
from app.registry.models import ModelRegistry, build_adapter
from app.models.schemas import NormalizedRequest, ChatCompletionResponse
from app.adapters.base import BaseProviderAdapter

log = structlog.get_logger()


class NoProviderAvailableError(Exception):
    pass


class RoutingEngine:
    """
    For each request:
      1. Resolve model alias → list of (provider, native_model) candidates
      2. For each candidate, check if any token has available quota
      3. Use first available — with fallback to next candidate
      4. Consume quota after dispatching
    """

    def __init__(self, rl_manager: RateLimitManager, registry: ModelRegistry):
        self.rl = rl_manager
        self.registry = registry
        self.settings = get_settings()

        # Pre-build token pools: provider_id → list of (token_key, api_key)
        self._token_pools: dict[str, list[tuple[str, str]]] = {
            "groq":             self._build_pool("groq"),
            "openrouter":       self._build_pool("openrouter"),
            "google_ai_studio": self._build_pool("google_ai_studio"),
            "cerebras":         self._build_pool("cerebras"),

        }

    def _build_pool(self, provider_id: str) -> list[tuple[str, str]]:
        """Build list of (token_key, api_key) for a provider."""
        keys = self.settings.get_keys(provider_id)
        # token_key is a short stable ID for Redis namespacing
        return [(f"{provider_id}:{i}", key) for i, key in enumerate(keys) if key]

    async def select(self, req: NormalizedRequest) -> tuple[BaseProviderAdapter, str, str]:
        """
        Returns (adapter, provider_id, native_model) for the best available slot.
        Raises NoProviderAvailableError if all quota is exhausted.
        """
        candidates = self.registry.get_candidates(req.model)

        for provider_id, native_model in candidates:
            pool = self._token_pools.get(provider_id, [])
            if not pool:
                log.debug("no_tokens_configured", provider=provider_id)
                continue

            for token_key, api_key in pool:
                can = await self.rl.can_serve(token_key, provider_id, native_model)
                if can:
                    adapter = build_adapter(provider_id, api_key)
                    log.info("provider_selected",
                             provider=provider_id,
                             model=native_model,
                             token=token_key)
                    return adapter, token_key, native_model

            log.debug("provider_quota_exhausted", provider=provider_id, model=native_model)

        raise NoProviderAvailableError(
            f"All providers exhausted for model '{req.model}'. "
            "Try again after rate limit windows reset (typically 60s or midnight UTC)."
        )

    async def execute(self, req: NormalizedRequest) -> ChatCompletionResponse:
        adapter, token_key, native_model = await self.select(req)
        provider_id = adapter.provider_id
        try:
            # Mutate model to native before dispatch
            req_copy = req.model_copy(update={"model": native_model})
            response = await adapter.complete(req_copy)
            await self.rl.consume(token_key, provider_id, native_model)
            return response
        except Exception as e:
            log.error("provider_error", provider=provider_id, error=str(e))
            raise

    async def execute_stream(self, req: NormalizedRequest):
        adapter, token_key, native_model = await self.select(req)
        provider_id = adapter.provider_id
        req_copy = req.model_copy(update={"model": native_model, "stream": True})
        try:
            async for chunk in adapter.stream(req_copy):
                yield chunk
            await self.rl.consume(token_key, provider_id, native_model)
        except Exception as e:
            log.error("stream_error", provider=provider_id, error=str(e))
            raise

    async def get_provider_status(self) -> list[dict]:
        """For the /v1/providers status endpoint."""
        status = []
        for provider_id, pool in self._token_pools.items():
            for token_key, _ in pool:
                # Use default model for status check
                from app.ratelimit.manager import PROVIDER_LIMITS
                models = list(PROVIDER_LIMITS.get(provider_id, {}).keys())
                first_model = next((m for m in models if m != "_default"), "_default")
                s = await self.rl.get_status(token_key, provider_id, first_model)
                status.append({
                    "provider": provider_id,
                    "token": token_key,
                    **s
                })
        return status
