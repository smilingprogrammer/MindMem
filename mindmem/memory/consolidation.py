from dataclasses import dataclass

from mindmem.memory.long_term import (
    LongTermEpisode,
    LongTermMemoryCandidate,
    LongTermMemoryStore,
    LongTermTemporalExpression,
    MemoryWriteResult,
)
from mindmem.memory.reasoning_state import ReasoningStateItem
from mindmem.memory.short_term import ShortTermMemoryBuffer, ShortTermMemoryRecord
from mindmem.memory.topics import TopicGroup


DEFAULT_DURABLE_MEMORY_TYPES = frozenset(
    {
        "identity",
        "preference",
        "goal",
        "task",
        "correction",
        "relationship",
        "project",
        "event",
    }
)


@dataclass(frozen=True)
class ConsolidationPolicy:
    durable_memory_types: frozenset[str] = DEFAULT_DURABLE_MEMORY_TYPES
    minimum_fact_confidence: float = 0.70
    minimum_relevance_score: float = 0.40
    include_decisions: bool = True
    include_tasks: bool = True
    include_tool_results: bool = True

    def __post_init__(self) -> None:
        if not 0.0 <= self.minimum_fact_confidence <= 1.0:
            raise ValueError("minimum_fact_confidence must be between 0 and 1")
        if not 0.0 <= self.minimum_relevance_score <= 1.0:
            raise ValueError("minimum_relevance_score must be between 0 and 1")


@dataclass(frozen=True)
class ConsolidationResult:
    topic_id: str
    episode_count: int
    candidate_count: int
    created_count: int
    updated_count: int
    unchanged_count: int
    skipped_fact_count: int
    superseded_memory_ids: tuple[str, ...]
    memories: tuple[MemoryWriteResult, ...]


class ShortTermConsolidator:
    def __init__(
        self,
        *,
        short_term_memory: ShortTermMemoryBuffer,
        long_term_memory: LongTermMemoryStore,
        policy: ConsolidationPolicy | None = None,
        automatic: bool = False,
    ) -> None:
        self.short_term_memory = short_term_memory
        self.long_term_memory = long_term_memory
        self.policy = policy or ConsolidationPolicy()
        if automatic:
            short_term_memory.set_consolidation_handler(self._consolidate_automatically)

    def _consolidate_automatically(self, topic: TopicGroup) -> ConsolidationResult:
        return self.consolidate_topic(
            user_id=topic.user_id, session_id=topic.session_id, topic_id=topic.id,
        )

    def consolidate_topic(
        self,
        *,
        user_id: str,
        session_id: str,
        topic_id: str | None = None,
    ) -> ConsolidationResult:
        topic = self._resolve_topic(
            user_id=user_id,
            session_id=session_id,
            topic_id=topic_id,
        )
        records = self.short_term_memory.get_topic_records(topic.id)
        for record in records:
            self.long_term_memory.store_episode(self._episode_from(record))

        candidates: list[LongTermMemoryCandidate] = []
        skipped_facts = 0
        for record in records:
            record_candidates, record_skipped = self._fact_candidates(record)
            candidates.extend(record_candidates)
            skipped_facts += record_skipped

        state = self.short_term_memory.get_reasoning_state(
            user_id=user_id,
            session_id=session_id,
            topic_id=topic.id,
        )
        candidates.extend(
            self._state_candidates(
                topic=topic,
                state=state,
                available_record_ids={record.id for record in records},
            )
        )

        writes = tuple(self.long_term_memory.upsert(item) for item in candidates)
        superseded_ids = tuple(
            memory_id
            for write in writes
            for memory_id in write.superseded_ids
        )
        return ConsolidationResult(
            topic_id=topic.id,
            episode_count=len(records),
            candidate_count=len(candidates),
            created_count=sum(write.action == "created" for write in writes),
            updated_count=sum(write.action == "updated" for write in writes),
            unchanged_count=sum(write.action == "unchanged" for write in writes),
            skipped_fact_count=skipped_facts,
            superseded_memory_ids=superseded_ids,
            memories=writes,
        )

    def _fact_candidates(
        self,
        record: ShortTermMemoryRecord,
    ) -> tuple[list[LongTermMemoryCandidate], int]:
        memory_types = frozenset(record.extraction.memory_types)
        durable = bool(memory_types.intersection(self.policy.durable_memory_types))
        temporal = tuple(
            LongTermTemporalExpression(text=item.text, applies_to=item.applies_to)
            for item in record.extraction.temporal_expressions
        )
        candidates: list[LongTermMemoryCandidate] = []
        skipped = 0
        for fact in record.extraction.facts:
            if (
                not durable
                or fact.confidence < self.policy.minimum_fact_confidence
                or record.relevance_score < self.policy.minimum_relevance_score
            ):
                skipped += 1
                continue
            candidates.append(
                LongTermMemoryCandidate(
                    user_id=record.user_id,
                    kind="fact",
                    subject=fact.subject,
                    relation=fact.relation,
                    object=fact.object,
                    confidence=min(fact.confidence, record.relevance_score),
                    memory_types=tuple(record.extraction.memory_types),
                    evidence=(fact.evidence,),
                    temporal_expressions=temporal,
                    source_record_ids=(record.id,),
                )
            )
        return candidates, skipped

    def _state_candidates(
        self,
        *,
        topic: TopicGroup,
        state: tuple[ReasoningStateItem, ...],
        available_record_ids: set[str],
    ) -> list[LongTermMemoryCandidate]:
        candidates: list[LongTermMemoryCandidate] = []
        for item in state:
            if item.kind == "decision" and not self.policy.include_decisions:
                continue
            if item.kind == "task" and not self.policy.include_tasks:
                continue
            if item.kind == "tool_result" and not self.policy.include_tool_results:
                continue

            candidates.append(
                LongTermMemoryCandidate(
                    user_id=item.user_id,
                    kind=item.kind,
                    subject=topic.label,
                    relation=item.kind,
                    object=item.content,
                    confidence=1.0,
                    memory_types=(item.kind,),
                    evidence=(item.content,),
                    temporal_expressions=(),
                    source_record_ids=(
                        (item.source_record_id,)
                        if item.source_record_id in available_record_ids
                        else ()
                    ),
                    source_state_ids=(item.id,),
                    task_status=item.status if item.kind == "task" else None,
                )
            )
        return candidates

    @staticmethod
    def _episode_from(record: ShortTermMemoryRecord) -> LongTermEpisode:
        return LongTermEpisode(
            id=record.id,
            user_id=record.user_id,
            session_id=record.session_id,
            event_id=record.event_id,
            topic_id=record.topic_id,
            text=record.extraction.source_text,
            relevance_score=record.relevance_score,
            occurred_at=record.event_timestamp,
            stored_at=record.stored_at,
        )

    def _resolve_topic(
        self,
        *,
        user_id: str,
        session_id: str,
        topic_id: str | None,
    ) -> TopicGroup:
        topics = self.short_term_memory.get_topics(
            user_id=user_id,
            session_id=session_id,
        )
        if topic_id is None:
            topic = self.short_term_memory.get_current_topic(
                user_id=user_id,
                session_id=session_id,
            )
            if topic is None:
                raise ValueError("no topic exists for this user and session")
            return topic

        topic = next((item for item in topics if item.id == topic_id), None)
        if topic is None:
            raise KeyError("topic does not belong to this user and session")
        return topic
