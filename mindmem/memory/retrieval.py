from dataclasses import dataclass

from mindmem.memory.reasoning_state import ReasoningStateItem
from mindmem.memory.short_term import ShortTermMemoryBuffer, ShortTermMemoryRecord
from mindmem.memory.topics import TopicGroup


@dataclass(frozen=True)
class ShortTermContext:
    user_id: str
    session_id: str
    topic: TopicGroup | None
    records: tuple[ShortTermMemoryRecord, ...]
    decisions: tuple[ReasoningStateItem, ...]
    open_tasks: tuple[ReasoningStateItem, ...]
    tool_results: tuple[ReasoningStateItem, ...]


class ShortTermContextRetriever:
    def __init__(self, memory: ShortTermMemoryBuffer) -> None:
        self.memory = memory

    def retrieve(
        self,
        *,
        user_id: str,
        session_id: str,
        topic_id: str | None = None,
        record_limit: int | None = None,
    ) -> ShortTermContext:
        if record_limit is not None and record_limit < 1:
            raise ValueError("record_limit must be at least 1")

        topic = self._resolve_topic(
            user_id=user_id,
            session_id=session_id,
            topic_id=topic_id,
        )
        if topic is None:
            return ShortTermContext(
                user_id=user_id,
                session_id=session_id,
                topic=None,
                records=(),
                decisions=(),
                open_tasks=(),
                tool_results=(),
            )

        records = self.memory.get_topic_records(topic.id)
        if record_limit is not None:
            records = records[-record_limit:]

        state = self.memory.get_reasoning_state(
            user_id=user_id,
            session_id=session_id,
            topic_id=topic.id,
        )
        return ShortTermContext(
            user_id=user_id,
            session_id=session_id,
            topic=topic,
            records=records,
            decisions=tuple(item for item in state if item.kind == "decision"),
            open_tasks=tuple(
                item
                for item in state
                if item.kind == "task" and item.status != "completed"
            ),
            tool_results=tuple(item for item in state if item.kind == "tool_result"),
        )

    def _resolve_topic(
        self,
        *,
        user_id: str,
        session_id: str,
        topic_id: str | None,
    ) -> TopicGroup | None:
        if topic_id is None:
            return self.memory.get_current_topic(
                user_id=user_id,
                session_id=session_id,
            )

        topics = self.memory.get_topics(user_id=user_id, session_id=session_id)
        topic = next((item for item in topics if item.id == topic_id), None)
        if topic is None:
            raise KeyError("topic does not belong to this user and session")
        return topic
