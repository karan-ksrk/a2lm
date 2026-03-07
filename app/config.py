from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Gateway
    secret_key: str = "change-me"
    gateway_api_key: str = "dev-key"

    # DB & Redis
    database_url: str = "postgresql+asyncpg://omnillm:omnillm@postgres:5432/omnillm"
    redis_url: str = "redis://redis:6379/0"

    # Provider keys (single or comma-separated for rotation)
    groq_api_keys: str = ""
    openrouter_api_keys: str = ""
    google_ai_studio_api_keys: str = ""

    # Compat: allow single-key env vars too
    groq_api_key: str = ""
    openrouter_api_key: str = ""
    google_ai_studio_api_key: str = ""

    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        extra = "ignore"

    def get_keys(self, provider: str) -> list[str]:
        """Return list of API keys for a provider, supporting both single and multi-key."""
        multi = getattr(self, f"{provider}_api_keys", "")
        single = getattr(self, f"{provider}_api_key", "")
        keys = [k.strip() for k in multi.split(",") if k.strip()]
        if not keys and single:
            keys = [single]
        return keys


@lru_cache()
def get_settings() -> Settings:
    return Settings()
