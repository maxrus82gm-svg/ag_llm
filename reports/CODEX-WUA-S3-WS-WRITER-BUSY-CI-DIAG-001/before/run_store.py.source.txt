"""Workspace-local append-only RUN Store v2."""
from __future__ import annotations

import contextlib
import copy
import hashlib
import json
import os
import re
import stat
import time
import uuid
from pathlib import Path
from typing import Any

import context_storage as _ultra_core


_IDENTIFIER = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
STREAM_BY_SOURCE = {
    "SERVER": "server.jsonl",
    "EXECUTOR": "executor.jsonl",
    "PLANNER": "planner.jsonl",
    "DREDD": "dredd.jsonl",
}
USAGE_ROLES = ("planner", "executor", "dredd")
_ATOMIC_REPLACE_RETRY_DELAYS = (0.02, 0.05, 0.1, 0.2, 0.4, 0.8, 1.6, 2.0)
_INDEX_GENERATION_DIRNAME = "index_generations"
_MAX_AUDIT_BYTES = 64 * 1024 * 1024


class RunStoreRecoveryRequired(ValueError):
    """An unindexed stream tail must be inspected/recovered explicitly, never replayed as success."""


def _audit_location(path: Path):
    path = Path(os.path.abspath(path))  # lexical: do not follow an untrusted audit link
    directory = next((p for p in (path, *path.parents)
                      if p.name == "audit" and p.parent.name == ".ultra"), None)
    if directory is None:
        raise ValueError("Not a Run Store audit path")
    anchor = _ultra_core._write_anchor(directory.parent.parent)
    return anchor, path.relative_to(anchor.root).parts


def _checked_path(path: Path, *, directory: bool = False, create: bool = False) -> Path:
    anchor, parts = _audit_location(path)
    parents = parts if directory else parts[:-1]
    for n in range(1, len(parents) + 1):
        prefix = parents[:n]
        if not os.path.lexists(anchor.path(prefix)):
            if not create:
                return anchor.path(parts)
            _ultra_core._ensure_write_directory(anchor, prefix)
        else:
            _ultra_core._verify_write_directory(anchor, prefix)
    target = anchor.path(parts)
    if not directory and os.path.lexists(target):
        info = target.lstat()
        if _ultra_core._is_link_or_reparse(info) or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise _ultra_core.StorageWriteError("unsafe_storage_link", "Unsafe Run Store file")
    return target


def _read_bytes(path: Path) -> bytes:
    path = _checked_path(path)
    anchor, parts = _audit_location(path)
    try:
        return _ultra_core._read_file_bounded(anchor, parts, _MAX_AUDIT_BYTES)
    except _ultra_core.StorageReadError as exc:
        if exc.code == "missing":
            raise FileNotFoundError(path) from None
        raise _ultra_core._write_refusal(exc) from None


def _read_json(path: Path):
    return json.loads(_read_bytes(path).decode("utf-8"))


@contextlib.contextmanager
def _append_file(path: Path):
    path = _checked_path(path, create=True)
    anchor, parts = _audit_location(path)
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_APPEND | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        info = os.fstat(fd)
        if (_ultra_core._is_link_or_reparse(info) or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or os.path.normcase(_ultra_core._final_path_of_fd(fd)) != anchor.expected(parts)):
            raise _ultra_core.StorageWriteError("unsafe_storage_link", "Unsafe Run Store handle")
        with os.fdopen(fd, "a+b", closefd=False) as stream:
            stream.seek(0, os.SEEK_END)
            yield stream
    finally:
        os.close(fd)


def _replace_with_retry(source: Path, destination: Path) -> None:
    for delay in (*_ATOMIC_REPLACE_RETRY_DELAYS, None):
        try:
            os.replace(source, destination)
            return
        except PermissionError:
            if delay is None:
                raise
            time.sleep(delay)


def _safe(value: str | None, fallback: str = "direct") -> str:
    value = value or fallback
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ValueError("Invalid Run Store identifier")
    return value


def audit_root(workspace_root: str | Path) -> Path:
    return _checked_path(Path(workspace_root).resolve() / ".ultra" / "audit", directory=True)


def workspace_index_path(workspace_root: str | Path) -> Path:
    return _checked_path(audit_root(workspace_root) / "index.json")


def _index_generation_dir(workspace_root: str | Path) -> Path:
    return _checked_path(audit_root(workspace_root) / _INDEX_GENERATION_DIRNAME, directory=True)


