import unittest
from typing import Any, Mapping

from mindmem.input.text import RawTextInput, create_text_input_event
from mindmem.sensory.lightweight_relevance import RelevanceResult
from mindmem.sensory.relevance.llm_relevance import (
    LLMRelevanceScorer,
    LLMResponseValidationError,
    LLMScoringNotRequired,
)


class FakeProvider:
    def __init__(self, response: Mapping[str, Any]):
        self.response = response
        self.last_input: Mapping[str, Any] | None = None
        self.last_schema: Mapping[str, Any] | None = None

    def generate_json(self, *, input_data, output_schema, instructions):
        self.last_input = input_data
        self.last_schema = output_schema
        return self.response


def event_for(text: str):
    return create_text_input_event(
        RawTextInput(user_id="user-1", session_id="session-1", text=text)
    )


UNCLEAR = RelevanceResult(score=0.0, label="unclear", signals=())


class LLMRelevanceScorerTests(unittest.TestCase):
    def test_scores_only_unclear_messages(self):
        provider = FakeProvider({"score": 0.8, "label": "relevant"})
        scorer = LLMRelevanceScorer(provider)

        result = scorer.score(event_for("The server stopped again."), UNCLEAR)

        self.assertEqual(result.label, "relevant")
        self.assertEqual(provider.last_input["text"], "The server stopped again.")

    def test_reason_is_absent_by_default(self):
        provider = FakeProvider({"score": 0.2, "label": "noise"})
        scorer = LLMRelevanceScorer(provider)

        result = scorer.score(event_for("Something happened."), UNCLEAR)

        self.assertIsNone(result.reason)
        self.assertNotIn("reason", provider.last_schema["properties"])

    def test_reason_is_requested_when_enabled(self):
        provider = FakeProvider(
            {"score": 0.8, "label": "relevant", "reason": "A meaningful update."}
        )
        scorer = LLMRelevanceScorer(provider)

        result = scorer.score(
            event_for("The server stopped again."),
            UNCLEAR,
            include_reason=True,
        )

        self.assertEqual(result.reason, "A meaningful update.")
        self.assertIn("reason", provider.last_schema["properties"])

    def test_rejects_schema_invalid_output(self):
        provider = FakeProvider({"score": 2.0, "label": "relevant"})
        scorer = LLMRelevanceScorer(provider)

        with self.assertRaises(LLMResponseValidationError):
            scorer.score(event_for("The server stopped again."), UNCLEAR)

    def test_rejects_inconsistent_label(self):
        provider = FakeProvider({"score": 0.2, "label": "relevant"})
        scorer = LLMRelevanceScorer(provider)

        with self.assertRaises(LLMResponseValidationError):
            scorer.score(event_for("The server stopped again."), UNCLEAR)

    def test_rejects_messages_already_classified_by_heuristics(self):
        provider = FakeProvider({"score": 0.8, "label": "relevant"})
        scorer = LLMRelevanceScorer(provider)
        relevant = RelevanceResult(score=0.5, label="relevant", signals=())

        with self.assertRaises(LLMScoringNotRequired):
            scorer.score(event_for("My name is Ada."), relevant)


if __name__ == "__main__":
    unittest.main()
