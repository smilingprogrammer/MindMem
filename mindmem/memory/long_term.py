from collections.abc import Callable, Hashable, Iterable
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Literal, Protocol, TypeVar
from uuid import uuid4


LongTermMemoryKind = Literal["fact", "decision", "task", "tool_result"]
LongTermMemoryStatus = Literal["current", "superseded"]
MemoryWriteAction = Literal["created", "updated", "unchanged"]
LongTermTaskStatus = Literal["open", "in_progress", "completed", "blocked"]
_VALID_KINDS = {"fact", "decision", "task", "tool_result"}
_VALID_TASK_STATUSES = {"open", "in_progress", "completed", "blocked"}
_Mergeable = TypeVar("_Mergeable", bound=Hashable)


def _normalized(value: str) -> str:
    return " ".join(value.casefold().split())


def _merged(
    first: tuple[_Mergeable, ...],
    second: tuple[_Mergeable, ...],
) -> tuple[_Mergeable, ...]:
    return tuple(dict.fromkeys((*first, *second)))


@dataclass(frozen=True)
class LongTermEpisode:
    id: str
    user_id: str
    session_id: str
    event_id: str
    topic_id: str
    text: str
    relevance_score: float
    occurred_at: str
    stored_at: datetime


@dataclass(frozen=True)
class LongTermTemporalExpression:
    text: str
    applies_to: str


@dataclass(frozen=True)
class LongTermMemoryCandidate:
    user_id: str
    kind: LongTermMemoryKind
    subject: str
    relation: str
    object: str
    confidence: float
    memory_types: tuple[str, ...]
    evidence: tuple[str, ...]
    temporal_expressions: tuple[LongTermTemporalExpression, ...]
    source_record_ids: tuple[str, ...]
    source_state_ids: tuple[str, ...] = ()
    task_status: LongTermTaskStatus | None = None
    valid_from: datetime | None = None


@dataclass(frozen=True)
class LongTermMemory:
    id: str
    user_id: str
    kind: LongTermMemoryKind
    subject: str
    relation: str
    object: str
    confidence: float
    memory_types: tuple[str, ...]
    evidence: tuple[str, ...]
    temporal_expressions: tuple[LongTermTemporalExpression, ...]
    source_record_ids: tuple[str, ...]
    source_state_ids: tuple[str, ...]
    task_status: LongTermTaskStatus | None
    valid_from: datetime | None
    valid_until: datetime | None
    status: LongTermMemoryStatus
    created_at: datetime
    updated_at: datetime
    superseded_at: datetime | None


@dataclass(frozen=True)
class MemoryWriteResult:
    memory: LongTermMemory
    action: MemoryWriteAction
    superseded_ids: tuple[str, ...] = ()


class LongTermMemoryStore(Protocol):
    def store_episode(self, episode: LongTermEpisode) -> bool: ...

    def upsert(self, candidate: LongTermMemoryCandidate) -> MemoryWriteResult: ...


