# `tests/test_long_term_consolidation.py`

Automatic-trigger tests cover inactive topics, task reactivation, preservation of
facts and state before eviction, session isolation, repeated session-end calls,
and recovery from storage failures before eviction or after inactivity changes.

## Purpose

Protects the first long-term consolidation and storage implementation.

## Helpers and Tests

- `MutableClock`: provides deterministic timestamps for history checks.
- `store_fact()`: creates a realistic short-term fact fixture.
- `consolidate_current()`: invokes the public manual consolidation API.
- Durable-fact and episode test: verifies promotion and source preservation.
- Selection test: verifies temporary and low-confidence facts are skipped.
- Duplicate test: verifies repeated facts merge their sources.
- Conflict test: verifies configured single-value facts retain superseded history.
- Multi-value test: verifies unconfigured relations do not overwrite each other.
- State test: verifies decisions, tasks, and tool results are promoted.
- Policy test: verifies state types can be excluded.
- Task update test: verifies reconsolidation carries status changes forward.
- Evicted-source test: prevents state from referencing an episode that was not preserved.
- Idempotency test: verifies repeated consolidation does not replay old facts.
- Ownership test: prevents consolidating a topic from another session.
