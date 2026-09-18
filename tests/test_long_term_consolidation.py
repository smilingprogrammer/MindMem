import unittest
from datetime import datetime, timedelta, timezone

from mindmem.input.text import RawTextInput, create_text_input_event
from mindmem.memory import (
    ConsolidationPolicy,
    InMemoryLongTermMemoryStore,
    ShortTermConsolidator,
    ShortTermMemoryBuffer,
)
from mindmem.sensory.extraction import (
    EntityExtraction,
    FactExtraction,
    MemoryExtractionResult,
)


class MutableClock:
    def __init__(self) -> None:
        self.now = datetime(2026, 9, 8, 10, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        current = self.now
        self.now += timedelta(seconds=1)
        return current


def store_fact(
    memory: ShortTermMemoryBuffer,
    *,
    text: str,
    subject: str = "Apollo",
    relation: str = "deadline",
    object_: str = "Friday",
    memory_type: str = "project",
    confidence: float = 1.0,
    relevance_score: float = 0.8,
    session_id: str = "session_1",
):
    event = create_text_input_event(
        RawTextInput(
            user_id="user_1",
            session_id=session_id,
            text=text,
            timestamp="2026-09-08T09:00:00+00:00",
        )
    )
    extraction = MemoryExtractionResult(
        source_text=text,
        memory_types=[memory_type],
        entities=[
            EntityExtraction(
                name=subject,
                type="project",
                evidence=subject,
                confidence=1.0,
            )
        ],
        facts=[
            FactExtraction(
                subject=subject,
                relation=relation,
                object=object_,
                evidence=text,
                confidence=confidence,
            )
        ],
        temporal_expressions=[],
    )
    return memory.store(
        event=event,
        relevance_score=relevance_score,
        extraction=extraction,
    )


class LongTermConsolidationTests(unittest.TestCase):
    def enable_automatic(self, **kwargs):
        self.short_term = ShortTermMemoryBuffer(**kwargs)
        self.consolidator = ShortTermConsolidator(
            short_term_memory=self.short_term, long_term_memory=self.long_term,
            automatic=True,
        )

    def test_automatic_inactive_topic(self):
        self.enable_automatic(max_active_topics_per_session=1)
        store_fact(self.short_term, text="Apollo deadline is Friday.")
        store_fact(self.short_term, text="Atlas deadline is Monday.", subject="Atlas", object_="Monday")
        memories = self.long_term.get_memories(user_id="user_1")
        self.assertEqual([item.subject for item in memories], ["Apollo"])

    def test_automatic_eviction_preserves_fact_and_state(self):
        self.enable_automatic(max_records_per_session=1)
        store_fact(self.short_term, text="Apollo deadline is Friday.")
        self.short_term.add_decision(user_id="user_1", session_id="session_1", content="Use Stripe")
        store_fact(self.short_term, text="Atlas deadline is Monday.", subject="Atlas")
        memories = self.long_term.get_memories(user_id="user_1")
        self.assertEqual({item.kind for item in memories}, {"fact", "decision"})
        self.assertEqual(len(self.short_term.get_recent(user_id="user_1", session_id="session_1")), 1)

    def test_task_update_consolidates_displaced_topic(self):
        self.enable_automatic(max_active_topics_per_session=1)
        store_fact(self.short_term, text="Apollo deadline is Friday.")
        task = self.short_term.add_task(user_id="user_1", session_id="session_1", content="Test Apollo")
        store_fact(self.short_term, text="Atlas deadline is Monday.", subject="Atlas")
        self.short_term.update_task(task_id=task.id, status="completed")
        facts = [item.subject for item in self.long_term.get_memories(user_id="user_1") if item.kind == "fact"]
        self.assertEqual(set(facts), {"Apollo", "Atlas"})

    def test_inactivity_failure_can_retry_without_resubmitting_message(self):
        from unittest.mock import patch

        self.enable_automatic(max_active_topics_per_session=1)
        store_fact(self.short_term, text="Apollo deadline is Friday.")
        with patch.object(self.long_term, "upsert", side_effect=RuntimeError("offline")):
            with self.assertRaises(RuntimeError):
                store_fact(self.short_term, text="Atlas deadline is Monday.", subject="Atlas")
        self.short_term.end_session(user_id="user_1", session_id="session_1")
        self.assertEqual(len(self.long_term.get_memories(user_id="user_1")), 2)
        self.assertEqual(len(self.short_term.get_recent(user_id="user_1", session_id="session_1")), 2)

    def test_end_session_is_scoped_and_repeatable(self):
        self.enable_automatic()
        store_fact(self.short_term, text="Apollo deadline is Friday.")
        store_fact(self.short_term, text="Atlas deadline is Monday.", subject="Atlas", session_id="other")
        for _ in range(2):
            self.short_term.end_session(user_id="user_1", session_id="session_1")
        self.assertEqual([item.subject for item in self.long_term.get_memories(user_id="user_1")], ["Apollo"])
        self.assertEqual(len(self.short_term.get_recent(user_id="user_1", session_id="session_1")), 1)

    def test_storage_failure_prevents_eviction_and_can_retry(self):
        from unittest.mock import patch

        self.enable_automatic(max_records_per_session=1)
        record = store_fact(self.short_term, text="Apollo deadline is Friday.")
        with patch.object(self.long_term, "upsert", side_effect=RuntimeError("offline")):
            with self.assertRaisesRegex(RuntimeError, "offline"):
                store_fact(self.short_term, text="Atlas deadline is Monday.", subject="Atlas")
        self.assertEqual(self.short_term.get_recent(user_id="user_1", session_id="session_1"), (record,))
        store_fact(self.short_term, text="Atlas deadline is Monday.", subject="Atlas")
        self.assertEqual(len(self.long_term.get_memories(user_id="user_1")), 1)

    def setUp(self) -> None:
        self.clock = MutableClock()
        self.short_term = ShortTermMemoryBuffer(clock=self.clock)
        self.long_term = InMemoryLongTermMemoryStore(clock=self.clock)
        self.consolidator = ShortTermConsolidator(
            short_term_memory=self.short_term,
            long_term_memory=self.long_term,
        )

    def consolidate_current(self):
        return self.consolidator.consolidate_topic(
            user_id="user_1",
            session_id="session_1",
        )

    def test_promotes_a_durable_fact_and_preserves_its_episode(self):
        record = store_fact(
            self.short_term,
            text="Apollo deadline is Friday.",
        )

        result = self.consolidate_current()
        memories = self.long_term.get_memories(user_id="user_1")
        episodes = self.long_term.get_episodes(user_id="user_1")

        self.assertEqual(result.created_count, 1)
        self.assertEqual(memories[0].source_record_ids, (record.id,))
        self.assertEqual(memories[0].evidence, ("Apollo deadline is Friday.",))
        self.assertEqual(episodes[0].text, "Apollo deadline is Friday.")
        self.assertEqual(episodes[0].occurred_at, record.event_timestamp)

    def test_skips_non_durable_and_low_confidence_facts(self):
        store_fact(
            self.short_term,
            text="Apollo was mentioned.",
            memory_type="other",
        )
        store_fact(
            self.short_term,
            text="Apollo deadline may be Friday.",
            confidence=0.4,
        )

        result = self.consolidate_current()

        self.assertEqual(result.skipped_fact_count, 2)
        self.assertEqual(self.long_term.get_memories(user_id="user_1"), ())

    def test_merges_exact_duplicate_facts_and_source_records(self):
        first = store_fact(
            self.short_term,
            text="Apollo deadline is Friday.",
        )
        second = store_fact(
            self.short_term,
            text="The Apollo deadline remains Friday.",
        )

        result = self.consolidate_current()
        memories = self.long_term.get_memories(user_id="user_1")

        self.assertEqual(result.created_count, 1)
        self.assertEqual(result.updated_count, 1)
        self.assertEqual(len(memories), 1)
        self.assertEqual(memories[0].source_record_ids, (first.id, second.id))

    def test_versions_conflicts_only_for_configured_single_value_relations(self):
        long_term = InMemoryLongTermMemoryStore(
            single_value_relations={"deadline"},
            clock=self.clock,
        )
        consolidator = ShortTermConsolidator(
            short_term_memory=self.short_term,
            long_term_memory=long_term,
        )
        store_fact(
            self.short_term,
            text="Apollo deadline is Monday.",
            object_="Monday",
        )
        consolidator.consolidate_topic(
            user_id="user_1",
            session_id="session_1",
        )
        store_fact(
            self.short_term,
            text="Apollo deadline is Friday.",
            object_="Friday",
        )

        result = consolidator.consolidate_topic(
            user_id="user_1",
            session_id="session_1",
        )
        history = long_term.get_memories(
            user_id="user_1",
            include_superseded=True,
        )

        self.assertEqual(len(result.superseded_memory_ids), 1)
        self.assertEqual([item.object for item in history if item.status == "current"], ["Friday"])
        self.assertEqual([item.object for item in history if item.status == "superseded"], ["Monday"])

    def test_does_not_treat_unconfigured_multi_value_relation_as_conflict(self):
        store_fact(
            self.short_term,
            text="Apollo uses Stripe.",
            relation="uses",
            object_="Stripe",
        )
        store_fact(
            self.short_term,
            text="Apollo uses Postgres.",
            relation="uses",
            object_="Postgres",
        )

        self.consolidate_current()

        memories = self.long_term.get_memories(user_id="user_1")
        self.assertEqual({item.object for item in memories}, {"Stripe", "Postgres"})

    def test_promotes_decisions_tasks_and_tool_results(self):
        record = store_fact(
            self.short_term,
            text="Apollo uses Stripe.",
            relation="uses",
            object_="Stripe",
        )
        self.short_term.add_decision(
            user_id="user_1",
            session_id="session_1",
            content="Keep Stripe.",
            source_record_id=record.id,
        )
        task = self.short_term.add_task(
            user_id="user_1",
            session_id="session_1",
            content="Test checkout.",
        )
        self.short_term.update_task(task_id=task.id, status="in_progress")
        self.short_term.add_tool_result(
            user_id="user_1",
            session_id="session_1",
            content="Stripe sandbox connected.",
        )

        self.consolidate_current()
        memories = self.long_term.get_memories(user_id="user_1")

        self.assertEqual(
            {item.kind for item in memories},
            {"fact", "decision", "task", "tool_result"},
        )
        task_memory = next(item for item in memories if item.kind == "task")
        self.assertEqual(task_memory.task_status, "in_progress")

    def test_policy_can_exclude_state_types(self):
        store_fact(self.short_term, text="Apollo uses Stripe.")
        self.short_term.add_decision(
            user_id="user_1",
            session_id="session_1",
            content="Keep Stripe.",
        )
        consolidator = ShortTermConsolidator(
            short_term_memory=self.short_term,
            long_term_memory=self.long_term,
            policy=ConsolidationPolicy(include_decisions=False),
        )

        consolidator.consolidate_topic(
            user_id="user_1",
            session_id="session_1",
        )

        self.assertEqual(
            self.long_term.get_memories(user_id="user_1", kind="decision"),
            (),
        )

    def test_reconsolidation_updates_a_tasks_status(self):
        store_fact(self.short_term, text="Apollo uses Stripe.")
        task = self.short_term.add_task(
            user_id="user_1",
            session_id="session_1",
            content="Test checkout.",
        )
        self.consolidate_current()
        self.short_term.update_task(task_id=task.id, status="completed")

        result = self.consolidate_current()
        task_memory = self.long_term.get_memories(
            user_id="user_1",
            kind="task",
        )[0]

        self.assertEqual(result.updated_count, 1)
        self.assertEqual(task_memory.task_status, "completed")

    def test_state_does_not_reference_an_evicted_episode(self):
        short_term = ShortTermMemoryBuffer(
            max_records_per_session=1,
            clock=self.clock,
        )
        first = store_fact(short_term, text="Apollo uses Stripe.")
        short_term.add_decision(
            user_id="user_1",
            session_id="session_1",
            content="Keep Stripe.",
            source_record_id=first.id,
        )
        store_fact(short_term, text="Apollo launches Friday.")
        consolidator = ShortTermConsolidator(
            short_term_memory=short_term,
            long_term_memory=self.long_term,
        )

        consolidator.consolidate_topic(
            user_id="user_1",
            session_id="session_1",
        )
        decision = self.long_term.get_memories(
            user_id="user_1",
            kind="decision",
        )[0]

        self.assertEqual(decision.source_record_ids, ())
        self.assertEqual(len(decision.source_state_ids), 1)

    def test_reconsolidation_is_idempotent_even_after_a_conflict(self):
        long_term = InMemoryLongTermMemoryStore(
            single_value_relations={"deadline"},
            clock=self.clock,
        )
        consolidator = ShortTermConsolidator(
            short_term_memory=self.short_term,
            long_term_memory=long_term,
        )
        store_fact(
            self.short_term,
            text="Apollo deadline is Monday.",
            object_="Monday",
        )
        store_fact(
            self.short_term,
            text="Apollo deadline is Friday.",
            object_="Friday",
        )

        consolidator.consolidate_topic(
            user_id="user_1",
            session_id="session_1",
        )
        second = consolidator.consolidate_topic(
            user_id="user_1",
            session_id="session_1",
        )
        history = long_term.get_memories(
            user_id="user_1",
            include_superseded=True,
        )

        self.assertEqual(second.created_count, 0)
        self.assertEqual(second.superseded_memory_ids, ())
        self.assertEqual(len(history), 2)
        self.assertEqual([item.object for item in history if item.status == "current"], ["Friday"])

    def test_rejects_a_topic_from_another_session(self):
        record = store_fact(
            self.short_term,
            text="Apollo deadline is Friday.",
        )

        with self.assertRaisesRegex(KeyError, "does not belong"):
            self.consolidator.consolidate_topic(
                user_id="user_1",
                session_id="session_2",
                topic_id=record.topic_id,
            )


if __name__ == "__main__":
    unittest.main()
