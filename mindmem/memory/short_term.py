from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from mindmem.input.text import TextInputEvent
from mindmem.sensory.extraction import MemoryExtractionResult


@dataclass(frozen=True)
class ShortTermMemoryRecord:
    id: str
    event_id: str
    user_id: str
    session_id: str
    relevance_score: float
    extraction: MemoryExtractionResult
    stored_at: datetime
    expires_at: datetime


class ShortTermMemoryBuffer:
    def __init__(
        self,
        *,
        max_records_per_session: int = 50,
        ttl: timedelta = timedelta(minutes=30),
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if max_records_per_session < 1:
            raise ValueError("max_records_per_session must be at least 1")
        if ttl <= timedelta(0):
            raise ValueError("ttl must be greater than zero")

        self.max_records_per_session = max_records_per_session
        self.ttl = ttl
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._records: dict[tuple[str, str], list[ShortTermMemoryRecord]] = {}

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
        self.remove_expired(now=now)

        record = ShortTermMemoryRecord(
            id=str(uuid4()),
            event_id=event.id,
            user_id=event.user_id,
            session_id=event.session_id,
            relevance_score=relevance_score,
            extraction=extraction,
            stored_at=now,
            expires_at=now + self.ttl,
        )

        key = (event.user_id, event.session_id)
        session_records = self._records.setdefault(key, [])
        session_records.append(record)
        excess = len(session_records) - self.max_records_per_session
        if excess > 0:
            del session_records[:excess]

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

        self.remove_expired()
        records = self._records.get((user_id, session_id), [])
        if limit is not None:
            records = records[-limit:]
        return tuple(records)

    def remove_expired(self, *, now: datetime | None = None) -> int:
        current_time = now or self._now()
        removed = 0

        for key, records in list(self._records.items()):
            active = [record for record in records if record.expires_at > current_time]
            removed += len(records) - len(active)
            if active:
                self._records[key] = active
            else:
                del self._records[key]

        return removed

    def clear_session(self, *, user_id: str, session_id: str) -> int:
        records = self._records.pop((user_id, session_id), [])
        return len(records)

    def _now(self) -> datetime:
        now = self._clock()
        if now.tzinfo is None:
            raise ValueError("clock must return a timezone-aware datetime")
        return now
