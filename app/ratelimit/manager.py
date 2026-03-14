import time
import redis.asyncio as redis
from app.config import get_settings

# ── Per-provider hard rate limits (free tier defaults) ────────────────────────
PROVIDER_LIMITS = {
    "groq": {
        "llama-3.1-8b-instant":     {"rpm": 30, "daily": 14400},
        "llama-3.3-70b-versatile":  {"rpm": 30, "daily": 1000},
        "llama-3.3-70b-specdec":    {"rpm": 30, "daily": 1000},
        "moonshotai/kimi-k2-instruct": {"rpm": 30, "daily": 1000},
        "qwen/qwen3-32b":           {"rpm": 30, "daily": 1000},
        "_default":                 {"rpm": 30, "daily": 1000},
    },
    "openrouter": {
        "_default": {"rpm": 20, "daily": 50},   # base free; 1000/day with $10 topup
    },
    "google_ai_studio": {
        "gemini-2.5-flash":     {"rpm": 5,  "daily": 20},
        "gemini-2.5-flash-lite": {"rpm": 10, "daily": 20},
        "gemma-3-27b-it":       {"rpm": 30, "daily": 14400},
        "gemma-3-12b-it":       {"rpm": 30, "daily": 14400},
        "gemma-3-4b-it":        {"rpm": 30, "daily": 14400},
        "gemma-3-1b-it":        {"rpm": 30, "daily": 14400},
        "_default":             {"rpm": 10, "daily": 1000},
    },
    "cerebras": {
        "llama-3.3-70b":    {"rpm": 30, "daily": 14400},
        "llama-3.1-8b":     {"rpm": 30, "daily": 14400},
        "qwen-3-235b":      {"rpm": 30, "daily": 14400},
        "qwen-3-32b":       {"rpm": 30, "daily": 14400},
        "_default":         {"rpm": 30, "daily": 14400},
    },
    "cloudflare": {
        # Cloudflare bills by "neurons" not requests — 10,000/day free
        # Roughly ~500 req/day for 70B, ~2000 req/day for small models
        "@cf/meta/llama-3.3-70b-instruct-fp8-fast": {"rpm": 60, "daily": 500},
        "@cf/meta/llama-3.2-3b-instruct":           {"rpm": 60, "daily": 2000},
        "@cf/qwen/qwq-32b":                          {"rpm": 60, "daily": 300},
        "@cf/qwen/qwen3-30b-a3b-fp8":               {"rpm": 60, "daily": 500},
        "@cf/deepseek-ai/deepseek-r1-distill-qwen-32b": {"rpm": 60, "daily": 500},
        "@cf/google/gemma-3-12b-it":                {"rpm": 60, "daily": 800},
        "@cf/mistral/mistral-7b-instruct-v0.2":     {"rpm": 60, "daily": 1500},
        "@cf/microsoft/phi-4-mini-instruct":        {"rpm": 60, "daily": 1500},
        "_default":                                 {"rpm": 60, "daily": 500},
    },
    "cohere": {
        # Free tier: 20 RPM shared, 1,000 req/month total across all models
        "command-a-03-2025":      {"rpm": 20, "daily": 33},   # ~1000/month ÷ 30 days
        "command-r-08-2024":      {"rpm": 20, "daily": 33},
        "command-r-plus-08-2024": {"rpm": 20, "daily": 33},
        "command-r7b-12-2024":    {"rpm": 20, "daily": 33},
        "c4ai-aya-expanse-32b":   {"rpm": 20, "daily": 33},
        "c4ai-aya-expanse-8b":    {"rpm": 20, "daily": 33},
        "_default":               {"rpm": 20, "daily": 33},
    },
    "mistral": {
        # Free tier (Experiment plan): 1 req/sec = ~60 RPM, 500K TPM, 1B tokens/month
        # ~33,000 req/day assuming avg 1,000 tokens/request
        "mistral-small-latest":  {"rpm": 60, "daily": 33000},
        "mistral-medium-latest": {"rpm": 60, "daily": 33000},
        "mistral-large-latest":  {"rpm": 60, "daily": 33000},
        "codestral-latest":      {"rpm": 60, "daily": 33000},
        "open-mixtral-8x7b":     {"rpm": 60, "daily": 33000},
        "open-mixtral-8x22b":    {"rpm": 60, "daily": 33000},
        "open-mistral-7b":       {"rpm": 60, "daily": 33000},
        "open-mistral-nemo":     {"rpm": 60, "daily": 33000},
        "_default":              {"rpm": 60, "daily": 33000},
    },
    "nvidia": {
        # Free tier: 40 RPM shared across all models
        # No published daily limit — treating as generous but conservative estimate
        "meta/llama-3.3-70b-instruct":              {"rpm": 40, "daily": 5000},
        "meta/llama-3.1-8b-instruct":               {"rpm": 40, "daily": 5000},
        "meta/llama-3.1-405b-instruct":             {"rpm": 40, "daily": 5000},
        "deepseek-ai/deepseek-r1":                  {"rpm": 40, "daily": 5000},
        "qwen/qwen2.5-72b-instruct":                {"rpm": 40, "daily": 5000},
        "qwen/qwen2.5-coder-32b-instruct":          {"rpm": 40, "daily": 5000},
        "mistralai/mistral-nemo-12b-instruct":      {"rpm": 40, "daily": 5000},
        "microsoft/phi-4-mini-instruct":            {"rpm": 40, "daily": 5000},
        "google/gemma-3-27b-it":                    {"rpm": 40, "daily": 5000},
        "nvidia/llama-3.1-nemotron-70b-instruct":   {"rpm": 40, "daily": 5000},
        "_default":                                 {"rpm": 40, "daily": 5000},
    },
}


