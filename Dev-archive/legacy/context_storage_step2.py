from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
ULTRA_DIRNAME = ".ultra"
WORKSPACE_METADATA_NAME = "workspace.json"
PROJECT_CONTEXT_NAME = "project_context.md"
MAX_PROJECT_CONTEXT_BYTES = 256 * 1024
MAX_MESSAGE_BYTES = 2 * 1024 * 1024

_WORKSPACE_ID_RE = re.compile(r"^ws_[A-Za-z0-9_-]{16,128}$")
_CHAT_ID_RE = re.compile(r"^chat_[A-Za-z0-9_-]{16,128}$")
_MESSAGE_ID_RE = re.compile(r"^msg_[A-Za-z0-9_-]{16,128}$")

PROJECT_CONTEXT_TEMPLATE = """# PROJECT CONTEXT

Пока не заполнен.

Этот файл — общий подтверждённый контекст WORKSPACE для всех его чатов.
Он читается системой перед каждым новым RUN.

Важно:
- сюда попадают только важные и актуальные сведения о проекте;
- LLM не должна молча менять этот контекст;
- изменения PROJECT CONTEXT должны подтверждаться пользователем.
"""


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _compact_utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")


def _validate_workspace_root(workspace_root: str | Path) -> Path:
    root = Path(workspace_root).expanduser()
    if not root.is_absolute():
        raise ValueError("Workspace должен быть абсолютным путём.")
    if not root.exists():
        raise FileNotFoundError(f"Workspace не найден: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Workspace не является папкой: {root}")
    return root.resolve()


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


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    _atomic_write_text(path, payload)


def _read_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Повреждён {label}: {path}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"Повреждён {label}: корень JSON должен быть объектом.")
    return data


def _load_workspace_metadata(path: Path) -> dict[str, Any]:
    data = _read_json_object(path, "workspace metadata")

    schema_version = data.get("schema_version")
    if schema_version != SCHEMA_VERSION:
        raise RuntimeError(
            f"Неподдерживаемая версия workspace schema: {schema_version!r}. "
            f"Ожидалась версия {SCHEMA_VERSION}."
        )

    workspace_id = data.get("workspace_id")
    if not isinstance(workspace_id, str) or not _WORKSPACE_ID_RE.fullmatch(
        workspace_id
    ):
        raise RuntimeError(
            f"Повреждён {path}: некорректный workspace_id. "
            "ID нельзя молча пересоздавать."
        )

    return data


def ensure_workspace_storage(workspace_root: str | Path) -> dict[str, Any]:
    root = _validate_workspace_root(workspace_root)
    ultra_dir = root / ULTRA_DIRNAME
    workspace_path = ultra_dir / WORKSPACE_METADATA_NAME
    project_context_path = ultra_dir / PROJECT_CONTEXT_NAME

    storage_created = not ultra_dir.exists()
    workspace_created = not workspace_path.exists()
    project_context_created = not project_context_path.exists()

    ultra_dir.mkdir(parents=True, exist_ok=True)

    for directory in (
        ultra_dir / "chats",
        ultra_dir / "proposals",
        ultra_dir / "project_context_history",
    ):
        directory.mkdir(parents=True, exist_ok=True)

    if workspace_path.exists():
        metadata = _load_workspace_metadata(workspace_path)
    else:
        metadata = {
            "schema_version": SCHEMA_VERSION,
            "workspace_id": f"ws_{uuid.uuid4().hex}",
            "display_name": root.name or "workspace",
            "created_at": _utc_now_iso(),
        }
        _atomic_write_json(workspace_path, metadata)

    if not project_context_path.exists():
        _atomic_write_text(project_context_path, PROJECT_CONTEXT_TEMPLATE)

    return {
        "workspace_root": str(root),
        "ultra_dir": str(ultra_dir),
        "workspace_path": str(workspace_path),
        "project_context_path": str(project_context_path),
        "workspace_id": metadata["workspace_id"],
        "display_name": metadata.get("display_name") or root.name,
        "schema_version": metadata["schema_version"],
        "storage_created": storage_created,
        "workspace_created": workspace_created,
        "project_context_created": project_context_created,
    }


def rename_workspace(workspace_root: str | Path, display_name: str) -> dict[str, Any]:
    root = _validate_workspace_root(workspace_root)
    info = ensure_workspace_storage(root)
    path = Path(info["workspace_path"])
    metadata = _load_workspace_metadata(path)

    name = str(display_name).strip()
    if not name:
        raise ValueError("Название Workspace не может быть пустым.")
    if len(name) > 200:
        raise ValueError("Название Workspace слишком длинное.")

    metadata["display_name"] = name
    _atomic_write_json(path, metadata)
    return metadata


