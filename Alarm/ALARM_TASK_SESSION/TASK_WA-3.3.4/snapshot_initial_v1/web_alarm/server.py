"""Local typed HTTP API for Web Alarm Workspace WA-2.1.

This layer exposes WA-1 state operations over loopback HTTP. It does not own
state-transition policy yet (WA-2.2) and does not perform hidden mutations of
the registered real Workspace.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, is_dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit

from .context_pack import EntryContextPackBuilder
from .event_checkpoint_store import EventCheckpointStore, EventCheckpointStoreError
from .manifest_store import ManifestSnapshotStore, ManifestStoreError
from .models import SCHEMA_VERSION, record_to_dict
from .operation_store import (
    OperationConflictError,
    OperationStore,
    OperationStoreError,
    OperationTransitionError,
)
from .reconciliation import ReconciliationEvidenceError
from .reconciliation_service import ReconciliationService
from .state_machine import (
    ServerStateMachine,
    ServerStateMachineError,
    TransitionRejected,
)
from .task_store import TaskStore, TaskStoreError
from .ui import INDEX_HTML
from .workspace_registry import (
    WorkspaceRegistry,
    WorkspaceRegistryError,
)

API_VERSION = 1
MAX_REQUEST_BYTES = 1024 * 1024
LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}


class ApiError(RuntimeError):
    """Typed API error translated to a JSON HTTP response."""

    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        *,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status = int(status)
        self.code = code
        self.message = message
        self.details = dict(details or {})


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return record_to_dict(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _require_object(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ApiError(400, "invalid_body", "request body must be a JSON object")
    return value


def _require_text(body: Mapping[str, Any], key: str) -> str:
    value = body.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ApiError(400, "invalid_field", f"{key} must be a non-empty string")
    return value.strip()


def _optional_text(body: Mapping[str, Any], key: str) -> str | None:
    value = body.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ApiError(400, "invalid_field", f"{key} must be a non-empty string")
    return value.strip()


def _require_string_list(body: Mapping[str, Any], key: str) -> list[str]:
    value = body.get(key)
    if not isinstance(value, list) or not value:
        raise ApiError(400, "invalid_field", f"{key} must be a non-empty array")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ApiError(400, "invalid_field", f"{key} must contain only non-empty strings")
        result.append(item.strip())
    return result


class WebAlarmApi:
    """Narrow typed API façade over the verified WA-1 storage layer."""

    def __init__(self, storage_root: str | Path | None = None) -> None:
        self.registry = WorkspaceRegistry(storage_root)
        self.tasks = TaskStore(storage_root)
        self.manifests = ManifestSnapshotStore(storage_root)
        self.state = EventCheckpointStore(storage_root)
        self.machine = ServerStateMachine(storage_root)
        self.context_pack = EntryContextPackBuilder(storage_root)
        self.operations = OperationStore(storage_root)
        self.reconciliation = ReconciliationService(storage_root)

    @property
    def storage_root(self) -> Path:
        return self.tasks.storage_root

    def _task_bundle(self, task_id: str) -> dict[str, Any]:
        task = self.tasks.open_task(task_id)
        plan = self.tasks.open_plan(task_id)
        microtasks = self.tasks.list_microtasks(task_id)
        checkpoint = None
        try:
            checkpoint = self.state.read_checkpoint(task_id)
        except EventCheckpointStoreError as exc:
            if "checkpoint is missing" not in str(exc):
                raise
        return {
            "task": record_to_dict(task),
            "plan": record_to_dict(plan),
            "microtasks": [record_to_dict(item) for item in microtasks],
            "checkpoint": record_to_dict(checkpoint) if checkpoint is not None else None,
        }

    def _ui_task_view(self, task_id: str) -> dict[str, Any]:
        bundle = self._task_bundle(task_id)
        task = self.tasks.open_task(task_id)
        workspace = self.registry.get(task.workspace_id)
        plan = self.tasks.open_plan(task_id)
        checkpoint = bundle["checkpoint"]
        current_id = (
            checkpoint["current_microtask_id"]
            if checkpoint is not None
            else plan.current_microtask_id
        )
        if current_id is None:
            for micro in self.tasks.list_microtasks(task_id):
                if micro.status.value != "VERIFIED":
                    current_id = micro.microtask_id
                    break

        manifest_view: dict[str, Any] | None = None
        if current_id is not None:
            try:
                manifest = self.manifests.open_manifest(task_id, current_id)
                manifest_view = {
                    "record": record_to_dict(manifest),
                    "entries": [
                        record_to_dict(item)
                        for item in self.manifests.list_entries(task_id, current_id)
                    ],
                    "snapshots": [
                        record_to_dict(item)
                        for item in self.manifests.list_snapshots(task_id, current_id)
                    ],
                }
            except ManifestStoreError as exc:
                manifest_view = {"available": False, "reason": str(exc)}

        events = self.state.read_events(task_id)
        reports = [
            record_to_dict(item)
            for item in events
            if item.event_type == "REPORT"
        ]
        current_status = (
            checkpoint["current_status"]
            if checkpoint is not None
            else (
                self.tasks.open_microtask(task_id, current_id).status.value
                if current_id is not None
                else "NO_MICROTASK"
            )
        )
        recovery_states = {
            "BLOCKED_PREPARE",
            "UNKNOWN_AFTER_DISCONNECT",
            "RECOVERY_REQUIRED",
            "FAILED_VERIFICATION",
        }
        recovery_state = (
            current_status if current_status in recovery_states else "NORMAL"
        )
        if checkpoint is not None:
            next_action = checkpoint["next_safe_action"]
            snapshot_status = checkpoint["snapshot_status"]
        elif current_id is not None:
            next_action = self.machine.next_safe_action(task_id, current_id)
            snapshot_status = (
                "VERIFIED"
                if manifest_view
                and manifest_view.get("record", {}).get("status") == "VERIFIED"
                else "NOT_PREPARED"
            )
        else:
            next_action = "create a microtask and define the TASK plan"
            snapshot_status = "NOT_PREPARED"

        return {
            "workspace": record_to_dict(workspace),
            "task_state": bundle,
            "current_microtask_id": current_id,
            "manifest": manifest_view,
            "reports": reports,
            "recent_events": [record_to_dict(item) for item in events[-20:]],
            "recovery_state": recovery_state,
            "snapshot_status": snapshot_status,
            "next_safe_action": next_action,
        }

    def _list_tasks(self) -> dict[str, list[dict[str, Any]]]:
        result: dict[str, list[dict[str, Any]]] = {"active": [], "completed": []}
        for label, directory in (
            ("active", self.tasks.active_dir),
            ("completed", self.tasks.completed_dir),
        ):
            for path in sorted(directory.iterdir()):
                if not path.is_dir():
                    continue
                try:
                    result[label].append(record_to_dict(self.tasks.open_task(path.name)))
                except TaskStoreError as exc:
                    raise ApiError(
                        409,
                        "invalid_persisted_state",
                        f"cannot load TASK {path.name}",
                        details={"reason": str(exc)},
                    ) from exc
        return result
    def dispatch(
        self,
        method: str,
        raw_path: str,
        body: Any = None,
    ) -> tuple[int, dict[str, Any]]:
        method = method.upper()
        path = urlsplit(raw_path).path
        parts = [part for part in path.split("/") if part]

        try:
            if method == "GET" and parts == ["status"]:
                return 200, {
                    "service": "web_alarm_server",
                    "status": "ok",
                    "api_version": API_VERSION,
                    "schema_version": SCHEMA_VERSION,
                    "storage_root": str(self.storage_root),
                    "mode": "server_owned_state_machine",
                    "loopback_default": True,
                    "capabilities": [
                        "workspaces",
                        "tasks",
                        "plans",
                        "microtasks",
                        "prepare_restore_point",
                        "verify_snapshot",
                        "transition",
                        "operations",
                        "reconciliation",
                        "reports",
                        "recovery_entry",
                    ],
                }

            if parts == ["workspaces"]:
                if method == "GET":
                    return 200, {
                        "workspaces": [
                            record_to_dict(item) for item in self.registry.list()
                        ]
                    }
                if method == "POST":
                    data = _require_object(body)
                    record = self.registry.register(
                        _require_text(data, "display_name"),
                        _require_text(data, "workspace_root"),
                        workspace_id=_optional_text(data, "workspace_id"),
                    )
                    return 201, {"workspace": record_to_dict(record)}
                raise ApiError(405, "method_not_allowed", "unsupported method for /workspaces")

            if parts == ["tasks"]:
                if method == "GET":
                    return 200, self._list_tasks()
                if method == "POST":
                    data = _require_object(body)
                    workspace_id = _require_text(data, "workspace_id")
                    self.registry.get(workspace_id)
                    task = self.tasks.create_task(
                        workspace_id,
                        _require_text(data, "title"),
                        _require_text(data, "raw_task"),
                        _require_text(data, "goal"),
                        task_id=_optional_text(data, "task_id"),
                    )
                    return 201, {"task": record_to_dict(task)}
                raise ApiError(405, "method_not_allowed", "unsupported method for /tasks")

            if len(parts) == 2 and parts[0] == "tasks":
                task_id = parts[1]
                if method == "GET":
                    return 200, self._task_bundle(task_id)
                raise ApiError(405, "method_not_allowed", "TASK endpoint is read-only")

            if len(parts) == 3 and parts[0] == "tasks" and parts[2] == "ui":
                if method != "GET":
                    raise ApiError(405, "method_not_allowed", "UI task view is read-only")
                return 200, self._ui_task_view(parts[1])

            if len(parts) == 3 and parts[0] == "tasks" and parts[2] == "context":
                if method != "GET":
                    raise ApiError(405, "method_not_allowed", "Entry Context Pack is read-only")
                return 200, self.context_pack.build(parts[1])

            if len(parts) == 3 and parts[0] == "tasks" and parts[2] == "reconcile":
                if method != "POST":
                    raise ApiError(
                        405,
                        "method_not_allowed",
                        "reconciliation calculation requires POST but performs no mutation",
                    )
                data = _require_object(body)
                expected_post_state = data.get("expected_post_state")
                if expected_post_state is not None and not isinstance(
                    expected_post_state, dict
                ):
                    raise ApiError(
                        400,
                        "invalid_field",
                        "expected_post_state must be an object when provided",
                    )
                result = self.reconciliation.reconcile(
                    parts[1],
                    _require_text(data, "microtask_id"),
                    _require_text(data, "operation_id"),
                    expected_post_state=expected_post_state,
                )
                return 200, result

            if len(parts) == 3 and parts[0] == "tasks" and parts[2] == "plan":
                if method != "POST":
                    raise ApiError(405, "method_not_allowed", "plan endpoint requires POST")
                data = _require_object(body)
                plan = self.tasks.set_plan(
                    parts[1],
                    _require_string_list(data, "microtask_ids"),
                )
                return 200, {"plan": record_to_dict(plan)}

            if len(parts) == 3 and parts[0] == "tasks" and parts[2] == "microtasks":
                if method != "POST":
                    raise ApiError(405, "method_not_allowed", "microtasks endpoint requires POST")
                data = _require_object(body)
                microtask = self.tasks.create_microtask(
                    parts[1],
                    _require_text(data, "title"),
                    _require_text(data, "goal"),
                    microtask_id=_optional_text(data, "microtask_id"),
                )
                return 201, {"microtask": record_to_dict(microtask)}

            if len(parts) == 3 and parts[0] == "tasks" and parts[2] == "operations":
                task_id = parts[1]
                if method == "GET":
                    return 200, {
                        "operations": [
                            record_to_dict(item)
                            for item in self.operations.list(task_id)
                        ]
                    }
                if method == "POST":
                    data = _require_object(body)
                    result = self.operations.begin(
                        task_id,
                        _require_text(data, "microtask_id"),
                        _require_text(data, "action"),
                        _require_text(data, "target"),
                        operation_id=_optional_text(data, "operation_id"),
                        expected_precondition_sha256=_optional_text(
                            data, "expected_precondition_sha256"
                        ),
                        request_payload=data.get("request"),
                    )
                    return (201 if result["created"] else 200), _jsonable(result)
                raise ApiError(
                    405,
                    "method_not_allowed",
                    "operations collection supports GET and POST",
                )

            if (
                len(parts) == 4
                and parts[0] == "tasks"
                and parts[2] == "operations"
            ):
                if method != "GET":
                    raise ApiError(
                        405,
                        "method_not_allowed",
                        "operation record endpoint is read-only",
                    )
                record = self.operations.get(parts[1], parts[3])
                return 200, {
                    "operation": record_to_dict(record),
                    "replay_decision": self.operations.replay_decision(record.status),
                }

            if (
                len(parts) == 5
                and parts[0] == "tasks"
                and parts[2] == "operations"
                and parts[4] == "transition"
            ):
                if method != "POST":
                    raise ApiError(
                        405,
                        "method_not_allowed",
                        "operation transition endpoint requires POST",
                    )
                data = _require_object(body)
                result = self.operations.transition(
                    parts[1],
                    parts[3],
                    _require_text(data, "target_status"),
                    result_summary=_optional_text(data, "result_summary"),
                )
                return 200, _jsonable(result)

            if len(parts) == 3 and parts[0] == "microtasks" and parts[2] == "prepare":
                if method != "POST":
                    raise ApiError(405, "method_not_allowed", "prepare endpoint requires POST")
                data = _require_object(body)
                task_id = _require_text(data, "task_id")
                raw_targets = data.get("targets")
                if not isinstance(raw_targets, list) or not raw_targets:
                    raise ApiError(400, "invalid_field", "targets must be a non-empty array")
                targets: list[tuple[str, str]] = []
                for index, item in enumerate(raw_targets):
                    if not isinstance(item, dict):
                        raise ApiError(400, "invalid_field", f"targets[{index}] must be an object")
                    targets.append(
                        (
                            _require_text(item, "path"),
                            _require_text(item, "expected_change"),
                        )
                    )
                result = self.machine.prepare_microtask(
                    task_id,
                    parts[1],
                    targets,
                    operation_id=_optional_text(data, "operation_id"),
                )
                return 200, _jsonable(result)

            if len(parts) == 3 and parts[0] == "microtasks" and parts[2] == "snapshot":
                if method != "POST":
                    raise ApiError(405, "method_not_allowed", "snapshot endpoint requires POST")
                data = _require_object(body)
                task_id = _require_text(data, "task_id")
                action = data.get("action", "verify")
                if action != "verify":
                    raise ApiError(
                        409,
                        "real_workspace_mutation_not_exposed",
                        "WA-2.1 Server API exposes snapshot verification only; restore remains an explicit WA-1 CLI action",
                    )
                result = self.machine.verify_snapshot(
                    task_id,
                    parts[1],
                    operation_id=_optional_text(data, "operation_id"),
                )
                return 200, _jsonable(result)

            if len(parts) == 3 and parts[0] == "microtasks" and parts[2] == "transition":
                if method != "POST":
                    raise ApiError(405, "method_not_allowed", "transition endpoint requires POST")
                data = _require_object(body)
                task_id = _require_text(data, "task_id")
                result = self.machine.transition(
                    task_id,
                    parts[1],
                    _require_text(data, "target_status"),
                    verification_evidence=_optional_text(data, "verification_evidence"),
                    operation_id=_optional_text(data, "operation_id"),
                )
                return 200, _jsonable(result)

            if len(parts) == 3 and parts[0] == "microtasks" and parts[2] == "report":
                if method != "POST":
                    raise ApiError(405, "method_not_allowed", "report endpoint requires POST")
                data = _require_object(body)
                task_id = _require_text(data, "task_id")
                report = _require_text(data, "report")
                event = self.state.append_event(
                    task_id,
                    "REPORT",
                    microtask_id=parts[1],
                    operation_id=_optional_text(data, "operation_id"),
                    payload={"report": report},
                )
                return 201, {"event": record_to_dict(event)}

            if len(parts) == 3 and parts[0] == "tasks" and parts[2] == "recover":
                if method != "POST":
                    raise ApiError(405, "method_not_allowed", "recover endpoint requires POST")
                task_id = parts[1]
                bundle = self._task_bundle(task_id)
                events = self.state.read_events(task_id)
                checkpoint = bundle["checkpoint"]
                return 200, {
                    "mode": "advisory_only",
                    "mutation_performed": False,
                    "recovery_engine": "WA-3_NOT_IMPLEMENTED",
                    "task_state": bundle,
                    "recent_events": [
                        record_to_dict(item) for item in events[-20:]
                    ],
                    "next_safe_action": (
                        checkpoint["next_safe_action"]
                        if checkpoint is not None
                        else "create or refresh checkpoint before recovery decisions"
                    ),
                }

            raise ApiError(404, "not_found", f"unknown endpoint: {path}")

        except ApiError:
            raise
        except TransitionRejected as exc:
            raise ApiError(
                409,
                "transition_rejected",
                str(exc),
                details={
                    "current_status": exc.current_status.value,
                    "requested_status": exc.requested_status.value,
                    "reason": exc.reason,
                    "next_safe_action": exc.next_safe_action,
                },
            ) from exc
        except ServerStateMachineError as exc:
            raise ApiError(409, "state_machine_error", str(exc)) from exc
        except OperationConflictError as exc:
            raise ApiError(409, "operation_replay_conflict", str(exc)) from exc
        except OperationTransitionError as exc:
            raise ApiError(409, "operation_transition_rejected", str(exc)) from exc
        except ReconciliationEvidenceError as exc:
            raise ApiError(409, "reconciliation_evidence_error", str(exc)) from exc
        except OperationStoreError as exc:
            message = str(exc)
            status = 404 if "unknown operation_id" in message else 409
            raise ApiError(status, "operation_state_error", message) from exc
        except (WorkspaceRegistryError, TaskStoreError, ManifestStoreError) as exc:
            message = str(exc)
            status = 404 if "unknown " in message or "missing:" in message else 409
            raise ApiError(status, "state_error", message) from exc
        except EventCheckpointStoreError as exc:
            message = str(exc)
            status = 404 if "missing:" in message else 409
            raise ApiError(status, "state_error", message) from exc
        except ValueError as exc:
            raise ApiError(400, "invalid_value", str(exc)) from exc
class _JsonHandler(BaseHTTPRequestHandler):
    server_version = "WebAlarmHTTP/1"

    @property
    def api(self) -> WebAlarmApi:
        return self.server.web_alarm_api  # type: ignore[attr-defined]

    def _read_body(self) -> Any:
        length_raw = self.headers.get("Content-Length")
        if not length_raw:
            return {}
        try:
            length = int(length_raw)
        except ValueError as exc:
            raise ApiError(400, "invalid_content_length", "Content-Length must be an integer") from exc
        if length < 0 or length > MAX_REQUEST_BYTES:
            raise ApiError(413, "request_too_large", "request body is too large")
        raw = self.rfile.read(length)
        if not raw:
            return {}
        content_type = self.headers.get("Content-Type", "")
        if "application/json" not in content_type.lower():
            raise ApiError(415, "unsupported_media_type", "Content-Type must be application/json")
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ApiError(400, "invalid_json", "request body is not valid UTF-8 JSON") from exc

    def _send_json(self, status: int, payload: Mapping[str, Any]) -> None:
        raw = json.dumps(_jsonable(dict(payload)), ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _send_html(self, html: str) -> None:
        raw = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _run(self) -> None:
        try:
            path = urlsplit(self.path).path
            if self.command == "GET" and path in {"/", "/ui"}:
                self._send_html(INDEX_HTML)
                return
            body = self._read_body() if self.command in {"POST", "PUT", "PATCH"} else None
            status, payload = self.api.dispatch(self.command, self.path, body)
            self._send_json(status, payload)
        except ApiError as exc:
            self._send_json(
                exc.status,
                {
                    "error": {
                        "code": exc.code,
                        "message": exc.message,
                        "details": exc.details,
                    }
                },
            )
        except Exception as exc:  # defensive boundary; no traceback over HTTP
            self._send_json(
                500,
                {
                    "error": {
                        "code": "internal_error",
                        "message": "internal server error",
                    }
                },
            )
            print(f"Web Alarm server internal error: {exc}", file=sys.stderr)

    def do_GET(self) -> None:
        self._run()

    def do_POST(self) -> None:
        self._run()

    def do_PUT(self) -> None:
        self._run()

    def do_PATCH(self) -> None:
        self._run()

    def do_DELETE(self) -> None:
        self._run()

    def log_message(self, format: str, *args: Any) -> None:
        return


def create_server(
    api: WebAlarmApi,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    allow_non_loopback: bool = False,
) -> ThreadingHTTPServer:
    if not allow_non_loopback and host not in LOOPBACK_HOSTS:
        raise ValueError(
            "non-loopback bind is disabled by default; use allow_non_loopback=True explicitly"
        )

    class Handler(_JsonHandler):
        pass

    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    server.web_alarm_api = api  # type: ignore[attr-defined]
    return server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="webalarm-server")
    parser.add_argument("--storage-root")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--allow-non-loopback", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    api = WebAlarmApi(args.storage_root)
    try:
        server = create_server(
            api,
            host=args.host,
            port=args.port,
            allow_non_loopback=args.allow_non_loopback,
        )
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    host, port = server.server_address[:2]
    print(f"Web Alarm Server listening on http://{host}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
