import unittest
from datetime import datetime, timedelta, timezone

from mindmem.input.text import RawTextInput, create_text_input_event
from mindmem.memory import ShortTermMemoryBuffer
from mindmem.sensory.extraction import (
    FactExtraction,
    MemoryExtractionResult,
)


class MutableClock:
    def __init__(self) -> None:
        self.now = datetime(2026, 8, 8, 10, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.now


def event_for(text: str, *, user_id: str = "user_1", session_id: str = "session_1"):
    return create_text_input_event(
        RawTextInput(user_id=user_id, session_id=session_id, text=text)
    )


def extraction_for(text: str) -> MemoryExtractionResult:
    return MemoryExtractionResult(
        source_text=text,
        memory_types=["other"],
        entities=[],
        facts=[
            FactExtraction(
                subject="user",
                relation="stated",
                object=text,
                evidence=text,
                confidence=1.0,
            )
        ],
        temporal_expressions=[],
    )


class ShortTermMemoryBufferTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = MutableClock()
        self.buffer = ShortTermMemoryBuffer(
            max_records_per_session=2,
            ttl=timedelta(minutes=30),
            clock=self.clock,
        )

    def store(self, text: str, *, session_id: str = "session_1"):
        event = event_for(text, session_id=session_id)
        return self.buffer.store(
            event=event,
            relevance_score=0.8,
            extraction=extraction_for(text),
        )

    def test_stores_and_returns_recent_records(self):
        first = self.store("First fact")
        second = self.store("Second fact")

        records = self.buffer.get_recent(
            user_id="user_1", session_id="session_1"
        )

        self.assertEqual(records, (first, second))
        self.assertEqual(records[0].extraction.source_text, "First fact")

    def test_keeps_sessions_separate(self):
        self.store("Session one")
        self.store("Session two", session_id="session_2")

        records = self.buffer.get_recent(
            user_id="user_1", session_id="session_1"
        )

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].extraction.source_text, "Session one")

    def test_removes_oldest_record_when_capacity_is_reached(self):
        self.store("First")
        second = self.store("Second")
        third = self.store("Third")

        records = self.buffer.get_recent(
            user_id="user_1", session_id="session_1"
        )

        self.assertEqual(records, (second, third))

    def test_expired_records_are_not_returned(self):
        self.store("Temporary fact")
        self.clock.now += timedelta(minutes=30)

        records = self.buffer.get_recent(
            user_id="user_1", session_id="session_1"
        )

        self.assertEqual(records, ())

    def test_clears_one_session(self):
        self.store("Session one")
        self.store("Session two", session_id="session_2")

        removed = self.buffer.clear_session(
            user_id="user_1", session_id="session_1"
        )

        self.assertEqual(removed, 1)
        self.assertEqual(
            self.buffer.get_recent(user_id="user_1", session_id="session_1"),
            (),
        )

    def test_rejects_extraction_from_another_event(self):
        event = event_for("Original text")

        with self.assertRaisesRegex(ValueError, "source_text"):
            self.buffer.store(
                event=event,
                relevance_score=0.8,
                extraction=extraction_for("Different text"),
            )


if __name__ == "__main__":
    unittest.main()
