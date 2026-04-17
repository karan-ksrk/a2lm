import time
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.api.auth import verify_api_key
from app.schemas import ChatCompletionRequest, NormalizedRequest
from app.priorities.aliases import PRIORITIES
from app.router import Router

router = APIRouter()


def get_router(request: Request) -> Router:
    return request.app.state.router


@router.post("/v1/chat/completions")
async def chat_completions(
    body: ChatCompletionRequest,
    r: Router = Depends(get_router),
    _: str = Depends(verify_api_key),
):
    if body.model not in PRIORITIES:
        raise HTTPException(400, f"Unknown alias '{body.model}'. Valid: {list(PRIORITIES)}")

    req = NormalizedRequest(
        model=body.model,
        messages=[m.model_dump(exclude_none=True) for m in body.messages],
        temperature=body.temperature or 0.7,
        max_tokens=body.max_tokens or 1024,
        stream=body.stream or False,
        top_p=body.top_p,
        stop=body.stop,
    )

    if req.stream:
        return StreamingResponse(
            r.stream(req),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    result = await r.complete(req)
    return result.to_response()


@router.get("/v1/models")
async def list_models(r: Router = Depends(get_router), _: str = Depends(verify_api_key)):
    return {"object": "list", "data": r.list_models()}


@router.get("/health")
async def health():
    return {"status": "ok"}
