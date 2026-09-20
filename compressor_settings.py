from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any

from agent_global_context import AGENTS_ROOT


MAX_MESSAGE_COMPRESSION_TEMPLATE_BYTES = 256 * 1024
MESSAGE_COMPRESSION_TEMPLATE_PATH = (
    AGENTS_ROOT / "compressor" / "message_compression_template.md"
).resolve()

DEFAULT_MESSAGE_COMPRESSION_TEMPLATE = """# MESSAGE COMPRESSION TEMPLATE

Compress the SOURCE TEXT by approximately {{REDUCTION_PERCENT}}%.
Aim to retain approximately {{REMAINING_PERCENT}}% of the original length.

Preserve meaning, facts, constraints, numbers, names, relationships, and
important qualifications. Return only the compressed message text.
"""


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temp_path.open("w", encoding="utf-8", newline="\n") as file:
            file.write(text)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp_path, path)
    finally:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass


def get_message_compression_template_path() -> Path:
    return MESSAGE_COMPRESSION_TEMPLATE_PATH


def load_message_compression_template() -> str:
    path = get_message_compression_template_path()
    if not path.is_file():
        return DEFAULT_MESSAGE_COMPRESSION_TEMPLATE

    size = path.stat().st_size
    if size > MAX_MESSAGE_COMPRESSION_TEMPLATE_BYTES:
        raise ValueError(
            "Шаблон задачи COMPRESSOR слишком большой: "
            f"{size} байт. Лимит: "
            f"{MAX_MESSAGE_COMPRESSION_TEMPLATE_BYTES} байт."
        )

    text = path.read_text(encoding="utf-8-sig")
    if not text.strip():
        raise RuntimeError("Шаблон задачи COMPRESSOR пуст.")
    return text


def save_message_compression_template(text: str) -> dict[str, Any]:
    if not isinstance(text, str):
        raise TypeError("Шаблон задачи COMPRESSOR должен быть строкой.")
    if not text.strip():
        raise ValueError("Шаблон задачи COMPRESSOR не может быть пустым.")

    encoded = text.encode("utf-8")
    if len(encoded) > MAX_MESSAGE_COMPRESSION_TEMPLATE_BYTES:
        raise ValueError(
            "Шаблон задачи COMPRESSOR слишком большой: "
            f"{len(encoded)} байт. Лимит: "
            f"{MAX_MESSAGE_COMPRESSION_TEMPLATE_BYTES} байт."
        )

    path = get_message_compression_template_path()
    old_text = path.read_text(encoding="utf-8-sig") if path.is_file() else ""
    if old_text == text:
        return {"changed": False, "path": str(path)}

    _atomic_write_text(path, text)
    return {"changed": True, "path": str(path)}
