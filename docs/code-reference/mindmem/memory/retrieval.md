# `mindmem/memory/retrieval.py`

## Purpose

Builds focused, structured short-term context for an agent without making an LLM call
or modifying memory.

## Classes

### `ShortTermContext`

Immutable result containing ownership, selected topic, topic records, decisions,
unfinished tasks, and tool results. Needed as a predictable context contract for an
agent.

### `ShortTermContextRetriever`

Reads and assembles information from `ShortTermMemoryBuffer`. Needed to keep context
selection out of storage code.

## Functions and methods

### `ShortTermContextRetriever.__init__(memory)`

Stores the memory facade to read from. Needed for dependency injection and testing.

### `ShortTermContextRetriever.retrieve(...)`

Selects the current or requested session topic, optionally limits its latest records,
and separates state into decisions, unfinished tasks, and tool results. Returns an
empty context when a session has no topic. Needed to prepare agent-ready short-term
context.

### `ShortTermContextRetriever._resolve_topic(...)`

Returns the current topic or verifies that an explicit topic belongs to the requested
user/session. Needed to prevent cross-session retrieval.