def _atomic_json(path: Path, value: dict, *, retry_replace: bool = True) -> None:
    encoded = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if len(encoded) > _MAX_AUDIT_BYTES:
        raise ValueError("Run Store JSON read limit exceeded")
    path = _checked_path(path, create=True)
    anchor, parts = _audit_location(path)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600)
        with os.fdopen(fd, "wb") as stream:
            if os.path.normcase(_ultra_core._final_path_of_fd(stream.fileno())) != anchor.expected(parts[:-1]+(temporary.name,)):
                raise _ultra_core.StorageWriteError("unsafe_storage_link", "Unsafe Run Store temporary file")
            if stream.write(encoded) != len(encoded):
                raise OSError("Partial Run Store JSON write")
            stream.flush()
            os.fsync(stream.fileno())
        _checked_path(path)
        if retry_replace:
            _replace_with_retry(temporary, path)
        else:
            os.replace(temporary, path)
        if _read_bytes(path) != encoded:
            raise ValueError("Run Store JSON readback mismatch")
    finally:
        temporary.unlink(missing_ok=True)


@contextlib.contextmanager
def _index_lock(workspace_root: str | Path):
    """One Run Store index mutation at a time per Workspace (P9): the Workspace writer lock of the shared Ultra core.

    The same OS lock as every other Ultra writer (<root>/.ultra/locks/writer.lock): reentrant in its own thread, so
    ensure_run_index_entry -> ensure_task_index_entry nests without waiting; released by the OS when its process
    dies; a busy Workspace is a visible WorkspaceBusyError after the core's timeout, never an endless wait. Unlike the
    core's chat writers it does not require .ultra/workspace.json, only an existing root with a real .ultra folder
    (created here, as the Run Store always created it); .ultra replaced by a link is refused by the lock itself.
    """
    root = Path(workspace_root).resolve()
    (root / ".ultra").mkdir(exist_ok=True)
    with _ultra_core._workspace_writer_lock(_ultra_core._write_anchor(root)):
        _checked_path(root / ".ultra/audit", directory=True, create=True)
        yield


def _require_index_lock(workspace_root: str | Path) -> None:
    """Guard of the index publication: the current thread must hold the Workspace writer lock of this root."""
    anchor = _ultra_core._write_anchor(Path(workspace_root).resolve())
    key = anchor.expected((_ultra_core.ULTRA_DIRNAME, _ultra_core.LOCKS_DIRNAME, _ultra_core.WRITER_LOCK_NAME))
    if key not in _ultra_core._held_writer_locks():
        raise RuntimeError("Run Store index is written only under the Workspace writer lock")


def _empty_index() -> dict:
    return {"schema_version": 2, "revision": 0, "next_task_number": 1,
            "next_run_number": 1, "tasks": {}, "runs": {}}


def _validate_index(value: object) -> dict:
    if not isinstance(value, dict) or value.get("schema_version") != 2:
        raise ValueError("Invalid Run Store index")
    for key in ("tasks", "runs"):
        if not isinstance(value.get(key), dict):
            raise ValueError("Invalid Run Store index")
    revision = value.get("revision", 0)
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 0:
        raise ValueError("Invalid Run Store index revision")
    result = copy.deepcopy(value)
    result["revision"] = revision
    for run_id, entry in result["runs"].items():
        if (not isinstance(entry, dict) or entry.get("run_id") != run_id
                or (entry.get("chat_id") is not None and not isinstance(entry["chat_id"], str))
                or entry.get("summary_path") != (Path(_safe(entry.get("chat_id"))) / _safe(run_id) / "summary.json").as_posix()):
            raise ValueError("Invalid Run Store summary locator")
    return result


def _load_index_file(path: Path) -> dict:
    return _validate_index(_read_json(path))


def _generation_paths(workspace_root: str | Path) -> list[Path]:
    directory = _index_generation_dir(workspace_root)
    if not directory.is_dir():
        return []
    return sorted(directory.glob("index-*.json"), key=lambda item: item.name)


def load_workspace_run_index(workspace_root: str | Path) -> dict:
    canonical = workspace_index_path(workspace_root)
    candidates: list[tuple[int, bool, dict]] = []
    if canonical.is_file():
        value = _load_index_file(canonical)
        candidates.append((int(value["revision"]), True, value))
    for path in _generation_paths(workspace_root):
        try:
            value = _load_index_file(path)
        except FileNotFoundError:
            # A lock-free reader may list a generation that a writer then compacts: it was folded into a canonical
            # index of an equal or higher revision, so the reader gets an older but whole index, never a crash (P9).
            continue
        candidates.append((int(value["revision"]), False, value))
    if not candidates:
        return _empty_index()
    # At equal revision prefer canonical index.json.
    return max(candidates, key=lambda item: (item[0], item[1]))[2]


