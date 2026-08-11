# `tests/test_lightweight_relevance.py`

## Purpose

Protects weighted heuristic relevance behavior.

## Helpers and tests

- `event_for()`: creates events; needed to keep tests concise.
- `test_filler_is_noise()`: ensures exact fillers stop early.
- `test_personal_preference_is_relevant()`: protects preference weighting.
- `test_task_with_time_is_relevant()`: protects combined task/time scoring.
- `test_negation_is_not_removed_or_called_noise()`: preserves negated meaning.
- `test_unrecognized_statement_is_unclear()`: routes uncertainty to the LLM.
- `test_question_does_not_increase_score()`: prevents question marks implying memory value.
- `test_length_does_not_increase_score()`: prevents length implying memory value.
