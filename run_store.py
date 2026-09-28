"""Workspace-local append-only RUN Store v2."""
from __future__ import annotations

import copy
import json
import os
import re
import uuid
from pathlib import Path
from typing import Any


_IDENTIFIER = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
STREAM_BY_SOURCE = {
    "SERVER": "server.jsonl",
    "EXECUTOR": "executor.jsonl",
    "PLANNER": "planner.jsonl",
    "DREDD": "dredd.jsonl",
}
USAGE_ROLES = ("planner", "executor", "dredd")


def _safe(value: str | None, fallback: str = "direct") -> str:
    value = value or fallback
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ValueError("Invalid Run Store identifier")
    return value


def audit_root(workspace_root: str | Path) -> Path:
    return Path(workspace_root).resolve() / ".ultra" / "audit"


def workspace_index_path(workspace_root: str | Path) -> Path:
    return audit_root(workspace_root) / "index.json"


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _empty_index() -> dict:
    return {"schema_version": 2, "next_task_number": 1, "next_run_number": 1,
            "tasks": {}, "runs": {}}


def load_workspace_run_index(workspace_root: str | Path) -> dict:
    path = workspace_index_path(workspace_root)
    if not path.is_file():
        return _empty_index()
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema_version") != 2:
        raise ValueError("Invalid Run Store index")
    for key in ("tasks", "runs"):
        if not isinstance(value.get(key), dict):
            raise ValueError("Invalid Run Store index")
    return value


def _save_index(workspace_root: str | Path, index: dict) -> None:
    _atomic_json(workspace_index_path(workspace_root), index)


def ensure_task_index_entry(workspace_root: str | Path, task_block_id: str,
                            chat_id: str | None) -> dict:
    _safe(task_block_id)
    safe_chat = _safe(chat_id)
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
    return audit_root(workspace_root) / _safe(chat_id) / _safe(run_id)


def ensure_run_index_entry(workspace_root: str | Path, run_id: str,
                           task_block_id: str, chat_id: str | None) -> dict:
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
    directory.mkdir(parents=True, exist_ok=True)
    return copy.deepcopy(entry)


def get_task_index_entry(workspace_root: str | Path, task_block_id: str) -> dict | None:
    value = load_workspace_run_index(workspace_root)["tasks"].get(task_block_id)
    return copy.deepcopy(value) if value is not None else None


def get_run_index_entry(workspace_root: str | Path, run_id: str) -> dict | None:
    value = load_workspace_run_index(workspace_root)["runs"].get(run_id)
    return copy.deepcopy(value) if value is not None else None


def _empty_usage_bucket() -> dict:
    return {"calls": 0, "prompt_tokens": None, "completion_tokens": None,
            "total_tokens": None, "complete": True}


def empty_usage_summary() -> dict:
    result = {role: _empty_usage_bucket() for role in USAGE_ROLES}
    result["total"] = _empty_usage_bucket()
    return result


def create_run_summary(workspace_root: str | Path, workspace_id: str,
                       chat_id: str | None, task_block_id: str, run_id: str) -> dict:
    task = ensure_task_index_entry(workspace_root, task_block_id, chat_id)
    run = ensure_run_index_entry(workspace_root, run_id, task_block_id, chat_id)
    summary = {"schema_version": 2, "workspace_id": workspace_id,
               "chat_id": chat_id, "task_block_id": task_block_id,
               "task_display_id": task["display_id"], "run_id": run_id,
               "run_display_id": run["display_id"], "run_status": "RUNNING",
               "final_audit": "PENDING", "api_requests": 0, "tool_calls": 0,
               "usage": empty_usage_summary()}
    _atomic_json(run_storage_dir(workspace_root, chat_id, run_id) / "summary.json", summary)
    return summary


def load_run_summary(workspace_root: str | Path, run_id: str,
                     chat_id: str | None = None) -> dict | None:
    entry = get_run_index_entry(workspace_root, run_id)
    if entry is None:
        return None
    if chat_id is not None and entry.get("chat_id") != chat_id:
        return None
    path = audit_root(workspace_root) / entry["summary_path"]
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def update_run_summary_index(workspace_root: str | Path, run_id: str,
                             updates: dict) -> dict:
    entry = get_run_index_entry(workspace_root, run_id)
    if entry is None:
        raise KeyError(run_id)
    summary_path = audit_root(workspace_root) / entry["summary_path"]
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary.update(copy.deepcopy(updates))
    _atomic_json(summary_path, summary)
    index = load_workspace_run_index(workspace_root)
    for key in ("run_status", "final_audit"):
        if key in updates:
            index["runs"][run_id][key] = updates[key]
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
    return run_storage_dir(workspace_root, entry.get("chat_id"), run_id) / component


