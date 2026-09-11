# `mindmem/memory/reasoning_state.py`

## Purpose

Stores explicit decisions, tasks, task progress, and tool results under session topics.

## Plain-English Context

This file remembers the current state of work, not just conversation facts. For
example, it can remember that Stripe was selected, checkout testing is blocked, and
the connection tool succeeded. `short_term.py` calls it to add or update state;
`retrieval.py` reads that state for the agent.

## Classes

### `ReasoningStateItem`

Immutable state record containing ownership, topic, kind, content, status, optional
source record, and timestamps. Needed to represent resumable working state without
storing private chain-of-thought.

### `ReasoningStateStore`

Session-scoped in-memory collection of state items. Needed to manage their lifecycle
separately from sensory records.

## Functions and methods

### `ReasoningStateStore.__init__()`

Creates storage keyed by user/session. Needed for session isolation.

### `ReasoningStateStore.add(...)`

Validates content and status, then stores a new item. Needed to enforce that tasks use
task statuses while decisions/tool results use `recorded`.

### `ReasoningStateStore.get(...)`

Returns session state, optionally filtered by topic or kind. Needed to retrieve only
the state relevant to current work.

### `ReasoningStateStore.update_task(...)`

Validates and changes a task status and update timestamp. Needed to track progress.

### `ReasoningStateStore.remove_topic(topic_id)`

Removes all state attached to a deleted topic. Needed to prevent orphaned state.

### `ReasoningStateStore.clear_session(...)`

Removes all state for one user/session. Needed for complete session cleanup.

## Status types

- `TaskStatus`: `open`, `in_progress`, `completed`, or `blocked`.
- `recorded`: fixed status for decisions and tool results with no progress lifecycle.
- `_TASK_STATUSES`: runtime validation set; `Literal` types only help static checking.
