from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Union
import time, uuid


class Message(BaseModel):
    role: str
    content: Union[str, list]
    name: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")  # accept unknown fields (tools, penalties, etc.)

    model: str = "auto"
    messages: list[Message]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1024
    stream: Optional[bool] = False
    top_p: Optional[float] = None
    stop: Optional[Union[str, list[str]]] = None


class NormalizedRequest(BaseModel):
    model: str
    messages: list[dict]
    temperature: float = 0.7
    max_tokens: int = 1024
    stream: bool = False
    top_p: Optional[float] = None
    stop: Optional[Union[str, list[str]]] = None


class ChoiceDelta(BaseModel):
    role: Optional[str] = None
    content: Optional[str] = None


class Choice(BaseModel):
    index: int = 0
    message: Optional[dict] = None
    delta: Optional[ChoiceDelta] = None
    finish_reason: Optional[str] = None

    def model_dump_clean(self) -> dict:
        return self.model_dump(exclude_none=True)


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

    def to_response(self) -> dict:
        d = self.model_dump(exclude_none=True)
        d["choices"] = [c.model_dump(exclude_none=True) for c in self.choices]
        return d


class ChatCompletionChunk(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:12]}")
    object: str = "chat.completion.chunk"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: list[Choice]

    def to_sse(self) -> str:
        d = self.model_dump(exclude_none=True)
        d["choices"] = [c.model_dump(exclude_none=True) for c in self.choices]
        import json
        return f"data: {json.dumps(d)}\n\n"