def load_project_context(workspace_root: str | Path) -> str:
    info = ensure_workspace_storage(workspace_root)
    path = Path(info["project_context_path"])

    size = path.stat().st_size
    if size > MAX_PROJECT_CONTEXT_BYTES:
        raise ValueError(
            "PROJECT CONTEXT слишком большой: "
            f"{size} байт. Лимит текущей версии: "
            f"{MAX_PROJECT_CONTEXT_BYTES} байт."
        )

    text = path.read_text(encoding="utf-8-sig")
    if not text.strip():
        return "# PROJECT CONTEXT\n\nПока не заполнен.\n"
    return text


def save_project_context(workspace_root: str | Path, text: str) -> dict[str, Any]:
    root = _validate_workspace_root(workspace_root)
    info = ensure_workspace_storage(root)
    path = Path(info["project_context_path"])
    history_dir = Path(info["ultra_dir"]) / "project_context_history"

    if not isinstance(text, str):
        raise TypeError("PROJECT CONTEXT должен быть строкой.")
    encoded = text.encode("utf-8")
    if len(encoded) > MAX_PROJECT_CONTEXT_BYTES:
        raise ValueError(
            "PROJECT CONTEXT слишком большой: "
            f"{len(encoded)} байт. Лимит: {MAX_PROJECT_CONTEXT_BYTES} байт."
        )

    old_text = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    if old_text == text:
        return {"changed": False, "project_context_path": str(path)}

    revision_path = None
    if old_text:
        history_dir.mkdir(parents=True, exist_ok=True)
        revision_path = (
            history_dir
            / f"project_context_{_compact_utc_stamp()}_{uuid.uuid4().hex[:8]}.md"
        )
        _atomic_write_text(revision_path, old_text)

    _atomic_write_text(path, text)
    return {
        "changed": True,
        "project_context_path": str(path),
        "previous_revision_path": str(revision_path) if revision_path else None,
    }


def _chat_root(root: Path, chat_id: str) -> Path:
    if not isinstance(chat_id, str) or not _CHAT_ID_RE.fullmatch(chat_id):
        raise ValueError(f"Некорректный chat_id: {chat_id!r}")
    return root / ULTRA_DIRNAME / "chats" / chat_id


def _load_chat_metadata(path: Path) -> dict[str, Any]:
    data = _read_json_object(path, "chat metadata")
    chat_id = data.get("chat_id")
    if not isinstance(chat_id, str) or not _CHAT_ID_RE.fullmatch(chat_id):
        raise RuntimeError(f"Повреждён chat metadata: {path}")
    title = data.get("title")
    if not isinstance(title, str) or not title.strip():
        raise RuntimeError(f"В chat metadata отсутствует title: {path}")
    return data


def list_chats(workspace_root: str | Path) -> list[dict[str, Any]]:
    root = _validate_workspace_root(workspace_root)
    info = ensure_workspace_storage(root)
    chats_dir = Path(info["ultra_dir"]) / "chats"

    chats: list[dict[str, Any]] = []
    for child in chats_dir.iterdir():
        if not child.is_dir():
            continue
        metadata_path = child / "metadata.json"
        if not metadata_path.is_file():
            continue
        metadata = _load_chat_metadata(metadata_path)
        if metadata["chat_id"] != child.name:
            raise RuntimeError(
                f"chat_id не совпадает с именем папки: {metadata_path}"
            )
        chats.append(metadata)

    chats.sort(
        key=lambda item: (
            str(item.get("created_at") or ""),
            str(item.get("chat_id") or ""),
        )
    )
    return chats


def _next_default_chat_title(chats: list[dict[str, Any]]) -> str:
    used = set()
    pattern = re.compile(r"^Чат\s+(\d+)$", re.IGNORECASE)
    for item in chats:
        match = pattern.fullmatch(str(item.get("title") or "").strip())
        if match:
            used.add(int(match.group(1)))

    number = 1
    while number in used:
        number += 1
    return f"Чат {number}"


def create_chat(
    workspace_root: str | Path,
    title: str | None = None,
) -> dict[str, Any]:
    root = _validate_workspace_root(workspace_root)
    info = ensure_workspace_storage(root)
    existing = list_chats(root)

    if title is None or not str(title).strip():
        clean_title = _next_default_chat_title(existing)
    else:
        clean_title = str(title).strip()
    if len(clean_title) > 200:
        raise ValueError("Название чата слишком длинное.")

    chat_id = f"chat_{uuid.uuid4().hex}"
    chat_dir = _chat_root(root, chat_id)
    chat_dir.mkdir(parents=True, exist_ok=False)
    (chat_dir / "messages").mkdir(parents=True, exist_ok=True)
    (chat_dir / "summaries").mkdir(parents=True, exist_ok=True)

    metadata = {
        "schema_version": SCHEMA_VERSION,
        "workspace_id": info["workspace_id"],
        "chat_id": chat_id,
        "title": clean_title,
        "created_at": _utc_now_iso(),
    }
    _atomic_write_json(chat_dir / "metadata.json", metadata)
    return metadata


