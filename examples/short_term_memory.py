from dotenv import load_dotenv

from examples.provider_setup import create_provider
from mindmem.input.text import RawTextInput, create_text_input_event
from mindmem.memory import (
    InMemoryLongTermMemoryStore,
    ShortTermConsolidator,
    ShortTermContextRetriever,
    ShortTermMemoryBuffer,
)
from mindmem.sensory.extraction import LLMMemoryExtractor
from mindmem.sensory.lightweight_relevance import score_relevance
from mindmem.sensory.relevance.llm_relevance import LLMRelevanceScorer


def main() -> None:
    load_dotenv()
    provider = create_provider()
    relevance_scorer = LLMRelevanceScorer(provider)
    extractor = LLMMemoryExtractor(provider)
    buffer = ShortTermMemoryBuffer()
    context_retriever = ShortTermContextRetriever(buffer)
    long_term_memory = InMemoryLongTermMemoryStore(
        single_value_relations={"deadline"}
    )
    consolidator = ShortTermConsolidator(
        short_term_memory=buffer,
        long_term_memory=long_term_memory,
    )

    print(
        "Enter messages. Commands: /memories, /topics, /state, /context, "
        "/consolidate, /long-term, /exit"
    )
    print("State commands: /decision TEXT, /task TEXT, /tool TEXT, /complete TASK_ID")

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
        if text == "/topics":
            topics = buffer.get_topics(user_id="user_1", session_id="session_1")
            print(f"Topics: {len(topics)}")
            for topic in topics:
                status = "active" if topic.is_active else "inactive"
                print(f"- {topic.label} [{status}] ({len(topic.record_ids)} records)")
            continue
        if text == "/state":
            items = buffer.get_reasoning_state(
                user_id="user_1",
                session_id="session_1",
            )
            print(f"State items: {len(items)}")
            for item in items:
                print(f"- {item.id} | {item.kind} | {item.status} | {item.content}")
            continue
        if text == "/context":
            context = context_retriever.retrieve(
                user_id="user_1",
                session_id="session_1",
            )
            print(f"Current topic: {context.topic.label if context.topic else 'none'}")
            print(f"Records: {len(context.records)}")
            print(f"Decisions: {len(context.decisions)}")
            print(f"Open tasks: {len(context.open_tasks)}")
            print(f"Tool results: {len(context.tool_results)}")
            continue
        if text == "/consolidate":
            result = consolidator.consolidate_topic(
                user_id="user_1",
                session_id="session_1",
            )
            print(
                f"Consolidated: {result.created_count} created, "
                f"{result.updated_count} updated, "
                f"{result.unchanged_count} unchanged, "
                f"{result.skipped_fact_count} skipped"
            )
            continue
        if text == "/long-term":
            memories = long_term_memory.get_memories(
                user_id="user_1",
                include_superseded=True,
            )
            print(f"Long-term memories: {len(memories)}")
            for memory in memories:
                print(
                    f"- [{memory.status}] {memory.kind}: "
                    f"{memory.subject} -> {memory.relation} -> {memory.object}"
                )
            continue
        if text.startswith("/decision "):
            item = buffer.add_decision(
                user_id="user_1",
                session_id="session_1",
                content=text.removeprefix("/decision "),
            )
            print(f"Decision stored: {item.id}")
            continue
        if text.startswith("/task "):
            item = buffer.add_task(
                user_id="user_1",
                session_id="session_1",
                content=text.removeprefix("/task "),
            )
            print(f"Task stored: {item.id}")
            continue
        if text.startswith("/tool "):
            item = buffer.add_tool_result(
                user_id="user_1",
                session_id="session_1",
                content=text.removeprefix("/tool "),
            )
            print(f"Tool result stored: {item.id}")
            continue
        if text.startswith("/complete "):
            item = buffer.update_task(
                task_id=text.removeprefix("/complete ").strip(),
                status="completed",
            )
            print(f"Task completed: {item.id}")
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
        topic = buffer.get_current_topic(user_id="user_1", session_id="session_1")
        print(f"Topic: {topic.label}")
        print(
            "Session records:",
            len(buffer.get_recent(user_id="user_1", session_id="session_1")),
        )


if __name__ == "__main__":
    main()