def _cleanup_index_generations(workspace_root: str | Path,
                               canonical_revision: int) -> None:
    for path in _generation_paths(workspace_root):
        try:
            value = _load_index_file(path)
            if int(value["revision"]) <= canonical_revision:
                path.unlink(missing_ok=True)
        except PermissionError:
            continue


def _save_index(workspace_root: str | Path, index: dict) -> None:
    # The index read by the caller and the revision computed from it are only current under the lock (P9).
    _require_index_lock(workspace_root)
    snapshot = copy.deepcopy(index)
    revision = int(snapshot.get("revision", 0)) + 1
    snapshot["revision"] = revision
    canonical = workspace_index_path(workspace_root)
    fallback_active = bool(_generation_paths(workspace_root))
    try:
        _atomic_json(canonical, snapshot, retry_replace=not fallback_active)
    except PermissionError:
        directory = _index_generation_dir(workspace_root)
        _checked_path(directory, directory=True, create=True)
        generation = directory / f"index-{revision:020d}-{uuid.uuid4().hex}.json"
        _atomic_json(generation, snapshot)
    else:
        _cleanup_index_generations(workspace_root, revision)
    index["revision"] = revision


def ensure_task_index_entry(workspace_root: str | Path, task_block_id: str,
                            chat_id: str | None) -> dict:
    _safe(task_block_id)
    safe_chat = _safe(chat_id)
    with _index_lock(workspace_root):  # read, number and publish as one step (P9)
        index = load_workspace_run_index(workspace_root)
        entry = index["tasks"].get(task_block_id)
        if entry is None:
            number = int(index["next_task_number"])
            entry = {"display_id": f"T-{number:03d}", "task_block_id": task_block_id,
                     "chat_id": chat_id, "runs": []}
            index["tasks"][task_block_id] = entry
            index["next_task_number"] = number + 1
            _save_index(workspace_root, index)
        elif entry.get("chat_id") != chat_id:
            raise ValueError("Task index identity mismatch")
    return copy.deepcopy(entry)


def run_storage_dir(workspace_root: str | Path, chat_id: str | None,
                    run_id: str) -> Path:
    return _checked_path(audit_root(workspace_root) / _safe(chat_id) / _safe(run_id), directory=True)


def ensure_run_index_entry(workspace_root: str | Path, run_id: str,
                           task_block_id: str, chat_id: str | None) -> dict:
    _safe(run_id)
    _safe(chat_id)
    with _index_lock(workspace_root):  # the task and its run in one step; the nested task call re-enters (P9)
        task = ensure_task_index_entry(workspace_root, task_block_id, chat_id)
        index = load_workspace_run_index(workspace_root)
        entry = index["runs"].get(run_id)
        if entry is None:
            number = int(index["next_run_number"])
            summary = (Path(_safe(chat_id)) / _safe(run_id) / "summary.json").as_posix()
            entry = {"display_id": f"R-{number:03d}", "run_id": run_id,
                     "task_block_id": task_block_id, "chat_id": chat_id,
                     "run_status": "RUNNING", "final_audit": "PENDING",
                     "storage_version": 2, "summary_path": summary}
            index["runs"][run_id] = entry
            index["next_run_number"] = number + 1
            task_entry = index["tasks"][task_block_id]
            if run_id not in task_entry["runs"]:
                task_entry["runs"].append(run_id)
            _save_index(workspace_root, index)
        elif (entry.get("task_block_id") != task_block_id
              or entry.get("chat_id") != chat_id):
            raise ValueError("Run index identity mismatch")
        directory = run_storage_dir(workspace_root, chat_id, run_id)
        _checked_path(directory, directory=True, create=True)
    return copy.deepcopy(entry)


def get_task_index_entry(workspace_root: str | Path, task_block_id: str) -> dict | None:
    value = load_workspace_run_index(workspace_root)["tasks"].get(task_block_id)
    return copy.deepcopy(value) if value is not None else None


def get_run_index_entry(workspace_root: str | Path, run_id: str) -> dict | None:
    value = load_workspace_run_index(workspace_root)["runs"].get(run_id)
    return copy.deepcopy(value) if value is not None else None


def _empty_usage_bucket() -> dict:
    return {
        "calls": 0,
        "attempts_started": 0,
        "attempts_terminal": 0,
        "unknown_usage_calls": 0,
        "known_prompt_tokens": 0,
        "known_completion_tokens": 0,
        "known_total_tokens": 0,
        "prompt_tokens": None,
        "completion_tokens": None,
        "total_tokens": None,
        "complete": True,
    }


