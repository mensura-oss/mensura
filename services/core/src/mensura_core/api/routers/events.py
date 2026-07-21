import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request
from sse_starlette.sse import EventSourceResponse

from mensura_core.event_publisher import InMemoryEventPublisher

logger = logging.getLogger(__name__)

router = APIRouter(tags=["events"])

_STREAM_TIMEOUT = 15.0


def _event_publisher(request: Request) -> InMemoryEventPublisher:
    return request.app.state.event_publisher


async def _stream_events(
    publisher: InMemoryEventPublisher,
    workspace_id: UUID | None,
    last_event_id: str | None,
) -> AsyncIterator[dict[str, str]]:
    queue = publisher.subscribe()

    connected_event = json.dumps(
        {"eventType": "connected", "bufferSize": publisher.buffer_size},
        separators=(",", ":"),
    )
    yield {"event": "connected", "data": connected_event, "id": "0"}

    if last_event_id:
        replay = publisher.replay_from(last_event_id)
        for event in replay:
            yield {
                "event": event.event_type,
                "data": event.to_sse_data(),
                "id": str(event.event_id),
            }

    try:
        while True:
            try:
                event = await asyncio.wait_for(
                    queue.get(), timeout=_STREAM_TIMEOUT
                )
            except TimeoutError:
                yield {"comment": "keepalive"}
                continue

            if event is None:
                break

            if (
                workspace_id is not None
                and event.workspace_id is not None
                and event.workspace_id != workspace_id
            ):
                continue

            yield {
                "event": event.event_type,
                "data": event.to_sse_data(),
                "id": str(event.event_id),
            }
    except asyncio.CancelledError:
        pass
    finally:
        publisher.unsubscribe(queue)


@router.get("/events/stream")
async def event_stream(
    request: Request,
    workspace_id: Annotated[UUID | None, Query(description="Filter events by workspace")] = None,
) -> EventSourceResponse:
    publisher: InMemoryEventPublisher = _event_publisher(request)
    last_event_id = request.headers.get("Last-Event-Id")

    return EventSourceResponse(
        _stream_events(publisher, workspace_id, last_event_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