def audit_exists(workspace_root: str | Path, chat_id: str | None, run_id: str) -> bool:
    if get_run_index_entry(workspace_root, run_id) is not None:
        return run_component_path(workspace_root, run_id, "summary.json").is_file()
    legacy = audit_root(workspace_root) / _safe(chat_id) / f"{_safe(run_id)}.json"
    return legacy.is_file()


def _next_sequence(index_path: Path) -> int:
    if not index_path.is_file():
        return 1
    last = None
    with index_path.open("rb") as stream:
        for line in stream:
            if line.strip():
                last = line
    if last is None:
        return 1
    return int(json.loads(last.decode("utf-8"))["sequence"]) + 1


def append_run_record(workspace_root: str | Path, run_id: str, *, source: str,
                      event: str, payload: dict, timestamp: float) -> dict:
    if source not in STREAM_BY_SOURCE:
        raise ValueError("Unknown Run Store source")
    index_path = run_component_path(workspace_root, run_id, "records.idx.jsonl")
    sequence = _next_sequence(index_path)
    record_id = "rec_" + uuid.uuid4().hex
    record = {"record_id": record_id, "sequence": sequence, "timestamp": timestamp,
              "source": source, "event": event, "payload": copy.deepcopy(payload)}
    stream_name = STREAM_BY_SOURCE[source]
    stream_path = run_component_path(workspace_root, run_id, stream_name)
    encoded = (json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    stream_path.parent.mkdir(parents=True, exist_ok=True)
    with stream_path.open("ab") as stream:
        offset = stream.tell()
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())
    index_record = {"record_id": record_id, "sequence": sequence, "source": source,
                    "event": event, "stream": stream_name, "offset": offset,
                    "length": len(encoded), "timestamp": timestamp}
    for key in ("stage_id", "api_request_number", "status", "mode"):
        if payload.get(key) is not None:
            index_record[key] = payload[key]
    index_encoded = (json.dumps(index_record, ensure_ascii=False,
                                separators=(",", ":")) + "\n").encode("utf-8")
    with index_path.open("ab") as index_stream:
        index_stream.write(index_encoded)
        index_stream.flush()
        os.fsync(index_stream.fileno())
    return index_record


def list_run_records(workspace_root: str | Path, run_id: str) -> list[dict]:
    path = run_component_path(workspace_root, run_id, "records.idx.jsonl")
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def load_run_record(workspace_root: str | Path, run_id: str,
                    record_id: str) -> dict | None:
    item = next((value for value in list_run_records(workspace_root, run_id)
                 if value.get("record_id") == record_id), None)
    if item is None:
        return None
    path = run_component_path(workspace_root, run_id, item["stream"])
    with path.open("rb") as stream:
        stream.seek(int(item["offset"]))
        encoded = stream.read(int(item["length"]))
    return json.loads(encoded.decode("utf-8"))


def load_stream_records(workspace_root: str | Path, run_id: str,
                        source: str) -> list[dict]:
    if source not in STREAM_BY_SOURCE:
        raise ValueError("Unknown Run Store source")
    path = run_component_path(workspace_root, run_id, STREAM_BY_SOURCE[source])
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def record_usage(summary: dict, role: str, usage: dict | None) -> dict:
    if role not in USAGE_ROLES:
        raise ValueError("Unknown usage role")
    bucket = summary["usage"][role]
    bucket["calls"] += 1
    known = isinstance(usage, dict) and all(
        isinstance(usage.get(key), int) and not isinstance(usage.get(key), bool)
        for key in ("prompt_tokens", "completion_tokens", "total_tokens")
    )
    if not known:
        bucket["complete"] = False
    else:
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            bucket[key] = (bucket[key] or 0) + usage[key]
    total = _empty_usage_bucket()
    total["calls"] = sum(summary["usage"][item]["calls"] for item in USAGE_ROLES)
    total["complete"] = all(summary["usage"][item]["complete"] for item in USAGE_ROLES
                            if summary["usage"][item]["calls"])
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        values = [summary["usage"][item][key] for item in USAGE_ROLES
                  if summary["usage"][item][key] is not None]
        total[key] = sum(values) if values else None
    summary["usage"]["total"] = total
    return summary


def reconstruct_executor_context(workspace_root: str | Path, run_id: str,
                                 api_request_number: int) -> list[dict]:
    base_path = run_component_path(workspace_root, run_id, "executor_base.json")
    base = json.loads(base_path.read_text(encoding="utf-8"))
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
