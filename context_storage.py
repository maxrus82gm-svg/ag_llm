from __future__ import annotations

import contextlib
import json
import os
import re
import shutil
import stat
import threading
import time
import uuid
from dataclasses import dataclass
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
_TASK_BLOCK_ID_RE = re.compile(r"^tb_[a-f0-9]{32}$")
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


def _replace_with_retry(source: Path, destination: Path) -> None:
    # Windows refuses to replace a file while any reader holds it open, even with FILE_SHARE_DELETE (stage 0, P11/P12).
    # A short bounded retry, as in Run Store; after the last attempt the error is visible and the old file is intact.
    for delay in (*_REPLACE_RETRY_DELAYS, None):
        try:
            os.replace(source, destination)
            return
        except PermissionError:
            if delay is None:
                raise
            time.sleep(delay)


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temp_path.open("w", encoding="utf-8", newline="\n") as file:
            file.write(text)
            file.flush()
            os.fsync(file.fileno())
        _replace_with_retry(temp_path, path)
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


def new_task_block_id() -> str:
    """Create one persistent identity for a new user task."""
    return f"tb_{uuid.uuid4().hex}"


def validate_task_block_id(task_block_id: str) -> str:
    if not isinstance(task_block_id, str) or not _TASK_BLOCK_ID_RE.fullmatch(task_block_id):
        raise ValueError(f"Некорректный task_block_id: {task_block_id!r}")
    return task_block_id


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


_STORAGE_SUBDIRECTORIES = ("chats", "proposals", "project_context_history")


def ensure_workspace_storage(workspace_root: str | Path) -> dict[str, Any]:
    """Use the Ultra storage of a folder, creating what is missing; only for an explicit user action.

    A complete storage is only read (no lock, no write). Anything missing is created under the Workspace writer lock
    after a second look, so two processes never mint two identities or overwrite a fresh Project Context. A
    ``workspace.json`` that is missing next to an existing chat history is refused: a new ID would orphan it.
    """
    root = _validate_workspace_root(workspace_root)
    ultra_dir = root / ULTRA_DIRNAME
    workspace_path = ultra_dir / WORKSPACE_METADATA_NAME
    project_context_path = ultra_dir / PROJECT_CONTEXT_NAME

    storage_created = not ultra_dir.exists()
    workspace_created = False
    project_context_created = False

    complete = (
        not storage_created
        and all((ultra_dir / name).is_dir() for name in _STORAGE_SUBDIRECTORIES)
        and workspace_path.is_file()
        and project_context_path.exists()
    )
    if complete:
        metadata = _load_workspace_metadata(workspace_path)
    else:
        anchor = _write_anchor(root)
        if storage_created:
            _ensure_write_directory(anchor, (ULTRA_DIRNAME,))
        with _workspace_writer_lock(anchor):
            for name in _STORAGE_SUBDIRECTORIES:
                _ensure_write_directory(anchor, (ULTRA_DIRNAME, name))
            if not os.path.lexists(workspace_path):
                if _has_chat_history(anchor):
                    raise StorageWriteError(
                        "missing_workspace_metadata",
                        "Workspace metadata отсутствует, но в папке есть история чатов: "
                        "новый Workspace ID не создаётся. Восстановите .ultra/workspace.json.",
                    )
                new_metadata = {
                    "schema_version": SCHEMA_VERSION,
                    "workspace_id": f"ws_{uuid.uuid4().hex}",
                    "display_name": root.name or "workspace",
                    "created_at": _utc_now_iso(),
                }
                try:
                    _publish_new_file(anchor, (ULTRA_DIRNAME, WORKSPACE_METADATA_NAME), _json_bytes(new_metadata))
                    workspace_created = True
                except FileExistsError:
                    pass  # another writer outside this lock published first: its identity is the one kept
            metadata = _load_workspace_metadata(workspace_path)
            if not os.path.lexists(project_context_path):
                try:
                    _publish_new_file(
                        anchor, (ULTRA_DIRNAME, PROJECT_CONTEXT_NAME), PROJECT_CONTEXT_TEMPLATE.encode("utf-8")
                    )
                    project_context_created = True
                except FileExistsError:
                    pass

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
    name = str(display_name).strip()
    if not name:
        raise ValueError("Название Workspace не может быть пустым.")
    if len(name) > 200:
        raise ValueError("Название Workspace слишком длинное.")

    ensure_workspace_storage(root)
    with _existing_workspace_writer(root) as writer:
        metadata = dict(writer.metadata)  # read again under the lock: every other field is kept as found
        metadata["display_name"] = name
        _atomic_write_json(writer.anchor.path((ULTRA_DIRNAME, WORKSPACE_METADATA_NAME)), metadata)
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
    if not isinstance(text, str):
        raise TypeError("PROJECT CONTEXT должен быть строкой.")
    encoded = text.encode("utf-8")
    if len(encoded) > MAX_PROJECT_CONTEXT_BYTES:
        raise ValueError(
            "PROJECT CONTEXT слишком большой: "
            f"{len(encoded)} байт. Лимит: {MAX_PROJECT_CONTEXT_BYTES} байт."
        )

    info = ensure_workspace_storage(root)
    path = Path(info["project_context_path"])
    history_dir = Path(info["ultra_dir"]) / "project_context_history"

    with _existing_workspace_writer(root) as writer:
        old_text = path.read_text(encoding="utf-8-sig") if path.exists() else ""
        if old_text == text:
            return {"changed": False, "project_context_path": str(path)}

        revision_path = None
        if old_text:
            _ensure_write_directory(writer.anchor, (ULTRA_DIRNAME, "project_context_history"))
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


def _chat_staging_root(root: Path) -> Path:
    return root / ULTRA_DIRNAME / "chat_staging"


def _publish_chat_directory(staging_dir: Path, chat_dir: Path) -> None:
    # rename, not replace: on Windows it fails on an existing name, so a published Chat is never replaced.
    # Windows also refuses to move a folder while any file in it is open (an antivirus scanning the fresh card):
    # the same short bounded retry as a file replacement, then a visible error with the staging removed.
    for delay in (*_REPLACE_RETRY_DELAYS, None):
        try:
            os.rename(staging_dir, chat_dir)
            return
        except FileExistsError:
            raise
        except PermissionError:
            if delay is None:
                raise
            time.sleep(delay)


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


