from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Self


@dataclass(frozen=True, slots=True)
class Result:
    name: str
    telegram_id: int
    score: int
    attempts: int
    test_date: str
    test_time: str
    phone_number: str | None


class ResultRepository:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(path)
        self._connection.row_factory = sqlite3.Row
        self._initialize()

    def _initialize(self) -> None:
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                score INTEGER NOT NULL DEFAULT 0,
                attempts INTEGER NOT NULL DEFAULT 0,
                test_date TEXT NOT NULL DEFAULT '',
                test_time TEXT NOT NULL DEFAULT '',
                phone_number TEXT
            )
            """
        )
        columns = {
            row["name"] for row in self._connection.execute("PRAGMA table_info(users)")
        }
        migrations = {
            "test_date": "ALTER TABLE users ADD COLUMN test_date TEXT NOT NULL DEFAULT ''",
            "test_time": "ALTER TABLE users ADD COLUMN test_time TEXT NOT NULL DEFAULT ''",
            "phone_number": "ALTER TABLE users ADD COLUMN phone_number TEXT",
            "attempts": "ALTER TABLE users ADD COLUMN attempts INTEGER NOT NULL DEFAULT 0",
        }
        for column, statement in migrations.items():
            if column not in columns:
                self._connection.execute(statement)
        self._connection.commit()

    def has_result(self, telegram_id: int) -> bool:
        row = self._connection.execute(
            "SELECT 1 FROM users WHERE telegram_id = ?", (telegram_id,)
        ).fetchone()
        return row is not None

    def save_result(
        self,
        *,
        name: str,
        telegram_id: int,
        score: int,
        test_date: str,
        test_time: str,
        phone_number: str | None,
    ) -> None:
        self._connection.execute(
            """
            INSERT INTO users (
                telegram_id, name, score, attempts, test_date, test_time, phone_number
            ) VALUES (?, ?, ?, 1, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                name = excluded.name,
                score = excluded.score,
                attempts = users.attempts + 1,
                test_date = excluded.test_date,
                test_time = excluded.test_time,
                phone_number = excluded.phone_number
            """,
            (telegram_id, name, score, test_date, test_time, phone_number),
        )
        self._connection.commit()

    def list_results(self) -> list[Result]:
        rows = self._connection.execute(
            """
            SELECT name, telegram_id, score, attempts, test_date, test_time, phone_number
            FROM users
            ORDER BY test_date, test_time, telegram_id
            """
        ).fetchall()
        return [Result(**dict(row)) for row in rows]

    def delete_result(self, telegram_id: int) -> bool:
        cursor = self._connection.execute(
            "DELETE FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        self._connection.commit()
        return cursor.rowcount > 0

    def clear(self) -> int:
        cursor = self._connection.execute("DELETE FROM users")
        self._connection.commit()
        return cursor.rowcount

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
