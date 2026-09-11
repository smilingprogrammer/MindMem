# MindMem Plain-Language Code Map

Use this page when returning to the codebase after a break. It explains the code in
the order a message moves through MindMem.

## Complete Flow

```text
Backend message
-> input/text.py creates a valid event
-> lightweight_relevance.py makes the cheap first decision
-> llm_relevance.py asks an LLM only when the decision is unclear
-> llm_extraction.py extracts facts from relevant messages
-> short_term.py stores the result
-> topics.py groups it with related records and tracks the latest 3 topics
-> reasoning_state.py keeps decisions, tasks, and tool results
-> retrieval.py prepares the current topic and state for an agent
-> consolidation.py selects durable information from a topic
-> long_term.py stores source episodes and versioned long-term memories
```

## Main Code

| File | Plain-language responsibility | Called by / connects to |
| --- | --- | --- |
| `main.py` | Runs three fixed messages so a developer can see heuristic scores. | Calls `input/text.py` and `lightweight_relevance.py`. |
| `mindmem/input/text.py` | Turns backend text into a valid MindMem event with IDs, timestamp, modality, and metadata. | Called before any sensory processing. Its event is consumed by both relevance scorers and extraction. |
| `mindmem/sensory/lightweight_relevance.py` | Makes a cheap first relevance decision: noise, unclear, or relevant. | Receives `TextInputEvent`. Unclear goes to `llm_relevance.py`; relevant goes to extraction. |
| `mindmem/sensory/relevance/llm_relevance.py` | Uses an LLM to resolve only unclear messages. The LLM returns a score and Python decides noise/relevant. | Calls a provider from `llm_providers.py`; relevant output allows extraction. |
| `mindmem/sensory/relevance/llm_providers.py` | Hides differences between OpenAI, Anthropic, and Gemini behind one JSON method. | Called by relevance and extraction. Returns structured JSON. |
| `mindmem/sensory/extraction/llm_extraction.py` | Converts relevant text into memory types, entities, facts, evidence, confidence, and time expressions. | Calls `llm_providers.py`; output is passed to `short_term.py`. |
| `mindmem/memory/short_term.py` | Main short-term memory controller. Stores up to 50 records per session and coordinates topics and state. | Calls `topics.py` during storage and `reasoning_state.py` for tasks/decisions/tool results. Read by `retrieval.py`. |
| `mindmem/memory/topics.py` | Groups related records. Only the 3 most recently used topics are marked active; older topics remain stored. | Called by `short_term.py` whenever a record is stored or a topic is used again. `_refresh_active()` enforces the latest-3 rule. |
| `mindmem/memory/reasoning_state.py` | Stores explicit decisions, tasks, task progress, and useful tool outputs under topics. | Called through `short_term.py`; read later by `retrieval.py`. |
| `mindmem/memory/retrieval.py` | Collects one topic's records, decisions, unfinished tasks, and tool results into agent-ready context. | Reads `short_term.py`; it makes no LLM call and changes no memory. |
| `mindmem/memory/consolidation.py` | Manually selects durable facts and state from one short-term topic and sends candidates into long-term storage. | Reads `short_term.py` and writes through `long_term.py`. It uses rules, not an LLM. |
| `mindmem/memory/long_term.py` | Keeps raw source episodes plus current and superseded durable memories. It merges exact duplicates and versions configured single-value conflicts. | Called by `consolidation.py`; currently stores everything in RAM. |

## Package Files

| File | Plain-language responsibility |
| --- | --- |
| `mindmem/__init__.py` | Marks the main folder as a Python package. |
| `mindmem/input/__init__.py` | Provides shorter public imports for input classes/functions. |
| `mindmem/sensory/__init__.py` | Provides public imports for lightweight relevance. |
| `mindmem/sensory/relevance/__init__.py` | Provides public imports for LLM relevance. |
| `mindmem/sensory/extraction/__init__.py` | Provides public imports for extraction models and extractor. |
| `mindmem/memory/__init__.py` | Provides public imports for the buffer, topics, state, and context retrieval. |
| `examples/__init__.py` | Allows examples to run with `python -m`. |
| `tests/__init__.py` | Allows tests to be treated as a package. |

These files mainly control imports; they do not implement memory behavior.

## Runnable Examples

| File | What a person uses it for |
| --- | --- |
| `examples/provider_setup.py` | Reads `.env` and creates the chosen LLM provider. |
| `examples/llm_scoring.py` | Shows when heuristics stop and when the LLM scorer runs. |
| `examples/llm_extraction.py` | Shows the structured facts produced from one message. |
| `examples/short_term_memory.py` | Runs the complete current flow and lets a person inspect records, topics, state, and context. |

## Tests

| File | Behavior it protects |
| --- | --- |
| `tests/test_lightweight_relevance.py` | Filler, preferences, tasks, negation, questions, and length scoring. |
| `tests/test_llm_relevance.py` | Unclear-only LLM calls, schemas, optional reasons, and score-derived labels. |
| `tests/test_llm_providers.py` | Correct JSON Schema request format for each provider. |
| `tests/test_llm_extraction.py` | Valid extraction, exact evidence, source matching, and duplicate rejection. |
| `tests/test_short_term_memory.py` | Session separation, 50-record behavior, limits, and cleanup. |
| `tests/test_short_term_topics.py` | Topic matching, latest-3 activation, reactivation, and topic cleanup. |
| `tests/test_reasoning_state.py` | Decisions, task status, tool results, ownership, and cleanup. |
| `tests/test_short_term_retrieval.py` | Current/specific-topic context, unfinished tasks, limits, and session safety. |
| `tests/test_long_term_consolidation.py` | Candidate rules, source episodes, duplicate merging, conflict history, state promotion, task updates, and idempotency. |

## Important Defaults

- `50` is the default maximum number of short-term records per session.
- `3` is the default number of active topics per session.
- Exceeding 3 active topics does not delete a topic; it only sets older topics to
  `is_active=False`.
- The buffer is in RAM, so it disappears when the process stops.
- Topic grouping and short-term context retrieval make no LLM calls.
- Consolidation is currently manual and rule-based.
- Conflict replacement runs only for relations explicitly configured as single-value.
- Long-term storage is currently in RAM.