class InMemoryLongTermMemoryStore:
    def __init__(
        self,
        *,
        single_value_relations: Iterable[str] = (),
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        normalized_relations = {
            _normalized(relation) for relation in single_value_relations
        }
        if "" in normalized_relations:
            raise ValueError("single-value relations must not be empty")
        self._single_value_relations = normalized_relations
        self._memories: dict[str, list[LongTermMemory]] = {}
        self._episodes: dict[str, dict[str, LongTermEpisode]] = {}

    def store_episode(self, episode: LongTermEpisode) -> bool:
        if not episode.id.strip() or not episode.user_id.strip():
            raise ValueError("episode ID and user_id must not be empty")
        if not episode.text.strip():
            raise ValueError("episode text must not be empty")
        if not 0.0 <= episode.relevance_score <= 1.0:
            raise ValueError("episode relevance_score must be between 0 and 1")
        if episode.stored_at.tzinfo is None:
            raise ValueError("episode stored_at must be timezone-aware")
        episodes = self._episodes.setdefault(episode.user_id, {})
        existing = episodes.get(episode.id)
        if existing is not None and existing != episode:
            raise ValueError("episode ID already contains different data")
        if existing is not None:
            return False
        episodes[episode.id] = episode
        return True

    def upsert(self, candidate: LongTermMemoryCandidate) -> MemoryWriteResult:
        self._validate_candidate(candidate)
        now = self._now()
        memories = self._memories.setdefault(candidate.user_id, [])

        duplicate_index = self._find_current_duplicate(memories, candidate)
        if duplicate_index is not None:
            existing = memories[duplicate_index]
            updated = replace(
                existing,
                confidence=max(existing.confidence, candidate.confidence),
                memory_types=_merged(existing.memory_types, candidate.memory_types),
                evidence=_merged(existing.evidence, candidate.evidence),
                temporal_expressions=_merged(
                    existing.temporal_expressions,
                    candidate.temporal_expressions,
                ),
                source_record_ids=_merged(
                    existing.source_record_ids,
                    candidate.source_record_ids,
                ),
                source_state_ids=_merged(
                    existing.source_state_ids,
                    candidate.source_state_ids,
                ),
                task_status=candidate.task_status or existing.task_status,
                valid_from=candidate.valid_from or existing.valid_from,
                updated_at=now,
            )
            comparable = replace(updated, updated_at=existing.updated_at)
            if comparable == existing:
                return MemoryWriteResult(memory=existing, action="unchanged")
            memories[duplicate_index] = updated
            return MemoryWriteResult(memory=updated, action="updated")

        processed = self._find_processed_source(memories, candidate)
        if processed is not None:
            return MemoryWriteResult(memory=processed, action="unchanged")

        superseded_ids: list[str] = []
        if (
            candidate.kind == "fact"
            and _normalized(candidate.relation) in self._single_value_relations
        ):
            for index, existing in enumerate(memories):
                if not self._is_conflict(existing, candidate):
                    continue
                memories[index] = replace(
                    existing,
                    status="superseded",
                    valid_until=candidate.valid_from or existing.valid_until,
                    updated_at=now,
                    superseded_at=now,
                )
                superseded_ids.append(existing.id)

        memory = LongTermMemory(
            id=str(uuid4()),
            user_id=candidate.user_id,
            kind=candidate.kind,
            subject=candidate.subject.strip(),
            relation=candidate.relation.strip(),
            object=candidate.object.strip(),
            confidence=candidate.confidence,
            memory_types=candidate.memory_types,
            evidence=candidate.evidence,
            temporal_expressions=candidate.temporal_expressions,
            source_record_ids=candidate.source_record_ids,
            source_state_ids=candidate.source_state_ids,
            task_status=candidate.task_status,
            valid_from=candidate.valid_from,
            valid_until=None,
            status="current",
            created_at=now,
            updated_at=now,
            superseded_at=None,
        )
        memories.append(memory)
        return MemoryWriteResult(
            memory=memory,
            action="created",
            superseded_ids=tuple(superseded_ids),
        )

    def get_memories(
        self,
        *,
        user_id: str,
        include_superseded: bool = False,
        kind: LongTermMemoryKind | None = None,
    ) -> tuple[LongTermMemory, ...]:
        memories = self._memories.get(user_id, [])
        if not include_superseded:
            memories = [memory for memory in memories if memory.status == "current"]
        if kind is not None:
            memories = [memory for memory in memories if memory.kind == kind]
        return tuple(memories)

    def get_episodes(self, *, user_id: str) -> tuple[LongTermEpisode, ...]:
        return tuple(self._episodes.get(user_id, {}).values())

    @staticmethod
    def _find_current_duplicate(
        memories: list[LongTermMemory],
        candidate: LongTermMemoryCandidate,
    ) -> int | None:
        key = (
            candidate.kind,
            _normalized(candidate.subject),
            _normalized(candidate.relation),
            _normalized(candidate.object),
        )
        for index, memory in enumerate(memories):
            memory_key = (
                memory.kind,
                _normalized(memory.subject),
                _normalized(memory.relation),
                _normalized(memory.object),
            )
            if memory.status == "current" and memory_key == key:
                return index
        return None

    @staticmethod
    def _find_processed_source(
        memories: list[LongTermMemory],
        candidate: LongTermMemoryCandidate,
    ) -> LongTermMemory | None:
        candidate_key = (
            candidate.kind,
            _normalized(candidate.subject),
            _normalized(candidate.relation),
            _normalized(candidate.object),
        )
        for memory in memories:
            memory_key = (
                memory.kind,
                _normalized(memory.subject),
                _normalized(memory.relation),
                _normalized(memory.object),
            )
            same_records = bool(candidate.source_record_ids) and set(
                candidate.source_record_ids
            ).issubset(memory.source_record_ids)
            same_state = bool(candidate.source_state_ids) and set(
                candidate.source_state_ids
            ).issubset(memory.source_state_ids)
            if memory_key == candidate_key and (same_records or same_state):
                return memory
        return None

    @staticmethod
    def _is_conflict(
        memory: LongTermMemory,
        candidate: LongTermMemoryCandidate,
    ) -> bool:
        return (
            memory.status == "current"
            and memory.kind == "fact"
            and _normalized(memory.subject) == _normalized(candidate.subject)
            and _normalized(memory.relation) == _normalized(candidate.relation)
            and _normalized(memory.object) != _normalized(candidate.object)
        )

    @staticmethod
    def _validate_candidate(candidate: LongTermMemoryCandidate) -> None:
        if not candidate.user_id.strip():
            raise ValueError("candidate user_id must not be empty")
        if not candidate.subject.strip():
            raise ValueError("candidate subject must not be empty")
        if not candidate.relation.strip():
            raise ValueError("candidate relation must not be empty")
        if not candidate.object.strip():
            raise ValueError("candidate object must not be empty")
        if candidate.kind not in _VALID_KINDS:
            raise ValueError("candidate kind is invalid")
        if not 0.0 <= candidate.confidence <= 1.0:
            raise ValueError("candidate confidence must be between 0 and 1")
        if not candidate.memory_types:
            raise ValueError("candidate memory_types must not be empty")
        if not candidate.evidence or any(not item.strip() for item in candidate.evidence):
            raise ValueError("candidate evidence must not be empty")
        if not candidate.source_record_ids and not candidate.source_state_ids:
            raise ValueError("candidate must contain a source reference")
        if candidate.kind == "task" and candidate.task_status not in _VALID_TASK_STATUSES:
            raise ValueError("task candidates require a valid task_status")
        if candidate.kind != "task" and candidate.task_status is not None:
            raise ValueError("only task candidates may contain task_status")
        if candidate.valid_from is not None and candidate.valid_from.tzinfo is None:
            raise ValueError("valid_from must be timezone-aware")

    def _now(self) -> datetime:
        now = self._clock()
        if now.tzinfo is None:
            raise ValueError("clock must return a timezone-aware datetime")
        return now
