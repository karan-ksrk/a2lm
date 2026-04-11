import time
import structlog
from app.config import get_settings
from app.ratelimit.manager import RateLimitManager
from app.registry.models import ModelRegistry, build_adapter
from app.models.schemas import NormalizedRequest, ChatCompletionResponse
from app.routing.latency import LatencyTracker
from app.routing.health import HealthTracker
from app.routing.scorer import CompositeScorer, ProviderCandidate
from app.adapters.base import BaseProviderAdapter

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

        # Pre-built adapters keyed by token_key — one httpx client per key, reused across requests
        self._adapters: dict[str, BaseProviderAdapter] = {
            token_key: build_adapter(provider_id, api_key)
            for provider_id, pool in self._token_pools.items()
            for token_key, api_key in pool
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

    async def _rank(self, model: str):
        """Score and rank all candidates. Raises NoProviderAvailableError if none available."""
        candidates = self._build_candidates(model)
        ranked = await self.scorer.rank(candidates)
        if not ranked:
            raise NoProviderAvailableError(
                f"All providers exhausted for '{model}'. "
                "Retry after 60s or check /v1/providers for quota status."
            )
        return ranked

    # ── Execute with fallback retry ───────────────────────────────────────────

    async def execute(self, req: NormalizedRequest) -> ChatCompletionResponse:
        ranked = await self._rank(req.model)
        last_error: Exception | None = None

        for scored in ranked:
            c = scored.candidate
            adapter = self._adapters[c.token_key]
            start = time.monotonic()
            log.info(
                "provider_selected",
                provider=c.provider_id,
                model=c.native_model,
                score=scored.breakdown["final_score"],
                p95_ms=scored.breakdown["p95_ms"],
                error_rate=scored.breakdown["error_rate"],
                quota_pct=scored.breakdown["daily_pct"],
            )
            try:
                req_copy = req.model_copy(update={"model": c.native_model})
                response = await adapter.complete(req_copy)
                elapsed_ms = (time.monotonic() - start) * 1000
                await self.latency.record(c.provider_id, elapsed_ms)
                await self.health.record_success(c.provider_id, elapsed_ms)
                await self.rl.consume(c.token_key, c.provider_id, c.native_model)
                return response
            except Exception as e:
                elapsed_ms = (time.monotonic() - start) * 1000
                await self.health.record_failure(c.provider_id)
                log.error("provider_error", provider=c.provider_id, error=str(e), latency_ms=elapsed_ms)
                last_error = e

        raise NoProviderAvailableError(
            f"All providers failed for '{req.model}'."
        ) from last_error

    async def execute_stream(self, req: NormalizedRequest):
        ranked = await self._rank(req.model)
        last_error: Exception | None = None

        for scored in ranked:
            c = scored.candidate
            adapter = self._adapters[c.token_key]
            start = time.monotonic()
            req_copy = req.model_copy(update={"model": c.native_model, "stream": True})

            stream_iter = adapter.stream(req_copy).__aiter__()
            try:
                first = await stream_iter.__anext__()
            except StopAsyncIteration:
                # Empty stream — still counts as success
                elapsed_ms = (time.monotonic() - start) * 1000
                await self.latency.record(c.provider_id, elapsed_ms)
                await self.health.record_success(c.provider_id, elapsed_ms)
                await self.rl.consume(c.token_key, c.provider_id, c.native_model)
                return
            except Exception as e:
                await stream_iter.aclose()
                elapsed_ms = (time.monotonic() - start) * 1000
                await self.health.record_failure(c.provider_id)
                log.error("stream_error", provider=c.provider_id, error=str(e))
                last_error = e
                continue

            # Provider responded — committed to this stream, no more fallback
            elapsed_ms = (time.monotonic() - start) * 1000
            await self.latency.record(c.provider_id, elapsed_ms)
            await self.health.record_success(c.provider_id, elapsed_ms)
            await self.rl.consume(c.token_key, c.provider_id, c.native_model)
            yield first
            async for chunk in stream_iter:
                yield chunk
            return

        raise NoProviderAvailableError(
            f"All providers failed for '{req.model}'."
        ) from last_error

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
        for adapter in self._adapters.values():
            await adapter.close()
        await self.latency.close()
        await self.health.close()
        await self.rl.close()
