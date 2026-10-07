"""Persistent replay-safe operation identity for Web Alarm Workspace WA-3.2.

RC-1: every new operation persists a self-contained Operation Contract v2
(``operation_contract``); legacy v1 records stay readable and are never
rewritten into v2 shape. Record writes of one TASK are serialized across
processes. The store still never executes project mutations: it only observes
target bytes (pre-state at INTENT, receipt at DONE).
"""

from __future__ import annotations

import json
import os
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .event_checkpoint_store import EventCheckpointStore, EventCheckpointStoreError
from .file_state import FileStateError, authority_of, observe_path
from .models import (
    SCHEMA_VERSION,
    OperationRecord,
    OperationStatus,
    new_id,
    utc_now_iso,
)
from .operation_contract import (
    LEGACY_CONTRACT_VERSION,
    OPERATION_CONTRACT_VERSION,
    ContractRequest,
    OperationContractError,
    OperationScopeError,
    assess,
    finalize_contract,
    fingerprint_v1,
    make_receipt,
    prepare_request,
    record_for_storage,
    validate_record,
)
from .payload_store import (
    PayloadIntegrityError,
    PayloadScopeError,
    PayloadStore,
    PayloadStoreError,
)
from .storage_policy import MAX_PAYLOAD_BYTES, secret_pattern_for
from .store_lock import DEFAULT_LOCK_TIMEOUT_SECONDS, InterProcessLock, StoreLockTimeout
from .target_identity import TargetIdentityError, canonical_target
from .task_store import TaskStore, TaskStoreError
from .workspace_registry import WorkspaceRegistry, WorkspaceRegistryError


class OperationStoreError(RuntimeError):
    """Raised when operation state is missing, invalid, or unsafe."""


class OperationConflictError(OperationStoreError):
    """Same operation_id was replayed with a different immutable request."""


class OperationTransitionError(OperationStoreError):
    """Requested operation lifecycle transition is not allowed."""


class OperationContractRejected(OperationStoreError):
    """A new operation request violates the durable operation contract."""


class OperationScopeRejected(OperationContractRejected):
    """Target or payload is outside the secret, size or storage scope."""


class OperationReceiptMismatch(OperationTransitionError):
    """Server-observed DONE state contradicts the contracted post-state."""


class OperationPayloadIntegrityError(OperationStoreError):
    """Stored payload bytes do not match the contract payload reference."""


