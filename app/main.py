import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.router import Router
from app.providers.groq import GroqProvider
from app.providers.cerebras import CerebrasProvider
from app.providers.google import GoogleProvider
from app.providers.mistral import MistralProvider
from app.providers.openrouter import OpenRouterProvider
from app.providers.cohere import CohereProvider
from app.providers.nvidia import NvidiaProvider
from app.providers.cloudflare import CloudflareProvider
from app.api.routes import router

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def build_providers(settings) -> dict:
    providers = {}
    if settings.groq_api_key:
        providers["groq"] = GroqProvider(settings.groq_api_key)
    if settings.cerebras_api_key:
        providers["cerebras"] = CerebrasProvider(settings.cerebras_api_key)
    if settings.google_ai_studio_api_key:
        providers["google"] = GoogleProvider(settings.google_ai_studio_api_key)
    if settings.mistral_api_key:
        providers["mistral"] = MistralProvider(settings.mistral_api_key)
    if settings.openrouter_api_key:
        providers["openrouter"] = OpenRouterProvider(settings.openrouter_api_key)
    if settings.cohere_api_key:
        providers["cohere"] = CohereProvider(settings.cohere_api_key)
    if settings.nvidia_api_key:
        providers["nvidia"] = NvidiaProvider(settings.nvidia_api_key)
    if settings.cloudflare_api_key and settings.cloudflare_account_id:
        providers["cloudflare"] = CloudflareProvider(settings.cloudflare_api_key, settings.cloudflare_account_id)
    return providers


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    providers = build_providers(settings)
    app.state.router = Router(providers)
    log.info(f"gateway ready — active providers: {list(providers)}")
    yield
    await app.state.router.close()
    log.info("gateway stopped")


app = FastAPI(
    title="A2LM Gateway",
    description="Lightweight LLM gateway with priority-based provider fallback.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=True)
