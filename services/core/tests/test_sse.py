import json
from uuid import uuid4

from mensura_core.event_publisher import InMemoryEventPublisher, MensuraEvent


def test_event_publisher_publishes_and_serializes(client) -> None:
    publisher: InMemoryEventPublisher = client.app.state.event_publisher

    event = MensuraEvent(
        event_type="run.status.changed",
        workspace_id=uuid4(),
        entity_type="run",
        entity_id=uuid4(),
        status="succeeded",
        summary="Run completed.",
    )
    publisher.publish(event)

    serialized = event.to_sse_data()
    payload = json.loads(serialized)
    assert payload["eventType"] == "run.status.changed"
    assert payload["entityType"] == "run"
    assert payload["status"] == "succeeded"
    assert len(payload["summary"]) < 200
    assert "eventId" in payload
    assert "occurredAt" in payload


def test_event_payload_no_file_contents(client) -> None:
    event = MensuraEvent(
        event_type="application.created",
        workspace_id=uuid4(),
        entity_type="application",
        entity_id=uuid4(),
        status="applied_guard_passed",
        summary="Applied 3 files.",
    )
    payload = json.loads(event.to_sse_data())
    assert "fileContents" not in payload
    assert "fileBody" not in payload
    assert "diff" not in payload
    assert "patch" not in payload


def test_event_publisher_buffer_replay(client) -> None:
    publisher: InMemoryEventPublisher = client.app.state.event_publisher

    ids = []
    for i in range(5):
        event = MensuraEvent(
            event_type="run.status.changed",
            workspace_id=None,
            entity_type="run",
            entity_id=uuid4(),
            status="succeeded",
            summary=f"Run {i}.",
        )
        publisher.publish(event)
        ids.append(str(event.event_id))

    replay = publisher.replay_from(ids[-1])
    assert len(replay) == 0

    replay_from_none = publisher.replay_from(None)
    assert replay_from_none == []


def test_event_publisher_buffer_bounded(client) -> None:
    publisher: InMemoryEventPublisher = client.app.state.event_publisher

    for _ in range(200):
        publisher.publish(
            MensuraEvent(
                event_type="run.status.changed",
                workspace_id=None,
                entity_type="run",
                entity_id=uuid4(),
                status="succeeded",
                summary="x",
            )
        )

    assert publisher.buffer_size == 100


def test_summary_truncated_to_200_chars(client) -> None:
    long_summary = "A" * 500
    event = MensuraEvent(
        event_type="verification.created",
        workspace_id=uuid4(),
        entity_type="verification",
        entity_id=uuid4(),
        status="passed",
        summary=long_summary,
    )
    payload = json.loads(event.to_sse_data())
    assert len(payload["summary"]) <= 200


def test_run_event_serialization(client) -> None:
    publisher: InMemoryEventPublisher = client.app.state.event_publisher
    run_id = uuid4()

    publisher.publish(
        MensuraEvent(
            event_type="run.status.changed",
            workspace_id=None,
            entity_type="run",
            entity_id=run_id,
            status="succeeded",
            summary="Task analysis completed.",
        )
    )

    payload = json.loads(
        MensuraEvent(
            event_type="run.status.changed",
            workspace_id=None,
            entity_type="run",
            entity_id=run_id,
            status="failed",
            summary="Provider execution failed.",
        ).to_sse_data()
    )
    assert payload["status"] == "failed"
    assert payload["eventType"] == "run.status.changed"


def test_verification_event_serialization(client) -> None:
    publisher: InMemoryEventPublisher = client.app.state.event_publisher
    verification_id = uuid4()
    ws_id = uuid4()

    publisher.publish(
        MensuraEvent(
            event_type="verification.created",
            workspace_id=ws_id,
            entity_type="verification",
            entity_id=verification_id,
            status="passed",
            summary="Verification passed.",
        )
    )

    payload = json.loads(
        MensuraEvent(
            event_type="verification.created",
            workspace_id=ws_id,
            entity_type="verification",
            entity_id=verification_id,
            status="passed",
            summary="Verification passed.",
        ).to_sse_data()
    )
    assert payload["entityType"] == "verification"
    assert payload["workspaceId"] == str(ws_id)


