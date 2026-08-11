# `tests/test_llm_providers.py`

## Purpose

Verifies each provider sends the correct structured-output configuration.

## Helpers and tests

- `RecordingEndpoint.__init__()`: stores a fake response and call state.
- `RecordingEndpoint.create()`: captures request arguments; needed to inspect API calls.
- `test_openai_uses_strict_json_schema()`: protects OpenAI strict schema formatting.
- `test_anthropic_uses_output_config_json_schema()`: protects Anthropic schema formatting.
- `test_gemini_uses_response_format_json_schema()`: protects Gemini schema formatting.
