from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
MESSAGE_CONTEXT_SCHEMA_VERSION = 1
ULTRA_DIRNAME = ".ultra"
WORKSPACE_METADATA_NAME = "workspace.json"
PROJECT_CONTEXT_NAME = "project_context.md"
MAX_PROJECT_CONTEXT_BYTES = 256 * 1024
MAX_MESSAGE_BYTES = 2 * 1024 * 1024
MAX_CONTEXT_VARIANT_BYTES = 2 * 1024 * 1024

_WORKSPACE_ID_RE = re.compile(r"^ws_[A-Za-z0-9_-]{16,128}$")
_CHAT_ID_RE = re.compile(r"^chat_[A-Za-z0-9_-]{16,128}$")
_MESSAGE_ID_RE = re.compile(r"^msg_[A-Za-z0-9_-]{16,128}$")
_CONTEXT_VARIANT_ID_RE = re.compile(r"^ctxv_[A-Za-z0-9_-]{16,128}$")
_LLM_PRODUCER_STRING_FIELDS = (
    "kind",
    "role_id",
    "run_id",
    "model_id",
    "model_display_name",
    "provider",
    "provider_model_id",
)

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


def _validate_producer(producer: object) -> dict[str, Any]:
    if not isinstance(producer, dict):
        raise TypeError("producer должен быть словарём.")

    kind = producer.get("kind")
    if not isinstance(kind, str) or not kind.strip():
        raise ValueError("producer.kind должен быть непустой строкой.")

    if kind == "llm":
        for field in _LLM_PRODUCER_STRING_FIELDS:
            value = producer.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"producer.{field} должен быть непустой строкой."
                )

    return dict(producer)


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


def _probe_existing_workspace_internal(
    workspace_root: str | Path,
    expected_workspace_id: str | None = None,
) -> tuple[dict[str, Any], Path | None, dict[str, Any] | None]:
    root = Path(workspace_root).expanduser()
    result: dict[str, Any] = {
        "status": "missing_path",
        "workspace_root": str(root),
    }

    try:
        exists = root.exists()
    except OSError as exc:
        result["error"] = str(exc)
        return result, None, None
    if not exists:
        return result, None, None

    try:
        is_directory = root.is_dir()
    except OSError as exc:
        result["error"] = str(exc)
        return result, None, None
    if not is_directory:
        result["status"] = "not_directory"
        return result, None, None

    try:
        root = root.resolve()
    except OSError as exc:
        result["error"] = str(exc)
        return result, None, None
    result["workspace_root"] = str(root)

    metadata_path = root / ULTRA_DIRNAME / WORKSPACE_METADATA_NAME
    if not metadata_path.is_file():
        result["status"] = "missing_metadata"
        return result, root, None

    try:
        metadata = _load_workspace_metadata(metadata_path)
    except (OSError, UnicodeError, RuntimeError) as exc:
        result["status"] = "invalid_metadata"
        result["error"] = str(exc)
        return result, root, None

    actual_workspace_id = metadata["workspace_id"]
    if (
        expected_workspace_id is not None
        and actual_workspace_id != expected_workspace_id
    ):
        result.update(
            {
                "status": "id_conflict",
                "expected_workspace_id": expected_workspace_id,
                "actual_workspace_id": actual_workspace_id,
            }
        )
        return result, root, metadata

    result.update(
        {
            "status": "ok",
            "workspace_id": actual_workspace_id,
            "display_name": metadata.get("display_name") or root.name,
            "schema_version": metadata["schema_version"],
        }
    )
    return result, root, metadata


def probe_existing_workspace(
    workspace_root: str | Path,
    expected_workspace_id: str | None = None,
) -> dict[str, Any]:
    """Read-only probe существующей Workspace identity без создания storage."""
    result, _root, _metadata = _probe_existing_workspace_internal(
        workspace_root,
        expected_workspace_id,
    )
    return result


