# `tests/test_reasoning_state.py`

## Purpose

Protects decisions, tasks, tool results, ownership, lifecycle, and cleanup.

## Helpers and tests

- `MutableClock.__init__()`: starts deterministic time.
- `MutableClock.__call__()`: advances time for update assertions.
- `store_project_record()`: creates a project topic fixture.
- `ReasoningStateTests.setUp()`: creates a fresh buffer and topic.
- `test_adds_decision_to_current_topic()`: verifies default topic selection.
- `test_adds_and_updates_task()`: verifies task progress and timestamps.
- `test_adds_tool_result()`: verifies source-linked tool output.
- `test_state_update_reactivates_its_topic()`: ensures state changes update focus.
- `test_rejects_invalid_task_status()`: protects runtime status validation.
- `test_task_memory_is_captured_automatically()`: verifies extracted tasks start open.
- `test_filters_state_by_topic_and_kind()`: verifies focused retrieval.
- `test_rejects_a_source_record_from_another_topic()`: prevents invalid linking.
- `test_clear_session_removes_state_and_topics()`: verifies complete cleanup.
- `test_eviction_removes_state_when_its_topic_becomes_empty()`: prevents orphaned state.
