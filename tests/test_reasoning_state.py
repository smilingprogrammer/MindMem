import unittest
from datetime import datetime, timedelta, timezone

from mindmem.input.text import RawTextInput, create_text_input_event
from mindmem.memory import ShortTermMemoryBuffer
from mindmem.sensory.extraction import (
    EntityExtraction,
    FactExtraction,
    MemoryExtractionResult,
)


class MutableClock:
    def __init__(self) -> None:
        self.now = datetime(2026, 8, 10, 10, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        current = self.now
        self.now += timedelta(seconds=1)
        return current


def store_project_record(
    buffer: ShortTermMemoryBuffer,
    *,
    text: str = "Apollo uses Stripe.",
    entity_name: str = "Apollo",
    memory_types: list[str] | None = None,
    session_id: str = "session_1",
):
    event = create_text_input_event(
        RawTextInput(user_id="user_1", session_id=session_id, text=text)
    )
    extraction = MemoryExtractionResult(
        source_text=text,
        memory_types=memory_types or ["project"],
        entities=[
            EntityExtraction(
                name=entity_name,
                type="project",
                evidence=entity_name,
                confidence=1.0,
            )
        ],
        facts=[
            FactExtraction(
                subject=entity_name,
                relation="uses",
                object="Stripe",
                evidence=text,
                confidence=1.0,
            )
        ],
        temporal_expressions=[],
    )
    return buffer.store(event=event, relevance_score=0.8, extraction=extraction)


class ReasoningStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.buffer = ShortTermMemoryBuffer(clock=MutableClock())
        self.record = store_project_record(self.buffer)

    def test_adds_decision_to_current_topic(self):
        decision = self.buffer.add_decision(
            user_id="user_1",
            session_id="session_1",
            content="Use Stripe for Apollo payments.",
        )

        self.assertEqual(decision.kind, "decision")
        self.assertEqual(decision.status, "recorded")
        self.assertEqual(decision.topic_id, self.record.topic_id)

    def test_adds_and_updates_task(self):
        task = self.buffer.add_task(
            user_id="user_1",
            session_id="session_1",
            content="Finish the payment integration.",
        )

        updated = self.buffer.update_task(task_id=task.id, status="completed")

        self.assertEqual(updated.status, "completed")
        self.assertGreater(updated.updated_at, updated.created_at)

    def test_adds_tool_result(self):
        result = self.buffer.add_tool_result(
            user_id="user_1",
            session_id="session_1",
            content="Deployment completed successfully.",
            source_record_id=self.record.id,
        )

        self.assertEqual(result.kind, "tool_result")
        self.assertEqual(result.source_record_id, self.record.id)

    def test_state_update_reactivates_its_topic(self):
        apollo_topic_id = self.record.topic_id
        for name in ("Atlas", "Orion", "Nova"):
            store_project_record(
                self.buffer,
                text=f"{name} uses Stripe.",
                entity_name=name,
            )

        self.buffer.add_decision(
            user_id="user_1",
            session_id="session_1",
            topic_id=apollo_topic_id,
            content="Return to Apollo.",
        )

        active_ids = {
            topic.id
            for topic in self.buffer.get_topics(
                user_id="user_1",
                session_id="session_1",
                active_only=True,
            )
        }
        self.assertIn(apollo_topic_id, active_ids)

    def test_rejects_invalid_task_status(self):
        task = self.buffer.add_task(
            user_id="user_1",
            session_id="session_1",
            content="Implement Stripe.",
        )

        with self.assertRaisesRegex(ValueError, "invalid task status"):
            self.buffer.update_task(task_id=task.id, status="unknown")

    def test_task_memory_is_captured_automatically(self):
        buffer = ShortTermMemoryBuffer(clock=MutableClock())
        record = store_project_record(
            buffer,
            text="Finish Apollo before Friday.",
            memory_types=["task", "project"],
        )

        tasks = buffer.get_reasoning_state(
            user_id="user_1",
            session_id="session_1",
            kind="task",
        )

        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].content, "Finish Apollo before Friday.")
        self.assertEqual(tasks[0].source_record_id, record.id)

    def test_filters_state_by_topic_and_kind(self):
        self.buffer.add_decision(
            user_id="user_1",
            session_id="session_1",
            content="Use Stripe.",
        )
        self.buffer.add_task(
            user_id="user_1",
            session_id="session_1",
            content="Implement Stripe.",
        )

        decisions = self.buffer.get_reasoning_state(
            user_id="user_1",
            session_id="session_1",
            topic_id=self.record.topic_id,
            kind="decision",
        )

        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0].content, "Use Stripe.")

    def test_rejects_a_source_record_from_another_topic(self):
        other = store_project_record(
            self.buffer,
            text="Atlas uses Stripe.",
            session_id="session_2",
        )

        with self.assertRaisesRegex(ValueError, "source_record_id"):
            self.buffer.add_tool_result(
                user_id="user_1",
                session_id="session_1",
                content="A result.",
                source_record_id=other.id,
            )

    def test_clear_session_removes_state_and_topics(self):
        self.buffer.add_decision(
            user_id="user_1",
            session_id="session_1",
            content="Use Stripe.",
        )

        self.buffer.clear_session(user_id="user_1", session_id="session_1")

        self.assertEqual(
            self.buffer.get_topics(user_id="user_1", session_id="session_1"),
            (),
        )
        self.assertEqual(
            self.buffer.get_reasoning_state(
                user_id="user_1", session_id="session_1"
            ),
            (),
        )

    def test_eviction_removes_state_when_its_topic_becomes_empty(self):
        buffer = ShortTermMemoryBuffer(
            max_records_per_session=1,
            clock=MutableClock(),
        )
        first = store_project_record(buffer)
        buffer.add_decision(
            user_id="user_1",
            session_id="session_1",
            topic_id=first.topic_id,
            content="Use Stripe.",
        )

        store_project_record(
            buffer,
            text="Atlas uses Postgres.",
            entity_name="Atlas",
        )

        self.assertEqual(
            buffer.get_reasoning_state(
                user_id="user_1",
                session_id="session_1",
            ),
            (),
        )


if __name__ == "__main__":
    unittest.main()
