import time
import structlog
from app.config import get_settings
from app.ratelimit.manager import RateLimitManager
from app.registry.models import ModelRegistry, build_adapter, ALIAS_PRIORITY
from app.models.schemas import NormalizedRequest, ChatCompletionResponse
from app.routing.latency import LatencyTracker
from app.routing.health import HealthTracker
from app.routing.scorer import CompositeScorer, ProviderCandidate

log = structlog.get_logger()


class NoProviderAvailableError(Exception):
    pass


class RoutingEngine:
    def __init__(self, rl_manager: RateLimitManager, registry: ModelRegistry):
        self.rl = rl_manager
        self.registry = registry
        self.settings = get_settings()

        # Instantiate tracking modules
        self.latency = LatencyTracker()
        self.health = HealthTracker()
        self.scorer = CompositeScorer(
            latency_tracker=self.latency,
            health_tracker=self.health,
            rl_manager=self.rl,
        )

        # Token pools: provider_id → [(token_key, api_key), ...]
        self._token_pools: dict[str, list[tuple[str, str]]] = {
            "groq":             self._build_pool("groq"),
            "openrouter":       self._build_pool("openrouter"),
            "google_ai_studio": self._build_pool("google_ai_studio"),
            "cerebras":         self._build_pool("cerebras"),
            "cloudflare":       self._build_pool("cloudflare"),
            "cohere":           self._build_pool("cohere"),
            "mistral":          self._build_pool("mistral"),
            "nvidia":           self._build_pool("nvidia"),
        }

    def _build_pool(self, provider_id: str) -> list[tuple[str, str]]:
        keys = self.settings.get_keys(provider_id)
        return [(f"{provider_id}:{i}", key) for i, key in enumerate(keys) if key]

    # ── Build candidates list ─────────────────────────────────────────────────

    def _build_candidates(self, model_alias: str) -> list[ProviderCandidate]:
        """
        Expand a model alias into all possible (provider, model, token) combinations.
        Each token for a provider = separate candidate (different quota buckets).
        """
        priority_list = self.registry.get_candidates(model_alias)
        candidates = []
        for provider_id, native_model in priority_list:
            pool = self._token_pools.get(provider_id, [])
            model_info = next(
                (m for m in self.registry._models.values()
                 if m.provider_id == provider_id and m.native_id == native_model),
                None
            )
            weight = model_info.weight if model_info else 100
            for token_key, api_key in pool:
                candidates.append(ProviderCandidate(
                    provider_id=provider_id,
                    native_model=native_model,
                    token_key=token_key,
                    api_key=api_key,
                    weight=weight,
                ))
        return candidates

    # ── Core select ───────────────────────────────────────────────────────────

    async def select(self, req: NormalizedRequest):
        """
        Returns the top-scored available (adapter, token_key, native_model).
        Raises NoProviderAvailableError if nothing is available.
        """
        candidates = self._build_candidates(req.model)
        ranked = await self.scorer.rank(candidates)

        if not ranked:
            raise NoProviderAvailableError(
                f"All providers exhausted for '{req.model}'. "
                "Retry after 60s or check /v1/providers for quota status."
            )

        best = ranked[0]
        log.info(
            "provider_selected",
            provider=best.candidate.provider_id,
            model=best.candidate.native_model,
            score=best.breakdown["final_score"],
            p95_ms=best.breakdown["p95_ms"],
            error_rate=best.breakdown["error_rate"],
            quota_pct=best.breakdown["daily_pct"],
        )
        adapter = build_adapter(best.candidate.provider_id, best.candidate.api_key)
        return adapter, best.candidate.token_key, best.candidate.native_model

    # ── Execute with observability ────────────────────────────────────────────

    async def execute(self, req: NormalizedRequest) -> ChatCompletionResponse:
        adapter, token_key, native_model = await self.select(req)
        provider_id = adapter.provider_id
        start = time.monotonic()
        try:
            req_copy = req.model_copy(update={"model": native_model})
            response = await adapter.complete(req_copy)

            elapsed_ms = (time.monotonic() - start) * 1000
            await self.latency.record(provider_id, elapsed_ms)
            await self.health.record_success(provider_id, elapsed_ms)
            await self.rl.consume(token_key, provider_id, native_model)

            return response

        except Exception as e:
            elapsed_ms = (time.monotonic() - start) * 1000
            await self.health.record_failure(provider_id)
            log.error("provider_error", provider=provider_id, error=str(e), latency_ms=elapsed_ms)
            raise

    async def execute_stream(self, req: NormalizedRequest):
        adapter, token_key, native_model = await self.select(req)
        provider_id = adapter.provider_id
        start = time.monotonic()
        req_copy = req.model_copy(update={"model": native_model, "stream": True})
        try:
            async for chunk in adapter.stream(req_copy):
                yield chunk
            elapsed_ms = (time.monotonic() - start) * 1000
            await self.latency.record(provider_id, elapsed_ms)
            await self.health.record_success(provider_id, elapsed_ms)
            await self.rl.consume(token_key, provider_id, native_model)
        except Exception as e:
            await self.health.record_failure(provider_id)
            log.error("stream_error", provider=provider_id, error=str(e))
            raise

    # ── Status endpoint ───────────────────────────────────────────────────────

    async def get_provider_status(self) -> list[dict]:
        status = []
        for provider_id, pool in self._token_pools.items():
            if not pool:
                continue
            from app.ratelimit.manager import PROVIDER_LIMITS
            models = [
                m for m in PROVIDER_LIMITS.get(provider_id, {}).keys()
                if m != "_default"
            ]
            native_model = models[0] if models else "_default"

            for token_key, _ in pool:
                rl = await self.rl.get_status(token_key, provider_id, native_model)
                health = await self.health.get_all(provider_id)
                lat = await self.latency.get_all(provider_id)
                status.append({
                    "provider":  provider_id,
                    "token":     token_key,
                    **rl,
                    **health,
                    **lat,
                })
        return status

    async def close(self):
        await self.latency.close()
        await self.health.close()
        await self.rl.close()
