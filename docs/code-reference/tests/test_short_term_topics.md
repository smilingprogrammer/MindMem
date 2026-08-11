# `tests/test_short_term_topics.py`

## Purpose

Protects deterministic topic grouping and active-topic behavior.

## Helpers and tests

- `MutableClock.__init__()`: starts deterministic time; needed for recency tests.
- `MutableClock.__call__()`: advances deterministic time per operation.
- `extraction_for()`: builds entity/fact extraction fixtures.
- `TopicGroupingTests.setUp()`: creates a configured fresh buffer.
- `store()`: stores a topic fixture through the public API.
- `topics()`: retrieves topics through the public API.
- `test_groups_records_with_the_same_project_entity()`: joins project variants.
- `test_creates_separate_topics_for_unrelated_entities()`: prevents unrelated merges.
- `test_shared_person_does_not_merge_different_named_projects()`: protects strong anchors.
- `test_groups_matching_fact_objects_when_entities_are_absent()`: supports fact-only output.
- `test_only_most_recent_topics_remain_active()`: verifies the active-topic limit.
- `test_reusing_an_inactive_topic_reactivates_it()`: verifies topic return.
- `test_topics_are_isolated_by_session()`: prevents cross-session topic sharing.
- `test_eviction_removes_an_empty_topic()`: prevents empty topics after eviction.
