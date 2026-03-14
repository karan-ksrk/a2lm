from dataclasses import dataclass
from app.routing.latency import LatencyTracker
from app.routing.health import HealthTracker
from app.ratelimit.manager import RateLimitManager


@dataclass
class ProviderCandidate:
    provider_id:  str
    native_model: str
    token_key:    str
    api_key:      str
    weight:       int = 100   # operator-assigned static weight


@dataclass
class ScoredCandidate:
    candidate:  ProviderCandidate
    score:      float
    breakdown:  dict   # for observability — shows why a score was given


class CompositeScorer:
    """
    Scores each candidate provider on a 0-100 scale using:

      Score = base_weight
            - latency_penalty     (0-30 pts)  high latency = lower score
            - error_rate_penalty  (0-40 pts)  recent errors = lower score
            + quota_bonus         (0-20 pts)  more quota left = higher score
            + weight_bonus        (0-10 pts)  operator preference

    Providers with open circuits are filtered out before scoring.
    """

    # ── Tunable weights ───────────────────────────────────────────────────────
    MAX_LATENCY_PENALTY = 30.0
    MAX_ERROR_PENALTY = 40.0
    MAX_QUOTA_BONUS = 20.0
    MAX_WEIGHT_BONUS = 10.0

    # Latency above this threshold gets max penalty
    LATENCY_CEILING_MS = 5000.0

    def __init__(
        self,
        latency_tracker: LatencyTracker,
        health_tracker:  HealthTracker,
        rl_manager:      RateLimitManager,
    ):
        self.latency = latency_tracker
        self.health = health_tracker
        self.rl = rl_manager

    async def score(self, candidate: ProviderCandidate) -> ScoredCandidate:
        breakdown = {}

        # ── 1. Latency penalty (0 → -30) ─────────────────────────────────────
        p95_ms = await self.latency.get_p95(candidate.provider_id)
        latency_ratio = min(p95_ms / self.LATENCY_CEILING_MS, 1.0)
        latency_penalty = latency_ratio * self.MAX_LATENCY_PENALTY
        breakdown["p95_ms"] = round(p95_ms, 1)
        breakdown["latency_penalty"] = round(latency_penalty, 2)

        # ── 2. Error rate penalty (0 → -40) ──────────────────────────────────
        error_rate = await self.health.get_error_rate(candidate.provider_id)
        error_penalty = error_rate * self.MAX_ERROR_PENALTY
        breakdown["error_rate"] = round(error_rate, 3)
        breakdown["error_penalty"] = round(error_penalty, 2)

        # ── 3. Quota bonus (0 → +20) ──────────────────────────────────────────
        daily_rem = await self.rl.get_daily_remaining(
            candidate.token_key,
            candidate.provider_id,
            candidate.native_model
        )
        from app.ratelimit.manager import PROVIDER_LIMITS
        provider_limits = PROVIDER_LIMITS.get(candidate.provider_id, {})
        model_limits = provider_limits.get(candidate.native_model) \
            or provider_limits.get("_default") \
            or {"daily": 1}
        daily_limit = model_limits["daily"]
        quota_pct = daily_rem / daily_limit if daily_limit > 0 else 0.0
        quota_bonus = quota_pct * self.MAX_QUOTA_BONUS
        breakdown["daily_remaining"] = daily_rem
        breakdown["daily_pct"] = round(quota_pct, 3)
        breakdown["quota_bonus"] = round(quota_bonus, 2)

        # ── 4. Operator weight bonus (0 → +10) ───────────────────────────────
        weight_bonus = (candidate.weight / 100) * self.MAX_WEIGHT_BONUS
        breakdown["weight"] = candidate.weight
        breakdown["weight_bonus"] = round(weight_bonus, 2)

        # ── Final score ───────────────────────────────────────────────────────
        score = (
            100.0
            - latency_penalty
            - error_penalty
            + quota_bonus
            + weight_bonus
        )
        score = max(0.0, min(score, 130.0))   # clamp to reasonable range
        breakdown["final_score"] = round(score, 2)

        return ScoredCandidate(candidate=candidate, score=score, breakdown=breakdown)

    async def rank(
        self, candidates: list[ProviderCandidate]
    ) -> list[ScoredCandidate]:
        """
        Filter out unhealthy providers, score the rest, return ranked list.
        """
        eligible = []
        for c in candidates:
            # Gate 1: circuit breaker
            if await self.health.is_circuit_open(c.provider_id):
                continue
            # Gate 2: has quota
            has_quota = await self.rl.can_serve(c.token_key, c.provider_id, c.native_model)
            if not has_quota:
                continue
            eligible.append(c)

        if not eligible:
            return []

        scored = [await self.score(c) for c in eligible]
        scored.sort(key=lambda s: s.score, reverse=True)
        return scored
