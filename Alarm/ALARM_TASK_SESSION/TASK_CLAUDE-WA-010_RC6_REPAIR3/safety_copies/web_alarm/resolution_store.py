"""Persistent Resolver records for Web Alarm recovery actions (RC-2).

A ResolutionRecord is one tracked recovery action (ADOPT / RETRY / ROLLBACK /
ABORT) bound to the exact reconciliation evidence fingerprint and operation
revision on which the Resolver evaluated it. ``result`` (ACCEPTED / STALE /
REJECTED) is a storage detail of the Resolver, not a new public operation or
microtask lifecycle: RT-001 V15 keeps that state machine deferred.

Records are written once and never rewritten. No record performs or claims a
physical mutation.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from .models import SCHEMA_VERSION, new_id, utc_now_iso
from .task_store import TaskStore, TaskStoreError

RESOLUTION_VERSION = 1

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_REQUESTED_FIELDS = frozenset({"evidence_fingerprint", "operation_revision"})
_BASIS_FIELDS = frozenset(
    {
        "evidence_version",
        "evidence_fingerprint",
        "decision_version",
        "decision",
        "reason_code",
        "operation_status",
        "operation_contract_version",
        "operation_revision",
        "operation_request_fingerprint",
        "affected_targets",
    }
)


class ResolutionStoreError(RuntimeError):
    """Raised when resolution state is missing, invalid, or unsafe."""


class ResolutionConflictError(ResolutionStoreError):
    """Same resolution identity was reused for a different action or basis."""


class ResolutionAction(str, Enum):
    ADOPT = "ADOPT"
    RETRY = "RETRY"
    ROLLBACK = "ROLLBACK"
    ABORT = "ABORT"


class ResolutionResult(str, Enum):
    ACCEPTED = "ACCEPTED"
    STALE = "STALE"
    REJECTED = "REJECTED"


# What an ACCEPTED resolution means. None of these is a physical mutation.
EFFECTS = {
    ResolutionAction.ADOPT: "WORKSPACE_STATE_ADOPTED",
    ResolutionAction.RETRY: "REARMED_FOR_FUTURE_EXECUTOR",
    ResolutionAction.ROLLBACK: "ROLLBACK_REQUESTED",
    ResolutionAction.ABORT: "RECOVERY_ABORTED",
}


def _text(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _revision(name: str, value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer or null")
    return value


def _fingerprint(name: str, value: Any) -> str:
    if not isinstance(value, str) or not _SHA256_RE.match(value):
        raise ValueError(f"{name} must be lowercase hex SHA-256")
    return value


def requested_basis(evidence_fingerprint: Any, operation_revision: Any) -> dict[str, Any]:
    """The basis a caller observed in its reconciliation; validated, not trusted."""
    return {
        "evidence_fingerprint": _fingerprint("evidence_fingerprint", evidence_fingerprint),
        "operation_revision": _revision("operation_revision", operation_revision),
    }


def logical_identity(
    task_id: str,
    microtask_id: str,
    operation_id: str,
    action: ResolutionAction,
    basis: dict[str, Any],
) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "microtask_id": microtask_id,
        "operation_id": operation_id,
        "action": action.value,
        "requested_basis": dict(basis),
    }


def logical_resolution_id(identity: dict[str, Any]) -> str:
    raw = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "res_" + hashlib.sha256(raw).hexdigest()[:32]


@dataclass(slots=True)
class ResolutionRecord:
    resolution_id: str
    task_id: str
    microtask_id: str
    operation_id: str
    action: ResolutionAction
    requested_basis: dict[str, Any]
    basis: dict[str, Any]
    result: ResolutionResult
    result_code: str
    result_reason: str
    effect: str | None
    next_safe_action: str
    provenance: dict[str, Any]
    payload_verified: bool | None = None
    physical_mutation_performed: bool = False
    resolution_version: int = RESOLUTION_VERSION
    schema_version: int = SCHEMA_VERSION
    created_at: str = field(default_factory=utc_now_iso)

    def __post_init__(self) -> None:
        for name in (
            "resolution_id",
            "task_id",
            "microtask_id",
            "operation_id",
            "result_code",
            "result_reason",
            "next_safe_action",
            "created_at",
        ):
            _text(name, getattr(self, name))
        self.action = ResolutionAction(self.action)
        self.result = ResolutionResult(self.result)
        if not isinstance(self.requested_basis, dict) or set(self.requested_basis) != _REQUESTED_FIELDS:
            raise ValueError("requested_basis must have exactly the basis fields")
        requested_basis(
            self.requested_basis["evidence_fingerprint"],
            self.requested_basis["operation_revision"],
        )
        if not isinstance(self.basis, dict) or set(self.basis) != _BASIS_FIELDS:
            raise ValueError("basis must have exactly the resolver basis fields")
        _fingerprint("basis.evidence_fingerprint", self.basis["evidence_fingerprint"])
        _revision("basis.operation_revision", self.basis["operation_revision"])
        _text("basis.decision", self.basis["decision"])
        if not isinstance(self.basis["affected_targets"], list) or not all(
            isinstance(item, str) for item in self.basis["affected_targets"]
        ):
            raise ValueError("basis.affected_targets must be a list of strings")
        expected_effect = EFFECTS[self.action] if self.result is ResolutionResult.ACCEPTED else None
        if self.effect != expected_effect:
            raise ValueError("effect does not match action/result")
        if self.payload_verified not in (True, False, None):
            raise ValueError("payload_verified must be boolean or null")
        if self.physical_mutation_performed is not False:
            raise ValueError("RC-2 resolutions never perform physical mutations")
        if not isinstance(self.provenance, dict) or set(self.provenance) != {
            "agent",
            "channel",
            "authority",
        } or self.provenance["authority"] != "claimed":
            raise ValueError("provenance must be claimed agent/channel")
        if self.resolution_version != RESOLUTION_VERSION:
            raise ValueError("unsupported resolution_version")
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("unsupported schema_version")

    def logical_identity(self) -> dict[str, Any]:
        return logical_identity(
            self.task_id,
            self.microtask_id,
            self.operation_id,
            self.action,
            self.requested_basis,
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["action"] = self.action.value
        data["result"] = self.result.value
        return data

    @classmethod
    def from_dict(cls, raw: Any) -> "ResolutionRecord":
        if not isinstance(raw, dict):
            raise ValueError("resolution record must be an object")
        return cls(**raw)


class ResolutionStore:
    """Write-once resolution records inside the machine-local TASK directory.

    Callers serialize writes with the TASK operation lock (OperationStore.task_lock)
    so a resolution is evaluated and persisted atomically w.r.t. operation writes.
    """

    DIRECTORY = "resolutions"

    def __init__(self, storage_root: str | os.PathLike[str] | None = None) -> None:
        self.tasks = TaskStore(storage_root)

    def _directory(self, task_id: str, *, active_only: bool = False) -> Path:
        try:
            return self.tasks.task_directory(task_id, active_only=active_only) / self.DIRECTORY
        except TaskStoreError as exc:
            raise ResolutionStoreError(str(exc)) from exc

    def path(self, task_id: str, resolution_id: str, *, active_only: bool = False) -> Path:
        resolution_id = _text("resolution_id", resolution_id).strip()
        if Path(resolution_id).name != resolution_id or "/" in resolution_id or "\\" in resolution_id:
            raise ResolutionStoreError("resolution_id must not contain path separators")
        return self._directory(task_id, active_only=active_only) / f"{resolution_id}.json"

    def _load(self, path: Path, task_id: str, resolution_id: str) -> ResolutionRecord:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            record = ResolutionRecord.from_dict(raw)
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise ResolutionStoreError(f"invalid resolution record: {path}: {exc}") from exc
        if record.task_id != task_id or record.resolution_id != resolution_id:
            raise ResolutionStoreError("resolution identity does not match requested record")
        return record

    def find(self, task_id: str, resolution_id: str) -> ResolutionRecord | None:
        path = self.path(task_id, resolution_id)
        if not path.is_file():
            return None
        return self._load(path, task_id, resolution_id)

    def get(self, task_id: str, resolution_id: str) -> ResolutionRecord:
        record = self.find(task_id, resolution_id)
        if record is None:
            raise ResolutionStoreError(f"unknown resolution_id: {resolution_id}")
        return record

    def list(self, task_id: str, *, operation_id: str | None = None) -> list[ResolutionRecord]:
        directory = self._directory(task_id)
        if not directory.is_dir():
            return []
        records = [
            self._load(path, task_id, path.stem)
            for path in sorted(directory.glob("*.json"))
        ]
        if operation_id is not None:
            records = [item for item in records if item.operation_id == operation_id]
        return sorted(records, key=lambda item: (item.created_at, item.resolution_id))

    def write_new(self, record: ResolutionRecord) -> None:
        path = self.path(record.task_id, record.resolution_id, active_only=True)
        if path.exists():
            raise ResolutionStoreError(f"resolution already exists: {record.resolution_id}")
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.parent / f".{path.name}.{new_id('tmp')}.tmp"
        raw = json.dumps(record.to_dict(), ensure_ascii=False, indent=2) + "\n"
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
            raise ResolutionStoreError(f"cannot persist resolution: {path}") from exc
