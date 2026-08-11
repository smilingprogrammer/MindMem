from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from mindmem.input.text import TextInputEvent
from mindmem.memory.reasoning_state import (
    ReasoningStateItem,
    ReasoningStateKind,
    ReasoningStateStore,
    TaskStatus,
)
from mindmem.memory.topics import TopicGroup, TopicTracker
from mindmem.sensory.extraction import MemoryExtractionResult


@dataclass(frozen=True)
class ShortTermMemoryRecord:
    id: str
    event_id: str
    user_id: str
    session_id: str
    topic_id: str
    relevance_score: float
    extraction: MemoryExtractionResult
    stored_at: datetime


class ShortTermMemoryBuffer:
    def __init__(
        self,
        *,
        max_records_per_session: int = 50,
        max_active_topics_per_session: int = 3,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if max_records_per_session < 1:
            raise ValueError("max_records_per_session must be at least 1")

        self.max_records_per_session = max_records_per_session
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._records: dict[tuple[str, str], list[ShortTermMemoryRecord]] = {}
        self._records_by_id: dict[str, ShortTermMemoryRecord] = {}
        self._topics = TopicTracker(
            max_active_topics_per_session=max_active_topics_per_session
        )
        self._state = ReasoningStateStore()

    def store(
        self,
        *,
        event: TextInputEvent,
        relevance_score: float,
        extraction: MemoryExtractionResult,
    ) -> ShortTermMemoryRecord:
        if not 0.0 <= relevance_score <= 1.0:
            raise ValueError("relevance_score must be between 0 and 1")
        if extraction.source_text != event.text:
            raise ValueError("extraction source_text must match the input event")

        now = self._now()
        record_id = str(uuid4())
        topic = self._topics.assign(
            record_id=record_id,
            user_id=event.user_id,
            session_id=event.session_id,
            extraction=extraction,
            now=now,
        )
        record = ShortTermMemoryRecord(
            id=record_id,
            event_id=event.id,
            user_id=event.user_id,
            session_id=event.session_id,
            topic_id=topic.id,
            relevance_score=relevance_score,
            extraction=extraction,
            stored_at=now,
        )

        key = (event.user_id, event.session_id)
        records = self._records.setdefault(key, [])
        records.append(record)
        self._records_by_id[record.id] = record

        excess = len(records) - self.max_records_per_session
        if excess > 0:
            evicted = records[:excess]
            del records[:excess]
            for old_record in evicted:
                self._records_by_id.pop(old_record.id, None)
                removed_topic_id = self._topics.remove_record(old_record.id)
                if removed_topic_id is not None:
                    self._state.remove_topic(removed_topic_id)

        if "task" in extraction.memory_types:
            self._state.add(
                user_id=event.user_id,
                session_id=event.session_id,
                topic_id=topic.id,
                kind="task",
                content=extraction.source_text,
                status="open",
                source_record_id=record.id,
                now=now,
            )
        return record

    def get_recent(
        self,
        *,
        user_id: str,
        session_id: str,
        limit: int | None = None,
    ) -> tuple[ShortTermMemoryRecord, ...]:
        if limit is not None and limit < 1:
            raise ValueError("limit must be at least 1")

        records = self._records.get((user_id, session_id), [])
        if limit is not None:
            records = records[-limit:]
        return tuple(records)

    def get_topics(
        self,
        *,
        user_id: str,
        session_id: str,
        active_only: bool = False,
    ) -> tuple[TopicGroup, ...]:
        return self._topics.get_topics(
            user_id=user_id,
            session_id=session_id,
            active_only=active_only,
        )

    def get_current_topic(
        self,
        *,
        user_id: str,
        session_id: str,
    ) -> TopicGroup | None:
        return self._topics.current_topic(user_id=user_id, session_id=session_id)

    def get_topic_records(self, topic_id: str) -> tuple[ShortTermMemoryRecord, ...]:
        topic = self._require_topic(topic_id)
        return tuple(
            self._records_by_id[record_id]
            for record_id in topic.record_ids
            if record_id in self._records_by_id
        )

    def add_decision(
        self,
        *,
        user_id: str,
        session_id: str,
        content: str,
        topic_id: str | None = None,
        source_record_id: str | None = None,
    ) -> ReasoningStateItem:
        return self._add_state(
            user_id=user_id,
            session_id=session_id,
            topic_id=topic_id,
            kind="decision",
            content=content,
            source_record_id=source_record_id,
        )

    def add_task(
        self,
        *,
        user_id: str,
        session_id: str,
        content: str,
        status: TaskStatus = "open",
        topic_id: str | None = None,
        source_record_id: str | None = None,
    ) -> ReasoningStateItem:
        return self._add_state(
            user_id=user_id,
            session_id=session_id,
            topic_id=topic_id,
            kind="task",
            content=content,
            status=status,
            source_record_id=source_record_id,
        )

    def add_tool_result(
        self,
        *,
        user_id: str,
        session_id: str,
        content: str,
        topic_id: str | None = None,
        source_record_id: str | None = None,
    ) -> ReasoningStateItem:
        return self._add_state(
            user_id=user_id,
            session_id=session_id,
            topic_id=topic_id,
            kind="tool_result",
            content=content,
            source_record_id=source_record_id,
        )

    def update_task(self, *, task_id: str, status: TaskStatus) -> ReasoningStateItem:
        now = self._now()
        item = self._state.update_task(task_id=task_id, status=status, now=now)
        self._topics.touch(topic_id=item.topic_id, now=now)
        return item

    def get_reasoning_state(
        self,
        *,
        user_id: str,
        session_id: str,
        topic_id: str | None = None,
        kind: ReasoningStateKind | None = None,
    ) -> tuple[ReasoningStateItem, ...]:
        if topic_id is not None:
            self._require_owned_topic(
                topic_id=topic_id,
                user_id=user_id,
                session_id=session_id,
            )
        return self._state.get(
            user_id=user_id,
            session_id=session_id,
            topic_id=topic_id,
            kind=kind,
        )

    def clear_session(self, *, user_id: str, session_id: str) -> int:
        records = self._records.pop((user_id, session_id), [])
        for record in records:
            self._records_by_id.pop(record.id, None)
        self._topics.clear_session(user_id=user_id, session_id=session_id)
        self._state.clear_session(user_id=user_id, session_id=session_id)
        return len(records)

    def _add_state(
        self,
        *,
        user_id: str,
        session_id: str,
        topic_id: str | None,
        kind: ReasoningStateKind,
        content: str,
        source_record_id: str | None,
        status: TaskStatus | None = None,
    ) -> ReasoningStateItem:
        topic = self._resolve_topic(
            user_id=user_id,
            session_id=session_id,
            topic_id=topic_id,
        )
        if source_record_id is not None:
            record = self._records_by_id.get(source_record_id)
            if record is None or record.topic_id != topic.id:
                raise ValueError("source_record_id must belong to the selected topic")

        now = self._now()
        item = self._state.add(
            user_id=user_id,
            session_id=session_id,
            topic_id=topic.id,
            kind=kind,
            content=content,
            status=status or "recorded",
            source_record_id=source_record_id,
            now=now,
        )
        self._topics.touch(topic_id=topic.id, now=now)
        return item

    def _resolve_topic(
        self,
        *,
        user_id: str,
        session_id: str,
        topic_id: str | None,
    ) -> TopicGroup:
        if topic_id is not None:
            return self._require_owned_topic(
                topic_id=topic_id,
                user_id=user_id,
                session_id=session_id,
            )

        topic = self.get_current_topic(user_id=user_id, session_id=session_id)
        if topic is None:
            raise ValueError("no active topic exists for this session")
        return topic

    def _require_owned_topic(
        self,
        *,
        topic_id: str,
        user_id: str,
        session_id: str,
    ) -> TopicGroup:
        topic = self._require_topic(topic_id)
        if topic.user_id != user_id or topic.session_id != session_id:
            raise ValueError("topic does not belong to this user and session")
        return topic

    def _require_topic(self, topic_id: str) -> TopicGroup:
        topic = self._topics.get_topic(topic_id)
        if topic is None:
            raise KeyError(f"unknown topic_id: {topic_id}")
        return topic

    def _now(self) -> datetime:
        now = self._clock()
        if now.tzinfo is None:
            raise ValueError("clock must return a timezone-aware datetime")
        return now