def test_backup_event_serialization(client) -> None:
    publisher: InMemoryEventPublisher = client.app.state.event_publisher
    backup_id = uuid4()

    publisher.publish(
        MensuraEvent(
            event_type="backup.created",
            workspace_id=None,
            entity_type="backup",
            entity_id=backup_id,
            status="completed",
            summary="Backup completed. Size: 1024 bytes.",
        )
    )

    payload = json.loads(
        MensuraEvent(
            event_type="backup.created",
            workspace_id=None,
            entity_type="backup",
            entity_id=backup_id,
            status="completed",
            summary="Backup completed. Size: 1024 bytes.",
        ).to_sse_data()
    )
    assert payload["entityType"] == "backup"
    assert "workspaceId" not in payload


def test_application_event_serialization(client) -> None:
    publisher: InMemoryEventPublisher = client.app.state.event_publisher
    app_id = uuid4()
    ws_id = uuid4()

    publisher.publish(
        MensuraEvent(
            event_type="application.created",
            workspace_id=ws_id,
            entity_type="application",
            entity_id=app_id,
            status="applied_guard_passed",
            summary="Applied 3 files successfully.",
        )
    )

    payload = json.loads(
        MensuraEvent(
            event_type="application.created",
            workspace_id=ws_id,
            entity_type="application",
            entity_id=app_id,
            status="applied_guard_passed",
            summary="Applied 3 files successfully.",
        ).to_sse_data()
    )
    assert payload["entityType"] == "application"
    assert payload["workspaceId"] == str(ws_id)
    assert payload["entityId"] == str(app_id)


def test_undo_event_serialization(client) -> None:
    publisher: InMemoryEventPublisher = client.app.state.event_publisher
    undo_id = uuid4()
    ws_id = uuid4()

    publisher.publish(
        MensuraEvent(
            event_type="undo.created",
            workspace_id=ws_id,
            entity_type="undo",
            entity_id=undo_id,
            status="undone_guard_passed",
            summary="Undo completed. Guard passed.",
        )
    )

    payload = json.loads(
        MensuraEvent(
            event_type="undo.created",
            workspace_id=ws_id,
            entity_type="undo",
            entity_id=undo_id,
            status="undone_guard_passed",
            summary="Undo completed. Guard passed.",
        ).to_sse_data()
    )
    assert payload["entityType"] == "undo"
    assert payload["workspaceId"] == str(ws_id)


def test_connected_event_shape(client) -> None:
    connected = json.dumps(
        {"eventType": "connected", "bufferSize": 42}, separators=(",", ":")
    )
    payload = json.loads(connected)
    assert payload["eventType"] == "connected"
    assert payload["bufferSize"] == 42


def test_event_publisher_subscribe_unsubscribe(client) -> None:
    import asyncio

    publisher: InMemoryEventPublisher = client.app.state.event_publisher

    async def _collect():
        queue = publisher.subscribe()
        publisher.unsubscribe(queue)
        publisher.publish(
            MensuraEvent(
                event_type="run.status.changed",
                workspace_id=None,
                entity_type="run",
                entity_id=uuid4(),
                status="succeeded",
                summary="After unsubscribe.",
            )
        )
        assert queue.empty()

    asyncio.run(_collect())


def test_event_publisher_empty_queue_on_no_subscribers(client) -> None:
    publisher: InMemoryEventPublisher = client.app.state.event_publisher

    for _ in range(10):
        publisher.publish(
            MensuraEvent(
                event_type="run.status.changed",
                workspace_id=None,
                entity_type="run",
                entity_id=uuid4(),
                status="succeeded",
                summary="Event without subscribers.",
            )
        )

    assert publisher.buffer_size == 10