def _require_existing_workspace(
    workspace_root: str | Path,
    expected_workspace_id: str | None = None,
) -> tuple[Path, dict[str, Any]]:
    result, root, metadata = _probe_existing_workspace_internal(
        workspace_root,
        expected_workspace_id,
    )
    status = result["status"]
    if status == "ok" and root is not None and metadata is not None:
        return root, metadata
    if status == "missing_path":
        raise FileNotFoundError(
            f"Workspace не найден: {result['workspace_root']}"
        )
    if status == "not_directory":
        raise NotADirectoryError(
            f"Workspace не является папкой: {result['workspace_root']}"
        )
    if status == "missing_metadata":
        raise FileNotFoundError(
            "Workspace metadata не найдена: "
            f"{result['workspace_root']}"
        )
    if status == "id_conflict":
        raise RuntimeError(
            "Workspace identity conflict: expected="
            f"{result.get('expected_workspace_id')!r}, actual="
            f"{result.get('actual_workspace_id')!r}."
        )
    raise RuntimeError(
        result.get("error")
        or f"Workspace metadata недоступна: {result['workspace_root']}"
    )


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


def _read_project_context_file(path: Path) -> str:
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


def load_project_context(workspace_root: str | Path) -> str:
    info = ensure_workspace_storage(workspace_root)
    path = Path(info["project_context_path"])
    return _read_project_context_file(path)


def load_existing_project_context(
    workspace_root: str | Path,
    *,
    expected_workspace_id: str | None = None,
) -> str | None:
    """Прочитать существующий PROJECT CONTEXT без создания файла."""
    root, _metadata = _require_existing_workspace(
        workspace_root,
        expected_workspace_id,
    )
    path = root / ULTRA_DIRNAME / PROJECT_CONTEXT_NAME
    if not path.exists():
        return None
    if not path.is_file():
        raise FileNotFoundError(f"PROJECT CONTEXT недоступен: {path}")
    return _read_project_context_file(path)


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


def _list_existing_chats_from_root(root: Path) -> list[dict[str, Any]]:
    chats_dir = root / ULTRA_DIRNAME / "chats"
    if not chats_dir.exists():
        return []
    if not chats_dir.is_dir():
        raise NotADirectoryError(f"Папка чатов недоступна: {chats_dir}")
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


def list_chats(workspace_root: str | Path) -> list[dict[str, Any]]:
    root = _validate_workspace_root(workspace_root)
    info = ensure_workspace_storage(root)
    return _list_existing_chats_from_root(Path(info["workspace_root"]))


def list_existing_chats(
    workspace_root: str | Path,
    *,
    expected_workspace_id: str | None = None,
) -> list[dict[str, Any]]:
    """Перечислить существующие чаты без создания storage или Chat 1."""
    root, _metadata = _require_existing_workspace(
        workspace_root,
        expected_workspace_id,
    )
    return _list_existing_chats_from_root(root)


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
    *,
    producer: dict[str, Any] | None = None,
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
    if producer is not None:
        message["producer"] = _validate_producer(producer)

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
        if "producer" in data:
            try:
                _validate_producer(data["producer"])
            except (TypeError, ValueError) as exc:
                raise RuntimeError(
                    f"Повреждён producer RAW MESSAGE: {msg_path}"
                ) from exc
        messages.append(data)

    messages.sort(
        key=lambda item: (
            str(item.get("created_at") or ""),
            str(item.get("message_id") or ""),
        )
    )
    return messages


def _require_chat(
    root: Path,
    workspace_metadata: dict[str, Any],
    chat_id: str,
) -> tuple[Path, dict[str, Any]]:
    chat_dir = _chat_root(root, chat_id)
    metadata_path = chat_dir / "metadata.json"
    if not metadata_path.is_file():
        raise FileNotFoundError(f"Чат не найден: {chat_id}")
    metadata = _load_chat_metadata(metadata_path)
    if metadata.get("chat_id") != chat_id:
        raise RuntimeError(f"chat_id не совпадает с папкой: {metadata_path}")
    if metadata.get("workspace_id") != workspace_metadata.get("workspace_id"):
        raise RuntimeError(f"Чат принадлежит другому Workspace: {metadata_path}")
    return chat_dir, metadata


