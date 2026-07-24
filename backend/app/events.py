"""Per-run event bus backing `GET /runs/{id}/events` (API_ENDPOINTS §4).

The fan-out is what makes the product visibly different, so progress is streamed rather
than polled. Late subscribers get the replay buffer first, then live events.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from uuid import UUID

from .models import RunEvent


class EventBus:
    def __init__(self, buffer_size: int = 500) -> None:
        self._subscribers: dict[UUID, list[asyncio.Queue[RunEvent | None]]] = defaultdict(list)
        self._history: dict[UUID, list[RunEvent]] = defaultdict(list)
        self._buffer_size = buffer_size

    async def publish(self, event: RunEvent) -> None:
        history = self._history[event.run_id]
        history.append(event)
        if len(history) > self._buffer_size:
            del history[: len(history) - self._buffer_size]
        for queue in list(self._subscribers[event.run_id]):
            queue.put_nowait(event)

    async def close(self, run_id: UUID) -> None:
        for queue in list(self._subscribers[run_id]):
            queue.put_nowait(None)

    def history(self, run_id: UUID) -> list[RunEvent]:
        return list(self._history[run_id])

    def subscribe(self, run_id: UUID) -> asyncio.Queue[RunEvent | None]:
        queue: asyncio.Queue[RunEvent | None] = asyncio.Queue()
        self._subscribers[run_id].append(queue)
        return queue

    def unsubscribe(self, run_id: UUID, queue: asyncio.Queue[RunEvent | None]) -> None:
        if queue in self._subscribers[run_id]:
            self._subscribers[run_id].remove(queue)


BUS = EventBus()
