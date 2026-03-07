import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.ratelimit.manager import RateLimitManager
from app.registry.models import ModelRegistry
from app.routing.engine import RoutingEngine
from app.api.routes import router

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer(),
    ]
)
log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──
    log.info("gateway_starting")
    settings = get_settings()

    rl_manager = RateLimitManager()
    registry = ModelRegistry()
    engine = RoutingEngine(rl_manager=rl_manager, registry=registry)

    app.state.engine = engine
    log.info("gateway_ready", providers=list(engine._token_pools.keys()))

    yield

    # ── Shutdown ──
    await rl_manager.close()
    log.info("gateway_stopped")


app = FastAPI(
    title="A2LM Gateway",
    description="Unified LLM API aggregating Groq, OpenRouter, Google AI Studio and more.",
    version="0.1.0-mvp",
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
