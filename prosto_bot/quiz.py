from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Question:
    text: str
    options: tuple[str, ...]
    correct: str


def load_questions(path: Path) -> tuple[Question, ...]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"Quiz file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Quiz file contains invalid JSON: {path}") from exc

    if not isinstance(raw, list) or not raw:
        raise RuntimeError("Quiz file must contain a non-empty list.")

    questions: list[Question] = []
    for index, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            raise TypeError(f"Question {index} must be an object.")
        text = item.get("question")
        options = item.get("options")
        correct = item.get("correct")
        if not isinstance(text, str) or not isinstance(options, list) or not options:
            raise RuntimeError(f"Question {index} has an invalid text or option list.")
        if not all(isinstance(option, str) for option in options):
            raise RuntimeError(f"Question {index} contains a non-text option.")
        if not isinstance(correct, str) or correct not in options:
            raise RuntimeError(f"Question {index} has no matching correct answer.")
        questions.append(Question(text=text, options=tuple(options), correct=correct))
    return tuple(questions)


@dataclass(slots=True)
class VisitorSession:
    content_index: int = 0
    question_index: int = 0
    score: int = 0
    phone_number: str | None = None
    current_answer: int | None = None
    previous_message_id: int | None = None

    def answer(self, option_index: int, question: Question) -> bool:
        if self.current_answer is not None:
            raise ValueError("The current question has already been answered.")
        if option_index < 0 or option_index >= len(question.options):
            raise ValueError("Answer index is outside the available options.")
        self.current_answer = option_index
        is_correct = question.options[option_index] == question.correct
        if is_correct:
            self.score += 1
        return is_correct

    def advance_question(self) -> None:
        self.question_index += 1
        self.current_answer = None


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[int, VisitorSession] = {}
        self._pending_admin_deletion: set[int] = set()

    def start(self, user_id: int) -> VisitorSession:
        session = VisitorSession()
        self._sessions[user_id] = session
        return session

    def get(self, user_id: int) -> VisitorSession | None:
        return self._sessions.get(user_id)

    def require(self, user_id: int) -> VisitorSession:
        session = self.get(user_id)
        if session is None:
            raise LookupError("Start the bot with /start first.")
        return session

    def request_admin_deletion(self, admin_id: int) -> None:
        self._pending_admin_deletion.add(admin_id)

    def cancel_admin_deletion(self, admin_id: int) -> None:
        self._pending_admin_deletion.discard(admin_id)

    def awaits_admin_deletion(self, admin_id: int) -> bool:
        return admin_id in self._pending_admin_deletion
