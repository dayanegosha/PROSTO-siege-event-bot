import tempfile
import unittest
from pathlib import Path

from prosto_bot.database import ResultRepository


class DatabaseTests(unittest.TestCase):
    def test_clean_database_is_initialized_and_mutable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "results.db"
            with ResultRepository(path) as repository:
                self.assertFalse(repository.has_result(42))
                repository.save_result(
                    name="Участник",
                    telegram_id=42,
                    score=7,
                    test_date="2026-01-27",
                    test_time="14:20:00",
                    phone_number="+70000000000",
                )
                self.assertTrue(repository.has_result(42))
                results = repository.list_results()
                self.assertEqual(len(results), 1)
                self.assertEqual(results[0].score, 7)
                self.assertEqual(results[0].attempts, 1)
                self.assertTrue(repository.delete_result(42))
                self.assertFalse(repository.has_result(42))

    def test_upsert_counts_attempts(self) -> None:
        with (
            tempfile.TemporaryDirectory() as directory,
            ResultRepository(Path(directory) / "results.db") as repository,
        ):
            for score in (4, 8):
                repository.save_result(
                    name="Участник",
                    telegram_id=9,
                    score=score,
                    test_date="2026-01-27",
                    test_time="15:00:00",
                    phone_number=None,
                )
            result = repository.list_results()[0]
            self.assertEqual(result.score, 8)
            self.assertEqual(result.attempts, 2)


if __name__ == "__main__":
    unittest.main()
