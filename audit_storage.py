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
    "execution_consistency_detected", "execution_consistency_feedback_delivered",
    "execution_consistency_recheck_started", "execution_consistency_verifier_started",
    "execution_consistency_verifier_passed", "execution_consistency_verifier_failed",
    "execution_consistency_correction_started", "execution_consistency_resolved",
    "execution_consistency_terminal",
    "permission_denied", "permission_scope_blocked", "permission_review_started",
    "permission_review_passed", "permission_review_failed",
    "permission_user_prompted", "permission_granted", "permission_user_denied",
    "permission_escalation_terminal",
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
        if kind.startswith("permission_"):
            capability = event.get("capability") or "UNKNOWN"
            permission = self.thread.setdefault("permission_escalations", {}).setdefault(capability, {
                "capability": None, "status": "PENDING", "attempts": [],
                "verifier_run_id": None, "verifier_reason": None,
                "required_action": None, "user_decision": None, "scope": None,
            })
            # Keep the latest section readable by clients using the V1 shape.
            self.thread["permission_escalation"] = permission
            permission["capability"] = event.get("capability") or permission["capability"]
            if kind == "permission_denied":
                args = event.get("arguments") or {}
                permission["attempts"].append({
                    "attempt": event.get("attempt"),
                    "tool": _short(event.get("function")),
                    "path": _short(args.get("path")) if isinstance(args, dict) else "",
                    "executed": False,
                })
            if event.get("scope") is not None:
                permission["scope"] = _short(event["scope"])
            for source, target in (("verifier_run_id", "verifier_run_id"),
                                   ("verifier_reason", "verifier_reason"),
                                   ("required_action", "required_action"),
                                   ("user_decision", "user_decision")):
                if event.get(source) is not None:
                    permission[target] = _short(event[source])
            permission["status"] = {
                "permission_scope_blocked": "BLOCKED",
                "permission_review_started": "PENDING",
                "permission_review_passed": "PENDING",
                "permission_review_failed": "NOT_JUSTIFIED",
                "permission_user_prompted": "PENDING",
                "permission_granted": "GRANTED",
                "permission_user_denied": "DENIED",
                "permission_escalation_terminal": "BLOCKED",
            }.get(kind, permission["status"])
            if kind == "permission_escalation_terminal":
                permission["terminal_reason"] = _short(event.get("reason"))
        elif kind.startswith("execution_consistency_"):
            consistency = self.thread.setdefault("execution_consistency", {
                "status": "PENDING", "events": [], "correction_activity": [],
            })
            consistency["events"].append({
                "event": kind, "attempt": event.get("attempt"),
                "decision": _short(event.get("decision")),
                "mutation_intent": event.get("mutation_intent"),
                "verifier_run_id": _short(event.get("verifier_run_id")),
                "reason": _short(event.get("reason")),
                "violations": [_short(item) for item in (event.get("violations") or [])[:20]],
                "required_action": _short(event.get("required_action")),
                "write_revision": event.get("write_revision"),
                "tool_call_count": event.get("tool_call_count"),
                "correction_count": event.get("correction_count"),
            })
            if kind == "execution_consistency_resolved":
                consistency["status"] = "RESOLVED"
            elif kind == "execution_consistency_terminal":
                consistency["status"] = "UNRESOLVED"
        elif kind == "final_audit_failed":
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
        elif kind in {"tool_finished", "tool_error"}:
            arguments = event.get("arguments") or {}
            path = arguments.get("path") if isinstance(arguments, dict) else None
            activity = {
                "tool_sequence": event.get("tool_sequence"),
                "tool_name": _short(event.get("function"))[:80],
                "path": _short(path)[:300] if path else None,
                "status": "OK" if kind == "tool_finished" else "ERROR",
            }
            if issues and issues[-1]["result"] == "PENDING":
                issues[-1]["correction_activity"].append(activity)
            consistency = self.thread.get("execution_consistency")
            if (consistency and consistency["status"] == "PENDING"
                    and any(item["event"] == "execution_consistency_correction_started"
                            for item in consistency["events"])):
                consistency["correction_activity"].append(activity)
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
            consistency = self.thread.get("execution_consistency")
            if consistency and consistency["status"] == "PENDING":
                consistency["status"] = "UNRESOLVED"
        elif kind == "run_finished":
            self.thread["run_status"] = _short(event.get("status")) or "FINISHED"
        _save_audit_thread(self.path, self.thread)
