# `tests/test_short_term_retrieval.py`

## Purpose

Protects focused short-term context assembly.

## Helpers and tests

- `MutableClock.__init__()`: starts deterministic time for memory operations.
- `MutableClock.__call__()`: advances deterministic time.
- `store_project()`: creates and stores project extraction fixtures.
- `ShortTermContextRetrieverTests.setUp()`: creates fresh memory and retriever objects.
- `test_returns_empty_context_when_the_session_has_no_topic()`: verifies safe empty output.
- `test_retrieves_current_topic_records_and_state()`: verifies complete context assembly.
- `test_completed_tasks_are_not_returned_as_open_tasks()`: keeps context focused on unfinished work.
- `test_can_retrieve_a_specific_non_current_topic()`: supports explicit topic retrieval.
- `test_applies_the_record_limit_to_the_latest_topic_records()`: protects context limits.
- `test_rejects_a_topic_from_another_session()`: prevents cross-session access.
- `test_rejects_an_invalid_record_limit()`: protects limit validation.
