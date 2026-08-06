import unittest

from mindmem.input.text import RawTextInput, create_text_input_event
from mindmem.sensory.extraction.llm_extraction import (
    ExtractionValidationError,
    LLMMemoryExtractor,
)


class FakeProvider:
    def __init__(self, result):
        self.result = result
        self.arguments = None

    def generate_json(self, **kwargs):
        self.arguments = kwargs
        return self.result


def event_for(text: str):
    return create_text_input_event(
        RawTextInput(user_id="user_1", session_id="session_1", text=text)
    )


def valid_result():
    return {
        "source_text": "I joined OpenAI last year.",
        "memory_types": ["identity", "event"],
        "entities": [
            {
                "name": "OpenAI",
                "type": "organization",
                "evidence": "OpenAI",
                "confidence": 1.0,
            }
        ],
        "facts": [
            {
                "subject": "user",
                "relation": "joined",
                "object": "OpenAI",
                "evidence": "I joined OpenAI last year",
                "confidence": 1.0,
            }
        ],
        "temporal_expressions": [
            {"text": "last year", "applies_to": "user joined OpenAI"}
        ],
    }


class LLMMemoryExtractorTests(unittest.TestCase):
    def test_extracts_structured_memory(self):
        provider = FakeProvider(valid_result())
        result = LLMMemoryExtractor(provider).extract(
            event_for("I joined OpenAI last year.")
        )

        self.assertEqual(result.facts[0].relation, "joined")
        self.assertEqual(result.temporal_expressions[0].text, "last year")
        self.assertEqual(provider.arguments["input_data"]["speaker_id"], "user_1")

    def test_rejects_invented_evidence(self):
        output = valid_result()
        output["facts"][0]["evidence"] = "I became CEO of OpenAI"

        with self.assertRaisesRegex(ExtractionValidationError, "evidence"):
            LLMMemoryExtractor(FakeProvider(output)).extract(
                event_for("I joined OpenAI last year.")
            )

    def test_rejects_duplicate_facts(self):
        output = valid_result()
        output["facts"].append(dict(output["facts"][0]))

        with self.assertRaisesRegex(ExtractionValidationError, "duplicate facts"):
            LLMMemoryExtractor(FakeProvider(output)).extract(
                event_for("I joined OpenAI last year.")
            )

    def test_rejects_changed_source_text(self):
        output = valid_result()
        output["source_text"] = "I joined OpenAI."

        with self.assertRaisesRegex(ExtractionValidationError, "source_text"):
            LLMMemoryExtractor(FakeProvider(output)).extract(
                event_for("I joined OpenAI last year.")
            )


if __name__ == "__main__":
    unittest.main()