class RateLimitManager:
    def __init__(self):
        settings = get_settings()
        self._redis: redis.Redis = redis.from_url(settings.redis_url, decode_responses=True)

    async def close(self):
        await self._redis.aclose()

    def _limits(self, provider_id: str, native_model: str) -> dict:
        provider = PROVIDER_LIMITS.get(provider_id, {})
        return provider.get(native_model) or provider.get("_default") or {"rpm": 10, "daily": 100}

    # ── RPM Sliding Window ────────────────────────────────────────────────────

    async def check_rpm(self, token_key: str, provider_id: str, native_model: str) -> bool:
        """Returns True if a request can be made (not yet at RPM limit)."""
        limits = self._limits(provider_id, native_model)
        rpm_limit = limits["rpm"]
        key = f"rl:{token_key}:rpm"
        now = time.time()
        window_start = now - 60

        pipe = self._redis.pipeline()
        pipe.zremrangebyscore(key, "-inf", window_start)
        pipe.zcard(key)
        pipe.expire(key, 120)
        _, count, _ = await pipe.execute()
        return count < rpm_limit

    async def consume_rpm(self, token_key: str):
        """Record one request in the RPM sliding window."""
        key = f"rl:{token_key}:rpm"
        now = time.time()
        pipe = self._redis.pipeline()
        pipe.zadd(key, {str(now): now})
        pipe.expire(key, 120)
        await pipe.execute()

    async def get_rpm_remaining(self, token_key: str, provider_id: str, native_model: str) -> int:
        limits = self._limits(provider_id, native_model)
        rpm_limit = limits["rpm"]
        key = f"rl:{token_key}:rpm"
        now = time.time()
        await self._redis.zremrangebyscore(key, "-inf", now - 60)
        used = await self._redis.zcard(key)
        return max(0, rpm_limit - used)

    # ── Daily Quota ───────────────────────────────────────────────────────────

    async def check_daily(self, token_key: str, provider_id: str, native_model: str) -> bool:
        limits = self._limits(provider_id, native_model)
        daily_limit = limits["daily"]
        key = f"rl:{token_key}:daily"
        used = int(await self._redis.get(key) or 0)
        return used < daily_limit

    async def consume_daily(self, token_key: str, provider_id: str, native_model: str):
        key = f"rl:{token_key}:daily"
        pipe = self._redis.pipeline()
        pipe.incr(key)
        # Expire at the next midnight UTC
        seconds_until_midnight = 86400 - int(time.time()) % 86400
        pipe.expire(key, seconds_until_midnight + 60)
        await pipe.execute()

    async def get_daily_remaining(self, token_key: str, provider_id: str, native_model: str) -> int:
        limits = self._limits(provider_id, native_model)
        key = f"rl:{token_key}:daily"
        used = int(await self._redis.get(key) or 0)
        return max(0, limits["daily"] - used)

    # ── Combined check ────────────────────────────────────────────────────────

    async def can_serve(self, token_key: str, provider_id: str, native_model: str) -> bool:
        rpm_ok = await self.check_rpm(token_key, provider_id, native_model)
        daily_ok = await self.check_daily(token_key, provider_id, native_model)
        return rpm_ok and daily_ok

    async def consume(self, token_key: str, provider_id: str, native_model: str):
        """Call this after a successful request dispatch."""
        await self.consume_rpm(token_key)
        await self.consume_daily(token_key, provider_id, native_model)

    # ── Status snapshot (for /v1/providers endpoint) ─────────────────────────

    async def get_status(self, token_key: str, provider_id: str, native_model: str) -> dict:
        rpm_rem = await self.get_rpm_remaining(token_key, provider_id, native_model)
        daily_rem = await self.get_daily_remaining(token_key, provider_id, native_model)
        limits = self._limits(provider_id, native_model)
        return {
            "rpm_remaining": rpm_rem,
            "rpm_limit": limits["rpm"],
            "daily_remaining": daily_rem,
            "daily_limit": limits["daily"],
            "available": rpm_rem > 0 and daily_rem > 0,
        }

    # ── Sync from response headers ────────────────────────────────────────────

    async def sync_from_headers(self, token_key: str, rl_info):
        """If provider returns remaining counts in headers, trust those over our estimate."""
        if rl_info.rpm_remaining is not None:
            await self._redis.setex(f"rl:{token_key}:rpm_synced", 65, rl_info.rpm_remaining)
