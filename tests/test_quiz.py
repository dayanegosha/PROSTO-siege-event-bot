import json
import tempfile
import unittest
from pathlib import Path

from prosto_bot.quiz import Question, SessionStore, VisitorSession, load_questions


class QuizTests(unittest.TestCase):
    def test_load_questions_rejects_missing_correct_option(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "quiz.json"
            path.write_text(
                json.dumps(
                    [
                        {
                            "question": "Вопрос",
                            "options": ["Первый", "Второй"],
                            "correct": "Третий",
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "matching correct answer"):
                load_questions(path)

    def test_answer_is_accepted_once(self) -> None:
        question = Question("Вопрос", ("Нет", "Да"), "Да")
        session = VisitorSession()
        self.assertTrue(session.answer(1, question))
        self.assertEqual(session.score, 1)
        with self.assertRaisesRegex(ValueError, "already been answered"):
            session.answer(1, question)
        self.assertEqual(session.score, 1)

    def test_advancing_resets_answer_state(self) -> None:
        question = Question("Вопрос", ("Нет", "Да"), "Да")
        session = VisitorSession()
        session.answer(0, question)
        session.advance_question()
        self.assertEqual(session.question_index, 1)
        self.assertIsNone(session.current_answer)

    def test_session_store_requires_start(self) -> None:
        store = SessionStore()
        with self.assertRaises(LookupError):
            store.require(7)
        self.assertIs(store.start(7), store.require(7))


if __name__ == "__main__":
    unittest.main()
