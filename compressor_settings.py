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
FINAL_CHECK_TEMPLATE_PATH = (
    AGENTS_ROOT / "compressor" / "final_check_template.md"
).resolve()

DEFAULT_MESSAGE_COMPRESSION_TEMPLATE = """# MESSAGE COMPRESSION TEMPLATE

Compress the canonical RAW SOURCE TEXT by approximately
{{REDUCTION_PERCENT}}%.

Preserve meaning, facts, constraints, numbers, names,
relationships and important qualifications.

Meaning preservation has priority over matching the target exactly.

Return only the compressed message text.
"""

DEFAULT_FINAL_CHECK_TEMPLATE = """FINAL CHECK:

Before returning the result, compare it specifically with the
original full RAW SOURCE TEXT.

Make sure the result has moved reasonably toward approximately
{{REDUCTION_PERCENT}}% reduction from that ORIGINAL RAW SOURCE.

Do not sacrifice meaning merely to hit the number exactly.

Return only the compressed text.
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


def get_final_check_template_path() -> Path:
    return FINAL_CHECK_TEMPLATE_PATH


def _load_template(path: Path, default_text: str, label: str) -> str:
    if not path.is_file():
        return default_text

    size = path.stat().st_size
    if size > MAX_MESSAGE_COMPRESSION_TEMPLATE_BYTES:
        raise ValueError(
            f"{label} слишком большой: "
            f"{size} байт. Лимит: "
            f"{MAX_MESSAGE_COMPRESSION_TEMPLATE_BYTES} байт."
        )

    text = path.read_text(encoding="utf-8-sig")
    if not text.strip():
        raise RuntimeError(f"{label} пуст.")
    return text


def _save_template(path: Path, text: str, label: str) -> dict[str, Any]:
    if not isinstance(text, str):
        raise TypeError(f"{label} должен быть строкой.")
    if not text.strip():
        raise ValueError(f"{label} не может быть пустым.")

    encoded = text.encode("utf-8")
    if len(encoded) > MAX_MESSAGE_COMPRESSION_TEMPLATE_BYTES:
        raise ValueError(
            f"{label} слишком большой: "
            f"{len(encoded)} байт. Лимит: "
            f"{MAX_MESSAGE_COMPRESSION_TEMPLATE_BYTES} байт."
        )

    old_text = path.read_text(encoding="utf-8-sig") if path.is_file() else ""
    if old_text == text:
        return {"changed": False, "path": str(path)}

    _atomic_write_text(path, text)
    return {"changed": True, "path": str(path)}


def load_message_compression_template() -> str:
    return _load_template(
        get_message_compression_template_path(),
        DEFAULT_MESSAGE_COMPRESSION_TEMPLATE,
        "Шаблон задачи COMPRESSOR",
    )


def save_message_compression_template(text: str) -> dict[str, Any]:
    return _save_template(
        get_message_compression_template_path(),
        text,
        "Шаблон задачи COMPRESSOR",
    )


def load_final_check_template() -> str:
    return _load_template(
        get_final_check_template_path(),
        DEFAULT_FINAL_CHECK_TEMPLATE,
        "Шаблон FINAL CHECK COMPRESSOR",
    )


def save_final_check_template(text: str) -> dict[str, Any]:
    return _save_template(
        get_final_check_template_path(),
        text,
        "Шаблон FINAL CHECK COMPRESSOR",
    )
