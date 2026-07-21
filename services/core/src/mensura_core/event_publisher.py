import asyncio
import json
import logging
from collections import deque
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)

_MAX_BUFFER_SIZE = 100


class MensuraEvent:
    def __init__(
        self,
        event_type: str,
        workspace_id: UUID | None,
        entity_type: str,
        entity_id: UUID,
        status: str,
        summary: str,
        *,
        event_id: UUID | None = None,
        occurred_at: datetime | None = None,
    ) -> None:
        self.event_id = event_id or uuid4()
        self.event_type = event_type
        self.occurred_at = occurred_at or datetime.now(UTC)
        self.workspace_id = workspace_id
        self.entity_type = entity_type
        self.entity_id = str(entity_id)
        self.status = status
        self.summary = summary[:200]

    def to_sse_data(self) -> str:
        payload = {
            "eventId": str(self.event_id),
            "eventType": self.event_type,
            "occurredAt": self.occurred_at.isoformat(),
            "entityType": self.entity_type,
            "entityId": self.entity_id,
            "status": self.status,
            "summary": self.summary,
        }
        if self.workspace_id is not None:
            payload["workspaceId"] = str(self.workspace_id)
        return json.dumps(payload, separators=(",", ":"))


class EventPublisher(Protocol):
    def publish(self, event: MensuraEvent) -> None:
        """Fire-and-forget event publication. Must not raise on normal conditions."""


class InMemoryEventPublisher:
    def __init__(self) -> None:
        self._queues: list[asyncio.Queue[MensuraEvent | None]] = []
        self._buffer: deque[MensuraEvent] = deque(maxlen=_MAX_BUFFER_SIZE)

    def publish(self, event: MensuraEvent) -> None:
        self._buffer.append(event)
        for queue in self._queues:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("Event queue full, dropping event %s", event.event_id)

    def subscribe(self) -> asyncio.Queue[MensuraEvent | None]:
        queue: asyncio.Queue[MensuraEvent | None] = asyncio.Queue(maxsize=256)
        self._queues.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[MensuraEvent | None]) -> None:
        self._queues.remove(queue)

    def replay_from(self, last_event_id: str | None) -> list[MensuraEvent]:
        if last_event_id is None:
            return []
        found = False
        replay: list[MensuraEvent] = []
        for event in self._buffer:
            if found:
                replay.append(event)
            elif str(event.event_id) == last_event_id:
                found = True
        return replay

    @property
    def buffer_size(self) -> int:
        return len(self._buffer)
