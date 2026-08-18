"""OpenAI-compatible provider (OpenAI, OpenRouter, Groq, Together, Ollama, custom)."""
from __future__ import annotations
import json
import aiohttp
from typing import AsyncGenerator
from providers.base import AIProvider, ChatRequest, ChatResponse, ModelInfo
from core.errors import RateLimitError, AuthError, ModelNotFoundError, ProviderError
from core.streaming import TokenStream

class OpenAICompatProvider(AIProvider):
    """Handles /v1/chat/completions with SSE streaming."""
    VENDORS = {
        "openai": "https://api.openai.com/v1",
        "openrouter": "https://openrouter.ai/api/v1",
        "groq": "https://api.groq.com/openai/v1",
        "together": "https://api.together.xyz/v1",
        "ollama": "http://localhost:11434/v1",  # local
    }

    def __init__(self, provider_id: str, base_url: str, api_key: str | None = None,
                 extra_headers: dict | None = None):
        super().__init__(provider_id, base_url, api_key)
        self.extra_headers = extra_headers or {}

    async def _get_session(self):
        session = await super()._get_session()
        # merge extra headers (OpenRouter needs HTTP-Referer, X-Title)
        session._default_headers.update(self.extra_headers)
        return session

    # ---- Models ----
    async def list_models(self) -> list[ModelInfo]:
        session = await self._get_session()
        async with session.get("/models") as resp:
            if resp.status == 401:
                raise AuthError("Invalid API key")
            if resp.status != 200:
                raise ProviderError(f"Models list failed: {resp.status}")
            data = await resp.json()
        models = []
        for m in data.get("data", []):
            mid = m["id"]
            models.append(ModelInfo(
                id=mid,
                display_name=mid,
                context_length=m.get("context_length", 4096),
                max_output=m.get("max_output_tokens", 4096),
                supports_vision="vision" in mid.lower() or "gpt-4o" in mid.lower(),
                supports_tools=True,
                supports_streaming=True,
            ))
        return models

    # ---- Chat ----
    async def _raw_chat(self, req: ChatRequest) -> AsyncGenerator[dict, None] | ChatResponse:
        session = await self._get_session()
        payload = {
            "model": req.model,
            "messages": req.messages,
            "temperature": req.temperature,
            "top_p": req.top_p,
            "stream": req.stream,
        }
        if req.max_tokens:
            payload["max_tokens"] = req.max_tokens
        if req.tools:
            payload["tools"] = req.tools
            payload["tool_choice"] = req.tool_choice or "auto"

        url = "/chat/completions"
        if req.stream:
            return self._stream_request(session, url, payload)
        else:
            return await self._single_request(session, url, payload)

    async def _single_request(self, session, url, payload) -> ChatResponse:
        async with session.post(url, json=payload) as resp:
            await self._check_error(resp)
            data = await resp.json()
        return self._parse_response(data)

    async def _stream_request(self, session, url, payload) -> AsyncGenerator[dict, None]:
        async with session.post(url, json=payload) as resp:
            await self._check_error(resp)
            async for line in resp.content:
                line = line.decode().strip()
                if not line or line == "data: [DONE]":
                    continue
                if line.startswith("data: "):
                    line = line[6:]
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    pass

    async def _check_error(self, resp: aiohttp.ClientResponse):
        if resp.status == 401:
            raise AuthError("Authentication failed")
        if resp.status == 404:
            raise ModelNotFoundError("Model not found")
        if resp.status == 429:
            raise RateLimitError("Rate limit exceeded")
        if resp.status >= 400:
            text = await resp.text()
            raise ProviderError(f"HTTP {resp.status}: {text}")

    def _parse_response(self, data: dict) -> ChatResponse:
        choice = data["choices"][0]
        msg = choice["message"]
        usage = data.get("usage", {})
        return ChatResponse(
            content=msg.get("content", "") or "",
            tokens_in=usage.get("prompt_tokens", 0),
            tokens_out=usage.get("completion_tokens", 0),
            cost_usd=0.0,  # calculated later via pricing table
            tool_calls=msg.get("tool_calls"),
            finish_reason=choice.get("finish_reason", "stop")
        )

    async def _handle_stream_chunk(self, chunk: dict, stream: TokenStream):
        try:
            delta = chunk["choices"][0]["delta"]
            if "content" in delta and delta["content"]:
                await stream.feed(delta["content"])
        except (KeyError, IndexError):
            pass
