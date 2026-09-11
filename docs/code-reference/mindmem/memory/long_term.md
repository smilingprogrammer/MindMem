# `mindmem/memory/long_term.py`

## Purpose

Provides the first in-memory long-term store, including source episodes, exact
deduplication, and controlled conflict history.

## Plain-English Context

This file is where accepted durable information lives. If the same fact arrives from
another message, it adds the new source to the existing memory. If a configured
single-value fact changes, such as Apollo's deadline, it marks the old value
`superseded` and keeps both versions. `consolidation.py` calls this file.

## Classes

### `LongTermEpisode`

Preserves a promoted short-term record's raw text, ownership, topic, relevance, event
time, and storage time. Needed so long-term memories keep inspectable source evidence.

### `LongTermTemporalExpression`

Preserves a raw time phrase and the fact it applies to. Needed until temporal
normalization is implemented.

### `LongTermMemoryCandidate`

Represents information proposed for long-term storage. Needed to separate selection
from storage and conflict handling.

### `LongTermMemory`

Represents a durable fact, decision, task, or tool result with confidence, evidence,
sources, temporal fields, and current/superseded status.

### `MemoryWriteResult`

Reports whether an upsert created, updated, or left a memory unchanged and which old
memories it superseded. Needed for observable consolidation results.

### `LongTermMemoryStore`

Defines the `store_episode()` and `upsert()` methods required by consolidation.
Needed so persistent database adapters can later replace the in-memory store without
changing the consolidator.

### `InMemoryLongTermMemoryStore`

Stores episodes and memories by user in RAM. Needed as the working default before
persistent adapters are introduced.

## Functions and Methods

### `_normalized(value)`

Normalizes case and whitespace. Needed for stable duplicate/conflict comparison.

### `_merged(first, second)`

Combines source/evidence values without duplicates. Needed when repeated evidence
supports one fact.

### `InMemoryLongTermMemoryStore.__init__(...)`

Creates storage and accepts configured single-value relations. Needed because a new
`deadline` may replace an old one, while multiple `likes` facts may all be valid.

### `store_episode(episode)`

Stores a raw source episode once. Needed for provenance after short-term eviction.

### `upsert(candidate)`

Validates a candidate, merges exact duplicates, blocks replay of processed evidence,
supersedes configured conflicts, or creates a new memory. Needed as the consolidation
write boundary.

### `get_memories(...)`

Returns current memories by default, optionally including history or filtering kind.
Needed for later long-term retrieval.

### `get_episodes(user_id=...)`

Returns the user's promoted source episodes. Needed for evidence inspection.

### `_find_current_duplicate(...)`

Finds an equivalent current memory. Needed to merge repeated facts.

### `_find_processed_source(...)`

Detects evidence already consolidated, including evidence supporting superseded facts.
Needed to make repeated consolidation idempotent.

### `_is_conflict(...)`

Checks whether a current fact has the same subject/relation but a different value.
Needed for controlled versioning.

### `_validate_candidate(candidate)`

Rejects empty, invalid, ungrounded, or incorrectly typed candidates. Needed to protect
long-term data quality.

### `_now()`

Returns a timezone-aware time. Needed for reliable history timestamps.
