import json
import tempfile
import unittest
from pathlib import Path

from prosto_bot.content import load_content_blocks


class ContentTests(unittest.TestCase):
    def test_optional_media_fields_become_none(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "content.json"
            path.write_text(
                json.dumps(
                    [{"title": "Раздел", "photo": "", "audio": ""}],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            block = load_content_blocks(path)[0]
            self.assertEqual(block.title, "Раздел")
            self.assertIsNone(block.photo)
            self.assertIsNone(block.audio)


if __name__ == "__main__":
    unittest.main()
