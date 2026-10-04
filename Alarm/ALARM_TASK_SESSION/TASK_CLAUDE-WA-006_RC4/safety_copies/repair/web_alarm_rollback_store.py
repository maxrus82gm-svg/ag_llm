"""Persistent tracked-rollback sessions for Web Alarm recovery (RC-4).

One JSON record per rollback session (``<task_dir>/rollbacks/<rollback_id>.json``)
holds the source resolution basis, the server-derived target set, per-target
preserved current state, planned action, claim, status and receipt, plus the
overall result. The record is replaced atomically and carries a revision.

Session status is a Resolver-layer storage detail, not a new public
Operation/Microtask lifecycle:
PREPARED -> PRESERVED -> AUTHORIZED -> APPLYING -> VERIFIED | PARTIAL | FAILED,
with PRESERVATION_FAILED (nothing mutated) and CLOSED (claims released after a
non-verified outcome) as terminal states.

Current bytes preserved before a destructive restore live content-addressed in
``<task_dir>/rollback_preserved/<sha256>.bin`` (outside repository/vault, hash +
size verified on write and read, never copied into events or reports).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from .models import SCHEMA_VERSION, new_id
from .payload_store import PayloadStore
from .task_store import TaskStore, TaskStoreError

ROLLBACK_VERSION = 1

PREPARED = "PREPARED"
PRESERVED = "PRESERVED"
PRESERVATION_FAILED = "PRESERVATION_FAILED"
AUTHORIZED = "AUTHORIZED"
APPLYING = "APPLYING"
VERIFIED = "VERIFIED"
PARTIAL = "PARTIAL"
FAILED = "FAILED"
CLOSED = "CLOSED"
SESSION_STATUSES = (
    PREPARED, PRESERVED, PRESERVATION_FAILED, AUTHORIZED, APPLYING, VERIFIED, PARTIAL, FAILED, CLOSED,
)

T_PENDING = "PENDING"
T_PRESERVED = "PRESERVED"
T_APPLYING = "APPLYING"
T_RESTORED = "RESTORED"
T_NOOP = "NOOP"
T_DRIFTED = "DRIFTED"
T_FAILED = "FAILED"
TARGET_STATUSES = (T_PENDING, T_PRESERVED, T_APPLYING, T_RESTORED, T_NOOP, T_DRIFTED, T_FAILED)

WRITE_RESTORE = "WRITE_RESTORE"
DELETE_CREATED = "DELETE_CREATED"
NOOP = "NOOP"
ACTIONS = (WRITE_RESTORE, DELETE_CREATED, NOOP)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_RECORD_FIELDS = frozenset(
    {
        "rollback_version", "schema_version", "rollback_id", "task_id", "microtask_id",
        "operation_id", "resolution_id", "basis", "status", "revision", "created_at",
        "updated_at", "provenance", "targets", "last_attempt", "result",
        "claims_released", "next_safe_action",
    }
)
_BASIS_FIELDS = frozenset(
    {
        "evidence_fingerprint", "operation_revision", "operation_request_fingerprint",
        "manifest_id", "restore_point_fingerprint",
    }
)
_TARGET_FIELDS = frozenset(
    {
        "manifest_entry_id", "snapshot_id", "source_path", "target", "target_key",
        "target_hash", "expected_restore", "preserved", "planned_action", "claim_id",
        "status", "receipt", "failure",
    }
)
_RECEIPT_FIELDS = frozenset(
    {
        "rollback_id", "target", "target_key", "target_hash", "action", "preserved",
        "expected_restore", "observed_post", "matches_expected_restore",
        "recovered_after_interruption", "operation_revision", "evidence_fingerprint",
        "restore_point_fingerprint", "at",
    }
)


class RollbackStoreError(RuntimeError):
    """Raised when a rollback record is invalid or cannot be persisted."""


class PreservedStateStore(PayloadStore):
    """Content-addressed preserved current bytes; same integrity rules as payloads."""

    DIRECTORY = "rollback_preserved"

    @staticmethod
    def reference(sha256: str, size: int) -> dict[str, Any]:
        reference = PayloadStore.reference(sha256, size)
        reference["store"] = "rollback_preserved"
        return reference


def rollback_identity(task_id: str, resolution_id: str) -> str:
    """One rollback session per accepted ROLLBACK resolution (logical basis)."""
    raw = json.dumps([task_id, resolution_id], separators=(",", ":")).encode("utf-8")
    return "rb_" + hashlib.sha256(raw).hexdigest()[:32]


def _fail(message: str) -> None:
    raise RollbackStoreError(message)


def _check_text(name: str, value: Any) -> None:
    if not isinstance(value, str) or not value.strip():
        _fail(f"{name} must be a non-empty string")


def check_state(name: str, value: Any) -> None:
    if not isinstance(value, dict) or set(value) != {"exists", "size", "sha256"}:
        _fail(f"{name} must be an authority state")
    if not isinstance(value["exists"], bool):
        _fail(f"{name}.exists must be boolean")
    if value["exists"]:
        if isinstance(value["size"], bool) or not isinstance(value["size"], int) or value["size"] < 0:
            _fail(f"{name}.size is invalid")
        if not isinstance(value["sha256"], str) or not _SHA256_RE.match(value["sha256"]):
            _fail(f"{name}.sha256 is invalid")
    elif value["size"] is not None or value["sha256"] is not None:
        _fail(f"absent {name} must not carry size/sha256")


def _check_target(target: Any, rollback_id: str) -> None:
    if not isinstance(target, dict) or set(target) != _TARGET_FIELDS:
        _fail("rollback target has unexpected fields")
    for name in ("manifest_entry_id", "snapshot_id", "source_path", "target", "target_key"):
        _check_text(f"target.{name}", target[name])
    if not isinstance(target["target_hash"], str) or not _SHA256_RE.match(target["target_hash"]):
        _fail("target.target_hash is invalid")
    check_state("target.expected_restore", target["expected_restore"])
    if target["status"] not in TARGET_STATUSES:
        _fail("target.status is invalid")
    preserved = target["preserved"]
    if (preserved is None) != (target["status"] == T_PENDING):
        _fail("target.preserved must be set exactly when the target left PENDING")
    if preserved is not None:
        if not isinstance(preserved, dict) or set(preserved) != {"exists", "size", "sha256", "blob", "preserved_at"}:
            _fail("target.preserved has unexpected fields")
        check_state("target.preserved", {k: preserved[k] for k in ("exists", "size", "sha256")})
        _check_text("target.preserved.preserved_at", preserved["preserved_at"])
        blob = preserved["blob"]
        if preserved["exists"] != (blob is not None):
            _fail("preserved blob must exist exactly for an existing target")
        if blob is not None and (
            not isinstance(blob, dict)
            or blob.get("sha256") != preserved["sha256"]
            or blob.get("size") != preserved["size"]
        ):
            _fail("preserved blob reference does not match preserved state")
        if target["planned_action"] not in ACTIONS:
            _fail("target.planned_action is invalid")
    elif target["planned_action"] is not None:
        _fail("planned_action requires a preserved state")
    if target["claim_id"] is not None:
        _check_text("target.claim_id", target["claim_id"])
    receipt = target["receipt"]
    if target["status"] in (T_RESTORED, T_NOOP) and receipt is None:
        _fail("receipt must exist for RESTORED/NOOP targets")
    if target["status"] not in (T_RESTORED, T_NOOP, T_FAILED) and receipt is not None:
        _fail("only RESTORED/NOOP/FAILED targets carry a receipt")
    if receipt is not None:
        if not isinstance(receipt, dict) or set(receipt) != _RECEIPT_FIELDS:
            _fail("receipt has unexpected fields")
        if receipt["rollback_id"] != rollback_id or receipt["action"] not in ACTIONS:
            _fail("receipt identity/action is invalid")
        for name in ("preserved", "expected_restore", "observed_post"):
            check_state(f"receipt.{name}", receipt[name])
        if not isinstance(receipt["matches_expected_restore"], bool):
            _fail("receipt.matches_expected_restore must be boolean")
        if target["status"] in (T_RESTORED, T_NOOP) and not receipt["matches_expected_restore"]:
            _fail("RESTORED/NOOP receipt must match the expected restore state")
    failure = target["failure"]
    if failure is not None and (
        not isinstance(failure, dict) or set(failure) != {"code", "reason", "observed"}
    ):
        _fail("target.failure has unexpected fields")


def validate_record(record: Any) -> None:
    if not isinstance(record, dict) or set(record) != _RECORD_FIELDS:
        _fail("rollback record has unexpected fields")
    if record["rollback_version"] != ROLLBACK_VERSION or record["schema_version"] != SCHEMA_VERSION:
        _fail("unsupported rollback record version")
    for name in ("rollback_id", "task_id", "microtask_id", "operation_id", "resolution_id",
                 "created_at", "updated_at", "next_safe_action"):
        _check_text(name, record[name])
    if record["rollback_id"] != rollback_identity(record["task_id"], record["resolution_id"]):
        _fail("rollback_id does not match its resolution identity")
    basis = record["basis"]
    if not isinstance(basis, dict) or set(basis) != _BASIS_FIELDS:
        _fail("rollback basis has unexpected fields")
    for name in ("evidence_fingerprint", "operation_request_fingerprint", "restore_point_fingerprint"):
        if not isinstance(basis[name], str) or not _SHA256_RE.match(basis[name]):
            _fail(f"basis.{name} is invalid")
    if isinstance(basis["operation_revision"], bool) or not isinstance(basis["operation_revision"], int) or basis["operation_revision"] < 1:
        _fail("basis.operation_revision must be a positive integer")
    _check_text("basis.manifest_id", basis["manifest_id"])
    if record["status"] not in SESSION_STATUSES:
        _fail("rollback status is invalid")
    if isinstance(record["revision"], bool) or not isinstance(record["revision"], int) or record["revision"] < 1:
        _fail("rollback revision must be a positive integer")
    provenance = record["provenance"]
    if not isinstance(provenance, dict) or set(provenance) != {"agent", "channel", "authority"} or provenance["authority"] != "claimed":
        _fail("provenance must be claimed agent/channel")
    targets = record["targets"]
    if not isinstance(targets, list) or not targets:
        _fail("rollback must have a non-empty target set")
    for target in targets:
        _check_target(target, record["rollback_id"])
    hashes = [target["target_hash"] for target in targets]
    if hashes != sorted(hashes) or len(set(hashes)) != len(hashes):
        _fail("targets must be unique and ordered by target_hash")
    if not isinstance(record["claims_released"], bool):
        _fail("claims_released must be boolean")
    for name in ("last_attempt", "result"):
        if record[name] is not None and not isinstance(record[name], dict):
            _fail(f"{name} must be an object or null")
    if record["status"] == VERIFIED and not all(t["status"] in (T_RESTORED, T_NOOP) for t in targets):
        _fail("VERIFIED rollback requires every target RESTORED or NOOP")


class RollbackStore:
    DIRECTORY = "rollbacks"

    def __init__(self, storage_root: str | os.PathLike[str] | None = None) -> None:
        self.tasks = TaskStore(storage_root)

    def _directory(self, task_id: str, *, active_only: bool = False) -> Path:
        try:
            return self.tasks.task_directory(task_id, active_only=active_only) / self.DIRECTORY
        except TaskStoreError as exc:
            raise RollbackStoreError(str(exc)) from exc

    def path(self, task_id: str, rollback_id: str, *, active_only: bool = False) -> Path:
        if not isinstance(rollback_id, str) or not re.fullmatch(r"rb_[0-9a-f]{32}", rollback_id):
            raise RollbackStoreError(f"invalid rollback_id: {rollback_id!r}")
        return self._directory(task_id, active_only=active_only) / f"{rollback_id}.json"

    def find(self, task_id: str, rollback_id: str) -> dict[str, Any] | None:
        path = self.path(task_id, rollback_id)
        if not path.is_file():
            return None
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RollbackStoreError(f"cannot read rollback record: {path}") from exc
        validate_record(record)
        if record["task_id"] != task_id or record["rollback_id"] != rollback_id:
            raise RollbackStoreError("rollback identity does not match requested record")
        return record

    def get(self, task_id: str, rollback_id: str) -> dict[str, Any]:
        record = self.find(task_id, rollback_id)
        if record is None:
            raise RollbackStoreError(f"unknown rollback_id: {rollback_id}")
        return record

    def list(self, task_id: str, *, operation_id: str | None = None) -> list[dict[str, Any]]:
        directory = self._directory(task_id)
        if not directory.is_dir():
            return []
        records = [self.get(task_id, path.stem) for path in sorted(directory.glob("rb_*.json"))]
        if operation_id is not None:
            records = [item for item in records if item["operation_id"] == operation_id]
        return sorted(records, key=lambda item: (item["created_at"], item["rollback_id"]))

    def write(self, record: dict[str, Any]) -> None:
        validate_record(record)
        path = self.path(record["task_id"], record["rollback_id"], active_only=True)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.parent / f".{path.name}.{new_id('tmp')}.tmp"
        raw = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
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
            raise RollbackStoreError(f"cannot persist rollback record: {path}") from exc
