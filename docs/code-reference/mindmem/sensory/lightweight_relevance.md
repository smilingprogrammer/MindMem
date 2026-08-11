# `mindmem/sensory/lightweight_relevance.py`

## Purpose

Scores obvious memory relevance cheaply before deciding whether LLM scoring is
required.

## Classes

### `RelevanceResult`

Immutable result containing `score`, `label`, and diagnostic `signals`. It is needed
as the shared output contract for the sensory pipeline.

## Functions

### `score_relevance(event)`

Tokenizes text with spaCy, detects exact filler phrases, weighted signal phrases,
time references, negation, length, and questions. It returns `noise`, `unclear`, or
`relevant`. It is needed to avoid LLM calls for obvious cases while preserving
uncertain messages for LLM review.

## Configuration

- `NOISE_PHRASES` identifies exact filler messages.
- `SIGNAL_PHRASES` and `SIGNAL_WEIGHTS` define memory-relevance evidence.
- `RELEVANT_THRESHOLD` converts the heuristic score to `relevant`.
- Length, questions, and negation are reported as signals but do not add relevance.