def create_chat_record(
    workspace_root: str | Path,
    title: str | None = None,
    *,
    chat_id: str | None = None,
    expected_workspace_id: str | None = None,
) -> dict[str, Any]:
    """Create one Chat through the shared writer contract; ``{"chat": metadata, "created": bool}``.

    With ``expected_workspace_id`` the Workspace must already exist with exactly that identity (the web path and
    the Tk sidebar); without it the folder's storage is first ensured, as the Tk "new Workspace" action always did.
    A caller-chosen ``chat_id`` makes a repeated request idempotent: the same ID with the same (or no) title returns
    the existing Chat without a write, the same ID with another title is a conflict. The Chat is assembled in
    staging and published with one directory rename under the Workspace writer lock.
    """
    requested_title = _clean_chat_title(title, allow_empty=True)
    if chat_id is not None and (not isinstance(chat_id, str) or not _CHAT_ID_RE.fullmatch(chat_id)):
        raise ValueError(f"Некорректный chat_id: {chat_id!r}")
    if expected_workspace_id is None:
        ensure_workspace_storage(workspace_root)
    with _existing_workspace_writer(workspace_root, expected_workspace_id) as writer:
        anchor = writer.anchor
        chats_parts = (ULTRA_DIRNAME, "chats")
        _ensure_write_directory(anchor, chats_parts)
        if chat_id is not None and os.path.lexists(anchor.path(chats_parts + (chat_id,))):
            try:
                _parts, existing = _require_chat_for_write(writer, chat_id)
            except ChatNotFoundError:
                raise StorageWriteError(
                    "chat_id_conflict", f"Папка с этим chat_id уже существует без карточки чата: {chat_id}"
                ) from None
            if requested_title is not None and existing.get("title") != requested_title:
                raise StorageWriteError(
                    "chat_id_conflict", f"Чат {chat_id} уже создан с другим названием: повтор отклонён."
                )
            return {"chat": existing, "created": False}

        try:
            listing = list_chats_bounded(writer.root)
        except StorageReadError as exc:
            if exc.code == "chats_listing_too_large":
                raise StorageWriteError("chats_limit_reached", "В Workspace слишком много чатов.") from None
            raise _write_refusal(exc) from None
        if len(listing["chats"]) >= MAX_CHATS_PER_WORKSPACE:
            raise StorageWriteError(
                "chats_limit_reached",
                f"В Workspace уже {len(listing['chats'])} чатов: больше этого числа история не читается.",
            )
        clean_title = requested_title or _next_default_chat_title(
            [item for item in listing["chats"] if item["status"] == "ok"]
        )

        new_chat_id = chat_id or f"chat_{uuid.uuid4().hex}"
        chat_dir = anchor.path(chats_parts + (new_chat_id,))
        staging_parts = (ULTRA_DIRNAME, "chat_staging")
        _ensure_write_directory(anchor, staging_parts)
        staging_root = anchor.path(staging_parts)
        staging_dir = staging_root / f"{new_chat_id}.{uuid.uuid4().hex}.tmp"
        staging_dir.mkdir(parents=False, exist_ok=False)

        metadata = {
            "schema_version": SCHEMA_VERSION,
            "workspace_id": writer.workspace_id,
            "chat_id": new_chat_id,
            "title": clean_title,
            "created_at": _utc_now_iso(),
        }
        try:
            (staging_dir / "messages").mkdir(parents=False, exist_ok=False)
            (staging_dir / "summaries").mkdir(parents=False, exist_ok=False)
            _atomic_write_json(staging_dir / "metadata.json", metadata)
            _publish_chat_directory(staging_dir, chat_dir)
        finally:
            if staging_dir.exists():
                shutil.rmtree(staging_dir)
            try:
                staging_root.rmdir()  # safe: every cooperating writer stages only under the same lock
            except OSError:
                pass
        _parts, published = _require_chat_for_write(writer, new_chat_id)
        if published != metadata:
            raise StorageWriteError("verify_failed", f"Опубликованный чат не совпадает с записанным: {new_chat_id}")
        return {"chat": metadata, "created": True}


def create_chat(
    workspace_root: str | Path,
    title: str | None = None,
    *,
    chat_id: str | None = None,
    expected_workspace_id: str | None = None,
) -> dict[str, Any]:
    return create_chat_record(
        workspace_root, title, chat_id=chat_id, expected_workspace_id=expected_workspace_id
    )["chat"]


def ensure_chat(workspace_root: str | Path) -> dict[str, Any]:
    root = _validate_workspace_root(workspace_root)
    ensure_workspace_storage(root)
    with _existing_workspace_writer(root):  # listing and creation as one step: two callers get one Chat
        chats = _list_existing_chats_from_root(root)
        if chats:
            return chats[-1]
        return create_chat(root)


def rename_chat(
    workspace_root: str | Path,
    chat_id: str,
    title: str,
    *,
    expected_title: str | None = None,
    expected_workspace_id: str | None = None,
) -> dict[str, Any]:
    """Atomically replace the title in the Chat card under the Workspace writer lock.

    The card must belong to this Workspace and have a supported version; every other field is kept as found.
    ``expected_title`` is the title the user saw: if another window changed it meanwhile, the rename is refused
    instead of silently overwriting that change. Repeating the same rename is a no-op.
    """
    clean_title = _clean_chat_title(title)
    _chat_root(Path("."), chat_id)  # the ID is checked before any lock or disk access
    with _existing_workspace_writer(workspace_root, expected_workspace_id) as writer:
        parts, metadata = _require_chat_for_write(writer, chat_id)
        if metadata.get("title") == clean_title:
            return metadata
        if expected_title is not None and metadata.get("title") != expected_title:
            raise StorageWriteError(
                "title_changed",
                "Название чата уже изменено в другом окне: обновите список и повторите.",
            )
        updated = {**metadata, "title": clean_title}
        payload = _json_bytes(updated)
        _atomic_write_json(writer.anchor.path(parts + ("metadata.json",)), updated)
        _verify_published(writer.anchor, parts + ("metadata.json",), payload)
        return updated


def _validated_raw_fields(
    role: str,
    original_text: str,
    producer: dict[str, Any] | None,
    task_block_id: str | None,
) -> dict[str, Any]:
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
    fields: dict[str, Any] = {"role": clean_role, "original_text": original_text}
    if producer is not None:
        fields["producer"] = _validate_producer(producer)
    if task_block_id is not None:
        fields["task_block_id"] = validate_task_block_id(task_block_id)
    return fields