def empty_usage_summary() -> dict:
    result = {role: _empty_usage_bucket() for role in USAGE_ROLES}
    result["total"] = _empty_usage_bucket()
    return result


def empty_provider_accounting_summary() -> dict:
    return {
        "schema_version": 1,
        "started_ids": [],
        "terminal_ids": [],
        "orphan_terminal_ids": [],
        "duplicate_terminal_ids": [],
        "complete": True,
    }


def _usage_known(usage: dict | None) -> bool:
    return isinstance(usage, dict) and all(
        isinstance(usage.get(key), int) and not isinstance(usage.get(key), bool)
        for key in ("prompt_tokens", "completion_tokens", "total_tokens")
    )


def _refresh_usage_bucket(bucket: dict) -> None:
    bucket["complete"] = (
        int(bucket.get("attempts_started") or 0)
        == int(bucket.get("attempts_terminal") or 0)
        and int(bucket.get("unknown_usage_calls") or 0) == 0
    )
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        known_key = "known_" + key
        bucket[key] = (
            int(bucket.get(known_key) or 0)
            if bucket["complete"] and int(bucket.get("calls") or 0) > 0
            else None
        )


def _refresh_total_usage(summary: dict) -> None:
    total = _empty_usage_bucket()
    role_buckets = [summary["usage"][role] for role in USAGE_ROLES]
    for field in (
        "calls", "attempts_started", "attempts_terminal", "unknown_usage_calls",
        "known_prompt_tokens", "known_completion_tokens", "known_total_tokens",
    ):
        total[field] = sum(int(bucket.get(field) or 0) for bucket in role_buckets)
    total["complete"] = all(
        bucket.get("complete", False)
        for bucket in role_buckets
        if int(bucket.get("attempts_started") or 0)
        or int(bucket.get("attempts_terminal") or 0)
        or int(bucket.get("calls") or 0)
    )
    accounting = summary.get("provider_accounting") or {}
    if accounting and not accounting.get("complete", False):
        total["complete"] = False
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        total[key] = (
            int(total.get("known_" + key) or 0)
            if total["complete"] and total["calls"] > 0
            else None
        )
    summary["usage"]["total"] = total


def create_run_summary(workspace_root: str | Path, workspace_id: str,
                       chat_id: str | None, task_block_id: str, run_id: str) -> dict:
    with _index_lock(workspace_root):  # index entries and the summary they point to as one step (P9)
        task = ensure_task_index_entry(workspace_root, task_block_id, chat_id)
        run = ensure_run_index_entry(workspace_root, run_id, task_block_id, chat_id)
        summary = {"schema_version": 2, "workspace_id": workspace_id,
                   "chat_id": chat_id, "task_block_id": task_block_id,
                   "task_display_id": task["display_id"], "run_id": run_id,
                   "run_display_id": run["display_id"], "run_status": "RUNNING",
                   "final_audit": "PENDING", "api_requests": 0, "tool_calls": 0,
                   "usage": empty_usage_summary(),
                   "provider_accounting": empty_provider_accounting_summary()}
        _atomic_json(run_storage_dir(workspace_root, chat_id, run_id) / "summary.json", summary)
    return summary


def load_run_summary(workspace_root: str | Path, run_id: str,
                     chat_id: str | None = None) -> dict | None:
    entry = get_run_index_entry(workspace_root, run_id)
    if entry is None:
        return None
    if chat_id is not None and entry.get("chat_id") != chat_id:
        return None
    path = _checked_path(audit_root(workspace_root) / entry["summary_path"])
    if not path.is_file():
        return None
    return _read_json(path)


def update_run_summary_index(workspace_root: str | Path, run_id: str,
                             updates: dict) -> dict:
    with _index_lock(workspace_root):  # the summary and the index status read and written as one step (P9)
        entry = get_run_index_entry(workspace_root, run_id)
        if entry is None:
            raise KeyError(run_id)
        summary_path = _checked_path(audit_root(workspace_root) / entry["summary_path"])
        summary = _read_json(summary_path)
        summary.update(copy.deepcopy(updates))
        _atomic_json(summary_path, summary)
        index = load_workspace_run_index(workspace_root)
        index_changed = False
        for key in ("run_status", "final_audit"):
            if key in updates and index["runs"][run_id].get(key) != updates[key]:
                index["runs"][run_id][key] = updates[key]
                index_changed = True
        if index_changed:
            _save_index(workspace_root, index)
    return summary