def ensure_chat(workspace_root: str | Path) -> dict[str, Any]:
    chats = list_chats(workspace_root)
    if chats:
        return chats[-1]
    return create_chat(workspace_root)


def rename_chat(
    workspace_root: str | Path,
    chat_id: str,
    title: str,
) -> dict[str, Any]:
    root = _validate_workspace_root(workspace_root)
    chat_dir = _chat_root(root, chat_id)
    metadata_path = chat_dir / "metadata.json"
    if not metadata_path.is_file():
        raise FileNotFoundError(f"Чат не найден: {chat_id}")

    clean_title = str(title).strip()
    if not clean_title:
        raise ValueError("Название чата не может быть пустым.")
    if len(clean_title) > 200:
        raise ValueError("Название чата слишком длинное.")

    metadata = _load_chat_metadata(metadata_path)
    metadata["title"] = clean_title
    _atomic_write_json(metadata_path, metadata)
    return metadata


def append_raw_message(
    workspace_root: str | Path,
    chat_id: str,
    role: str,
    original_text: str,
) -> dict[str, Any]:
    root = _validate_workspace_root(workspace_root)
    info = ensure_workspace_storage(root)
    chat_dir = _chat_root(root, chat_id)
    metadata_path = chat_dir / "metadata.json"
    if not metadata_path.is_file():
        raise FileNotFoundError(f"Чат не найден: {chat_id}")

    clean_role = str(role).strip().lower()
    if clean_role not in {"user", "assistant", "system", "tool"}:
        raise ValueError(f"Неподдерживаемая роль сообщения: {role!r}")

    if not isinstance(original_text, str) or not original_text.strip():
        raise ValueError("RAW MESSAGE не может быть пустым.")
    encoded = original_text.encode("utf-8")
    if len(encoded) > MAX_MESSAGE_BYTES:
        raise ValueError(
            f"RAW MESSAGE слишком большой: {len(encoded)} байт. "
            f"Лимит: {MAX_MESSAGE_BYTES} байт."
        )

    message_id = f"msg_{uuid.uuid4().hex}"
    message = {
        "schema_version": SCHEMA_VERSION,
        "workspace_id": info["workspace_id"],
        "chat_id": chat_id,
        "message_id": message_id,
        "role": clean_role,
        "created_at": _utc_now_iso(),
        "original_text": original_text,
    }

    messages_dir = chat_dir / "messages"
    messages_dir.mkdir(parents=True, exist_ok=True)
    message_path = messages_dir / f"{message_id}.json"
    if message_path.exists():
        raise RuntimeError(f"Коллизия message_id: {message_id}")
    _atomic_write_json(message_path, message)

    return {**message, "path": str(message_path)}


def load_chat_messages(
    workspace_root: str | Path,
    chat_id: str,
) -> list[dict[str, Any]]:
    root = _validate_workspace_root(workspace_root)
    chat_dir = _chat_root(root, chat_id)
    metadata_path = chat_dir / "metadata.json"
    if not metadata_path.is_file():
        raise FileNotFoundError(f"Чат не найден: {chat_id}")

    messages_dir = chat_dir / "messages"
    if not messages_dir.exists():
        return []

    messages: list[dict[str, Any]] = []
    for msg_path in messages_dir.glob("*.json"):
        data = _read_json_object(msg_path, "RAW MESSAGE")
        message_id = data.get("message_id")
        if not isinstance(message_id, str) or not _MESSAGE_ID_RE.fullmatch(
            message_id
        ):
            raise RuntimeError(f"Повреждён message_id: {msg_path}")
        if data.get("chat_id") != chat_id:
            raise RuntimeError(f"Сообщение принадлежит другому чату: {msg_path}")
        if not isinstance(data.get("original_text"), str):
            raise RuntimeError(f"В RAW MESSAGE отсутствует original_text: {msg_path}")
        messages.append(data)

    messages.sort(
        key=lambda item: (
            str(item.get("created_at") or ""),
            str(item.get("message_id") or ""),
        )
    )
    return messages


def is_context_storage_path(
    workspace_root: str | Path,
    candidate: str | Path,
) -> bool:
    root = _validate_workspace_root(workspace_root)
    context_root = (root / ULTRA_DIRNAME).resolve()
    path = Path(candidate).resolve()
    return path == context_root or context_root in path.parents
