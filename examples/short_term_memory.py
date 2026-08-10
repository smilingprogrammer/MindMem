from dotenv import load_dotenv

from examples.provider_setup import create_provider
from mindmem.input.text import RawTextInput, create_text_input_event
from mindmem.memory import ShortTermMemoryBuffer
from mindmem.sensory.extraction import LLMMemoryExtractor
from mindmem.sensory.lightweight_relevance import score_relevance
from mindmem.sensory.relevance.llm_relevance import LLMRelevanceScorer


def main() -> None:
    load_dotenv()
    provider = create_provider()
    relevance_scorer = LLMRelevanceScorer(provider)
    extractor = LLMMemoryExtractor(provider)
    buffer = ShortTermMemoryBuffer()

    print("Enter messages. Use /memories to inspect the buffer or /exit to stop.")

    while True:
        text = input("You: ").strip()
        if text == "/exit":
            break
        if text == "/memories":
            records = buffer.get_recent(
                user_id="user_1",
                session_id="session_1",
            )
            print(f"Stored records: {len(records)}")
            for record in records:
                print(f"- {record.extraction.source_text}")
            continue
        if not text:
            continue

        event = create_text_input_event(
            RawTextInput(
                user_id="user_1",
                session_id="session_1",
                text=text,
            )
        )
        relevance = score_relevance(event)
        if relevance.label == "unclear":
            relevance = relevance_scorer.score(event, relevance, context=[])

        print(f"Relevance: {relevance.label} ({relevance.score})")
        if relevance.label == "noise":
            print("Not stored.")
            continue

        extraction = extractor.extract(event)
        record = buffer.store(
            event=event,
            relevance_score=relevance.score,
            extraction=extraction,
        )

        print("Stored facts:")
        for fact in record.extraction.facts:
            print(f"- {fact.subject} -> {fact.relation} -> {fact.object}")
        print(
            "Session records:",
            len(buffer.get_recent(user_id="user_1", session_id="session_1")),
        )


if __name__ == "__main__":
    main()
