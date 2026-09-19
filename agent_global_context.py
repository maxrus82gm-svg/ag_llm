from __future__ import annotations

import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


APP_DATA_ROOT = (
    Path(os.getenv("LOCALAPPDATA") or Path.home())
    / "GigaChatUltra"
).resolve()
AGENTS_ROOT = APP_DATA_ROOT / "agents"
MAX_GLOBAL_AGENT_CONTEXT_BYTES = 256 * 1024
_AGENT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


def _validate_agent_id(agent_id: str) -> str:
    value = str(agent_id).strip().lower()
    if not _AGENT_ID_RE.fullmatch(value):
        raise ValueError(f"Некорректный agent_id: {agent_id!r}")
    return value


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temp.open("w", encoding="utf-8", newline="\n") as file:
            file.write(text)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp, path)
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass


def get_agent_global_context_path(agent_id: str = "ultra") -> Path:
    agent_id = _validate_agent_id(agent_id)
    return (AGENTS_ROOT / agent_id / "global_context.md").resolve()


def load_agent_global_context(
    agent_id: str = "ultra",
    *,
    allow_missing: bool = False,
) -> str:
    path = get_agent_global_context_path(agent_id)

    if not path.is_file():
        if allow_missing:
            return ""
        raise FileNotFoundError(
            f"Глобальный контекст агента {agent_id!r} ещё не настроен. "
            "Открой его редактор в UI и сохрани непустой текст."
        )

    size = path.stat().st_size
    if size > MAX_GLOBAL_AGENT_CONTEXT_BYTES:
        raise ValueError(
            "Глобальный контекст агента слишком большой: "
            f"{size} байт. Лимит: {MAX_GLOBAL_AGENT_CONTEXT_BYTES} байт."
        )

    text = path.read_text(encoding="utf-8-sig")
    if not text.strip():
        if allow_missing:
            return ""
        raise RuntimeError(
            f"Глобальный контекст агента {agent_id!r} пуст. "
            "RUN без глобального контекста запрещён."
        )
    return text


def save_agent_global_context(
    text: str,
    agent_id: str = "ultra",
) -> dict[str, Any]:
    agent_id = _validate_agent_id(agent_id)
    if not isinstance(text, str):
        raise TypeError("Глобальный контекст агента должен быть строкой.")
    if not text.strip():
        raise ValueError("Глобальный контекст агента не может быть пустым.")

    encoded = text.encode("utf-8")
    if len(encoded) > MAX_GLOBAL_AGENT_CONTEXT_BYTES:
        raise ValueError(
            "Глобальный контекст агента слишком большой: "
            f"{len(encoded)} байт. Лимит: {MAX_GLOBAL_AGENT_CONTEXT_BYTES} байт."
        )

    path = get_agent_global_context_path(agent_id)
    old_text = path.read_text(encoding="utf-8-sig") if path.is_file() else ""
    if old_text == text:
        return {
            "changed": False,
            "path": str(path),
            "previous_revision_path": None,
        }

    revision_path = None
    if old_text.strip():
        history_dir = path.parent / "history"
        history_dir.mkdir(parents=True, exist_ok=True)
        revision_path = (
            history_dir
            / f"global_context_{_utc_stamp()}_{uuid.uuid4().hex[:8]}.md"
        )
        _atomic_write_text(revision_path, old_text)

    _atomic_write_text(path, text)
    return {
        "changed": True,
        "path": str(path),
        "previous_revision_path": (
            str(revision_path) if revision_path is not None else None
        ),
    }
