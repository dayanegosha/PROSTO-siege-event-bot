from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ContentBlock:
    title: str
    transition: str
    photo: str | None = None
    audio: str | None = None


def load_content_blocks(path: Path) -> tuple[ContentBlock, ...]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"Content file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Content file contains invalid JSON: {path}") from exc

    if not isinstance(raw, list) or not raw:
        raise RuntimeError("Content file must contain a non-empty list.")

    blocks: list[ContentBlock] = []
    for index, item in enumerate(raw, start=1):
        if not isinstance(item, dict) or not isinstance(item.get("title"), str):
            raise TypeError(f"Content block {index} requires a text title.")
        blocks.append(
            ContentBlock(
                title=item["title"].strip(),
                transition=str(item.get("transition", "")).strip(),
                photo=_optional_text(item.get("photo")),
                audio=_optional_text(item.get("audio")),
            )
        )
    return tuple(blocks)


def _optional_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None
