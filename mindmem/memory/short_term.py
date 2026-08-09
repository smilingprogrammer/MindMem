from dataclasses import dataclass
from datetime import datetime, timezone
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


class ShortTermMemoryBuffer:
    def __init__(self, *, max_records_per_session: int = 50) -> None:
        if max_records_per_session < 1:
            raise ValueError("max_records_per_session must be at least 1")

        self.max_records_per_session = max_records_per_session
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

        record = ShortTermMemoryRecord(
            id=str(uuid4()),
            event_id=event.id,
            user_id=event.user_id,
            session_id=event.session_id,
            relevance_score=relevance_score,
            extraction=extraction,
            stored_at=datetime.now(timezone.utc),
        )

        key = (event.user_id, event.session_id)
        records = self._records.setdefault(key, [])
        records.append(record)
        del records[: -self.max_records_per_session]
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

    def clear_session(self, *, user_id: str, session_id: str) -> int:
        records = self._records.pop((user_id, session_id), [])
        return len(records)
