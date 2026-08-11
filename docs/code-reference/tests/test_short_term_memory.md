# `tests/test_short_term_memory.py`

## Purpose

Protects the core session record buffer behavior.

## Helpers and tests

- `event_for()`: creates events with configurable ownership; needed for isolation tests.
- `extraction_for()`: creates matching extraction fixtures.
- `ShortTermMemoryBufferTests.setUp()`: creates a fresh buffer per test.
- `store()`: stores a fixture through the public API.
- `recent()`: retrieves fixtures through the public API.
- `test_stores_and_returns_recent_records()`: verifies normal storage.
- `test_keeps_sessions_separate()`: prevents cross-session records.
- `test_keeps_only_latest_records()`: verifies capacity eviction.
- `test_limits_recent_results()`: verifies retrieval limits.
- `test_clears_one_session()`: verifies targeted cleanup.
- `test_rejects_extraction_from_another_event()`: prevents mismatched source data.
