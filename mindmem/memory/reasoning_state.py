from dataclasses import dataclass, replace
from datetime import datetime
from typing import Literal
from uuid import uuid4


ReasoningStateKind = Literal["decision", "task", "tool_result"]
ReasoningStateStatus = Literal[
    "recorded",
    "open",
    "in_progress",
    "completed",
    "blocked",
]
TaskStatus = Literal["open", "in_progress", "completed", "blocked"]

_TASK_STATUSES = {"open", "in_progress", "completed", "blocked"}


@dataclass(frozen=True)
class ReasoningStateItem:
    id: str
    user_id: str
    session_id: str
    topic_id: str
    kind: ReasoningStateKind
    content: str
    status: ReasoningStateStatus
    source_record_id: str | None
    created_at: datetime
    updated_at: datetime


class ReasoningStateStore:
    def __init__(self) -> None:
        self._items: dict[tuple[str, str], list[ReasoningStateItem]] = {}

    def add(
        self,
        *,
        user_id: str,
        session_id: str,
        topic_id: str,
        kind: ReasoningStateKind,
        content: str,
        now: datetime,
        status: ReasoningStateStatus,
        source_record_id: str | None = None,
    ) -> ReasoningStateItem:
        content = content.strip()
        if not content:
            raise ValueError("reasoning state content must not be empty")
        if kind == "task" and status not in _TASK_STATUSES:
            raise ValueError("tasks require a valid task status")
        if kind != "task" and status != "recorded":
            raise ValueError("decisions and tool results use recorded status")

        item = ReasoningStateItem(
            id=str(uuid4()),
            user_id=user_id,
            session_id=session_id,
            topic_id=topic_id,
            kind=kind,
            content=content,
            status=status,
            source_record_id=source_record_id,
            created_at=now,
            updated_at=now,
        )
        self._items.setdefault((user_id, session_id), []).append(item)
        return item

    def get(
        self,
        *,
        user_id: str,
        session_id: str,
        topic_id: str | None = None,
        kind: ReasoningStateKind | None = None,
    ) -> tuple[ReasoningStateItem, ...]:
        items = self._items.get((user_id, session_id), [])
        if topic_id is not None:
            items = [item for item in items if item.topic_id == topic_id]
        if kind is not None:
            items = [item for item in items if item.kind == kind]
        return tuple(items)

    def update_task(
        self,
        *,
        task_id: str,
        status: TaskStatus,
        now: datetime,
    ) -> ReasoningStateItem:
        if status not in _TASK_STATUSES:
            raise ValueError("invalid task status")
        for key, items in self._items.items():
            for index, item in enumerate(items):
                if item.id != task_id:
                    continue
                if item.kind != "task":
                    raise ValueError("only task items can change status")
                updated = replace(item, status=status, updated_at=now)
                items[index] = updated
                return updated
        raise KeyError(f"unknown task_id: {task_id}")

    def remove_topic(self, topic_id: str) -> None:
        for key, items in list(self._items.items()):
            remaining = [item for item in items if item.topic_id != topic_id]
            if remaining:
                self._items[key] = remaining
            else:
                del self._items[key]

    def clear_session(self, *, user_id: str, session_id: str) -> None:
        self._items.pop((user_id, session_id), None)
