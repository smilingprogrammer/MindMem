# `tests/test_llm_extraction.py`

## Purpose

Verifies structured extraction and grounding validation without a real provider.

## Helpers and tests

- `FakeProvider.__init__()`: stores deterministic output; needed to isolate extraction.
- `FakeProvider.generate_json()`: returns that output; needed to satisfy the provider protocol.
- `event_for()`: creates test events.
- `valid_result()`: supplies a valid extraction fixture.
- `test_extracts_structured_memory()`: checks successful parsing.
- `test_rejects_invented_evidence()`: prevents unsupported evidence.
- `test_rejects_duplicate_facts()`: prevents duplicate atomic facts.
- `test_rejects_changed_source_text()`: ensures output belongs to the input message.
