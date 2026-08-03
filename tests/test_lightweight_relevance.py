import unittest

from mindmem.input.text import RawTextInput, create_text_input_event
from mindmem.sensory.lightweight_relevance import score_relevance


def event_for(text: str):
    return create_text_input_event(
        RawTextInput(user_id="user-1", session_id="session-1", text=text)
    )


class RelevanceScoringTests(unittest.TestCase):
    def test_filler_is_noise(self):
        result = score_relevance(event_for("ok"))

        self.assertEqual(result.label, "noise")
        self.assertEqual(result.score, 0.0)
        self.assertIn("filler_phrase", result.signals)

    def test_personal_preference_is_relevant(self):
        result = score_relevance(event_for("I prefer short answers, please."))

        self.assertEqual(result.label, "relevant")
        self.assertEqual(result.score, 0.45)
        self.assertIn("preference", result.signals)

    def test_task_with_time_is_relevant(self):
        result = score_relevance(event_for("Remind me tomorrow at 9am."))

        self.assertEqual(result.label, "relevant")
        self.assertEqual(result.score, 0.50)
        self.assertIn("task", result.signals)
        self.assertIn("time_reference", result.signals)

    def test_negation_is_not_removed_or_called_noise(self):
        result = score_relevance(event_for("not good"))

        self.assertEqual(result.label, "unclear")
        self.assertEqual(result.score, 0.0)
        self.assertIn("negation", result.signals)

    def test_unrecognized_statement_is_unclear(self):
        result = score_relevance(event_for("The server stopped unexpectedly."))

        self.assertEqual(result.label, "unclear")
        self.assertEqual(result.score, 0.0)

    def test_question_does_not_increase_score(self):
        result = score_relevance(event_for("What happened here?"))

        self.assertEqual(result.score, 0.0)
        self.assertIn("question", result.signals)

    def test_length_does_not_increase_score(self):
        result = score_relevance(event_for("These words make the message longer without adding a signal."))

        self.assertEqual(result.score, 0.0)
        self.assertIn("longer_text", result.signals)


if __name__ == "__main__":
    unittest.main()
