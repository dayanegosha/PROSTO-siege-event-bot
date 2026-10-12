from dataclasses import dataclass

from .config import Settings
from .content import ContentBlock
from .database import ResultRepository
from .quiz import Question, SessionStore


@dataclass(slots=True)
class AppContext:
    settings: Settings
    database: ResultRepository
    questions: tuple[Question, ...]
    content_blocks: tuple[ContentBlock, ...]
    sessions: SessionStore
