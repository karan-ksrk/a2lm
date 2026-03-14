import time
import redis.asyncio as redis
from app.config import get_settings


class HealthTracker:
    """
    Tracks per-provider health using:
    - Sliding window error rate (last 5 minutes)
    - Circuit breaker: auto-disables provider after threshold
    - Consecutive failure counter for fast-fail
    """
    ERROR_WINDOW_SEC = 300   # 5 minute sliding window
    CIRCUIT_OPEN_SEC = 120   # disable provider for 2 min after tripping
    ERROR_RATE_THRESHOLD = 0.4  # trip circuit at 40% error rate
    MIN_REQUESTS = 3     # min requests before circuit can trip

    def __init__(self):
        self._redis: redis.Redis = redis.from_url(
            get_settings().redis_url, decode_responses=True
        )

    # ── Record outcomes ───────────────────────────────────────────────────────

    async def record_success(self, provider_id: str, latency_ms: float = 0):
        now = time.time()
        key = f"health:success:{provider_id}"
        pipe = self._redis.pipeline()
        pipe.zadd(key, {str(now): now})
        pipe.zremrangebyscore(key, "-inf", now - self.ERROR_WINDOW_SEC)
        pipe.expire(key, self.ERROR_WINDOW_SEC + 60)
        await pipe.execute()
        # Reset consecutive failure counter on success
        await self._redis.delete(f"health:consec_fail:{provider_id}")

    async def record_failure(self, provider_id: str, status_code: int = 0):
        now = time.time()
        err_key = f"health:error:{provider_id}"
        consec_key = f"health:consec_fail:{provider_id}"

        pipe = self._redis.pipeline()
        pipe.zadd(err_key, {str(now): now})
        pipe.zremrangebyscore(err_key, "-inf", now - self.ERROR_WINDOW_SEC)
        pipe.expire(err_key, self.ERROR_WINDOW_SEC + 60)
        pipe.incr(consec_key)
        pipe.expire(consec_key, self.CIRCUIT_OPEN_SEC)
        await pipe.execute()

        # Check if circuit should trip
        await self._maybe_trip_circuit(provider_id)

    # ── Circuit breaker ───────────────────────────────────────────────────────

    async def _maybe_trip_circuit(self, provider_id: str):
        error_rate = await self.get_error_rate(provider_id)
        total = await self.get_total_requests(provider_id)
        consec = await self.get_consecutive_failures(provider_id)

        should_trip = (
            (total >= self.MIN_REQUESTS and error_rate >= self.ERROR_RATE_THRESHOLD)
            or consec >= 5  # always trip after 5 consecutive failures
        )
        if should_trip:
            await self._redis.setex(
                f"health:circuit_open:{provider_id}",
                self.CIRCUIT_OPEN_SEC,
                "1"
            )

    async def is_circuit_open(self, provider_id: str) -> bool:
        """True = provider is disabled (circuit tripped)."""
        return bool(await self._redis.get(f"health:circuit_open:{provider_id}"))

    async def reset_circuit(self, provider_id: str):
        """Manually re-enable a provider."""
        await self._redis.delete(f"health:circuit_open:{provider_id}")

    # ── Metrics ───────────────────────────────────────────────────────────────

    async def get_error_rate(self, provider_id: str) -> float:
        now = time.time()
        window_start = now - self.ERROR_WINDOW_SEC

        pipe = self._redis.pipeline()
        pipe.zcount(f"health:error:{provider_id}", window_start, now)
        pipe.zcount(f"health:success:{provider_id}", window_start, now)
        errors, successes = await pipe.execute()

        total = errors + successes
        return errors / total if total > 0 else 0.0

    async def get_total_requests(self, provider_id: str) -> int:
        now = time.time()
        window_start = now - self.ERROR_WINDOW_SEC
        pipe = self._redis.pipeline()
        pipe.zcount(f"health:error:{provider_id}", window_start, now)
        pipe.zcount(f"health:success:{provider_id}", window_start, now)
        errors, successes = await pipe.execute()
        return errors + successes

    async def get_consecutive_failures(self, provider_id: str) -> int:
        val = await self._redis.get(f"health:consec_fail:{provider_id}")
        return int(val) if val else 0

    async def get_all(self, provider_id: str) -> dict:
        circuit_open = await self.is_circuit_open(provider_id)
        error_rate = await self.get_error_rate(provider_id)
        consec = await self.get_consecutive_failures(provider_id)
        return {
            "circuit_open":           circuit_open,
            "error_rate_5min":        round(error_rate, 3),
            "consecutive_failures":   consec,
            "healthy": not circuit_open and error_rate < self.ERROR_RATE_THRESHOLD,
        }

    async def close(self):
        await self._redis.aclose()
