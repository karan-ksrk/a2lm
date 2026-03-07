from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
import structlog

from app.api.auth import verify_api_key
from app.models.schemas import ChatCompletionRequest, NormalizedRequest
from app.routing.engine import RoutingEngine, NoProviderAvailableError

log = structlog.get_logger()
router = APIRouter()


def get_engine(request: Request) -> RoutingEngine:
    return request.app.state.engine


# ── Primary endpoint ──────────────────────────────────────────────────────────

@router.post("/v1/chat/completions")
async def chat_completions(
    body: ChatCompletionRequest,
    engine: RoutingEngine = Depends(get_engine),
    _: str = Depends(verify_api_key),
):
    # Convert to internal normalized format
    req = NormalizedRequest(
        model=body.model,
        messages=[m.model_dump() for m in body.messages],
        temperature=body.temperature or 0.7,
        max_tokens=body.max_tokens or 1024,
        stream=body.stream or False,
        top_p=body.top_p,
        stop=body.stop,
    )

    try:
        if req.stream:
            return StreamingResponse(
                engine.execute_stream(req),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Accel-Buffering": "no",
                },
            )
        return await engine.execute(req)

    except NoProviderAvailableError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
            headers={"Retry-After": "60"},
        )
    except Exception as e:
        log.error("request_failed", error=str(e), model=req.model)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Provider error: {str(e)}",
        )


# ── Model listing ─────────────────────────────────────────────────────────────

@router.get("/v1/models")
async def list_models(
    engine: RoutingEngine = Depends(get_engine),
    _: str = Depends(verify_api_key),
):
    models = engine.registry.list_models()
    return {"object": "list", "data": models}


# ── Provider quota status ─────────────────────────────────────────────────────

@router.get("/v1/providers")
async def provider_status(
    engine: RoutingEngine = Depends(get_engine),
    _: str = Depends(verify_api_key),
):
    status_list = await engine.get_provider_status()
    return {"providers": status_list}


# ── Health checks ─────────────────────────────────────────────────────────────

@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness(request: Request):
    checks = {}
    # Redis check
    try:
        engine: RoutingEngine = request.app.state.engine
        await engine.rl._redis.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    all_ok = all(v == "ok" for v in checks.values())
    return {"status": "ready" if all_ok else "degraded", "checks": checks}