def _validate_message_id(message_id: str) -> str:
    if not isinstance(message_id, str) or not _MESSAGE_ID_RE.fullmatch(message_id):
        raise ValueError(f"Некорректный message_id: {message_id!r}")
    return message_id


def _validate_context_variant_id(context_variant_id: str) -> str:
    if (
        not isinstance(context_variant_id, str)
        or not _CONTEXT_VARIANT_ID_RE.fullmatch(context_variant_id)
    ):
        raise ValueError(
            f"Некорректный context_variant_id: {context_variant_id!r}"
        )
    return context_variant_id


def load_raw_message(
    workspace_root: str | Path,
    chat_id: str,
    message_id: str,
) -> dict[str, Any]:
    """Load one immutable RAW MESSAGE by identity without creating storage."""
    root, workspace_metadata = _require_existing_workspace(workspace_root)
    chat_dir, _chat_metadata = _require_chat(root, workspace_metadata, chat_id)
    _validate_message_id(message_id)
    path = chat_dir / "messages" / f"{message_id}.json"
    if not path.is_file():
        raise FileNotFoundError(f"RAW MESSAGE не найден: {message_id}")
    data = _read_json_object(path, "RAW MESSAGE")
    if data.get("workspace_id") != workspace_metadata.get("workspace_id"):
        raise RuntimeError(f"RAW MESSAGE принадлежит другому Workspace: {path}")
    if data.get("chat_id") != chat_id or data.get("message_id") != message_id:
        raise RuntimeError(f"Повреждена identity RAW MESSAGE: {path}")
    if not isinstance(data.get("original_text"), str):
        raise RuntimeError(f"В RAW MESSAGE отсутствует original_text: {path}")
    return data


def _message_context_root(chat_dir: Path, message_id: str) -> Path:
    return chat_dir / "message_context" / message_id


def _default_message_context_state(
    workspace_id: str,
    chat_id: str,
    message_id: str,
) -> dict[str, Any]:
    return {
        "schema_version": MESSAGE_CONTEXT_SCHEMA_VERSION,
        "workspace_id": workspace_id,
        "chat_id": chat_id,
        "message_id": message_id,
        "active_representation": "raw",
        "active_variant_id": None,
        "updated_at": None,
    }


def _validate_context_owner(
    data: dict[str, Any],
    *,
    label: str,
    workspace_id: str,
    chat_id: str,
    message_id: str,
) -> None:
    if data.get("schema_version") != MESSAGE_CONTEXT_SCHEMA_VERSION:
        raise RuntimeError(
            f"Неподдерживаемая версия {label}: {data.get('schema_version')!r}."
        )
    expected = {
        "workspace_id": workspace_id,
        "chat_id": chat_id,
        "message_id": message_id,
    }
    for key, value in expected.items():
        if data.get(key) != value:
            raise RuntimeError(f"{label} принадлежит другому {key}: {data.get(key)!r}")


def get_message_context_state(
    workspace_root: str | Path,
    chat_id: str,
    message_id: str,
) -> dict[str, Any]:
    """Return persisted state, or a non-persisted FULL default for legacy RAW."""
    root, workspace_metadata = _require_existing_workspace(workspace_root)
    chat_dir, _chat_metadata = _require_chat(root, workspace_metadata, chat_id)
    load_raw_message(root, chat_id, message_id)
    state_path = _message_context_root(chat_dir, message_id) / "state.json"
    if not state_path.exists():
        return _default_message_context_state(
            workspace_metadata["workspace_id"], chat_id, message_id
        )
    if not state_path.is_file():
        raise RuntimeError(f"MESSAGE CONTEXT state недоступен: {state_path}")
    state = _read_json_object(state_path, "MESSAGE CONTEXT state")
    _validate_context_owner(
        state,
        label="MESSAGE CONTEXT state",
        workspace_id=workspace_metadata["workspace_id"],
        chat_id=chat_id,
        message_id=message_id,
    )
    representation = state.get("active_representation")
    variant_id = state.get("active_variant_id")
    if representation == "raw":
        if variant_id is not None:
            raise RuntimeError("Повреждён MESSAGE CONTEXT state: RAW с active_variant_id.")
    elif representation == "summary":
        try:
            _validate_context_variant_id(variant_id)
        except ValueError as exc:
            raise RuntimeError(
                "Повреждён MESSAGE CONTEXT state: некорректный active_variant_id."
            ) from exc
        # Fail closed immediately if the active reference is missing/corrupt.
        load_context_variant(root, chat_id, message_id, variant_id)
    else:
        raise RuntimeError(
            "Повреждён MESSAGE CONTEXT state: неизвестное active_representation."
        )
    return state


