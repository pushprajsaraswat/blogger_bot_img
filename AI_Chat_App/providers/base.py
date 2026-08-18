"""Abstract provider interface — every provider implements this."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncGenerator, Any
from core.streaming import TokenStream
from core.errors import ProviderError, RateLimitError, AuthError, ModelNotFoundError

@dataclass
class ModelInfo:
    id: str
    display_name: str
    context_length: int = 4096
    max_output: int = 4096
    supports_vision: bool = False
    supports_tools: bool = False
    supports_streaming: bool = True
    input_cost_per_1k: float = 0.0
    output_cost_per_1k: float = 0.0

@dataclass
class ChatRequest:
    model: str
    messages: list[dict]          # [{"role":"user","content":"..."}]
    temperature: float = 0.7
    top_p: float = 1.0
    max_tokens: int | None = None
    stream: bool = True
    tools: list[dict] | None = None
    tool_choice: str | dict | None = None

@dataclass
class ChatResponse:
    content: str
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    tool_calls: list[dict] | None = None
    finish_reason: str = "stop"

class AIProvider(ABC):
    """Base class — implements retry/backoff, cost calc, streaming wrapper."""
    def __init__(self, provider_id: str, base_url: str, api_key: str | None = None):
        self.provider_id = provider_id
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._session = None  # lazy aiohttp.ClientSession

    # ---- lifecycle ----
    async def _get_session(self):
        if self._session is None or self._session.closed:
            import aiohttp
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._session = aiohttp.ClientSession(base_url=self.base_url, headers=headers)
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    # ---- abstract ----
    @abstractmethod
    async def list_models(self) -> list[ModelInfo]: ...

    @abstractmethod
    async def _raw_chat(self, req: ChatRequest) -> AsyncGenerator[dict, None] | ChatResponse: ...
        # returns async gen of SSE chunks if streaming, else ChatResponse

    # ---- public high-level ----
    async def chat(self, req: ChatRequest, on_token=None) -> ChatResponse:
        stream = TokenStream(on_token)
        try:
            result = await self._raw_chat(req)
            if req.stream and hasattr(result, "__aiter__"):
                async for chunk in result:
                    await self._handle_stream_chunk(chunk, stream)
                await stream.wait_done()
                return ChatResponse(
                    content=stream.text(),
                    tokens_in=0, tokens_out=0, cost_usd=0.0  # filled by subclass if available
                )
            else:
                return result  # ChatResponse
        except Exception as e:
            await stream.feed(f"\n[Error: {e}]")
            raise

    async def _handle_stream_chunk(self, chunk: dict, stream: TokenStream):
        """Override in subclass to parse provider-specific SSE format."""
        raise NotImplementedError
