# `mindmem/memory/consolidation.py`

## Purpose

Selects durable information from a short-term topic and writes it into long-term
memory using deterministic rules.

## Plain-English Context

This file is the bridge between short-term and long-term memory. A developer manually
calls `consolidate_topic()`. It preserves each source message, accepts durable and
confident facts, includes configured decisions/tasks/tool results, and passes them to
`long_term.py`. It does not call an LLM.

## Classes

### `ConsolidationPolicy`

Configures durable memory types, confidence/relevance thresholds, and which state
types are included. Needed to make promotion rules explicit and adjustable.

### `ConsolidationResult`

Reports episodes, candidates, created/updated/unchanged memories, skipped facts, and
superseded IDs. Needed to inspect what consolidation actually did.

### `ShortTermConsolidator`

Coordinates candidate selection and long-term writes for one topic.

## Functions and Methods

### `ConsolidationPolicy.__post_init__()`

Validates thresholds. Needed to reject invalid configuration early.

### `ShortTermConsolidator.__init__(...)`

Receives short-term memory, long-term storage, and optional policy. Needed for clear
dependency injection and testing.

### `consolidate_topic(...)`

Selects the current or requested topic, preserves episodes, builds fact/state
candidates, writes them, and returns counts. Needed as the manual consolidation API.

### `_fact_candidates(record)`

Keeps facts with a durable memory type, sufficient extraction confidence, and
sufficient relevance. Needed to keep weak or temporary information out.

### `_state_candidates(topic, state)`

Converts enabled decisions, tasks, and tool results into candidates and avoids linking
to already-evicted records. Needed to retain useful working outcomes without dangling
episode references.

### `_episode_from(record)`

Copies a short-term record into a durable source episode. Needed for provenance.

### `_resolve_topic(...)`

Selects the current topic or validates an explicit session topic. Needed to prevent
cross-session consolidation.