def commit_raw_message(
    workspace_root: str | Path,
    chat_id: str,
    message_id: str,
    role: str,
    original_text: str,
    *,
    producer: dict[str, Any] | None = None,
    task_block_id: str | None = None,
    expected_workspace_id: str | None = None,
) -> dict[str, Any]:
    """Save one RAW MESSAGE under a caller-chosen ``message_id`` exactly once (local storage idempotency).

    A new ID gives one new record. The same ID with the same content returns the stored record (``created`` is
    False, nothing is written). The same ID with other content or identity is a ``message_id_conflict``: the stored
    record is never overwritten. Publication is exclusive (a rename that fails on an existing name), so even a
    writer outside this lock cannot be overwritten. The Workspace must already exist; nothing is created for it.
    This is not a Turn: a retry key and the outcome of a provider call belong to stage 3.
    """
    _validate_message_id(message_id)
    _chat_root(Path("."), chat_id)  # the ID is checked before any lock or disk access
    fields = _validated_raw_fields(role, original_text, producer, task_block_id)
    with _existing_workspace_writer(workspace_root, expected_workspace_id) as writer:
        chat_parts, _chat_metadata = _require_chat_for_write(writer, chat_id)
        messages_parts = chat_parts + ("messages",)
        _ensure_write_directory(writer.anchor, messages_parts)
        target_parts = messages_parts + (f"{message_id}.json",)
        target_path = writer.anchor.path(target_parts)
        candidate = {
            "schema_version": SCHEMA_VERSION,
            "workspace_id": writer.workspace_id,
            "chat_id": chat_id,
            "message_id": message_id,
            **fields,
        }
        existing = _read_existing_raw(writer, target_parts)
        if existing is None:
            message = {  # the field order append_raw_message has always written
                "schema_version": SCHEMA_VERSION,
                "workspace_id": writer.workspace_id,
                "chat_id": chat_id,
                "message_id": message_id,
                "role": fields["role"],
                "created_at": _utc_now_iso(),
                "original_text": fields["original_text"],
            }
            for key in ("producer", "task_block_id"):
                if key in fields:
                    message[key] = fields[key]
            try:
                _publish_new_file(writer.anchor, target_parts, _json_bytes(message))
                return {**message, "path": str(target_path), "created": True}
            except FileExistsError:
                existing = _read_existing_raw(writer, target_parts)
                if existing is None:
                    raise
        if _raw_canonical(existing) != _raw_canonical(candidate):
            raise StorageWriteError(
                "message_id_conflict",
                f"RAW MESSAGE {message_id} уже сохранён с другим содержимым или идентичностью: перезапись запрещена.",
            )
        return {**existing, "path": str(target_path), "created": False}


def append_raw_message(
    workspace_root: str | Path,
    chat_id: str,
    role: str,
    original_text: str,
    *,
    producer: dict[str, Any] | None = None,
    task_block_id: str | None = None,
) -> dict[str, Any]:
    """Save a new RAW MESSAGE with a fresh ID; a compatible wrapper over ``commit_raw_message``."""
    message_id = f"msg_{uuid.uuid4().hex}"
    result = commit_raw_message(
        workspace_root,
        chat_id,
        message_id,
        role,
        original_text,
        producer=producer,
        task_block_id=task_block_id,
    )
    if not result.pop("created"):
        raise RuntimeError(f"Коллизия message_id: {message_id}")
    return result


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
        if "task_block_id" in data:
            try:
                validate_task_block_id(data["task_block_id"])
            except ValueError as exc:
                raise RuntimeError(f"Повреждён task_block_id RAW MESSAGE: {msg_path}") from exc
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
    if "task_block_id" in data:
        try:
            validate_task_block_id(data["task_block_id"])
        except ValueError as exc:
            raise RuntimeError(f"Повреждён task_block_id RAW MESSAGE: {path}") from exc
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


