# `tests/test_llm_relevance.py`

## Purpose

Protects conditional LLM relevance scoring, schemas, and Python label derivation.

## Helpers and tests

- `FakeProvider.__init__()`: stores deterministic output.
- `FakeProvider.generate_json()`: captures request/schema and returns fake output.
- `event_for()`: creates a test event.
- `test_scores_only_unclear_messages()`: checks successful unclear scoring.
- `test_reason_is_absent_by_default()`: protects token-saving output.
- `test_reason_is_requested_when_enabled()`: protects optional reasons.
- `test_rejects_schema_invalid_output()`: prevents malformed provider results.
- `test_derives_noise_label_from_score()`: ensures Python derives labels.
- `test_rejects_messages_already_classified_by_heuristics()`: enforces LLM-call boundaries.
