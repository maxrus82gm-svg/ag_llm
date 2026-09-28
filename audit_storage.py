"""Server-owned, workspace-portable Final Audit observability records.

These records are deliberately separate from RAW chat and working context.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import uuid
from pathlib import Path

from context_storage import validate_task_block_id
from run_store import (
    append_run_record,
    audit_exists as run_audit_exists,
    audit_root,
    create_run_summary,
    get_run_index_entry,
    get_task_index_entry,
    list_run_records,
    load_run_record,
    load_run_summary,
    load_stream_records,
    record_usage,
    reconstruct_executor_context,
    run_component_path,
    update_run_summary_index,
)


_IDENTIFIER = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
PLANNER_EVENTS = {
    "planner_started", "planner_completed", "planner_failed", "plan_created", "plan_revised",
    "stage_started", "stage_status_changed", "stage_satisfied", "stage_blocked",
    "planner_readiness_started", "planner_readiness_result", "persistence_required",
    "persistence_unsatisfied", "persistence_satisfied", "persistence_recovery_started",
    "persistence_recovery_exhausted", "replan_started", "replan_completed",
    "final_audit_routed_execution_defect", "final_audit_routed_plan_defect", "persistence_dispatch",
    "planner_readiness_rejected", "mutation_preflight_rejected",
    "planner_session_started", "planner_session_message", "planner_attempt_rejected",
    "planner_dredd_review_started", "planner_dredd_review_completed",
    "planner_session_completed", "planner_session_blocked",
}
PLANNER_DIAGNOSTIC_EVENTS = {
    "planner_diagnostic_request", "planner_diagnostic_context",
    "planner_diagnostic_response", "planner_diagnostic_error",
}
PLANNER_OWNED_EVENTS = PLANNER_DIAGNOSTIC_EVENTS | {
    "planner_session_started", "planner_session_message", "planner_attempt_rejected",
    "planner_session_completed", "planner_session_blocked",
}
PLANNER_DREDD_EVENTS = {
    "planner_dredd_review_started", "planner_dredd_review_completed",
}
EXECUTOR_DIAGNOSTIC_EVENTS = {
    "executor_diagnostic_context",
    "executor_diagnostic_response",
    "executor_diagnostic_reset",
}
_AUDIT_EVENTS = {
    "run_started", "api_request", "api_response", "tool_started",
    "final_audit_started",
    "final_audit_failed", "audit_diagnostic_question", "audit_diagnostic_answer",
    "audit_diagnostic_error", "tool_finished", "tool_error",
    "final_audit_passed", "final_audit_skipped", "final_audit_error", "run_failed", "run_finished",
    "execution_consistency_detected", "execution_consistency_feedback_delivered",
    "execution_consistency_recheck_started", "execution_consistency_verifier_started",
    "execution_consistency_verifier_passed", "execution_consistency_verifier_failed",
    "execution_consistency_correction_started", "execution_consistency_resolved",
    "execution_consistency_terminal",
    "permission_denied", "permission_scope_blocked", "permission_review_started",
    "permission_review_passed", "permission_review_failed",
    "permission_user_prompted", "permission_granted", "permission_user_denied",
    "permission_escalation_terminal",
} | PLANNER_EVENTS | PLANNER_DIAGNOSTIC_EVENTS | EXECUTOR_DIAGNOSTIC_EVENTS
_TEXT_LIMIT = 2000
_PLANNER_SESSION_TEXT_LIMIT = 32768


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
    v2 = get_run_index_entry(workspace_root, run_id)
    if v2 is not None:
        summary = load_run_summary(workspace_root, run_id, chat_id)
        if summary is None or summary.get("workspace_id") != workspace_id:
            raise ValueError("Audit Thread identity mismatch.")
        recorder = AuditThreadRecorder.__new__(AuditThreadRecorder)
        recorder.workspace_root = Path(workspace_root).resolve()
        recorder.workspace_id = workspace_id
        recorder.chat_id = chat_id
        recorder.run_id = run_id
        recorder.task_block_id = summary.get("task_block_id")
        recorder.thread = recorder._empty_legacy_thread()
        recorder._previous_executor_messages = None
        for item in list_run_records(workspace_root, run_id):
            record = load_run_record(workspace_root, run_id, item["record_id"])
            if record is None:
                continue
            payload = dict(record.get("payload") or {})
            delta = payload.pop("context_delta", None)
            context_base = payload.get("context_base")
            if isinstance(context_base, dict):
                try:
                    payload["messages"] = reconstruct_executor_context(
                        workspace_root, run_id, int(context_base["api_request_number"])
                    )
                except Exception:
                    payload["messages"] = []
            if isinstance(delta, dict):
                try:
                    payload["messages"] = reconstruct_executor_context(
                        workspace_root, run_id, int(delta["api_request_number"])
                    )
                except Exception:
                    payload["messages"] = []
            event = {"event": record.get("event"), "run_id": run_id,
                     "timestamp": record.get("timestamp"), **payload}
            recorder.observe(event, persist=False)
        recorder.thread["run_status"] = summary.get("run_status", recorder.thread["run_status"])
        recorder.thread["final_audit"] = summary.get("final_audit", recorder.thread["final_audit"])
        recorder.thread["task_display_id"] = summary.get("task_display_id")
        recorder.thread["run_display_id"] = summary.get("run_display_id")
        recorder.thread["usage"] = summary.get("usage")
        return recorder.thread
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
    indexed_run_ids = set()
    index_path = audit_root(workspace_root) / "index.json"
    if index_path.is_file():
        from run_store import load_workspace_run_index
        index = load_workspace_run_index(workspace_root)
        for entry in index["runs"].values():
            if entry.get("chat_id") != chat_id:
                continue
            indexed_run_ids.add(entry["run_id"])
            thread = load_audit_thread(workspace_root, workspace_id, chat_id, entry["run_id"])
            if thread is not None:
                threads.append(thread)
    for path in sorted(audit_dir.glob("*.json"), key=lambda item: item.name):
        if path.stem in indexed_run_ids:
            continue
        thread = load_audit_thread(workspace_root, workspace_id, chat_id, path.stem)
        if thread is not None:
            threads.append(thread)
    return threads


def list_chat_audit_summaries(
    workspace_root: str | Path, workspace_id: str, chat_id: str,
) -> list[dict]:
    """Lightweight v2 summaries only; never parses legacy full JSON files."""
    from run_store import load_workspace_run_index
    index = load_workspace_run_index(workspace_root)
    result = []
    for entry in index["runs"].values():
        if entry.get("chat_id") != chat_id:
            continue
        summary = load_run_summary(workspace_root, entry["run_id"], chat_id)
        if summary is not None and summary.get("workspace_id") == workspace_id:
            result.append(summary)
    return result


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
        raw_task: str | None = None,
    ) -> None:
        self.workspace_root = Path(workspace_root).resolve()
        self.workspace_id = _safe_identifier(workspace_id, "workspace_id")
        self.chat_id = chat_id
        self.run_id = run_id
        original_task_block_id = task_block_id
        if task_block_id is None:
            seed = f"{self.workspace_id}:{chat_id or 'direct'}:{run_id}".encode("utf-8")
            task_block_id = "tb_" + hashlib.md5(seed).hexdigest()
        self._store_task_block_id = validate_task_block_id(task_block_id)
        self.task_block_id = (
            validate_task_block_id(original_task_block_id)
            if original_task_block_id is not None else None
        )
        self.path = run_component_path(
            self.workspace_root, run_id, "summary.json"
        ) if get_run_index_entry(self.workspace_root, run_id) else None
        create_run_summary(
            self.workspace_root, self.workspace_id, chat_id, self._store_task_block_id, run_id,
        )
        if self.task_block_id is None:
            update_run_summary_index(
                self.workspace_root, run_id, {"task_block_id": None},
            )
        self.path = run_component_path(self.workspace_root, run_id, "summary.json")
        task_entry = get_task_index_entry(self.workspace_root, self._store_task_block_id) or {}
        task_payload = {"schema_version": 2, "workspace_id": self.workspace_id,
                        "chat_id": chat_id, "task_block_id": self.task_block_id,
                        "task_display_id": task_entry.get("display_id"),
                        "raw_task": raw_task}
        _save_audit_thread(run_component_path(self.workspace_root, run_id, "task.json"), task_payload)
        self.thread = self._empty_legacy_thread()
        self._previous_executor_messages = None

    def _empty_legacy_thread(self) -> dict:
        return {
            "schema_version": 1,
            "workspace_id": self.workspace_id,
            "chat_id": self.chat_id,
            "task_block_id": self.task_block_id,
            "run_id": self.run_id,
            "issues": [],
            "final_audit": "PENDING",
            "run_status": "RUNNING",
        }

    def _source_for_event(self, event: dict) -> str:
        kind = str(event.get("event") or "")
        if kind in EXECUTOR_DIAGNOSTIC_EVENTS:
            return "EXECUTOR"
        if kind in PLANNER_DREDD_EVENTS:
            return "DREDD"
        if kind in PLANNER_OWNED_EVENTS:
            return "PLANNER"
        if kind.startswith("final_audit_") or kind.startswith("audit_diagnostic_"):
            return "DREDD"
        return "SERVER"

    @staticmethod
    def _context_delta(previous: list[dict], current: list[dict], api_number: int,
                       stage_id: object) -> dict:
        common = 0
        limit = min(len(previous), len(current))
        while common < limit and previous[common] == current[common]:
            common += 1
        return {"kind": "context_delta", "api_request_number": api_number,
                "stage_id": stage_id, "previous_message_count": len(previous),
                "message_count": len(current), "common_prefix": common,
                "removed_suffix_count": len(previous) - common,
                "added_messages": copy.deepcopy(current[common:])}

    def _persist_event(self, event: dict) -> None:
        kind = event["event"]
        source = self._source_for_event(event)
        payload = {key: copy.deepcopy(value) for key, value in event.items()
                   if key not in {"event", "timestamp", "run_id"}}
        if kind == "executor_diagnostic_context" and isinstance(payload.get("messages"), list):
            messages = payload.pop("messages")
            api_number = int(payload.get("api_request_number") or 1)
            if self._previous_executor_messages is None:
                base = {"schema_version": 2, "run_id": self.run_id,
                        "api_request_number": api_number,
                        "model_id": payload.get("model_id"),
                        "provider_model_id": payload.get("provider_model_id"),
                        "base_context_hash": __import__("hashlib").sha256(
                            json.dumps(messages, ensure_ascii=False,
                                       separators=(",", ":")).encode("utf-8")
                        ).hexdigest(), "messages": copy.deepcopy(messages)}
                _save_audit_thread(
                    run_component_path(self.workspace_root, self.run_id, "executor_base.json"), base,
                )
                payload["context_base"] = {key: value for key, value in base.items()
                                           if key != "messages"}
            else:
                payload["context_delta"] = self._context_delta(
                    self._previous_executor_messages, messages, api_number,
                    payload.get("stage_id"),
                )
            self._previous_executor_messages = copy.deepcopy(messages)
        append_run_record(
            self.workspace_root, self.run_id, source=source, event=kind,
            payload=payload, timestamp=float(event.get("timestamp") or 0.0),
        )
        summary = load_run_summary(self.workspace_root, self.run_id) or {}
        changed = False
        if kind == "api_request":
            summary["api_requests"] = max(int(summary.get("api_requests") or 0),
                                          int(event.get("api_request_number") or 0))
            changed = True
        if kind == "tool_started":
            summary["tool_calls"] = max(int(summary.get("tool_calls") or 0),
                                        int(event.get("tool_sequence") or 0))
            changed = True
        if kind == "final_audit_passed":
            summary["final_audit"] = "PASS"; changed = True
        elif kind == "final_audit_failed":
            summary["final_audit"] = "FAIL"; changed = True
        elif kind == "final_audit_error":
            summary["final_audit"] = "ERROR"; changed = True
        elif kind == "final_audit_skipped":
            summary["final_audit"] = "DISABLED"; changed = True
        if kind == "run_failed":
            summary["run_status"] = "FAILED"
            if summary.get("final_audit") == "PENDING":
                summary["final_audit"] = "NOT_RUN"
            changed = True
        elif kind == "run_finished":
            summary["run_status"] = event.get("status") or "FINISHED"; changed = True
        usage = event.get("usage")
        if kind == "executor_diagnostic_response":
            record_usage(summary, "executor", usage); changed = True
        elif kind == "planner_diagnostic_response":
            record_usage(summary, "planner", usage); changed = True
        elif source == "DREDD" and kind in {
            "planner_dredd_review_completed", "final_audit_passed", "final_audit_failed",
        }:
            record_usage(summary, "dredd", usage); changed = True
        if changed:
            update_run_summary_index(self.workspace_root, self.run_id, summary)

    def observe(self, event: dict, *, persist: bool = True) -> None:
        kind = event.get("event")
        if kind not in _AUDIT_EVENTS:
            return
        if persist:
            self._persist_event(event)
        issues = self.thread["issues"]
        if kind in EXECUTOR_DIAGNOSTIC_EVENTS:
            diagnostic_kind = kind.removeprefix(
                "executor_diagnostic_"
            )

            fields = {
                "context": (
                    "api_request_number",
                    "plan_id",
                    "plan_version",
                    "stage_id",
                    "model_id",
                    "provider_model_id",
                    "function_call_mode",
                    "message_count",
                    "messages",
                    "request_message_chars",
                    "request_functions_chars",
                    "request_total_chars",
                ),
                "response": (
                    "api_request_number",
                    "plan_id",
                    "plan_version",
                    "stage_id",
                    "finish_reason",
                    "message",
                    "usage",
                    "request_message_chars",
                    "request_functions_chars",
                    "request_total_chars",
                ),
                "reset": (
                    "plan_id",
                    "plan_version",
                    "stage_id",
                    "messages_before",
                    "messages_after",
                    "removed_messages",
                    "removed_function_messages",
                    "removed_assistant_function_calls",
                ),
            }[diagnostic_kind]

            recorded = {
                "kind": diagnostic_kind,
            }

            for key in fields:
                if key in event:
                    recorded[key] = event[key]

            diagnostics = self.thread.setdefault(
                "executor_diagnostics",
                [],
            )
            diagnostics.append(recorded)
            del diagnostics[:-64]

        elif kind in PLANNER_DIAGNOSTIC_EVENTS:
            diagnostic_kind = kind.removeprefix("planner_diagnostic_")
            fields = {
                "request": (
                    "mode", "planner_model_id", "provider_model_id",
                    "temperature", "max_tokens", "function_call",
                ),
                "context": ("mode", "system", "user"),
                "response": (
                    "mode", "finish_reason", "content", "function_call", "usage",
                ),
                "error": ("mode", "error_type", "error_message"),
            }[diagnostic_kind]
            recorded = {"kind": diagnostic_kind}
            for key in fields:
                if key in event:
                    recorded[key] = event[key]
            diagnostics = self.thread.setdefault("planner_diagnostics", [])
            diagnostics.append(recorded)
            del diagnostics[:-64]
        elif kind in PLANNER_EVENTS:
            if kind == "planner_session_started":
                self.thread["planner_session"] = {
                    "session_id": _short(event.get("session_id")),
                    "status": "ACTIVE",
                    "messages": [],
                }
            elif kind == "planner_session_message":
                session = self.thread.setdefault("planner_session", {
                    "session_id": _short(event.get("session_id")),
                    "status": "ACTIVE", "messages": [],
                })
                message = {
                    key: event[key]
                    for key in ("mode", "speaker", "attempt", "model_id",
                                "model_display_name", "provider_model_id")
                    if event.get(key) is not None
                }
                message["text"] = str(event.get("text") or "")[:_PLANNER_SESSION_TEXT_LIMIT]
                session["messages"].append(message)
                del session["messages"][:-32]
            elif kind == "planner_dredd_review_completed":
                session = self.thread.setdefault("planner_session", {
                    "session_id": _short(event.get("session_id")),
                    "status": "ACTIVE", "messages": [],
                })
                session["dredd_review"] = {
                    key: (_short(event[key]) if isinstance(event[key], str) else event[key])
                    for key in ("verifier_run_id", "model_id", "model_display_name",
                                "provider_model_id", "mode", "diagnosis", "required_action")
                    if event.get(key) is not None
                }
            elif kind in {"planner_session_completed", "planner_session_blocked"}:
                session = self.thread.setdefault("planner_session", {
                    "session_id": _short(event.get("session_id")),
                    "messages": [],
                })
                session["status"] = "VALID" if kind == "planner_session_completed" else "BLOCKED"
            lifecycle = self.thread.setdefault("task_lifecycle", {"events": []})
            for key in ("plan_id", "plan_version", "stage_id"):
                if event.get(key) is not None:
                    lifecycle[key] = event[key]
            recorded = {"event": kind, **{
                key: (_short(event[key]) if isinstance(event[key], str) else event[key])
                for key in ("plan_version", "stage_id", "mode", "status", "reason", "reason_code", "path", "function", "executed", "outcome", "attempt", "route", "session_id", "speaker", "error_type", "error_message")
                if key in event and isinstance(event[key], (str, int, bool))}}
            if kind == "planner_failed":
                if isinstance(event.get("error_type"), str):
                    recorded["error_type"] = _short(event["error_type"])
                if event.get("error_type") == "PlannerError" and isinstance(event.get("error_message"), str):
                    recorded["error_message"] = _short(event["error_message"])
            lifecycle["events"].append(recorded)
            del lifecycle["events"][:-128]
        elif kind.startswith("permission_"):
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
        elif kind == "final_audit_skipped":
            self.thread["final_audit"] = "DISABLED"
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
            if event.get("status") == "BLOCKED" and self.thread["final_audit"] == "PENDING":
                self.thread["final_audit"] = "NOT_RUN"