def _activate_message_context_variant(
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


def _create_message_context_variant(
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


def _restore_message_raw(
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



# Message context writers: the same lock, identity and path rule as every other writer (stage 2). The bodies above
# keep their checks unchanged; a nested call (create -> activate) re-enters the lock held by its own thread.
def activate_message_context_variant(
    workspace_root: str | Path,
    chat_id: str,
    message_id: str,
    context_variant_id: str,
    *,
    require_raw: bool = False,
) -> dict[str, Any]:
    with _chat_writer(workspace_root, chat_id):
        return _activate_message_context_variant(
            workspace_root, chat_id, message_id, context_variant_id, require_raw=require_raw
        )


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
    with _chat_writer(workspace_root, chat_id):
        return _create_message_context_variant(
            workspace_root,
            chat_id,
            message_id,
            text,
            source=source,
            parent_variant_id=parent_variant_id,
            manually_edited=manually_edited,
            compression=compression,
            activate=activate,
            require_raw=require_raw,
        )


def restore_message_raw(
    workspace_root: str | Path,
    chat_id: str,
    message_id: str,
) -> dict[str, Any]:
    with _chat_writer(workspace_root, chat_id):
        return _restore_message_raw(workspace_root, chat_id, message_id)


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


# ---------------------------------------------------------------------------
# Bounded read-only access for the web shell (Ultra Chat, programme No.37 stage 1).
#
# Everything above keeps its behaviour: Tkinter reads and writes through those functions and calls nothing below.
# The functions below never create, repair or rewrite storage. Every file is opened without following a final
# reparse point and checked through its own handle (regular file, a single link, final path under the same
# Workspace root that was pinned at the start of the read), then read only up to its limit. A swapped directory or
# file therefore fails the check at use, not only at an earlier lstat. Errors carry a short code, never a path.

_FILE_ATTRIBUTE_REPARSE_POINT = 0x400
_STORAGE_NAME_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$")
_MESSAGE_ROLES = {"user", "assistant", "system", "tool"}


@dataclass(frozen=True)
class ReadLimits:
    max_workspace_metadata_bytes: int = 64 * 1024
    max_chat_entries: int = 2000
    max_chats: int = 500
    max_chat_metadata_bytes: int = 64 * 1024
    max_message_files: int = 2000
    max_history_bytes: int = 64 * 1024 * 1024
    max_message_bytes: int = 4 * 1024 * 1024


DEFAULT_READ_LIMITS = ReadLimits()


class StorageReadError(Exception):
    """A refused or impossible bounded read. ``code`` is safe to show; the message never carries a path."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _is_link_or_reparse(st: os.stat_result) -> bool:
    return stat.S_ISLNK(st.st_mode) or bool(
        getattr(st, "st_file_attributes", 0) & _FILE_ATTRIBUTE_REPARSE_POINT
    )


if os.name == "nt":
    import ctypes
    import msvcrt
    import _winapi
    from ctypes import wintypes

    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _kernel32.GetFinalPathNameByHandleW.argtypes = [
        wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD,
    ]
    _kernel32.GetFinalPathNameByHandleW.restype = wintypes.DWORD
    _GENERIC_READ = 0x80000000
    _FILE_READ_ATTRIBUTES = 0x80
    _SHARE_ALL = 0x1 | 0x2 | 0x4
    _OPEN_EXISTING = 3
    _FLAG_OPEN_REPARSE_POINT = 0x00200000
    _FLAG_BACKUP_SEMANTICS = 0x02000000

    def _final_path_of_handle(handle: int) -> str:
        size = 512
        while True:
            buffer = ctypes.create_unicode_buffer(size)
            length = _kernel32.GetFinalPathNameByHandleW(handle, buffer, size, 0)
            if not length:
                raise ctypes.WinError(ctypes.get_last_error())
            if length < size:
                return buffer.value
            size = length + 1

    def _final_directory_path(path: Path) -> str:
        # The registered root itself may be a junction or a subst drive: it is followed once, here.
        handle = _winapi.CreateFile(
            str(path), _FILE_READ_ATTRIBUTES, _SHARE_ALL, 0, _OPEN_EXISTING, _FLAG_BACKUP_SEMANTICS, 0
        )
        try:
            return _final_path_of_handle(handle)
        finally:
            _winapi.CloseHandle(handle)

    def _open_file_no_follow(path: Path) -> int:
        handle = _winapi.CreateFile(
            str(path), _GENERIC_READ, _SHARE_ALL, 0, _OPEN_EXISTING, _FLAG_OPEN_REPARSE_POINT, 0
        )
        try:
            return msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
        except OSError:
            _winapi.CloseHandle(handle)
            raise

    def _final_path_of_fd(fd: int) -> str:
        return _final_path_of_handle(msvcrt.get_osfhandle(fd))

else:

    def _final_path_of_fd(fd: int) -> str:
        try:
            return os.readlink(f"/proc/self/fd/{fd}")
        except OSError:
            import fcntl

            if not hasattr(fcntl, "F_GETPATH"):
                raise StorageReadError("unsupported_platform") from None
            raw = fcntl.fcntl(fd, fcntl.F_GETPATH, b"\0" * 1024)
            return os.fsdecode(raw.split(b"\0", 1)[0])

    def _final_directory_path(path: Path) -> str:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            return _final_path_of_fd(fd)
        finally:
            os.close(fd)

    def _open_file_no_follow(path: Path) -> int:
        return os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0))


class _StorageAnchor:
    """Workspace root pinned by its final path once per read; every later open must land under it."""

    def __init__(self, workspace_root: str | Path) -> None:
        root = Path(workspace_root)
        if not root.is_absolute():
            raise StorageReadError("missing_path")
        try:
            root_stat = os.stat(root)
        except FileNotFoundError:
            raise StorageReadError("missing_path") from None
        except OSError:
            raise StorageReadError("unreadable") from None
        if not stat.S_ISDIR(root_stat.st_mode):
            raise StorageReadError("not_directory")
        try:
            self.final = _final_directory_path(root)
        except OSError:
            raise StorageReadError("unreadable") from None
        self.root = root

    def path(self, parts: tuple[str, ...]) -> Path:
        return self.root.joinpath(*parts)

    def expected(self, parts: tuple[str, ...]) -> str:
        return os.path.normcase(os.path.join(self.final, *parts))


def _verify_directory(anchor: _StorageAnchor, parts: tuple[str, ...]) -> None:
    path = anchor.path(parts)
    try:
        st = os.lstat(path)
    except FileNotFoundError:
        raise StorageReadError("missing") from None
    except OSError:
        raise StorageReadError("unreadable") from None
    if _is_link_or_reparse(st):
        raise StorageReadError("unsafe_storage_link")
    if not stat.S_ISDIR(st.st_mode):
        raise StorageReadError("damaged")
    try:
        # Followed on purpose: a directory swapped for a junction after the lstat resolves elsewhere.
        final = _final_directory_path(path)
    except FileNotFoundError:
        raise StorageReadError("missing") from None
    except OSError:
        raise StorageReadError("unreadable") from None
    if os.path.normcase(final) != anchor.expected(parts):
        raise StorageReadError("unsafe_storage_link")


def _read_up_to(fd: int, count: int) -> bytes:
    chunks: list[bytes] = []
    remaining = count
    while remaining > 0:
        chunk = os.read(fd, min(remaining, 1024 * 1024))
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _read_file_bounded(anchor: _StorageAnchor, parts: tuple[str, ...], limit: int) -> bytes:
    """Open without following, verify through the handle, read at most ``limit`` bytes (``limit + 1`` probes)."""
    try:
        fd = _open_file_no_follow(anchor.path(parts))
    except FileNotFoundError:
        raise StorageReadError("missing") from None
    except OSError:
        # A directory, a junction or a link in the final position cannot be opened as a regular file.
        raise StorageReadError("unreadable") from None
    try:
        st = os.fstat(fd)
        if _is_link_or_reparse(st) or not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
            raise StorageReadError("unsafe_storage_link")
        if os.path.normcase(_final_path_of_fd(fd)) != anchor.expected(parts):
            raise StorageReadError("unsafe_storage_link")
        if st.st_size > limit:
            raise StorageReadError("too_large")
        data = _read_up_to(fd, limit + 1)
        if len(data) > limit:
            raise StorageReadError("too_large")
        return data
    except OSError:
        raise StorageReadError("unreadable") from None
    finally:
        os.close(fd)


def _decode_json(data: bytes) -> Any:
    try:
        return json.loads(data.decode("utf-8-sig"))
    except (UnicodeDecodeError, ValueError):
        raise StorageReadError("damaged") from None


def _read_json_bounded(anchor: _StorageAnchor, parts: tuple[str, ...], limit: int) -> Any:
    return _decode_json(_read_file_bounded(anchor, parts, limit))


def _scan_directory(
    anchor: _StorageAnchor, parts: tuple[str, ...], max_entries: int
) -> list[tuple[str, str, int]]:
    """Names, kinds and sizes of at most ``max_entries`` entries; refuses (not truncates) a longer listing."""
    entries: list[tuple[str, str, int]] = []
    try:
        with os.scandir(anchor.path(parts)) as iterator:
            for entry in iterator:
                if len(entries) >= max_entries:
                    raise StorageReadError("listing_too_large")
                try:
                    st = entry.stat(follow_symlinks=False)
                except OSError:
                    entries.append((entry.name, "other", 0))
                    continue
                if _is_link_or_reparse(st):
                    kind = "link"
                elif stat.S_ISDIR(st.st_mode):
                    kind = "dir"
                elif stat.S_ISREG(st.st_mode):
                    kind = "file"
                else:
                    kind = "other"
                entries.append((entry.name, kind, st.st_size))
    except FileNotFoundError:
        raise StorageReadError("missing") from None
    except NotADirectoryError:
        raise StorageReadError("damaged") from None
    except OSError:
        raise StorageReadError("unreadable") from None
    return entries


def _open_workspace_bounded(
    workspace_root: str | Path, limits: ReadLimits
) -> tuple[_StorageAnchor, dict[str, Any]]:
    anchor = _StorageAnchor(workspace_root)
    try:
        _verify_directory(anchor, (ULTRA_DIRNAME,))
        data = _read_json_bounded(
            anchor, (ULTRA_DIRNAME, WORKSPACE_METADATA_NAME), limits.max_workspace_metadata_bytes
        )
    except StorageReadError as exc:
        code = {"missing": "missing_history", "damaged": "invalid_metadata", "too_large": "invalid_metadata"}
        raise StorageReadError(code.get(exc.code, exc.code)) from None
    if not isinstance(data, dict):
        raise StorageReadError("invalid_metadata")
    version = data.get("schema_version")
    if isinstance(version, int) and not isinstance(version, bool) and version > SCHEMA_VERSION:
        raise StorageReadError("unsupported_version")
    workspace_id = data.get("workspace_id")
    if version != SCHEMA_VERSION or not isinstance(workspace_id, str) or not _WORKSPACE_ID_RE.fullmatch(workspace_id):
        raise StorageReadError("invalid_metadata")
    display_name = data.get("display_name")
    return anchor, {"workspace_id": workspace_id,
                    "display_name": display_name if isinstance(display_name, str) else None}


def read_workspace_identity_bounded(
    workspace_root: str | Path, *, limits: ReadLimits = DEFAULT_READ_LIMITS
) -> dict[str, Any]:
    """Status of the Ultra history in a folder (``ok`` with its identity, or a reason code); creates nothing."""
    try:
        _anchor, identity = _open_workspace_bounded(workspace_root, limits)
    except StorageReadError as exc:
        return {"status": exc.code}
    return {"status": "ok", **identity}


def _chat_metadata_problem(data: Any, chat_id: str, workspace_id: str) -> str | None:
    if not isinstance(data, dict):
        return "damaged"
    if data.get("chat_id") != chat_id:
        return "damaged"
    if data.get("workspace_id") != workspace_id:
        return "foreign_identity"
    title = data.get("title")
    if not isinstance(title, str) or not title.strip():
        return "damaged"
    created_at = data.get("created_at")
    if created_at is not None and not isinstance(created_at, str):
        return "damaged"
    return None


def list_chats_bounded(
    workspace_root: str | Path, *, limits: ReadLimits = DEFAULT_READ_LIMITS
) -> dict[str, Any]:
    """Chats of one Workspace: each card checked on its own, a damaged one never hides the others."""
    anchor, identity = _open_workspace_bounded(workspace_root, limits)
    workspace_id = identity["workspace_id"]
    chats_parts = (ULTRA_DIRNAME, "chats")
    excluded: dict[str, int] = {}
    try:
        _verify_directory(anchor, chats_parts)
        entries = _scan_directory(anchor, chats_parts, limits.max_chat_entries)
    except StorageReadError as exc:
        if exc.code == "missing":
            return {**identity, "chats": [], "excluded": excluded}
        if exc.code == "listing_too_large":
            raise StorageReadError("chats_listing_too_large") from None
        raise
    chats: list[dict[str, Any]] = []
    for name, kind, _size in sorted(entries):
        if not _CHAT_ID_RE.fullmatch(name) or kind not in {"dir", "link"}:
            excluded["unexpected_entry"] = excluded.get("unexpected_entry", 0) + 1
            continue
        if kind == "link":
            chats.append({"chat_id": name, "status": "unsafe_storage_link"})
            continue
        try:
            _verify_directory(anchor, chats_parts + (name,))
            metadata = _read_json_bounded(
                anchor, chats_parts + (name, "metadata.json"), limits.max_chat_metadata_bytes
            )
        except StorageReadError as exc:
            status = "unsafe_storage_link" if exc.code == "unsafe_storage_link" else "damaged"
            chats.append({"chat_id": name, "status": status})
            continue
        problem = _chat_metadata_problem(metadata, name, workspace_id)
        if problem == "foreign_identity":
            excluded["foreign_identity"] = excluded.get("foreign_identity", 0) + 1
            continue
        if problem:
            chats.append({"chat_id": name, "status": "damaged"})
            continue
        chats.append({"chat_id": name, "status": "ok", "title": metadata["title"],
                      "created_at": metadata.get("created_at")})
    if len(chats) > limits.max_chats:
        raise StorageReadError("chats_listing_too_large")
    chats.sort(key=lambda item: (str(item.get("created_at") or ""), item["chat_id"]))
    return {**identity, "chats": chats, "excluded": excluded}


def _message_problem(data: Any, message_id: str, chat_id: str, workspace_id: str) -> str | None:
    if not isinstance(data, dict):
        return "damaged"
    version = data.get("schema_version", SCHEMA_VERSION)
    if isinstance(version, int) and not isinstance(version, bool) and version > SCHEMA_VERSION:
        return "unsupported_version"
    if version != SCHEMA_VERSION:
        return "damaged"
    if data.get("message_id") != message_id:
        return "name_mismatch"
    if data.get("chat_id") != chat_id or data.get("workspace_id") != workspace_id:
        return "foreign_identity"
    if not isinstance(data.get("original_text"), str) or data.get("role") not in _MESSAGE_ROLES:
        return "damaged"
    if not isinstance(data.get("created_at"), str):
        return "damaged"
    if "producer" in data:
        try:
            _validate_producer(data["producer"])
        except (TypeError, ValueError):
            return "damaged"
    if "task_block_id" in data:
        try:
            validate_task_block_id(data["task_block_id"])
        except ValueError:
            return "damaged"
    return None


def read_chat_history_bounded(
    workspace_root: str | Path,
    chat_id: str,
    *,
    limits: ReadLimits = DEFAULT_READ_LIMITS,
) -> dict[str, Any]:
    """All valid RAW messages of one chat in display order, with counted exclusions, under hard I/O limits.

    The listing is refused above ``max_message_files`` entries and the whole history above ``max_history_bytes``;
    a single file above ``max_message_bytes`` is excluded unread. Reading stops at the byte budget even if files
    grow after they were listed. For display only: the model context keeps its own fail-closed path.
    """
    if not isinstance(chat_id, str) or not _CHAT_ID_RE.fullmatch(chat_id):
        raise StorageReadError("invalid_chat_id")
    anchor, identity = _open_workspace_bounded(workspace_root, limits)
    workspace_id = identity["workspace_id"]
    chat_parts = (ULTRA_DIRNAME, "chats", chat_id)
    try:
        _verify_directory(anchor, (ULTRA_DIRNAME, "chats"))
        _verify_directory(anchor, chat_parts)
    except StorageReadError as exc:
        raise StorageReadError("chat_not_found" if exc.code == "missing" else exc.code) from None
    try:
        metadata = _read_json_bounded(anchor, chat_parts + ("metadata.json",), limits.max_chat_metadata_bytes)
    except StorageReadError as exc:
        raise StorageReadError("unsafe_storage_link" if exc.code == "unsafe_storage_link" else "chat_damaged") from None
    problem = _chat_metadata_problem(metadata, chat_id, workspace_id)
    if problem:
        raise StorageReadError("foreign_identity" if problem == "foreign_identity" else "chat_damaged")
    chat = {"chat_id": chat_id, "title": metadata["title"], "created_at": metadata.get("created_at")}
    messages_parts = chat_parts + ("messages",)
    try:
        _verify_directory(anchor, messages_parts)
        entries = _scan_directory(anchor, messages_parts, limits.max_message_files)
    except StorageReadError as exc:
        if exc.code == "missing":
            entries = []
        elif exc.code == "listing_too_large":
            raise StorageReadError("history_too_large") from None
        else:
            raise
    excluded: dict[str, int] = {}
    excluded_ids: list[str] = []

    def exclude(reason: str, message_id: str | None = None) -> None:
        excluded[reason] = excluded.get(reason, 0) + 1
        if message_id and len(excluded_ids) < 50:
            excluded_ids.append(message_id)

    candidates: list[str] = []
    listed_bytes = 0
    for name, kind, size in sorted(entries):
        if not name.endswith(".json"):
            continue  # writer temp files and foreign files, as Tk's glob("*.json")
        message_id = name[:-5]
        if not _MESSAGE_ID_RE.fullmatch(message_id):
            exclude("name_mismatch")
            continue
        if kind == "link":
            exclude("unsafe_storage_link", message_id)
            continue
        if kind != "file":
            exclude("damaged", message_id)
            continue
        if size > limits.max_message_bytes:
            exclude("too_large", message_id)
            continue
        listed_bytes += size
        candidates.append(message_id)
    if listed_bytes > limits.max_history_bytes:
        raise StorageReadError("history_too_large")
    budget = limits.max_history_bytes
    messages: list[dict[str, Any]] = []
    seen: set[str] = set()
    for message_id in candidates:
        cap = min(limits.max_message_bytes, budget)
        try:
            data = _read_file_bounded(anchor, messages_parts + (message_id + ".json",), cap)
        except StorageReadError as exc:
            if exc.code == "too_large" and cap < limits.max_message_bytes:
                raise StorageReadError("history_too_large") from None
            if exc.code != "missing":
                exclude(exc.code if exc.code in {"too_large", "unsafe_storage_link"} else "damaged", message_id)
            continue
        budget -= len(data)
        try:
            record = _decode_json(data)
        except StorageReadError:
            exclude("damaged", message_id)
            continue
        reason = _message_problem(record, message_id, chat_id, workspace_id)
        if reason is None and message_id in seen:
            reason = "duplicate_id"
        if reason:
            exclude(reason, message_id)
            continue
        seen.add(message_id)
        item: dict[str, Any] = {"message_id": message_id, "role": record["role"],
                                "created_at": record["created_at"], "text": record["original_text"]}
        if "task_block_id" in record:
            item["task_block_id"] = record["task_block_id"]
        producer = record.get("producer")
        if isinstance(producer, dict):
            item["producer"] = {key: producer[key] for key in ("kind", "run_id", "model_id", "model_display_name")
                                if isinstance(producer.get(key), str)}
        messages.append(item)
    messages.sort(key=lambda item: (item["created_at"], item["message_id"]))
    return {**identity, "chat": chat, "messages": messages, "excluded": excluded, "excluded_ids": excluded_ids,
            "files_read": len(candidates), "bytes_read": limits.max_history_bytes - budget}


def _storage_parts(relative_parts: tuple[str, ...]) -> tuple[str, ...]:
    if not relative_parts or any(
        not isinstance(part, str) or not _STORAGE_NAME_RE.fullmatch(part) or part in {".", ".."}
        for part in relative_parts
    ):
        raise StorageReadError("invalid_path")
    return (ULTRA_DIRNAME, *relative_parts)


def read_ultra_json_bounded(
    workspace_root: str | Path,
    relative_parts: tuple[str, ...],
    *,
    max_bytes: int,
    limits: ReadLimits = DEFAULT_READ_LIMITS,
) -> Any:
    """One JSON file under ``.ultra`` of a valid Workspace, with the same link and size checks as chat history."""
    parts = _storage_parts(relative_parts)
    anchor, _identity = _open_workspace_bounded(workspace_root, limits)
    for depth in range(2, len(parts)):
        _verify_directory(anchor, parts[:depth])
    return _read_json_bounded(anchor, parts, max_bytes)


def list_ultra_files_bounded(
    workspace_root: str | Path,
    relative_parts: tuple[str, ...],
    *,
    max_entries: int,
    limits: ReadLimits = DEFAULT_READ_LIMITS,
) -> list[str]:
    """Names of regular files in one directory under ``.ultra``; refuses a longer listing instead of truncating."""
    parts = _storage_parts(relative_parts)
    anchor, _identity = _open_workspace_bounded(workspace_root, limits)
    for depth in range(2, len(parts) + 1):
        _verify_directory(anchor, parts[:depth])
    return sorted(name for name, kind, _size in _scan_directory(anchor, parts, max_entries) if kind == "file")


# ---------------------------------------------------------------------------
# Shared writer contract (Ultra Chat, programme No.37 stage 2).
#
# One rule for every writer of the Ultra storage, Tk and web alike. A public write function:
#   1. checks the Workspace identity before anything is created (a refusal leaves the folder untouched);
#   2. takes the Workspace writer lock <root>/.ultra/locks/writer.lock - an OS byte-range lock that its process
#      releases on death - and reads the identity again under it;
#   3. checks every directory it writes through (no link or junction, final path under the pinned root), the
#      ownership of the Chat and the version of what it changes;
#   4. publishes atomically (replace with a bounded retry, or an exclusive rename that never overwrites) and reads
#      the published bytes back through the same no-follow checks as the stage-1 reader.
# The lock is reentrant per thread, held for milliseconds, never over a network call or a user dialog, and a busy
# Workspace is a visible WorkspaceBusyError after WRITER_LOCK_TIMEOUT_SECONDS. It does not replace steps 1, 3, 4.

WRITER_LOCK_TIMEOUT_SECONDS = 10.0
_WRITER_LOCK_POLL_SECONDS = 0.01
_REPLACE_RETRY_DELAYS = (0.01, 0.02, 0.05, 0.1, 0.2, 0.4, 0.8)
LOCKS_DIRNAME = "locks"
WRITER_LOCK_NAME = "writer.lock"
# The locked byte lies far past the end of the always-empty lock file: Windows byte-range locks are mandatory,
# so a lock on byte 0 would make the file unreadable and a copy of the Workspace fail while a writer works.
_WRITER_LOCK_OFFSET = 1 << 30
# The web listing refuses more chats than this (stage 1); creating more would hide every chat of the Workspace.
MAX_CHATS_PER_WORKSPACE = DEFAULT_READ_LIMITS.max_chats
MAX_CHAT_TITLE_CHARS = 200
_TITLE_FORBIDDEN_RE = re.compile(r"[\x00-\x1f\x7f-\x9f\u2028\u2029]")
_RAW_COMPARED_FIELDS = (
    "schema_version", "workspace_id", "chat_id", "message_id",
    "role", "original_text", "producer", "task_block_id", "turn_id",
)
_MAX_WRITER_JSON_BYTES = 16 * 1024 * 1024  # a 2 MiB RAW text may grow when JSON escapes it


class StorageWriteError(RuntimeError):
    """A refused or unverifiable write. ``code`` is safe to show; the stored data is left as it was."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class WorkspaceBusyError(StorageWriteError):
    def __init__(self) -> None:
        super().__init__("workspace_busy", "Workspace занят другой операцией записи. Повторите позже.")


class ChatNotFoundError(FileNotFoundError):
    """The Chat card does not exist; a FileNotFoundError, as the old writers raised."""

    code = "chat_not_found"


def _json_bytes(data: dict[str, Any]) -> bytes:
    return (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _clean_chat_title(title: object, *, allow_empty: bool = False) -> str | None:
    clean = "" if title is None else str(title).strip()
    if not clean:
        if allow_empty:
            return None
        raise ValueError("Название чата не может быть пустым.")
    if len(clean) > MAX_CHAT_TITLE_CHARS:
        raise ValueError("Название чата слишком длинное.")
    if _TITLE_FORBIDDEN_RE.search(clean):
        raise ValueError("Название чата содержит управляющие символы или перевод строки.")
    return clean


def _write_refusal(exc: StorageReadError) -> StorageWriteError:
    if exc.code == "unsafe_storage_link":
        return StorageWriteError(
            "unsafe_storage_link",
            "Внутри хранилища Ultra ссылка вместо папки или файла: запись запрещена.",
        )
    return StorageWriteError("storage_unavailable", f"Хранилище Ultra недоступно для записи ({exc.code}).")


def _write_anchor(root: Path) -> _StorageAnchor:
    try:
        return _StorageAnchor(root)
    except StorageReadError as exc:
        raise _write_refusal(exc) from None


def _verify_write_directory(anchor: _StorageAnchor, parts: tuple[str, ...]) -> None:
    try:
        _verify_directory(anchor, parts)
    except StorageReadError as exc:
        raise _write_refusal(exc) from None


def _ensure_write_directory(anchor: _StorageAnchor, parts: tuple[str, ...]) -> None:
    """One directory level whose parent the caller has verified: created if missing, then verified itself."""
    try:
        os.mkdir(anchor.path(parts))
    except FileExistsError:
        pass
    _verify_write_directory(anchor, parts)


_writer_locks_held = threading.local()


def _held_writer_locks() -> dict[str, int]:
    held = getattr(_writer_locks_held, "held", None)
    if held is None:
        held = _writer_locks_held.held = {}
    return held


def _try_lock_byte(handle: Any) -> bool:
    try:
        if os.name == "nt":
            handle.seek(_WRITER_LOCK_OFFSET)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return False
    return True


def _release_lock_byte(handle: Any) -> None:
    try:
        if os.name == "nt":
            handle.seek(_WRITER_LOCK_OFFSET)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        handle.close()


@contextlib.contextmanager
def _workspace_writer_lock(anchor: _StorageAnchor):
    """Exclusive writer of one physical Workspace folder: other threads and processes wait or time out."""
    parts = (ULTRA_DIRNAME, LOCKS_DIRNAME, WRITER_LOCK_NAME)
    key = anchor.expected(parts)
    held = _held_writer_locks()
    if key in held:  # the same thread, one logical operation (create -> activate): no second handle, no wait
        held[key] += 1
        try:
            yield
        finally:
            held[key] -= 1
        return
    _verify_write_directory(anchor, (ULTRA_DIRNAME,))
    _ensure_write_directory(anchor, parts[:2])
    path = anchor.path(parts)
    try:
        if _is_link_or_reparse(os.lstat(path)):
            raise _write_refusal(StorageReadError("unsafe_storage_link"))
    except FileNotFoundError:
        pass
    handle = open(path, "a+b")
    try:
        if os.path.normcase(_final_path_of_fd(handle.fileno())) != key:
            raise _write_refusal(StorageReadError("unsafe_storage_link"))
        deadline = time.monotonic() + WRITER_LOCK_TIMEOUT_SECONDS
        while not _try_lock_byte(handle):
            if time.monotonic() >= deadline:
                raise WorkspaceBusyError()
            time.sleep(_WRITER_LOCK_POLL_SECONDS)
    except BaseException:
        handle.close()
        raise
    held[key] = 1
    try:
        yield
    finally:
        del held[key]
        _release_lock_byte(handle)


def _read_workspace_metadata_for_write(anchor: _StorageAnchor) -> dict[str, Any]:
    """The whole ``workspace.json`` (every field kept) of a valid Workspace, through the no-follow reader."""
    try:
        _verify_directory(anchor, (ULTRA_DIRNAME,))
        data = _read_json_bounded(
            anchor, (ULTRA_DIRNAME, WORKSPACE_METADATA_NAME), DEFAULT_READ_LIMITS.max_workspace_metadata_bytes
        )
    except StorageReadError as exc:
        if exc.code == "missing":
            raise StorageWriteError(
                "missing_history", "В папке нет истории Ultra (.ultra/workspace.json): запись не выполняется."
            ) from None
        if exc.code in {"damaged", "too_large"}:
            raise StorageWriteError("invalid_metadata", "Workspace metadata повреждена: запись не выполняется.") from None
        raise _write_refusal(exc) from None
    if not isinstance(data, dict):
        raise StorageWriteError("invalid_metadata", "Workspace metadata повреждена: запись не выполняется.")
    version = data.get("schema_version")
    if version != SCHEMA_VERSION:
        newer = isinstance(version, int) and not isinstance(version, bool) and version > SCHEMA_VERSION
        raise StorageWriteError(
            "unsupported_version" if newer else "invalid_metadata",
            f"Неподдерживаемая версия workspace schema: {version!r}. Ожидалась версия {SCHEMA_VERSION}.",
        )
    workspace_id = data.get("workspace_id")
    if not isinstance(workspace_id, str) or not _WORKSPACE_ID_RE.fullmatch(workspace_id):
        raise StorageWriteError("invalid_metadata", "Некорректный workspace_id: ID нельзя молча пересоздавать.")
    return data


class _WorkspaceWriter:
    def __init__(self, root: Path, anchor: _StorageAnchor, metadata: dict[str, Any]) -> None:
        self.root = root
        self.anchor = anchor
        self.metadata = metadata
        self.workspace_id: str = metadata["workspace_id"]


def _check_expected_workspace(metadata: dict[str, Any], expected_workspace_id: str | None) -> None:
    if expected_workspace_id is not None and metadata["workspace_id"] != expected_workspace_id:
        raise StorageWriteError(
            "workspace_identity_changed",
            "В этой папке теперь другой Workspace Ultra: запись отменена.",
        )


@contextlib.contextmanager
def _existing_workspace_writer(workspace_root: str | Path, expected_workspace_id: str | None = None):
    """Writer session of an existing Workspace; refuses before creating anything (not even the lock file)."""
    root = _validate_workspace_root(workspace_root)
    anchor = _write_anchor(root)
    _check_expected_workspace(_read_workspace_metadata_for_write(anchor), expected_workspace_id)
    with _workspace_writer_lock(anchor):
        metadata = _read_workspace_metadata_for_write(anchor)  # it may have changed while this writer waited
        _check_expected_workspace(metadata, expected_workspace_id)
        yield _WorkspaceWriter(root, anchor, metadata)


def _require_chat_for_write(writer: _WorkspaceWriter, chat_id: str) -> tuple[tuple[str, ...], dict[str, Any]]:
    """The Chat card a writer may change: own folder (no link), own Workspace, supported version."""
    if not isinstance(chat_id, str) or not _CHAT_ID_RE.fullmatch(chat_id):
        raise ValueError(f"Некорректный chat_id: {chat_id!r}")
    chats_parts = (ULTRA_DIRNAME, "chats")
    parts = chats_parts + (chat_id,)
    try:
        _verify_directory(writer.anchor, chats_parts)
        _verify_directory(writer.anchor, parts)
        data = _read_json_bounded(writer.anchor, parts + ("metadata.json",), DEFAULT_READ_LIMITS.max_chat_metadata_bytes)
    except StorageReadError as exc:
        if exc.code == "missing":
            raise ChatNotFoundError(f"Чат не найден: {chat_id}") from None
        if exc.code == "unsafe_storage_link":
            raise _write_refusal(exc) from None
        raise StorageWriteError("chat_damaged", f"Повреждён chat metadata: {chat_id}") from None
    problem = _chat_metadata_problem(data, chat_id, writer.workspace_id)
    if problem == "foreign_identity":
        raise StorageWriteError("foreign_identity", f"Чат принадлежит другому Workspace: {chat_id}")
    if problem:
        raise StorageWriteError("chat_damaged", f"Повреждён chat metadata: {chat_id}")
    version = data.get("schema_version", SCHEMA_VERSION)
    if version != SCHEMA_VERSION:
        newer = isinstance(version, int) and not isinstance(version, bool) and version > SCHEMA_VERSION
        raise StorageWriteError(
            "unsupported_version" if newer else "chat_damaged",
            f"Неподдерживаемая версия chat metadata: {version!r}. Ожидалась версия {SCHEMA_VERSION}.",
        )
    return parts, data


@contextlib.contextmanager
def _chat_writer(workspace_root: str | Path, chat_id: str):
    with _existing_workspace_writer(workspace_root) as writer:
        _require_chat_for_write(writer, chat_id)
        yield writer


def _has_chat_history(anchor: _StorageAnchor) -> bool:
    try:
        _verify_directory(anchor, (ULTRA_DIRNAME, "chats"))
        entries = _scan_directory(anchor, (ULTRA_DIRNAME, "chats"), DEFAULT_READ_LIMITS.max_chat_entries)
    except StorageReadError as exc:
        if exc.code == "missing":
            return False
        if exc.code == "listing_too_large":
            return True
        raise _write_refusal(exc) from None
    return any(_CHAT_ID_RE.fullmatch(name) for name, _kind, _size in entries)


def _verify_published(anchor: _StorageAnchor, parts: tuple[str, ...], payload: bytes) -> None:
    """The bytes now under ``parts`` are exactly ``payload`` and live under the pinned root (no swapped path)."""
    try:
        data = _read_file_bounded(anchor, parts, max(len(payload), 1))
    except StorageReadError as exc:
        if exc.code == "unsafe_storage_link":
            raise _write_refusal(exc) from None
        raise StorageWriteError("verify_failed", "Записанный файл не читается обратно.") from None
    if data != payload:
        raise StorageWriteError("verify_failed", "Записанный файл не совпадает с отправленными байтами.")


def _publish_new_file(anchor: _StorageAnchor, parts: tuple[str, ...], payload: bytes) -> None:
    """Publish ``payload`` under a name that must not exist yet; FileExistsError instead of any overwrite.

    temp file (O_EXCL) -> fsync -> rename. On Windows ``os.rename`` refuses an existing target; on POSIX a hard
    link does the same and the temporary name is then removed. A crash leaves at most the hidden temporary file,
    which no reader lists (it does not end in ``.json`` / is not ``metadata.json``).
    """
    directory = anchor.path(parts[:-1])
    target = directory / parts[-1]
    temp = directory / f".{parts[-1]}.{uuid.uuid4().hex}.tmp"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(temp, flags, 0o600)
    try:
        try:
            # The temporary file must be where the checked directory is: a folder swapped for a link after its
            # check is refused here, before any byte is written or published elsewhere.
            if os.path.normcase(_final_path_of_fd(fd)) != anchor.expected(parts[:-1] + (temp.name,)):
                raise _write_refusal(StorageReadError("unsafe_storage_link"))
            view = memoryview(payload)
            while view:
                view = view[os.write(fd, view):]
            os.fsync(fd)
        finally:
            os.close(fd)
        for delay in (*_REPLACE_RETRY_DELAYS, None):
            try:
                if os.name == "nt":
                    os.rename(temp, target)
                else:
                    os.link(temp, target)
                break
            except FileExistsError:
                raise
            except PermissionError:
                if delay is None:
                    raise
                time.sleep(delay)
    finally:
        try:
            os.unlink(temp)
        except FileNotFoundError:
            pass
    _verify_published(anchor, parts, payload)


def _read_existing_raw(writer: _WorkspaceWriter, parts: tuple[str, ...]) -> dict[str, Any] | None:
    """The record already stored under this message ID, or None; anything unreadable is never overwritten."""
    try:
        data = _read_file_bounded(writer.anchor, parts, _MAX_WRITER_JSON_BYTES)
    except StorageReadError as exc:
        if exc.code == "missing":
            return None
        if exc.code == "unsafe_storage_link":
            raise _write_refusal(exc) from None
        raise StorageWriteError(
            "existing_record_damaged", "Под этим message_id лежит недоступная запись: перезапись запрещена."
        ) from None
    try:
        record = _decode_json(data)
    except StorageReadError:
        record = None
    if not isinstance(record, dict):
        raise StorageWriteError(
            "existing_record_damaged", "Под этим message_id лежит повреждённая запись: перезапись запрещена."
        )
    return record


def _raw_canonical(record: dict[str, Any]) -> dict[str, Any]:
    """Fields that make two RAW records the same message; ``created_at`` is when, not what."""
    return {key: record[key] for key in _RAW_COMPARED_FIELDS if key in record}
