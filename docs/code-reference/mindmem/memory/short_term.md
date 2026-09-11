# `mindmem/memory/short_term.py`

## Purpose

Provides the public facade that coordinates session records, topics, and working state.

## Plain-English Context

This is the main door into short-term memory. After the sensory layer extracts a
relevant message, it calls `store()`. This file saves the record, asks `topics.py`
where it belongs, and asks `reasoning_state.py` to create an open task when the
extraction says the message is a task. `retrieval.py` later reads through this file.

## Classes

### `ShortTermMemoryRecord`

Immutable link between the input event, relevance score, structured extraction, topic,
session, event time, and storage time. Needed as the unit held in short-term memory
and as the source for a long-term episode.

### `ShortTermMemoryBuffer`

Session-scoped in-memory facade. Needed so integrations use one API instead of
coordinating record, topic, and state stores themselves.

## Functions and methods

### `ShortTermMemoryBuffer.__init__(...)`

Validates capacity and creates record indexes, `TopicTracker`, and
`ReasoningStateStore`. Needed to initialize an isolated buffer with configurable
record and active-topic limits.

### `store(...)`

Validates relevance/extraction, assigns a topic, stores the record, evicts excess
records, cleans empty topics/state, and creates open extracted tasks. Needed as the
sensory-to-memory entry point.

### `get_recent(...)`

Returns ordered recent session records with an optional limit. Needed for continuity.

### `get_topics(...)`

Returns all or active session topics. Needed to inspect conversation subjects.

### `get_current_topic(...)`

Returns the most recently used topic. Needed to attach follow-up state correctly.

### `get_topic_records(topic_id)`

Returns buffered records assigned to a topic. Needed for topic-focused context.

### `add_decision(...)`

Stores a recorded decision under a selected/current topic. Needed to avoid repeating
settled choices.

### `add_task(...)`

Stores a task with progress status. Needed to track pending work.

### `add_tool_result(...)`

Stores useful tool output under a topic. Needed to preserve execution results and
avoid unnecessary reruns.

### `update_task(...)`

Changes task status and touches its topic. Needed to track progress and reactivate the
subject being worked on.

### `get_reasoning_state(...)`

Returns state filtered by session, topic, or kind. Needed to resume relevant work.

### `clear_session(...)`

Removes all session records, topics, indexes, and state. Needed for complete cleanup.

### `_add_state(...)`

Shared decision/task/tool-result storage logic with source-record validation. Needed
to enforce one consistent path.

### `_resolve_topic(...)`

Uses an explicit topic or the current topic. Needed for convenient but correct state
placement.

### `_require_owned_topic(...)`

Validates topic ownership. Needed to prevent cross-session state mixing.

### `_require_topic(topic_id)`

Returns a topic or raises `KeyError`. Needed to reject stale/invalid references.

### `_now()`

Returns a timezone-aware clock value. Needed for consistent ordering and timestamps.