def _safe_component(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OperationStoreError(f"{name} must be a non-empty string")
    value = value.strip()
    if Path(value).name != value or "/" in value or "\\" in value:
        raise OperationStoreError(f"{name} must not contain path separators")
    return value


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.parent / f".{path.name}.{new_id('tmp')}.tmp"
    raw = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    try:
        with temp.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    except OSError as exc:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass
        raise OperationStoreError(f"cannot persist operation record: {path}") from exc


def _persist_record(path: Path, record: OperationRecord) -> None:
    try:
        validate_record(record)
    except OperationContractError as exc:
        raise OperationStoreError(f"refusing to persist invalid operation record: {exc}") from exc
    _atomic_write_json(path, record_for_storage(record))


class OperationStore:
    """Disk-backed operation identity and lifecycle; it never executes mutations."""

    _ALLOWED: dict[OperationStatus, set[OperationStatus]] = {
        OperationStatus.INTENT: {
            OperationStatus.STARTED,
            OperationStatus.FAILED,
            OperationStatus.UNKNOWN_AFTER_DISCONNECT,
        },
        OperationStatus.STARTED: {
            OperationStatus.DONE,
            OperationStatus.FAILED,
            OperationStatus.UNKNOWN_AFTER_DISCONNECT,
        },
        OperationStatus.DONE: {
            OperationStatus.VERIFIED,
            OperationStatus.FAILED,
        },
        OperationStatus.VERIFIED: set(),
        OperationStatus.FAILED: set(),
        OperationStatus.UNKNOWN_AFTER_DISCONNECT: set(),
    }

    def __init__(
        self,
        storage_root: str | Path | None = None,
        *,
        lock_timeout: float = DEFAULT_LOCK_TIMEOUT_SECONDS,
        max_payload_bytes: int = MAX_PAYLOAD_BYTES,
    ) -> None:
        self.tasks = TaskStore(storage_root)
        self.events = EventCheckpointStore(self.tasks.storage_root)
        self.registry = WorkspaceRegistry(self.tasks.storage_root)
        self.payloads = PayloadStore(self.tasks.storage_root, max_bytes=max_payload_bytes)
        self.max_payload_bytes = max_payload_bytes
        self.lock_timeout = lock_timeout
        self._lock = threading.RLock()

    @contextmanager
    def _serialized(self, task_id: str) -> Iterator[None]:
        """Serialize read-check-write of one TASK's operations across processes."""
        lock = InterProcessLock(
            self.tasks.storage_root / "locks" / "operations" / f"{task_id}.lock",
            timeout=self.lock_timeout,
        )
        with self._lock:
            try:
                lock.acquire()
            except StoreLockTimeout as exc:
                raise OperationStoreError(str(exc)) from exc
            try:
                yield
            finally:
                lock.release()

    def task_lock(self, task_id: str):
        """Public TASK lock for components that must not interleave with
        operation writes (RC-2 Resolver). Not re-entrant across instances:
        never call begin/transition while holding it."""
        return self._serialized(task_id)

    def _operations_dir(
        self,
        task_id: str,
        *,
        active_only: bool = False,
        create: bool = False,
    ) -> Path:
        task_dir = self.tasks.task_directory(task_id, active_only=active_only)
        path = task_dir / "operations"
        if create:
            path.mkdir(parents=True, exist_ok=True)
        return path

    def _path(
        self,
        task_id: str,
        operation_id: str,
        *,
        active_only: bool = False,
        create_dir: bool = False,
    ) -> Path:
        operation_id = _safe_component("operation_id", operation_id)
        return self._operations_dir(
            task_id,
            active_only=active_only,
            create=create_dir,
        ) / f"{operation_id}.json"

    def _load_path(self, path: Path, task_id: str, operation_id: str) -> OperationRecord:
        if not path.is_file():
            raise OperationStoreError(f"unknown operation_id: {operation_id}")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise OperationStoreError(f"cannot read operation record: {path}") from exc
        if not isinstance(raw, dict) or raw.get("schema_version") != SCHEMA_VERSION:
            raise OperationStoreError(f"unsupported or invalid operation schema: {path}")
        try:
            raw["status"] = OperationStatus(raw["status"])
            record = OperationRecord(**raw)
            validate_record(record)
        except (KeyError, TypeError, ValueError) as exc:
            raise OperationStoreError(f"invalid operation record: {path}: {exc}") from exc
        if record.task_id != task_id or record.operation_id != operation_id:
            raise OperationStoreError("operation identity does not match requested record")
        return record

    def get(self, task_id: str, operation_id: str) -> OperationRecord:
        operation_id = _safe_component("operation_id", operation_id)
        path = self._path(task_id, operation_id)
        return self._load_path(path, task_id, operation_id)

    def list(self, task_id: str) -> list[OperationRecord]:
        directory = self._operations_dir(task_id)
        if not directory.is_dir():
            return []
        records: list[OperationRecord] = []
        for path in sorted(directory.glob("*.json"), key=lambda item: item.name):
            operation_id = path.stem
            records.append(self._load_path(path, task_id, operation_id))
        return records

    @staticmethod
    def replay_decision(status: OperationStatus) -> str:
        if status in {
            OperationStatus.STARTED,
            OperationStatus.UNKNOWN_AFTER_DISCONNECT,
        }:
            return "RECONCILE_REQUIRED"
        if status in {
            OperationStatus.DONE,
            OperationStatus.VERIFIED,
            OperationStatus.FAILED,
        }:
            return "RETURN_KNOWN_STATE"
        return "RETURN_EXISTING_INTENT"

    def _touch_checkpoint(self, task_id: str, operation_id: str) -> None:
        """RC-5: refresh an existing checkpoint as a projection (caller holds the TASK lock).

        The operation record is already persistent: a projection failure never
        undoes or fails it. The old checkpoint then simply validates as STALE.
        """
        from .projection import ProjectionError, ProjectionService

        if not (self.tasks.task_directory(task_id) / "checkpoint.json").is_file():
            return
        try:
            ProjectionService(self.tasks.storage_root).rebuild_checkpoint_locked(task_id)
        except (ProjectionError, EventCheckpointStoreError, TaskStoreError, OperationStoreError):
            return

    def _workspace(self, workspace_id: str) -> Path:
        try:
            return Path(self.registry.get(workspace_id).workspace_root)
        except WorkspaceRegistryError as exc:
            raise OperationContractRejected(
                f"operation references unknown workspace_id: {workspace_id}"
            ) from exc

    def _prepare(
        self,
        task_id: str,
        microtask_id: str,
        action: str,
        target: str,
        *,
        expected_precondition_sha256: str | None,
        request_payload: Any,
        expected_pre_state: Any,
        expected_post_state: Any,
        payload: bytes | None,
        agent: str | None,
        channel: str | None,
        allow_secret_target: bool,
    ) -> tuple[str, Path, ContractRequest]:
        workspace_id = self.tasks.open_task(task_id).workspace_id
        workspace_root = self._workspace(workspace_id)
        try:
            canonical = canonical_target(workspace_root, target)
            request = prepare_request(
                task_id=task_id,
                microtask_id=microtask_id,
                action=action,
                target=canonical,
                expected_precondition_sha256=expected_precondition_sha256,
                request_payload=request_payload,
                expected_pre_state=expected_pre_state,
                expected_post_state=expected_post_state,
                payload=payload,
                secret_pattern=secret_pattern_for(canonical.relative),
                allow_secret_target=allow_secret_target,
                agent=agent,
                channel=channel,
                max_payload_bytes=self.max_payload_bytes,
            )
        except OperationScopeError as exc:
            raise OperationScopeRejected(str(exc)) from exc
        except (OperationContractError, TargetIdentityError) as exc:
            raise OperationContractRejected(str(exc)) from exc
        return workspace_id, canonical.workspace_root, request

    def begin(
        self,
        task_id: str,
        microtask_id: str,
        action: str,
        target: str,
        *,
        operation_id: str | None = None,
        expected_precondition_sha256: str | None = None,
        request_payload: Any = None,
        expected_pre_state: Any = None,
        expected_post_state: Any = None,
        payload: bytes | None = None,
        agent: str | None = None,
        channel: str | None = None,
        allow_secret_target: bool = False,
    ) -> dict[str, Any]:
        task_id = _safe_component("task_id", task_id)
        microtask_id = _safe_component("microtask_id", microtask_id)
        action = action.strip() if isinstance(action, str) else ""
        target = target.strip() if isinstance(target, str) else ""
        if not action:
            raise OperationStoreError("action must be a non-empty string")
        if not target:
            raise OperationStoreError("target must be a non-empty string")
        self.tasks.open_microtask(task_id, microtask_id)
        self.tasks.task_directory(task_id, active_only=True)
        chosen_id = _safe_component(
            "operation_id",
            operation_id or new_id("op"),
        )
        prepare_args = dict(
            expected_precondition_sha256=expected_precondition_sha256,
            request_payload=request_payload,
            expected_pre_state=expected_pre_state,
            expected_post_state=expected_post_state,
            payload=payload,
            agent=agent,
            channel=channel,
            allow_secret_target=allow_secret_target,
        )

        with self._serialized(task_id):
            path = self._path(task_id, chosen_id, active_only=True)
            if path.exists():
                existing = self._load_path(path, task_id, chosen_id)
                if existing.contract_version == LEGACY_CONTRACT_VERSION:
                    legacy_fingerprint = fingerprint_v1(
                        task_id=task_id,
                        microtask_id=microtask_id,
                        action=action,
                        target=target,
                        expected_precondition_sha256=expected_precondition_sha256,
                        request_payload=request_payload,
                    )
                    immutable_match = (
                        existing.microtask_id == microtask_id
                        and existing.action == action
                        and existing.target == target
                        and existing.request_fingerprint == legacy_fingerprint
                        and existing.expected_precondition_sha256
                        == expected_precondition_sha256
                        and payload is None
                        and expected_pre_state is None
                        and expected_post_state is None
                    )
                else:
                    _, _, request = self._prepare(
                        task_id, microtask_id, action, target, **prepare_args
                    )
                    immutable_match = existing.request_fingerprint == request.fingerprint
                if not immutable_match:
                    self.events.append_event(
                        task_id,
                        "OPERATION_REPLAY_CONFLICT",
                        microtask_id=microtask_id,
                        operation_id=chosen_id,
                        payload={"existing_status": existing.status.value},
                    )
                    raise OperationConflictError(
                        "operation_id already exists with a different request fingerprint"
                    )
                self.events.append_event(
                    task_id,
                    "OPERATION_REPLAY",
                    microtask_id=microtask_id,
                    operation_id=chosen_id,
                    payload={
                        "status": existing.status.value,
                        "decision": self.replay_decision(existing.status),
                    },
                )
                self._touch_checkpoint(task_id, chosen_id)
                return {
                    "operation": existing,
                    "created": False,
                    "replayed": True,
                    "replay_decision": self.replay_decision(existing.status),
                    "contract_status": assess(existing),
                }

            workspace_id, workspace_root, request = self._prepare(
                task_id, microtask_id, action, target, **prepare_args
            )
            observed_at = utc_now_iso()
            try:
                observed_pre = observe_path(request.target.path)
            except FileStateError as exc:
                raise OperationContractRejected(str(exc)) from exc
            planned_ref = (
                PayloadStore.reference(
                    request.payload_identity["sha256"],
                    request.payload_identity["size"],
                )
                if request.payload_identity is not None
                else None
            )
            try:
                contract = finalize_contract(
                    request,
                    workspace_id=workspace_id,
                    observed_pre=observed_pre,
                    observed_at=observed_at,
                    payload_ref=planned_ref,
                    max_payload_bytes=self.max_payload_bytes,
                )
            except OperationContractError as exc:
                raise OperationContractRejected(str(exc)) from exc
            if request.payload is not None:
                try:
                    stored_ref = self.payloads.put(
                        task_id,
                        request.payload,
                        forbidden_roots=[workspace_root],
                    )
                except PayloadScopeError as exc:
                    raise OperationScopeRejected(str(exc)) from exc
                except PayloadIntegrityError as exc:
                    raise OperationPayloadIntegrityError(str(exc)) from exc
                except PayloadStoreError as exc:
                    raise OperationStoreError(str(exc)) from exc
                if stored_ref != planned_ref:
                    raise OperationStoreError("stored payload reference differs from contract")

            record = OperationRecord(
                operation_id=chosen_id,
                task_id=task_id,
                microtask_id=microtask_id,
                action=action,
                target=request.target.relative,
                status=OperationStatus.INTENT,
                request_fingerprint=request.fingerprint,
                expected_precondition_sha256=expected_precondition_sha256,
                created_at=observed_at,
                updated_at=observed_at,
                contract_version=OPERATION_CONTRACT_VERSION,
                revision=1,
                contract=contract,
            )
            _persist_record(path, record)
            self.events.append_event(
                task_id,
                "OPERATION_INTENT",
                microtask_id=microtask_id,
                operation_id=chosen_id,
                payload={
                    "action": action,
                    "target": record.target,
                    "request_fingerprint": request.fingerprint,
                    "contract_version": OPERATION_CONTRACT_VERSION,
                    "revision": record.revision,
                    "target_key": contract["target_key"],
                    "pre_state": authority_of(contract["pre_state"]),
                    "expected_post_state": authority_of(contract["expected_post_state"]),
                    "payload": (
                        {"sha256": planned_ref["sha256"], "size": planned_ref["size"]}
                        if planned_ref is not None
                        else None
                    ),
                    "contract_complete": contract["complete"],
                },
            )
            self._touch_checkpoint(task_id, chosen_id)
            return {
                "operation": record,
                "created": True,
                "replayed": False,
                "replay_decision": self.replay_decision(record.status),
                "contract_status": assess(record),
            }

    def _done_receipt(self, record: OperationRecord, revision: int) -> dict[str, Any]:
        contract = record.contract or {}
        try:
            canonical = canonical_target(
                self._workspace(contract["workspace_id"]),
                record.target,
            )
            if canonical.key != contract["target_key"]:
                raise OperationTransitionError("operation target identity drifted")
            observed = observe_path(canonical.path)
        except (OperationContractRejected, TargetIdentityError, FileStateError) as exc:
            raise OperationTransitionError(f"cannot observe DONE receipt: {exc}") from exc
        return make_receipt(
            observed,
            contract.get("expected_post_state"),
            observed_at=utc_now_iso(),
            revision=revision,
        )

    def transition(
        self,
        task_id: str,
        operation_id: str,
        requested_status: OperationStatus | str,
        *,
        result_summary: str | None = None,
    ) -> dict[str, Any]:
        requested = OperationStatus(requested_status)
        operation_id = _safe_component("operation_id", operation_id)
        with self._serialized(task_id):
            path = self._path(task_id, operation_id, active_only=True)
            record = self._load_path(path, task_id, operation_id)
            current = record.status

            if requested == current:
                self.events.append_event(
                    task_id,
                    "OPERATION_TRANSITION_REPLAY",
                    microtask_id=record.microtask_id,
                    operation_id=operation_id,
                    payload={"status": current.value},
                )
                self._touch_checkpoint(task_id, operation_id)
                return {
                    "operation": record,
                    "changed": False,
                    "replayed": True,
                    "replay_decision": self.replay_decision(record.status),
                    "contract_status": assess(record),
                }

            if requested not in self._ALLOWED.get(current, set()):
                raise OperationTransitionError(
                    f"{current.value} -> {requested.value} is not allowed"
                )
            if result_summary is not None and (
                not isinstance(result_summary, str) or not result_summary.strip()
            ):
                raise OperationStoreError(
                    "result_summary must be a non-empty string when provided"
                )

            is_contract = record.contract_version != LEGACY_CONTRACT_VERSION
            receipt = None
            if is_contract and requested == OperationStatus.DONE:
                receipt = self._done_receipt(record, record.revision + 1)
                if receipt["matches_expected_post"] is False:
                    self.events.append_event(
                        task_id,
                        "OPERATION_RECEIPT_MISMATCH",
                        microtask_id=record.microtask_id,
                        operation_id=operation_id,
                        payload={
                            "expected_post_state": authority_of(
                                record.contract["expected_post_state"]
                            ),
                            "observed": authority_of(receipt),
                            "eol_only_drift": receipt["eol_only_drift"],
                        },
                    )
                    raise OperationReceiptMismatch(
                        "server-observed target does not match expected post-state; "
                        "DONE refused, reconciliation required"
                        + (" (EOL_ONLY_DRIFT)" if receipt["eol_only_drift"] else "")
                    )

            record.status = requested
            if result_summary is not None:
                record.result_summary = result_summary.strip()
            record.updated_at = utc_now_iso()
            if is_contract:
                record.revision += 1
                if receipt is not None:
                    record.receipt = receipt
            _persist_record(path, record)
            event_payload: dict[str, Any] = {
                "from": current.value,
                "to": requested.value,
                "result_summary": record.result_summary,
            }
            if is_contract:
                event_payload["revision"] = record.revision
            if receipt is not None:
                event_payload["receipt"] = dict(
                    authority_of(receipt),
                    matches_expected_post=receipt["matches_expected_post"],
                )
            self.events.append_event(
                task_id,
                "OPERATION_TRANSITION",
                microtask_id=record.microtask_id,
                operation_id=operation_id,
                payload=event_payload,
            )
            self._touch_checkpoint(task_id, operation_id)
            return {
                "operation": record,
                "changed": True,
                "replayed": False,
                "replay_decision": self.replay_decision(record.status),
                "contract_status": assess(record),
            }

    def _settle_recovery_locked(
        self,
        task_id: str,
        operation_id: str,
        action: str,
        *,
        resolution_id: str,
        expected_revision: int | None,
    ) -> dict[str, Any]:
        """Internal recovery settlement for a caller holding ``task_lock``.

        This path is deliberately separate from ``transition``: generic
        callers cannot manufacture recovery-only STARTED/UNKNOWN ->
        VERIFIED/FAILED transitions.
        """
        action = action.strip().upper() if isinstance(action, str) else ""
        if action not in {"ADOPT", "ABORT", "ROLLBACK"}:
            raise OperationTransitionError(f"unsupported recovery settlement: {action!r}")
        if not isinstance(resolution_id, str) or not resolution_id.strip():
            raise OperationStoreError("resolution_id must be a non-empty string")
        operation_id = _safe_component("operation_id", operation_id)
        path = self._path(task_id, operation_id, active_only=True)
        record = self._load_path(path, task_id, operation_id)

        resolution_id = resolution_id.strip()
        existing = record.recovery_settlement
        if existing is not None:
            if existing["action"] == action and existing["resolution_id"] == resolution_id:
                return {
                    "operation": record,
                    "changed": False,
                    "replayed": True,
                    "settlement": action,
                    "resolution_id": resolution_id,
                }
            raise OperationTransitionError(
                f"operation already has recovery settlement {existing['action']} via "
                f"{existing['resolution_id']}; cannot settle it as {action}"
            )
        if record.revision != expected_revision:
            raise OperationTransitionError(
                "operation revision changed before recovery settlement: "
                f"expected {expected_revision!r}, current {record.revision!r}"
            )
        if record.contract_version == LEGACY_CONTRACT_VERSION:
            raise OperationTransitionError("legacy operation cannot receive RC-6 recovery settlement")

        previous = record.status
        receipt = None
        if action == "ADOPT":
            if record.status not in {
                OperationStatus.STARTED,
                OperationStatus.UNKNOWN_AFTER_DISCONNECT,
                OperationStatus.DONE,
            }:
                raise OperationTransitionError(f"{record.status.value} cannot be settled by ADOPT")
            receipt = self._done_receipt(record, record.revision + 1)
            if receipt["matches_expected_post"] is not True:
                raise OperationReceiptMismatch(
                    "ADOPT refused: current Workspace state does not match expected post-state"
                )
            record.status = OperationStatus.VERIFIED
            record.receipt = receipt
        elif record.status not in {
            OperationStatus.INTENT,
            OperationStatus.STARTED,
            OperationStatus.DONE,
            OperationStatus.UNKNOWN_AFTER_DISCONNECT,
        }:
            raise OperationTransitionError(f"{record.status.value} cannot be settled by {action}")

        now = utc_now_iso()
        record.recovery_settlement = {
            "action": action,
            "resolution_id": resolution_id,
            "basis_operation_revision": expected_revision,
            "settled_at": now,
        }
        record.result_summary = f"recovery {action} via {resolution_id}"
        record.updated_at = now
        record.revision += 1
        _persist_record(path, record)
        payload: dict[str, Any] = {
            "settlement": action,
            "resolution_id": resolution_id.strip(),
            "from": previous.value,
            "to": record.status.value,
            "revision": record.revision,
        }
        if receipt is not None:
            payload["receipt"] = dict(
                authority_of(receipt),
                matches_expected_post=receipt["matches_expected_post"],
            )
        self.events.append_event(
            task_id,
            "OPERATION_RECOVERY_SETTLED",
            microtask_id=record.microtask_id,
            operation_id=operation_id,
            payload=payload,
        )
        return {
            "operation": record,
            "changed": True,
            "replayed": False,
            "settlement": action,
            "resolution_id": resolution_id.strip(),
        }

    def read_payload(self, task_id: str, operation_id: str) -> bytes:
        """Return contract payload bytes after hash+size verification."""
        record = self.get(task_id, operation_id)
        payload_ref = (record.contract or {}).get("payload_ref")
        if payload_ref is None:
            raise OperationStoreError(f"operation has no durable payload: {operation_id}")
        try:
            return self.payloads.read(task_id, payload_ref)
        except PayloadIntegrityError as exc:
            raise OperationPayloadIntegrityError(str(exc)) from exc
        except PayloadStoreError as exc:
            raise OperationStoreError(str(exc)) from exc

    def contract_status(self, task_id: str, operation_id: str) -> dict[str, Any]:
        """Contract sufficiency facts plus payload integrity; no resolver decision."""
        record = self.get(task_id, operation_id)
        status = assess(record)
        payload_ref = (record.contract or {}).get("payload_ref")
        status["payload_verified"] = None
        if payload_ref is not None:
            try:
                self.payloads.verify(task_id, payload_ref)
            except PayloadStoreError:
                status["payload_verified"] = False
                status["rearm_contract_sufficient"] = False
                status["issues"] = status["issues"] + ["payload_integrity_failure"]
            else:
                status["payload_verified"] = True
        return status
