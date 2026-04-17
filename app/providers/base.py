from abc import ABC, abstractmethod
from typing import AsyncIterator
import httpx

from app.schemas import NormalizedRequest, ChatCompletionResponse, ChatCompletionChunk


class BaseProvider(ABC):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = httpx.AsyncClient(timeout=10.0)

    async def close(self):
        await self._client.aclose()

    @abstractmethod
    async def complete(self, req: NormalizedRequest) -> ChatCompletionResponse:
        pass

    @abstractmethod
    async def stream(self, req: NormalizedRequest) -> AsyncIterator[str]:
        pass
