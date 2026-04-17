from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    gateway_api_key: str = "dev-key"

    groq_api_key: str = ""
    cerebras_api_key: str = ""
    google_ai_studio_api_key: str = ""
    mistral_api_key: str = ""
    openrouter_api_key: str = ""
    cohere_api_key: str = ""
    nvidia_api_key: str = ""
    cloudflare_api_key: str = ""
    cloudflare_account_id: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
