import time
import redis.asyncio as redis
from app.config import get_settings


class LatencyTracker:
    """
    Tracks per-provider latency using:
    - EMA (Exponential Moving Average) for smooth trending
    - Sorted set of last 100 samples for P95 calculation
    """
    ALPHA = 0.2          # EMA smoothing — higher = more reactive to recent changes
    HISTORY_SIZE = 100   # samples kept per provider for percentile calc

    def __init__(self):
        self._redis: redis.Redis = redis.from_url(
            get_settings().redis_url, decode_responses=True
        )

    async def record(self, provider_id: str, latency_ms: float):
        """Record a completed request latency for a provider."""
        ema_key = f"latency:ema:{provider_id}"
        hist_key = f"latency:hist:{provider_id}"
        now = time.time()

        pipe = self._redis.pipeline()

        # Update EMA
        current_ema = await self._redis.get(ema_key)
        if current_ema is None:
            new_ema = latency_ms
        else:
            new_ema = self.ALPHA * latency_ms + (1 - self.ALPHA) * float(current_ema)
        pipe.setex(ema_key, 3600, new_ema)

        # Add to history sorted set (score = timestamp, member = latency:timestamp)
        member = f"{latency_ms}:{now}"
        pipe.zadd(hist_key, {member: now})

        # Keep only last N samples
        pipe.zremrangebyrank(hist_key, 0, -(self.HISTORY_SIZE + 1))
        pipe.expire(hist_key, 3600)

        await pipe.execute()

    async def get_ema(self, provider_id: str) -> float:
        """Returns EMA latency in ms. Defaults to 999ms if no data."""
        val = await self._redis.get(f"latency:ema:{provider_id}")
        return float(val) if val else 999.0

    async def get_p95(self, provider_id: str) -> float:
        """Returns P95 latency from history. Defaults to 999ms if no data."""
        key = f"latency:hist:{provider_id}"
        members = await self._redis.zrange(key, 0, -1)
        if not members:
            return 999.0
        latencies = sorted([float(m.split(":")[0]) for m in members])
        idx = int(len(latencies) * 0.95)
        return latencies[min(idx, len(latencies) - 1)]

    async def get_all(self, provider_id: str) -> dict:
        return {
            "ema_ms": await self.get_ema(provider_id),
            "p95_ms": await self.get_p95(provider_id),
        }

    async def close(self):
        await self._redis.aclose()