def run_component_path(workspace_root: str | Path, run_id: str,
                       component: str) -> Path:
    entry = get_run_index_entry(workspace_root, run_id)
    if entry is None:
        raise KeyError(run_id)
    allowed = {"summary.json", "task.json", "executor_base.json", "executor.jsonl",
               "planner.jsonl", "server.jsonl", "dredd.jsonl", "records.idx.jsonl"}
    if component not in allowed:
        raise ValueError("Unknown Run Store component")
    return _checked_path(run_storage_dir(workspace_root, entry.get("chat_id"), run_id) / component)


def audit_exists(workspace_root: str | Path, chat_id: str | None, run_id: str) -> bool:
    if get_run_index_entry(workspace_root, run_id) is not None:
        return run_component_path(workspace_root, run_id, "summary.json").is_file()
    legacy = _checked_path(audit_root(workspace_root) / _safe(chat_id) / f"{_safe(run_id)}.json")
    return legacy.is_file()


def _next_sequence(index_path: Path) -> int:
    return len(_record_index(index_path)) + 1


def _record_index(path: Path) -> list[dict]:
    try:
        raw = _read_bytes(path)
    except FileNotFoundError:
        return []
    return _parse_record_index(raw)


def _parse_record_index(raw: bytes) -> list[dict]:
    if raw and not raw.endswith(b"\n"):
        raise ValueError("Partial Run Store index; manual inspection required")
    result, ids = [], set()
    for line in raw.split(b"\n"):
        if not line.strip():
            continue
        item = json.loads(line.decode("utf-8"))
        if (not isinstance(item, dict) or type(item.get("sequence")) is not int
                or item["sequence"] != len(result)+1
                or not isinstance(item.get("record_id"), str) or item["record_id"] in ids
                or item.get("source") not in STREAM_BY_SOURCE
                or item.get("stream") != STREAM_BY_SOURCE[item["source"]]
                or type(item.get("offset")) is not int or item["offset"] < 0
                or type(item.get("length")) is not int or item["length"] <= 0):
            raise ValueError("Invalid Run Store record index")
        ids.add(item["record_id"])
        result.append(item)
    return result


def _scan_run(workspace_root: str | Path, run_id: str, *, records=None):
    if records is None:
        records = _record_index(run_component_path(workspace_root, run_id, "records.idx.jsonl"))
    streams, ends = {}, {name: 0 for name in STREAM_BY_SOURCE.values()}
    for name in ends:
        try:
            streams[name] = _read_bytes(run_component_path(workspace_root, run_id, name))
        except FileNotFoundError:
            streams[name] = b""
    if sum(map(len, streams.values())) > _MAX_AUDIT_BYTES:
        raise ValueError("Run Store stream read limit exceeded")
    decoded = []
    for item in records:
        name = item["stream"]
        if item["offset"] != ends[name]:
            raise ValueError("Run Store stream offset gap/overlap")
        end = item["offset"] + item["length"]
        encoded = streams[name][item["offset"]:end]
        if len(encoded) != item["length"] or not encoded.endswith(b"\n"):
            raise ValueError("Partial confirmed Run Store stream")
        if "sha256" in item and hashlib.sha256(encoded).hexdigest() != item["sha256"]:
            raise ValueError("Run Store record checksum mismatch")
        value = json.loads(encoded.decode("utf-8"))
        if not isinstance(value, dict) or any(value.get(k) != item.get(k) for k in ("record_id", "sequence", "source", "event", "timestamp")):
            raise ValueError("Run Store record/index identity mismatch")
        decoded.append(value)
        ends[name] = end
    tails = {name: len(streams[name])-end for name, end in ends.items() if len(streams[name]) != end}
    return records, decoded, ends, tails


