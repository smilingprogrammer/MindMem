# `mindmem/memory/topics.py`

## Purpose

Groups related short-term records using deterministic signals already present in
structured extraction. It performs no additional LLM call.

## Classes

### `TopicGroup`

Immutable topic containing ownership, label, keywords, record IDs, timestamps, and
active state. Needed to retrieve connected records as one conversation subject.

### `TopicTracker`

Owns topic matching, recency, activation, and record mappings. Needed to maintain
topic continuity independently for each session.

## Functions and methods

### `_meaningful_words(value)`

Normalizes text and removes generic words. Needed to reduce false matches.

### `_add_signal(signals, value, weight)`

Adds weighted phrase and word signals. Needed to make projects/products stronger
topic evidence than generic fact values.

### `_signal_values(value)`

Returns normalized phrase/word values. Needed to build entity anchors.

### `_signals_for(extraction)`

Builds weighted signals and strong anchors from entities and facts. Needed as the
matching representation for each record.

### `_topic_label(extraction)`

Chooses a readable label using entity priority, facts, or memory type. Needed so
topics are understandable to callers.

### `TopicTracker.__init__(...)`

Validates configuration and creates stores. Needed to configure matching threshold
and active-topic count.

### `TopicTracker.assign(...)`

Scores existing topics, prevents conflicting strong anchors from merging, then joins
or creates a topic. Needed for deterministic topic grouping.

### `TopicTracker.get_topics(...)`

Returns all or only active topics for a session. Needed for topic retrieval.

### `TopicTracker.get_topic(topic_id)`

Finds one topic globally by ID. Needed by the short-term memory facade.

### `TopicTracker.current_topic(...)`

Returns the most recently used active topic. Needed for follow-up state without an
explicit topic ID.

### `TopicTracker.touch(...)`

Moves a topic to most-recent position and refreshes active flags. Needed to reactivate
topics when work returns to them.

### `TopicTracker.remove_record(record_id)`

Detaches a record and removes an empty topic. Needed when buffer capacity evicts old
records.

### `TopicTracker.clear_session(...)`

Deletes session topics, signals, anchors, and record mappings. Needed for full cleanup.

### `TopicTracker._refresh_active(key)`

Marks only the configured most-recent topics active. Needed to represent current focus
without deleting older topics.

### `TopicTracker._topic_by_id(topic_id)`

Strict internal lookup after assignment/touch. Needed to expose internal consistency
failures instead of silently returning `None`.
