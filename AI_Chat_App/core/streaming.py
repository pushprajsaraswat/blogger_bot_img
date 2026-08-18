"""Token accumulator with optional callback per token."""
from __future__ import annotations
from typing import AsyncGenerator, Callable, Awaitable
import asyncio

class TokenStream:
    def __init__(self, on_token: Callable[[str], Awaitable[None]] | None = None):
        self.on_token = on_token
        self._buffer: list[str] = []
        self._done = asyncio.Event()

    async def feed(self, token: str):
        self._buffer.append(token)
        if self.on_token:
            await self.on_token(token)

    async def feed_gen(self, gen: AsyncGenerator[str, None]):
        async for t in gen:
            await self.feed(t)
        self._done.set()

    def text(self) -> str:
        return "".join(self._buffer)

    async def wait_done(self):
        await self._done.wait()
