from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str
    admin_id: int
    database_path: Path
    quiz_path: Path
    content_path: Path
    prize_deadline: date | None
    log_level: str

    @classmethod
    def from_env(cls) -> Settings:
        token = os.getenv("BOT_TOKEN", "").strip()
        if not token:
            raise RuntimeError("Set BOT_TOKEN before starting the bot.")

        admin_raw = os.getenv("ADMIN_ID", "0").strip()
        try:
            admin_id = int(admin_raw)
        except ValueError as exc:
            raise RuntimeError("ADMIN_ID must be an integer.") from exc

        deadline_raw = os.getenv("PRIZE_DEADLINE", "2024-01-27").strip()
        try:
            deadline = date.fromisoformat(deadline_raw) if deadline_raw else None
        except ValueError as exc:
            raise RuntimeError("PRIZE_DEADLINE must use YYYY-MM-DD format.") from exc

        return cls(
            bot_token=token,
            admin_id=admin_id,
            database_path=Path(
                os.getenv("DATABASE_PATH", PROJECT_ROOT / "users_data.db")
            ),
            quiz_path=Path(
                os.getenv("QUIZ_PATH", PROJECT_ROOT / "quiz_questions.json")
            ),
            content_path=Path(
                os.getenv("CONTENT_PATH", PROJECT_ROOT / "content_blocks.json")
            ),
            prize_deadline=deadline,
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        )
