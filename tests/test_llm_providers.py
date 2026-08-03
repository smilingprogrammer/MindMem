import unittest
from types import SimpleNamespace

from mindmem.sensory.relevance.llm_providers import (
    AnthropicProvider,
    GeminiProvider,
    OpenAIProvider,
)


INPUT = {"text": "The server stopped again.", "context": []}
SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "number"},
        "label": {"type": "string", "enum": ["noise", "relevant"]},
    },
    "required": ["score", "label"],
    "additionalProperties": False,
}


class RecordingEndpoint:
    def __init__(self, response):
        self.response = response
        self.arguments = None

    def create(self, **kwargs):
        self.arguments = kwargs
        return self.response


class ProviderAdapterTests(unittest.TestCase):
    def test_openai_uses_strict_json_schema(self):
        endpoint = RecordingEndpoint(
            SimpleNamespace(output_text='{"score":0.8,"label":"relevant"}')
        )
        provider = OpenAIProvider.__new__(OpenAIProvider)
        provider.client = SimpleNamespace(responses=endpoint)
        provider.model = "test-model"

        result = provider.generate_json(
            input_data=INPUT,
            output_schema=SCHEMA,
            instructions="Classify.",
        )

        output_format = endpoint.arguments["text"]["format"]
        self.assertTrue(output_format["strict"])
        self.assertEqual(output_format["schema"], SCHEMA)
        self.assertEqual(result["label"], "relevant")

    def test_anthropic_uses_output_config_json_schema(self):
        endpoint = RecordingEndpoint(
            SimpleNamespace(
                content=[
                    SimpleNamespace(
                        type="text",
                        text='{"score":0.2,"label":"noise"}',
                    )
                ]
            )
        )
        provider = AnthropicProvider.__new__(AnthropicProvider)
        provider.client = SimpleNamespace(messages=endpoint)
        provider.model = "test-model"
        provider.max_tokens = 256

        result = provider.generate_json(
            input_data=INPUT,
            output_schema=SCHEMA,
            instructions="Classify.",
        )

        output_format = endpoint.arguments["output_config"]["format"]
        self.assertEqual(output_format["type"], "json_schema")
        self.assertEqual(output_format["schema"], SCHEMA)
        self.assertEqual(result["label"], "noise")

    def test_gemini_uses_response_format_json_schema(self):
        endpoint = RecordingEndpoint(
            SimpleNamespace(output_text='{"score":0.8,"label":"relevant"}')
        )
        provider = GeminiProvider.__new__(GeminiProvider)
        provider.client = SimpleNamespace(interactions=endpoint)
        provider.model = "test-model"

        result = provider.generate_json(
            input_data=INPUT,
            output_schema=SCHEMA,
            instructions="Classify.",
        )

        output_format = endpoint.arguments["response_format"]
        self.assertEqual(output_format["mime_type"], "application/json")
        self.assertEqual(output_format["schema"], SCHEMA)
        self.assertEqual(result["label"], "relevant")


if __name__ == "__main__":
    unittest.main()
