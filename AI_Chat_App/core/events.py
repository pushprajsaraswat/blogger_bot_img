"""Tiny async pub/sub — no external deps."""
from __future__ import annotations
from collections import defaultdict
from typing import Callable, Awaitable, Any
import asyncio

class EventBus:
    def __init__(self):
        self._subs: dict[str, list[Callable[..., Awaitable[None]]]] = defaultdict(list)

    def on(self, event: str, handler: Callable[..., Awaitable[None]]):
        self._subs[event].append(handler)

    async def emit(self, event: str, *args, **kwargs):
        for h in self._subs.get(event, []):
            try:
                await h(*args, **kwargs)
            except Exception as e:
                print(f"[EventBus] handler error {event}: {e}")

bus = EventBus()  # global singleton
