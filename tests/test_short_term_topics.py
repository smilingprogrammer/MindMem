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


def extraction_for(
    text: str,
    *,
    entity_name: str,
    entity_type: str,
    person_name: str | None = None,
) -> MemoryExtractionResult:
    entities = [
        EntityExtraction(
            name=entity_name,
            type=entity_type,
            evidence=entity_name,
            confidence=1.0,
        )
    ]
    if person_name is not None:
        entities.append(
            EntityExtraction(
                name=person_name,
                type="person",
                evidence=person_name,
                confidence=1.0,
            )
        )
    return MemoryExtractionResult(
        source_text=text,
        memory_types=["project" if entity_type == "project" else "other"],
        entities=entities,
        facts=[
            FactExtraction(
                subject="user",
                relation="discussed",
                object=entity_name,
                evidence=text,
                confidence=1.0,
            )
        ],
        temporal_expressions=[],
    )


class TopicGroupingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.buffer = ShortTermMemoryBuffer(
            max_records_per_session=10,
            max_active_topics_per_session=2,
            clock=MutableClock(),
        )

    def store(
        self,
        text: str,
        *,
        entity_name: str,
        entity_type: str = "project",
        session_id: str = "session_1",
    ):
        event = create_text_input_event(
            RawTextInput(user_id="user_1", session_id=session_id, text=text)
        )
        return self.buffer.store(
            event=event,
            relevance_score=0.8,
            extraction=extraction_for(
                text,
                entity_name=entity_name,
                entity_type=entity_type,
            ),
        )

    def topics(self, *, session_id: str = "session_1", active_only: bool = False):
        return self.buffer.get_topics(
            user_id="user_1",
            session_id=session_id,
            active_only=active_only,
        )

    def test_groups_records_with_the_same_project_entity(self):
        first = self.store(
            "Apollo project deadline changed.",
            entity_name="Apollo project",
        )
        second = self.store(
            "Apollo payment integration failed.",
            entity_name="Apollo",
        )

        topics = self.topics()

        self.assertEqual(len(topics), 1)
        self.assertEqual(topics[0].record_ids, (first.id, second.id))
        self.assertEqual(first.topic_id, second.topic_id)

    def test_creates_separate_topics_for_unrelated_entities(self):
        self.store("Apollo changed.", entity_name="Apollo")
        self.store("I will visit Lagos.", entity_name="Lagos", entity_type="place")

        self.assertEqual({topic.label for topic in self.topics()}, {"Apollo", "Lagos"})

    def test_shared_person_does_not_merge_different_named_projects(self):
        first_text = "Sarah changed Apollo."
        first_event = create_text_input_event(
            RawTextInput(user_id="user_1", session_id="session_1", text=first_text)
        )
        self.buffer.store(
            event=first_event,
            relevance_score=0.8,
            extraction=extraction_for(
                first_text,
                entity_name="Apollo",
                entity_type="project",
                person_name="Sarah",
            ),
        )
        second_text = "Sarah changed Atlas."
        second_event = create_text_input_event(
            RawTextInput(user_id="user_1", session_id="session_1", text=second_text)
        )
        self.buffer.store(
            event=second_event,
            relevance_score=0.8,
            extraction=extraction_for(
                second_text,
                entity_name="Atlas",
                entity_type="project",
                person_name="Sarah",
            ),
        )

        self.assertEqual({topic.label for topic in self.topics()}, {"Apollo", "Atlas"})

    def test_groups_matching_fact_objects_when_entities_are_absent(self):
        for text in (
            "The payment integration failed.",
            "We fixed the payment integration.",
        ):
            event = create_text_input_event(
                RawTextInput(user_id="user_1", session_id="session_1", text=text)
            )
            extraction = MemoryExtractionResult(
                source_text=text,
                memory_types=["project"],
                entities=[],
                facts=[
                    FactExtraction(
                        subject="user",
                        relation="discussed",
                        object="payment integration",
                        evidence=text,
                        confidence=1.0,
                    )
                ],
                temporal_expressions=[],
            )
            self.buffer.store(
                event=event,
                relevance_score=0.8,
                extraction=extraction,
            )

        topics = self.topics()

        self.assertEqual(len(topics), 1)
        self.assertEqual(len(topics[0].record_ids), 2)

    def test_only_most_recent_topics_remain_active(self):
        self.store("Apollo changed.", entity_name="Apollo")
        self.store("Atlas changed.", entity_name="Atlas")
        self.store("Orion changed.", entity_name="Orion")

        active = self.topics(active_only=True)

        self.assertEqual([topic.label for topic in active], ["Atlas", "Orion"])
        self.assertFalse(self.topics()[0].is_active)

    def test_reusing_an_inactive_topic_reactivates_it(self):
        self.store("Apollo changed.", entity_name="Apollo")
        self.store("Atlas changed.", entity_name="Atlas")
        self.store("Orion changed.", entity_name="Orion")
        self.store("Apollo shipped.", entity_name="Apollo")

        active = self.topics(active_only=True)

        self.assertEqual([topic.label for topic in active], ["Orion", "Apollo"])

    def test_topics_are_isolated_by_session(self):
        self.store("Apollo changed.", entity_name="Apollo")
        self.store(
            "Apollo changed elsewhere.",
            entity_name="Apollo",
            session_id="session_2",
        )

        self.assertEqual(len(self.topics()), 1)
        self.assertEqual(len(self.topics(session_id="session_2")), 1)
        self.assertNotEqual(self.topics()[0].id, self.topics(session_id="session_2")[0].id)

    def test_eviction_removes_an_empty_topic(self):
        buffer = ShortTermMemoryBuffer(max_records_per_session=1, clock=MutableClock())
        first_event = create_text_input_event(
            RawTextInput(user_id="user_1", session_id="session_1", text="Apollo")
        )
        buffer.store(
            event=first_event,
            relevance_score=0.8,
            extraction=extraction_for(
                "Apollo", entity_name="Apollo", entity_type="project"
            ),
        )
        second_event = create_text_input_event(
            RawTextInput(user_id="user_1", session_id="session_1", text="Lagos")
        )
        buffer.store(
            event=second_event,
            relevance_score=0.8,
            extraction=extraction_for(
                "Lagos", entity_name="Lagos", entity_type="place"
            ),
        )

        topics = buffer.get_topics(user_id="user_1", session_id="session_1")

        self.assertEqual([topic.label for topic in topics], ["Lagos"])


if __name__ == "__main__":
    unittest.main()