def recover_run_records(workspace_root: str | Path, run_id: str) -> dict:
    """Recover one interrupted append, using its durable intent; never replay an event.

    The intent pins the exact previous index prefix and the planned record. Unexplained corruption or
    orphan bytes without an intent are refused. A complete record before a lost reply remains committed.
    """
    with _index_lock(workspace_root):
        pending = _pending_path(workspace_root, run_id)
        if not os.path.lexists(pending):
            if _scan_run(workspace_root, run_id)[3]:
                raise RunStoreRecoveryRequired("Orphan stream without append intent; manual inspection required")
            return {"removed_bytes": {}, "committed": False}
        intent = _read_json(pending)
        if (not isinstance(intent, dict) or intent.get("schema_version") != 1
                or intent.get("run_id") != run_id or type(intent.get("index_size")) is not int
                or intent["index_size"] < 0 or not isinstance(intent.get("index_sha256"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", intent["index_sha256"])
                or not isinstance(intent.get("record"), dict)
                or not isinstance(intent["record"].get("sha256"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", intent["record"]["sha256"])):
            raise ValueError("Invalid Run Store append intent")
        item = intent["record"]
        index_path = run_component_path(workspace_root, run_id, "records.idx.jsonl")
        try:
            raw = _read_bytes(index_path)
        except FileNotFoundError:
            raw = b""
        prefix = raw[:intent["index_size"]]
        if len(prefix) != intent["index_size"] or hashlib.sha256(prefix).hexdigest() != intent["index_sha256"]:
            raise ValueError("Run Store committed index prefix changed")
        planned = _index_bytes(item)
        # Validate even a tampered intent with the same index schema as real receipts.
        _parse_record_index(prefix + planned)
        suffix = raw[intent["index_size"]:]
        if suffix == planned:
            _records, _decoded, _ends, tails = _scan_run(workspace_root, run_id)
            if tails:
                raise ValueError("Unexpected stream tail after committed append")
            _clear_pending(pending)
            return {"removed_bytes": {}, "committed": True}
        if suffix and not planned.startswith(suffix):
            raise ValueError("Unrecognised Run Store index tail")
        # Validate the previous confirmed index against the streams BEFORE any truncation.
        old_records = _parse_record_index(prefix)
        _records, _decoded, ends, tails = _scan_run(workspace_root, run_id, records=old_records)
        name = item["stream"]
        if item["offset"] != ends[name] or any(k != name for k in tails) or tails.get(name, 0) > item["length"]:
            raise ValueError("Unrecognised Run Store stream tail")
        if tails.get(name) == item["length"]:
            tail = _read_bytes(run_component_path(workspace_root, run_id, name))[ends[name]:]
            if hashlib.sha256(tail).hexdigest() != item.get("sha256"):
                raise ValueError("Unconfirmed Run Store record checksum mismatch")
        if suffix:
            _truncate(index_path, intent["index_size"])
        if tails:
            _truncate(run_component_path(workspace_root, run_id, name), ends[name])
        if _scan_run(workspace_root, run_id)[3]:
            raise ValueError("Run Store recovery readback failed")
        _clear_pending(pending)
        return {"removed_bytes": tails, "committed": False}


def _pending_path(workspace_root: str | Path, run_id: str) -> Path:
    entry = get_run_index_entry(workspace_root, run_id)
    if entry is None:
        raise KeyError(run_id)
    return _checked_path(run_storage_dir(workspace_root, entry.get("chat_id"), run_id) / "append.pending.json")


def _clear_pending(path: Path) -> None:
    _checked_path(path).unlink()


def _truncate(path: Path, size: int) -> None:
    with _append_file(path) as stream:
        stream.truncate(size)
        stream.flush()
        os.fsync(stream.fileno())


def _index_bytes(record: dict) -> bytes:
    return (json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def append_run_record(workspace_root: str | Path, run_id: str, *, source: str,
                      event: str, payload: dict, timestamp: float) -> dict:
    with _index_lock(workspace_root):
        return _append_run_record_locked(workspace_root, run_id, source=source, event=event, payload=payload, timestamp=timestamp)


def _append_run_record_locked(workspace_root: str | Path, run_id: str, *, source: str,
                              event: str, payload: dict, timestamp: float) -> dict:
    if source not in STREAM_BY_SOURCE:
        raise ValueError("Unknown Run Store source")
    pending = _pending_path(workspace_root, run_id)
    if os.path.lexists(pending):
        raise RunStoreRecoveryRequired("Pending Run Store append; explicit recovery required")
    _records, _decoded, ends, tails = _scan_run(workspace_root, run_id)
    if tails:
        raise RunStoreRecoveryRequired("Unindexed Run Store stream tail; explicit recovery required")
    index_path = run_component_path(workspace_root, run_id, "records.idx.jsonl")
    sequence = _next_sequence(index_path)
    record_id = "rec_" + uuid.uuid4().hex
    record = {"record_id": record_id, "sequence": sequence, "timestamp": timestamp,
              "source": source, "event": event, "payload": copy.deepcopy(payload)}
    stream_name = STREAM_BY_SOURCE[source]
    stream_path = run_component_path(workspace_root, run_id, stream_name)
    encoded = (json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    offset = ends[stream_name]
    index_record = {"record_id": record_id, "sequence": sequence, "source": source,
                    "event": event, "stream": stream_name, "offset": offset,
                    "length": len(encoded), "timestamp": timestamp,
                    "sha256": hashlib.sha256(encoded).hexdigest()}
    for key in ("stage_id", "api_request_number", "status", "mode"):
        if payload.get(key) is not None:
            index_record[key] = payload[key]
    index_encoded = _index_bytes(index_record)
    try:
        old_index = _read_bytes(index_path)
    except FileNotFoundError:
        old_index = b""
    if (len(old_index) + len(index_encoded) > _MAX_AUDIT_BYTES
            or sum(ends.values()) + len(encoded) > _MAX_AUDIT_BYTES):
        raise ValueError("Run Store append read limit exceeded")
    _atomic_json(pending, {"schema_version": 1, "run_id": run_id, "index_size": len(old_index),
                           "index_sha256": hashlib.sha256(old_index).hexdigest(), "record": index_record})
    with _append_file(stream_path) as stream:
        if stream.tell() != offset:
            raise ValueError("Run Store stream changed outside the writer lock")
        if stream.write(encoded) != len(encoded):
            raise OSError("Partial Run Store outcome append")
        stream.flush()
        os.fsync(stream.fileno())
    with _append_file(index_path) as index_stream:
        if index_stream.write(index_encoded) != len(index_encoded):
            raise OSError("Partial Run Store index append")
        index_stream.flush()
        os.fsync(index_stream.fileno())
    persisted = load_run_record(workspace_root, run_id, record_id, expected_sha256=index_record["sha256"])
    if persisted != record:
        raise ValueError("Run Store acknowledgement readback failed")
    _clear_pending(pending)
    return index_record


def list_run_records(workspace_root: str | Path, run_id: str) -> list[dict]:
    path = run_component_path(workspace_root, run_id, "records.idx.jsonl")
    return _record_index(path)


def load_run_record(workspace_root: str | Path, run_id: str,
                    record_id: str, *, expected_sha256: str | None = None) -> dict | None:
    matches = [value for value in list_run_records(workspace_root, run_id)
               if value.get("record_id") == record_id]
    if not matches:
        return None
    if len(matches) != 1:
        raise ValueError("Ambiguous Run Store record identity")
    item = matches[0]
    if (item.get("source") not in STREAM_BY_SOURCE
            or item.get("stream") != STREAM_BY_SOURCE[item["source"]]
            or type(item.get("offset")) is not int or item["offset"] < 0
            or type(item.get("length")) is not int or item["length"] <= 0):
        raise ValueError("Invalid Run Store record locator")
    path = run_component_path(workspace_root, run_id, item["stream"])
    encoded = _read_bytes(path)[item["offset"]:item["offset"]+item["length"]]
    if len(encoded) != item["length"] or not encoded.endswith(b"\n"):
        raise ValueError("Partial Run Store record")
    # Older indexes remain readable. Current certified outcomes additionally bind
    # the acknowledged checksum, so removal of this field cannot downgrade them.
    if "sha256" in item and hashlib.sha256(encoded).hexdigest() != item["sha256"]:
        raise ValueError("Run Store record checksum mismatch")
    if expected_sha256 is not None and hashlib.sha256(encoded).hexdigest() != expected_sha256:
        raise ValueError("Durable outcome acknowledgement checksum mismatch")
    record = json.loads(encoded.decode("utf-8"))
    if not isinstance(record, dict) or any(
        record.get(key) != item.get(key)
        for key in ("record_id", "sequence", "source", "event", "timestamp")
    ):
        raise ValueError("Run Store record/index identity mismatch")
    return record


def validate_run_record(workspace_root: str | Path, run_id: str,
                        acknowledgement: dict, *, event: str,
                        payload: dict | None = None) -> dict:
    """Read back an acknowledged outcome, including its exact bytes and identity.

    The checksum comes from the append acknowledgement, not a mutable index.
    No retry or repair is performed here: an uncertain mutation is never replayed.
    """
    record_id = acknowledgement.get("record_id")
    checksum = acknowledgement.get("sha256")
    if (not isinstance(record_id, str) or not record_id
            or not isinstance(checksum, str)
            or not re.fullmatch(r"[0-9a-f]{64}", checksum)):
        raise ValueError("Missing durable Run Store acknowledgement")
    record = load_run_record(workspace_root, run_id, record_id, expected_sha256=checksum)
    if (record is None or record.get("event") != event
            or (payload is not None and record.get("payload") != payload)):
        raise ValueError("Missing or mismatched durable outcome")
    encoded = (json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    if hashlib.sha256(encoded).hexdigest() != checksum:
        raise ValueError("Durable outcome acknowledgement checksum mismatch")
    return record


def load_stream_records(workspace_root: str | Path, run_id: str,
                        source: str) -> list[dict]:
    if source not in STREAM_BY_SOURCE:
        raise ValueError("Unknown Run Store source")
    _records, decoded, _ends, tails = _scan_run(workspace_root, run_id)
    if tails:
        raise RunStoreRecoveryRequired("Unindexed Run Store stream tail; explicit recovery required")
    return [record for record in decoded if record["source"] == source]


def _apply_terminal_usage(bucket: dict, usage: dict | None) -> None:
    bucket["calls"] = int(bucket.get("calls") or 0) + 1
    bucket["attempts_terminal"] = int(bucket.get("attempts_terminal") or 0) + 1
    if _usage_known(usage):
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            known_key = "known_" + key
            bucket[known_key] = int(bucket.get(known_key) or 0) + int(usage[key])
    else:
        bucket["unknown_usage_calls"] = int(bucket.get("unknown_usage_calls") or 0) + 1
    _refresh_usage_bucket(bucket)


def record_usage(summary: dict, role: str, usage: dict | None) -> dict:
    """Compatibility helper for callers that only have a terminal usage record."""
    if role not in USAGE_ROLES:
        raise ValueError("Unknown usage role")
    bucket = summary["usage"][role]
    bucket["attempts_started"] = int(bucket.get("attempts_started") or 0) + 1
    _apply_terminal_usage(bucket, usage)
    _refresh_total_usage(summary)
    return summary


def record_provider_attempt_started(
    summary: dict, role: str, provider_attempt_id: str
) -> dict:
    if role not in USAGE_ROLES:
        raise ValueError("Unknown usage role")
    accounting = summary.setdefault(
        "provider_accounting", empty_provider_accounting_summary()
    )
    started = accounting.setdefault("started_ids", [])
    if provider_attempt_id not in started:
        started.append(provider_attempt_id)
        bucket = summary["usage"][role]
        bucket["attempts_started"] = int(bucket.get("attempts_started") or 0) + 1
        _refresh_usage_bucket(bucket)
    accounting["complete"] = (
        len(accounting.get("started_ids", []))
        == len(accounting.get("terminal_ids", []))
        and not accounting.get("orphan_terminal_ids")
        and not accounting.get("duplicate_terminal_ids")
    )
    _refresh_total_usage(summary)
    return summary


def record_provider_attempt_terminal(
    summary: dict, role: str, provider_attempt_id: str, usage: dict | None
) -> dict:
    if role not in USAGE_ROLES:
        raise ValueError("Unknown usage role")
    accounting = summary.setdefault(
        "provider_accounting", empty_provider_accounting_summary()
    )
    started = accounting.setdefault("started_ids", [])
    terminal = accounting.setdefault("terminal_ids", [])
    if provider_attempt_id in terminal:
        duplicates = accounting.setdefault("duplicate_terminal_ids", [])
        if provider_attempt_id not in duplicates:
            duplicates.append(provider_attempt_id)
    else:
        terminal.append(provider_attempt_id)
        if provider_attempt_id not in started:
            orphans = accounting.setdefault("orphan_terminal_ids", [])
            if provider_attempt_id not in orphans:
                orphans.append(provider_attempt_id)
        _apply_terminal_usage(summary["usage"][role], usage)
    accounting["complete"] = (
        len(started) == len(terminal)
        and not accounting.get("orphan_terminal_ids")
        and not accounting.get("duplicate_terminal_ids")
    )
    _refresh_total_usage(summary)
    return summary


def reconstruct_executor_context(workspace_root: str | Path, run_id: str,
                                 api_request_number: int) -> list[dict]:
    base_path = run_component_path(workspace_root, run_id, "executor_base.json")
    base = _read_json(base_path)
    messages = copy.deepcopy(base["messages"])
    if int(base.get("api_request_number", 1)) == api_request_number:
        return messages
    for record in load_stream_records(workspace_root, run_id, "EXECUTOR"):
        payload = record.get("payload") or {}
        delta = payload.get("context_delta")
        if not isinstance(delta, dict):
            continue
        prefix = int(delta["common_prefix"])
        messages = messages[:prefix] + copy.deepcopy(delta["added_messages"])
        if int(delta["api_request_number"]) == api_request_number:
            return messages
    raise KeyError(api_request_number)
