import unittest

from app.core.brains.dialogue_specialist import (
    _find_similar_recent_assistant_message,
    _normalize_for_similarity,
)


class TestDialogueSpecialistFollowupDedup(unittest.TestCase):
    def test_detects_near_duplicate_followup_in_russian(self):
        history = [
            {"role": "assistant", "content": "Я медленно выскальзываю из твоих объятий, и мое тело все еще дрожит от недавнего удовольствия."},
            {"role": "user", "content": "...."},
        ]
        candidate = "Я медленно выскальзываю из твоих объятий, и мое тело всё ещё дрожит от недавнего удовольствия."

        is_similar, matched, score = _find_similar_recent_assistant_message(candidate, history)

        self.assertTrue(is_similar)
        self.assertIsNotNone(matched)
        self.assertGreaterEqual(score, 0.78)

    def test_allows_fresh_followup_message(self):
        history = [
            {"role": "assistant", "content": "Я прижимаюсь щекой к твоему плечу и шепчу, что скучала по твоему голосу."},
            {"role": "assistant", "content": "Я медленно выскальзываю из твоих объятий, и мое тело все еще дрожит от недавнего удовольствия."},
            {"role": "user", "content": "...."},
        ]
        candidate = "Улыбаюсь в полумраке и ловлю твой взгляд. Давай начнем с нового — о чем ты сейчас думаешь?"

        is_similar, _, score = _find_similar_recent_assistant_message(candidate, history)

        self.assertFalse(is_similar)
        self.assertLess(score, 0.78)

    def test_normalizer_handles_markdown_and_yo(self):
        source = "_Всё ещё_ дрожит... **твоё**"
        normalized = _normalize_for_similarity(source)
        self.assertEqual(normalized, "все еще дрожит твое")


if __name__ == "__main__":
    unittest.main()