def load_context_variant(
    workspace_root: str | Path,
    chat_id: str,
    message_id: str,
    context_variant_id: str,
) -> dict[str, Any]:
    root, workspace_metadata = _require_existing_workspace(workspace_root)
    chat_dir, _chat_metadata = _require_chat(root, workspace_metadata, chat_id)
    load_raw_message(root, chat_id, message_id)
    _validate_context_variant_id(context_variant_id)
    path = (
        _message_context_root(chat_dir, message_id)
        / "variants"
        / f"{context_variant_id}.json"
    )
    if not path.is_file():
        raise RuntimeError(f"Активный Context Variant не найден: {path}")
    data = _read_json_object(path, "Context Variant")
    _validate_context_owner(
        data,
        label="Context Variant",
        workspace_id=workspace_metadata["workspace_id"],
        chat_id=chat_id,
        message_id=message_id,
    )
    if data.get("context_variant_id") != context_variant_id:
        raise RuntimeError(f"Context Variant id не совпадает с именем файла: {path}")
    text = data.get("text")
    if not isinstance(text, str) or not text.strip():
        raise RuntimeError(f"Context Variant содержит пустой text: {path}")
    if len(text.encode("utf-8")) > MAX_CONTEXT_VARIANT_BYTES:
        raise RuntimeError(f"Context Variant превышает допустимый размер: {path}")
    parent_id = data.get("parent_variant_id")
    if parent_id is not None:
        try:
            _validate_context_variant_id(parent_id)
        except ValueError as exc:
            raise RuntimeError(f"Context Variant имеет некорректный parent id: {path}") from exc
    return data


def activate_message_context_variant(
    workspace_root: str | Path,
    chat_id: str,
    message_id: str,
    context_variant_id: str,
    *,
    require_raw: bool = False,
) -> dict[str, Any]:
    root, workspace_metadata = _require_existing_workspace(workspace_root)
    chat_dir, _chat_metadata = _require_chat(root, workspace_metadata, chat_id)
    current = get_message_context_state(root, chat_id, message_id)
    if require_raw and current["active_representation"] != "raw":
        raise RuntimeError(
            "Повторное сжатие запрещено: сначала восстановите RAW в контекст."
        )
    load_context_variant(root, chat_id, message_id, context_variant_id)
    state = {
        "schema_version": MESSAGE_CONTEXT_SCHEMA_VERSION,
        "workspace_id": workspace_metadata["workspace_id"],
        "chat_id": chat_id,
        "message_id": message_id,
        "active_representation": "summary",
        "active_variant_id": context_variant_id,
        "updated_at": _utc_now_iso(),
    }
    state_path = _message_context_root(chat_dir, message_id) / "state.json"
    _atomic_write_json(state_path, state)
    return state


