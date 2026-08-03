import re
from dataclasses import dataclass

import spacy
from spacy.matcher import PhraseMatcher

from mindmem.input.text import TextInputEvent


@dataclass(frozen=True)
class RelevanceResult:
    score: float
    label: str
    signals: tuple[str, ...]


NOISE_PHRASES = {
    "hmm",
    "lol",
    "okay",
    "ok",
    "thanks",
    "thank you",
}

SIGNAL_PHRASES = {
    "personal_fact": ("i am", "i'm", "my name is", "i live", "i work", "i study", "i have"),
    "preference": (
        "i prefer",
        "i like",
        "i dislike",
        "my favorite",
        "my favourite",
        "i love",
        "i hate",
    ),
    "goal": ("i want", "i plan", "i'm planning", "i am planning", "i'm trying", "i am trying", "my goal"),
    "task": ("remind me", "schedule", "todo", "to-do", "deadline", "i need to"),
    "correction": ("actually", "correction", "i meant", "rather than"),
    "relationship": ("wife", "husband", "partner", "friend", "client", "colleague", "team"),
    "project": ("project", "application", "app", "feature", "bug", "release", "launch", "deployment"),
}

SIGNAL_WEIGHTS = {
    "personal_fact": 0.50,
    "preference": 0.45,
    "goal": 0.40,
    "task": 0.40,
    "correction": 0.35,
    "relationship": 0.20,
    "project": 0.15,
    "time_reference": 0.10,
}

RELEVANT_THRESHOLD = 0.40

TIME_PATTERN = re.compile(
    r"\b(?:today|tomorrow|yesterday|tonight|next week|next month|"
    r"monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
    r"\d{1,2}(?::\d{2})?\s?(?:am|pm))\b",
    re.IGNORECASE,
)

NEGATIONS = {"no", "not", "never", "n't"}

NLP = spacy.blank("en")
SIGNAL_MATCHER = PhraseMatcher(NLP.vocab, attr="LOWER")
for signal, phrases in SIGNAL_PHRASES.items():
    SIGNAL_MATCHER.add(signal, [NLP.make_doc(phrase) for phrase in phrases])


def score_relevance(event: TextInputEvent) -> RelevanceResult:
    text = event.text.strip()
    doc = NLP(text)
    words = [token for token in doc if not token.is_space and not token.is_punct]
    normalized = " ".join(token.lower_ for token in words)
    signals: list[str] = []

    if normalized in NOISE_PHRASES:
        return RelevanceResult(score=0.0, label="noise", signals=("filler_phrase",))

    if len(words) <= 2:
        signals.append("very_short")
    elif len(words) >= 5:
        signals.append("longer_text")

    if any(token.text == "?" for token in doc):
        signals.append("question")

    matched_signals = {NLP.vocab.strings[match_id] for match_id, _, _ in SIGNAL_MATCHER(doc)}

    if TIME_PATTERN.search(text):
        matched_signals.add("time_reference")

    if any(token.lower_ in NEGATIONS for token in words):
        signals.append("negation")

    signals.extend(sorted(matched_signals))

    score = round(min(sum(SIGNAL_WEIGHTS[signal] for signal in matched_signals), 1.0), 2)

    label = "relevant" if score >= RELEVANT_THRESHOLD else "unclear"

    return RelevanceResult(score=score, label=label, signals=tuple(signals))
