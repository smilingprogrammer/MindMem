from dotenv import load_dotenv

from examples.provider_setup import create_provider
from mindmem.input.text import RawTextInput, create_text_input_event
from mindmem.sensory.lightweight_relevance import score_relevance
from mindmem.sensory.relevance.llm_relevance import LLMRelevanceScorer


EXAMPLES = [
    "The server stopped unexpectedly after today's deployment.",
    "That makes sense.",
    "My colleague called.",
]


def main(*, include_reason: bool = False) -> None:
    load_dotenv()
    provider = create_provider()

    scorer = LLMRelevanceScorer(provider)

    for text in EXAMPLES:
        event = create_text_input_event(
            RawTextInput(
                user_id="user_1",
                session_id="session_1",
                text=text,
            )
        )
        heuristic = score_relevance(event)

        print(f"Input: {text}")
        print(f"Heuristic: {heuristic.label} ({heuristic.score})")

        if heuristic.label == "unclear":
            result = scorer.score(
                event,
                heuristic,
                context=[],
                include_reason=include_reason,
            )
            print(f"LLM: {result.label} ({result.score})")
            if result.reason is not None:
                print(f"Reason: {result.reason}")
        else:
            print("LLM: not called")

        print()


if __name__ == "__main__":
    main(include_reason=True)
