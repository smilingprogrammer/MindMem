import re
from dataclasses import dataclass, replace
from datetime import datetime
from uuid import uuid4

from mindmem.sensory.extraction import MemoryExtractionResult


_WORDS = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "a",
    "an",
    "and",
    "at",
    "before",
    "for",
    "from",
    "he",
    "her",
    "him",
    "i",
    "in",
    "it",
    "last",
    "me",
    "morning",
    "my",
    "next",
    "on",
    "project",
    "she",
    "the",
    "their",
    "them",
    "they",
    "this",
    "to",
    "today",
    "tomorrow",
    "tonight",
    "user",
    "we",
    "week",
    "with",
    "year",
    "yesterday",
    "you",
}

_ENTITY_WEIGHTS = {
    "project": 4,
    "product": 4,
    "organization": 3,
    "place": 3,
    "concept": 3,
    "person": 2,
    "other": 1,
}

_LABEL_PRIORITY = {
    "project": 0,
    "product": 1,
    "organization": 2,
    "place": 3,
    "concept": 4,
    "person": 5,
    "other": 6,
}


@dataclass(frozen=True)
class TopicGroup:
    id: str
    user_id: str
    session_id: str
    label: str
    keywords: tuple[str, ...]
    record_ids: tuple[str, ...]
    created_at: datetime
    updated_at: datetime
    is_active: bool


def _meaningful_words(value: str) -> list[str]:
    return [word for word in _WORDS.findall(value.casefold()) if word not in _STOPWORDS]


def _add_signal(signals: dict[str, int], value: str, weight: int) -> None:
    words = _meaningful_words(value)
    if not words:
        return

    phrase = " ".join(words)
    phrase_weight = max(weight, 2) if len(words) > 1 else weight
    signals[phrase] = max(signals.get(phrase, 0), phrase_weight)
    for word in words:
        signals[word] = max(signals.get(word, 0), weight)


def _signal_values(value: str) -> set[str]:
    words = _meaningful_words(value)
    if not words:
        return set()
    return {" ".join(words), *words}


def _signals_for(
    extraction: MemoryExtractionResult,
) -> tuple[dict[str, int], set[str]]:
    signals: dict[str, int] = {}
    anchors: set[str] = set()
    for entity in extraction.entities:
        _add_signal(signals, entity.name, _ENTITY_WEIGHTS[entity.type])
        if entity.type in {"project", "product", "organization", "place", "concept"}:
            anchors.update(_signal_values(entity.name))

    for fact in extraction.facts:
        _add_signal(signals, fact.subject, 1)
        _add_signal(signals, fact.object, 1)
    return signals, anchors


def _topic_label(extraction: MemoryExtractionResult) -> str:
    if extraction.entities:
        entity = min(
            enumerate(extraction.entities),
            key=lambda item: (_LABEL_PRIORITY[item[1].type], item[0]),
        )[1]
        return entity.name.strip()

    for fact in extraction.facts:
        for candidate in (fact.object, fact.subject):
            if _meaningful_words(candidate):
                return candidate.strip()[:80]

    return extraction.memory_types[0].replace("_", " ").title()


