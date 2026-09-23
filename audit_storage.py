"""Server-owned, workspace-portable Final Audit observability records.

These records are deliberately separate from RAW chat and working context.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path

from context_storage import validate_task_block_id


_IDENTIFIER = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
_AUDIT_EVENTS = {
    "final_audit_failed", "audit_diagnostic_question", "audit_diagnostic_answer",
    "audit_diagnostic_error", "tool_finished", "tool_error",
    "final_audit_passed", "final_audit_error", "run_failed", "run_finished",
}
_TEXT_LIMIT = 2000


def _safe_identifier(value: str | None, label: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"Некорректный {label} для Audit Thread.")
    return value


def audit_thread_path(workspace_root: str | Path, chat_id: str | None, run_id: str) -> Path:
    root = Path(workspace_root).resolve()
    safe_chat = _safe_identifier(chat_id or "direct", "chat_id")
    safe_run = _safe_identifier(run_id, "run_id")
    return root / ".ultra" / "audit" / safe_chat / f"{safe_run}.json"


def load_audit_thread(
    workspace_root: str | Path, workspace_id: str, chat_id: str | None, run_id: str
) -> dict | None:
    path = audit_thread_path(workspace_root, chat_id, run_id)
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or (
        data.get("workspace_id") != workspace_id
        or data.get("chat_id") != chat_id
        or data.get("run_id") != run_id
    ):
        raise ValueError("Audit Thread identity mismatch.")
    if data.get("task_block_id") is not None:
        validate_task_block_id(data["task_block_id"])
    return data


def list_chat_audit_threads(
    workspace_root: str | Path, workspace_id: str, chat_id: str
) -> list[dict]:
    """Read existing threads for one chat without creating audit storage."""
    audit_dir = Path(workspace_root).resolve() / ".ultra" / "audit" / _safe_identifier(chat_id, "chat_id")
    if not audit_dir.is_dir():
        return []
    threads = []
    for path in sorted(audit_dir.glob("*.json"), key=lambda item: item.name):
        thread = load_audit_thread(workspace_root, workspace_id, chat_id, path.stem)
        if thread is not None:
            threads.append(thread)
    return threads


def _save_audit_thread(path: Path, thread: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as stream:
            json.dump(thread, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _short(value: object) -> str:
    return str(value or "")[:_TEXT_LIMIT]


class AuditThreadRecorder:
    def __init__(
        self, workspace_root: str | Path, workspace_id: str,
        chat_id: str | None, run_id: str, task_block_id: str | None = None,
    ) -> None:
        self.path = audit_thread_path(workspace_root, chat_id, run_id)
        self.thread = {
            "schema_version": 1,
            "workspace_id": _safe_identifier(workspace_id, "workspace_id"),
            "chat_id": chat_id,
            "task_block_id": validate_task_block_id(task_block_id) if task_block_id is not None else None,
            "run_id": run_id,
            "issues": [],
            "final_audit": "PENDING",
            "run_status": "RUNNING",
        }
        _save_audit_thread(self.path, self.thread)

    def observe(self, event: dict) -> None:
        kind = event.get("event")
        if kind not in _AUDIT_EVENTS:
            return
        issues = self.thread["issues"]
        if kind == "final_audit_failed":
            issues.append({
                "audit_attempt": event.get("audit_attempt"),
                "verifier_run_id": _short(event.get("verifier_run_id")),
                "reason": _short(event.get("reason")),
                "violations": [_short(item) for item in (event.get("violations") or [])[:20]],
                "required_action": _short(event.get("required_action")),
                "diagnostic_question": None,
                "diagnostic_answer": None,
                "diagnostic_error": None,
                "correction_activity": [],
                "result": "PENDING",
            })
        elif kind in {"audit_diagnostic_question", "audit_diagnostic_answer", "audit_diagnostic_error"}:
            if issues:
                key = {
                    "audit_diagnostic_question": "diagnostic_question",
                    "audit_diagnostic_answer": "diagnostic_answer",
                    "audit_diagnostic_error": "diagnostic_error",
                }[kind]
                issues[-1][key] = _short(event.get("text"))
        elif kind in {"tool_finished", "tool_error"} and issues and issues[-1]["result"] == "PENDING":
            arguments = event.get("arguments") or {}
            path = arguments.get("path") if isinstance(arguments, dict) else None
            issues[-1]["correction_activity"].append({
                "tool_sequence": event.get("tool_sequence"),
                "tool_name": _short(event.get("function"))[:80],
                "path": _short(path)[:300] if path else None,
                "status": "OK" if kind == "tool_finished" else "ERROR",
            })
        elif kind == "final_audit_passed":
            self.thread["final_audit"] = "PASS"
            for issue in issues:
                if issue["result"] == "PENDING":
                    issue["result"] = "RESOLVED"
        elif kind in {"final_audit_error", "run_failed"}:
            if kind == "final_audit_error" or issues:
                self.thread["final_audit"] = "FAIL"
            elif self.thread["final_audit"] == "PENDING":
                self.thread["final_audit"] = "NOT_RUN"
            if kind == "run_failed":
                self.thread["run_status"] = "FAILED"
            for issue in issues:
                if issue["result"] == "PENDING":
                    issue["result"] = "UNRESOLVED"
        elif kind == "run_finished":
            self.thread["run_status"] = _short(event.get("status")) or "FINISHED"
        _save_audit_thread(self.path, self.thread)
