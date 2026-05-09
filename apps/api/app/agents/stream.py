import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

_event_queues: dict[str, asyncio.Queue] = {}
_event_history: dict[str, list["RunEvent"]] = {}


@dataclass
class RunEvent:
    event_type: str
    data: dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def create_queue(run_id: str) -> asyncio.Queue:
    queue: asyncio.Queue = asyncio.Queue()
    _event_queues[run_id] = queue
    _event_history[run_id] = []
    return queue


def get_queue(run_id: str) -> asyncio.Queue | None:
    return _event_queues.get(run_id)


def get_history(run_id: str) -> list[RunEvent]:
    return _event_history.get(run_id, [])


def emit(run_id: str, event: RunEvent):
    _event_history.setdefault(run_id, []).append(event)
    q = _event_queues.get(run_id)
    if q:
        q.put_nowait(event)


def cleanup(run_id: str):
    _event_queues.pop(run_id, None)


def cleanup_history(run_id: str):
    _event_history.pop(run_id, None)
