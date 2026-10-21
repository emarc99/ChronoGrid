"""Fan-out of screen events to every connected ambient display (WebSocket clients)."""

from __future__ import annotations

import asyncio
import time
from typing import Any


class Hub:
    def __init__(self) -> None:
        self._queues: set[asyncio.Queue] = set()
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._queues.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._queues.discard(queue)

    def publish(self, message: dict[str, Any]) -> None:
        """Thread-safe: callable from MCP tools, the linter, or agent threads."""
        message = {"at": time.time(), **message}
        if self._loop is None:
            return
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if running is self._loop:
            self._fanout(message)
        else:
            self._loop.call_soon_threadsafe(self._fanout, message)

    def _fanout(self, message: dict[str, Any]) -> None:
        for queue in list(self._queues):
            if queue.full():
                queue.get_nowait()
            queue.put_nowait(message)