def create_message_context_variant(
    workspace_root: str | Path,
    chat_id: str,
    message_id: str,
    text: str,
    *,
    source: str,
    parent_variant_id: str | None = None,
    manually_edited: bool = False,
    compression: dict[str, Any] | None = None,
    activate: bool = True,
    require_raw: bool = False,
) -> dict[str, Any]:
    root, workspace_metadata = _require_existing_workspace(workspace_root)
    chat_dir, _chat_metadata = _require_chat(root, workspace_metadata, chat_id)
    raw = load_raw_message(root, chat_id, message_id)
    if raw.get("role") not in {"user", "assistant"}:
        raise ValueError("Context Variant допустим только для user/assistant message.")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Текст Context Variant не может быть пустым.")
    if len(text.encode("utf-8")) > MAX_CONTEXT_VARIANT_BYTES:
        raise ValueError("Текст Context Variant превышает допустимый размер.")
    clean_source = str(source).strip()
    if clean_source not in {"llm_compression", "manual_edit"}:
        raise ValueError(f"Некорректный source Context Variant: {source!r}")
    if clean_source == "llm_compression":
        require_raw = True
    current = get_message_context_state(root, chat_id, message_id)
    if require_raw and current["active_representation"] != "raw":
        raise RuntimeError(
            "Повторное сжатие запрещено: сначала восстановите RAW в контекст."
        )
    if parent_variant_id is not None:
        load_context_variant(root, chat_id, message_id, parent_variant_id)
    variant_id = f"ctxv_{uuid.uuid4().hex}"
    variant = {
        "schema_version": MESSAGE_CONTEXT_SCHEMA_VERSION,
        "workspace_id": workspace_metadata["workspace_id"],
        "chat_id": chat_id,
        "message_id": message_id,
        "context_variant_id": variant_id,
        "created_at": _utc_now_iso(),
        "text": text,
        "source": clean_source,
        "parent_variant_id": parent_variant_id,
        "manually_edited": bool(manually_edited),
    }
    if compression is not None:
        if not isinstance(compression, dict):
            raise TypeError("compression metadata должна быть словарём.")
        variant["compression"] = dict(compression)
    path = _message_context_root(chat_dir, message_id) / "variants" / f"{variant_id}.json"
    _atomic_write_json(path, variant)
    if activate:
        activate_message_context_variant(
            root,
            chat_id,
            message_id,
            variant_id,
            require_raw=require_raw,
        )
    return {**variant, "path": str(path)}


def restore_message_raw(
    workspace_root: str | Path,
    chat_id: str,
    message_id: str,
) -> dict[str, Any]:
    root, workspace_metadata = _require_existing_workspace(workspace_root)
    chat_dir, _chat_metadata = _require_chat(root, workspace_metadata, chat_id)
    load_raw_message(root, chat_id, message_id)
    state = _default_message_context_state(
        workspace_metadata["workspace_id"], chat_id, message_id
    )
    state["updated_at"] = _utc_now_iso()
    _atomic_write_json(_message_context_root(chat_dir, message_id) / "state.json", state)
    return state


def get_message_working_representation(
    workspace_root: str | Path,
    chat_id: str,
    message_id: str,
) -> dict[str, Any]:
    raw = load_raw_message(workspace_root, chat_id, message_id)
    state = get_message_context_state(workspace_root, chat_id, message_id)
    if state["active_representation"] == "raw":
        return {"text": raw["original_text"], "state": state, "variant": None}
    variant = load_context_variant(
        workspace_root, chat_id, message_id, state["active_variant_id"]
    )
    return {"text": variant["text"], "state": state, "variant": variant}


def load_chat_working_messages(
    workspace_root: str | Path,
    chat_id: str,
) -> list[dict[str, Any]]:
    """Resolve user/assistant history in RAW order, failing closed on corruption."""
    working: list[dict[str, Any]] = []
    for raw in load_chat_messages(workspace_root, chat_id):
        role = raw.get("role")
        if role not in {"user", "assistant"}:
            continue
        resolved = get_message_working_representation(
            workspace_root, chat_id, raw["message_id"]
        )
        working.append(
            {
                "role": role,
                "content": resolved["text"],
                "message_id": raw["message_id"],
                "context_representation": resolved["state"]["active_representation"],
                "active_variant_id": resolved["state"]["active_variant_id"],
            }
        )
    return working


def is_context_storage_path(
    workspace_root: str | Path,
    candidate: str | Path,
) -> bool:
    root = _validate_workspace_root(workspace_root)
    context_root = (root / ULTRA_DIRNAME).resolve()
    path = Path(candidate).resolve()
    return path == context_root or context_root in path.parents