class TopicTracker:
    def __init__(
        self,
        *,
        max_active_topics_per_session: int = 3,
        match_threshold: int = 2,
    ) -> None:
        if max_active_topics_per_session < 1:
            raise ValueError("max_active_topics_per_session must be at least 1")
        if match_threshold < 1:
            raise ValueError("match_threshold must be at least 1")

        self.max_active_topics_per_session = max_active_topics_per_session
        self.match_threshold = match_threshold
        self._topics: dict[tuple[str, str], list[TopicGroup]] = {}
        self._signals: dict[str, dict[str, int]] = {}
        self._anchors: dict[str, set[str]] = {}
        self._record_topics: dict[str, str] = {}

    def assign(
        self,
        *,
        record_id: str,
        user_id: str,
        session_id: str,
        extraction: MemoryExtractionResult,
        now: datetime,
    ) -> TopicGroup:
        key = (user_id, session_id)
        topics = self._topics.setdefault(key, [])
        candidate_signals, candidate_anchors = _signals_for(extraction)

        best_index: int | None = None
        best_score = 0
        for index, topic in enumerate(topics):
            topic_signals = self._signals[topic.id]
            topic_anchors = self._anchors[topic.id]
            if (
                candidate_anchors
                and topic_anchors
                and not candidate_anchors.intersection(topic_anchors)
            ):
                continue
            score = sum(
                min(weight, topic_signals[signal])
                for signal, weight in candidate_signals.items()
                if signal in topic_signals
            )
            if score >= best_score and score >= self.match_threshold:
                best_index = index
                best_score = score

        if best_index is None:
            topic = TopicGroup(
                id=str(uuid4()),
                user_id=user_id,
                session_id=session_id,
                label=_topic_label(extraction),
                keywords=tuple(sorted(candidate_signals)),
                record_ids=(record_id,),
                created_at=now,
                updated_at=now,
                is_active=True,
            )
            topics.append(topic)
            self._signals[topic.id] = candidate_signals
            self._anchors[topic.id] = candidate_anchors
        else:
            previous = topics.pop(best_index)
            merged_signals = self._signals[previous.id]
            for signal, weight in candidate_signals.items():
                merged_signals[signal] = max(merged_signals.get(signal, 0), weight)
            self._anchors[previous.id].update(candidate_anchors)
            topic = replace(
                previous,
                keywords=tuple(sorted(merged_signals)),
                record_ids=previous.record_ids + (record_id,),
                updated_at=now,
                is_active=True,
            )
            topics.append(topic)

        self._record_topics[record_id] = topic.id
        self._refresh_active(key)
        return self._topic_by_id(topic.id)

    def get_topics(
        self,
        *,
        user_id: str,
        session_id: str,
        active_only: bool = False,
    ) -> tuple[TopicGroup, ...]:
        topics = self._topics.get((user_id, session_id), [])
        if active_only:
            topics = [topic for topic in topics if topic.is_active]
        return tuple(topics)

    def get_topic(self, topic_id: str) -> TopicGroup | None:
        for topics in self._topics.values():
            for topic in topics:
                if topic.id == topic_id:
                    return topic
        return None

    def current_topic(self, *, user_id: str, session_id: str) -> TopicGroup | None:
        topics = self.get_topics(
            user_id=user_id,
            session_id=session_id,
            active_only=True,
        )
        return topics[-1] if topics else None

    def touch(self, *, topic_id: str, now: datetime) -> TopicGroup:
        for key, topics in self._topics.items():
            for index, topic in enumerate(topics):
                if topic.id != topic_id:
                    continue
                topics.pop(index)
                topics.append(replace(topic, updated_at=now, is_active=True))
                self._refresh_active(key)
                return self._topic_by_id(topic_id)
        raise KeyError(f"unknown topic_id: {topic_id}")

    def remove_record(self, record_id: str) -> str | None:
        topic_id = self._record_topics.pop(record_id, None)
        if topic_id is None:
            return None

        for key, topics in list(self._topics.items()):
            for index, topic in enumerate(topics):
                if topic.id != topic_id:
                    continue

                remaining = tuple(item for item in topic.record_ids if item != record_id)
                if remaining:
                    topics[index] = replace(topic, record_ids=remaining)
                    self._refresh_active(key)
                    return None

                topics.pop(index)
                self._signals.pop(topic_id, None)
                self._anchors.pop(topic_id, None)
                if topics:
                    self._refresh_active(key)
                else:
                    del self._topics[key]
                return topic_id
        return None

    def clear_session(self, *, user_id: str, session_id: str) -> tuple[str, ...]:
        topics = self._topics.pop((user_id, session_id), [])
        topic_ids = tuple(topic.id for topic in topics)
        record_ids = {record_id for topic in topics for record_id in topic.record_ids}
        for record_id in record_ids:
            self._record_topics.pop(record_id, None)
        for topic_id in topic_ids:
            self._signals.pop(topic_id, None)
            self._anchors.pop(topic_id, None)
        return topic_ids

    def _refresh_active(self, key: tuple[str, str]) -> None:
        topics = self._topics.get(key, [])
        active_ids = {
            topic.id for topic in topics[-self.max_active_topics_per_session :]
        }
        self._topics[key] = [
            replace(topic, is_active=topic.id in active_ids) for topic in topics
        ]

    def _topic_by_id(self, topic_id: str) -> TopicGroup:
        topic = self.get_topic(topic_id)
        if topic is None:
            raise RuntimeError("topic assignment failed")
        return topic
