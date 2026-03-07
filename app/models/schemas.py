from pydantic import BaseModel, Field
from typing import Any, Optional, Union
import time, uuid


# ── Incoming Request ──────────────────────────

class Message(BaseModel):
    role: str                       # system | user | assistant
    content: Union[str, list]       # str for text, list for vision

class ChatCompletionRequest(BaseModel):
    model: str = "auto"
    messages: list[Message]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1024
    stream: Optional[bool] = False
    top_p: Optional[float] = None
    stop: Optional[Union[str, list[str]]] = None
    # Internal routing hints (ignored by providers)
    x_latency_hint: Optional[str] = Field(None, alias="x-latency-hint")  # "fast" | "smart"

    model_config = {"populate_by_name": True}


# ── Internal Normalized ───────────────────────

class NormalizedRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: f"req_{uuid.uuid4().hex[:12]}")
    model: str
    messages: list[dict]
    temperature: float = 0.7
    max_tokens: int = 1024
    stream: bool = False
    top_p: Optional[float] = None
    stop: Optional[Union[str, list[str]]] = None


# ── Outgoing Response ─────────────────────────

class ChoiceDelta(BaseModel):
    role: Optional[str] = None
    content: Optional[str] = None

class Choice(BaseModel):
    index: int = 0
    message: Optional[dict] = None
    delta: Optional[ChoiceDelta] = None
    finish_reason: Optional[str] = None

class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

class ChatCompletionResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:12]}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: list[Choice]
    usage: Optional[Usage] = None

class ChatCompletionChunk(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:12]}")
    object: str = "chat.completion.chunk"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: list[Choice]


# ── Rate Limit Info (parsed from headers) ─────

class RateLimitInfo(BaseModel):
    rpm_limit: Optional[int] = None
    rpm_remaining: Optional[int] = None
    tpm_limit: Optional[int] = None
    tpm_remaining: Optional[int] = None
    reset_requests: Optional[str] = None
    reset_tokens: Optional[str] = None


# ── Model Registry Entry ──────────────────────

class ModelInfo(BaseModel):
    id: str                         # alias exposed to users
    provider_id: str
    native_id: str                  # actual model string for the provider
    context_len: int = 8192
    supports_streaming: bool = True
    supports_vision: bool = False
    weight: int = 100
    is_active: bool = True
