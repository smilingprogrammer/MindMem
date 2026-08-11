import unittest
from datetime import datetime, timedelta, timezone

from mindmem.input.text import RawTextInput, create_text_input_event
from mindmem.memory import ShortTermContextRetriever, ShortTermMemoryBuffer
from mindmem.sensory.extraction import (
    EntityExtraction,
    FactExtraction,
    MemoryExtractionResult,
)


class MutableClock:
    def __init__(self) -> None:
        self.now = datetime(2026, 8, 11, 10, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        current = self.now
        self.now += timedelta(seconds=1)
        return current


def store_project(
    memory: ShortTermMemoryBuffer,
    *,
    text: str,
    project: str,
):
    event = create_text_input_event(
        RawTextInput(user_id="user_1", session_id="session_1", text=text)
    )
    extraction = MemoryExtractionResult(
        source_text=text,
        memory_types=["project"],
        entities=[
            EntityExtraction(
                name=project,
                type="project",
                evidence=project,
                confidence=1.0,
            )
        ],
        facts=[
            FactExtraction(
                subject="user",
                relation="discussed",
                object=project,
                evidence=text,
                confidence=1.0,
            )
        ],
        temporal_expressions=[],
    )
    return memory.store(event=event, relevance_score=0.8, extraction=extraction)


class ShortTermContextRetrieverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.memory = ShortTermMemoryBuffer(clock=MutableClock())
        self.retriever = ShortTermContextRetriever(self.memory)

    def test_returns_empty_context_when_the_session_has_no_topic(self):
        context = self.retriever.retrieve(
            user_id="user_1",
            session_id="session_1",
        )

        self.assertIsNone(context.topic)
        self.assertEqual(context.records, ())
        self.assertEqual(context.open_tasks, ())

    def test_retrieves_current_topic_records_and_state(self):
        first = store_project(
            self.memory,
            text="Apollo uses Stripe.",
            project="Apollo",
        )
        store_project(
            self.memory,
            text="Apollo launches Friday.",
            project="Apollo",
        )
        self.memory.add_decision(
            user_id="user_1",
            session_id="session_1",
            content="Use Stripe.",
        )
        task = self.memory.add_task(
            user_id="user_1",
            session_id="session_1",
            content="Finish checkout.",
        )
        self.memory.add_tool_result(
            user_id="user_1",
            session_id="session_1",
            content="Stripe connection succeeded.",
        )

        context = self.retriever.retrieve(
            user_id="user_1",
            session_id="session_1",
        )

        self.assertEqual(context.topic.id, first.topic_id)
        self.assertEqual(len(context.records), 2)
        self.assertEqual([item.kind for item in context.decisions], ["decision"])
        self.assertEqual(context.open_tasks, (task,))
        self.assertEqual([item.kind for item in context.tool_results], ["tool_result"])

    def test_completed_tasks_are_not_returned_as_open_tasks(self):
        store_project(self.memory, text="Apollo uses Stripe.", project="Apollo")
        task = self.memory.add_task(
            user_id="user_1",
            session_id="session_1",
            content="Finish checkout.",
        )
        self.memory.update_task(task_id=task.id, status="completed")

        context = self.retriever.retrieve(
            user_id="user_1",
            session_id="session_1",
        )

        self.assertEqual(context.open_tasks, ())

    def test_can_retrieve_a_specific_non_current_topic(self):
        apollo = store_project(
            self.memory,
            text="Apollo uses Stripe.",
            project="Apollo",
        )
        store_project(self.memory, text="Atlas uses Redis.", project="Atlas")

        context = self.retriever.retrieve(
            user_id="user_1",
            session_id="session_1",
            topic_id=apollo.topic_id,
        )

        self.assertEqual(context.topic.label, "Apollo")
        self.assertEqual(len(context.records), 1)

    def test_applies_the_record_limit_to_the_latest_topic_records(self):
        store_project(self.memory, text="Apollo one.", project="Apollo")
        latest = store_project(self.memory, text="Apollo two.", project="Apollo")

        context = self.retriever.retrieve(
            user_id="user_1",
            session_id="session_1",
            record_limit=1,
        )

        self.assertEqual([record.id for record in context.records], [latest.id])

    def test_rejects_a_topic_from_another_session(self):
        record = store_project(
            self.memory,
            text="Apollo uses Stripe.",
            project="Apollo",
        )

        with self.assertRaisesRegex(KeyError, "does not belong"):
            self.retriever.retrieve(
                user_id="user_1",
                session_id="session_2",
                topic_id=record.topic_id,
            )

    def test_rejects_an_invalid_record_limit(self):
        with self.assertRaisesRegex(ValueError, "record_limit"):
            self.retriever.retrieve(
                user_id="user_1",
                session_id="session_1",
                record_limit=0,
            )


if __name__ == "__main__":
    unittest.main()
