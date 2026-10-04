"""Machine-readable data schemas for Web Alarm Workspace WA-1.1."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

SCHEMA_VERSION = 1


def utc_now_iso() -> str:
    """Return an RFC3339/ISO-8601 UTC timestamp suitable for JSON storage."""
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    """Create a stable record identifier that can be persisted and reused."""
    return f"{prefix}_{uuid4().hex}"


def _require_text(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


class TaskStatus(str, Enum):
    PLANNED = "PLANNED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class MicrotaskStatus(str, Enum):
    PLANNED = "PLANNED"
    PREPARING = "PREPARING"
    BACKUP_VERIFIED = "BACKUP_VERIFIED"
    READY = "READY"
    ACTIVE = "ACTIVE"
    DONE = "DONE"
    VERIFIED = "VERIFIED"
    BLOCKED_PREPARE = "BLOCKED_PREPARE"
    UNKNOWN_AFTER_DISCONNECT = "UNKNOWN_AFTER_DISCONNECT"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"
    FAILED_VERIFICATION = "FAILED_VERIFICATION"


class ManifestStatus(str, Enum):
    PREPARING = "PREPARING"
    VERIFIED = "VERIFIED"
    BLOCKED_PREPARE = "BLOCKED_PREPARE"


class OperationStatus(str, Enum):
    INTENT = "INTENT"
    STARTED = "STARTED"
    DONE = "DONE"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    UNKNOWN_AFTER_DISCONNECT = "UNKNOWN_AFTER_DISCONNECT"


class VerificationStatus(str, Enum):
    PENDING = "PENDING"
    PASS = "PASS"
    FAIL = "FAIL"


@dataclass(slots=True)
class WorkspaceRegistration:
    workspace_id: str = field(default_factory=lambda: new_id("ws"))
    display_name: str = ""
    workspace_root: str = ""
    schema_version: int = SCHEMA_VERSION
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def __post_init__(self) -> None:
        _require_text("workspace_id", self.workspace_id)
        _require_text("display_name", self.display_name)
        _require_text("workspace_root", self.workspace_root)


@dataclass(slots=True)
class TaskRecord:
    task_id: str = field(default_factory=lambda: new_id("task"))
    workspace_id: str = ""
    title: str = ""
    raw_task: str = ""
    goal: str = ""
    status: TaskStatus = TaskStatus.PLANNED
    plan_revision: int = 1
    schema_version: int = SCHEMA_VERSION
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def __post_init__(self) -> None:
        _require_text("task_id", self.task_id)
        _require_text("workspace_id", self.workspace_id)
        _require_text("title", self.title)
        _require_text("raw_task", self.raw_task)
        _require_text("goal", self.goal)
        if self.plan_revision < 1:
            raise ValueError("plan_revision must be >= 1")


@dataclass(slots=True)
class MicrotaskRecord:
    microtask_id: str = field(default_factory=lambda: new_id("micro"))
    task_id: str = ""
    sequence: int = 1
    title: str = ""
    goal: str = ""
    status: MicrotaskStatus = MicrotaskStatus.PLANNED
    schema_version: int = SCHEMA_VERSION
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def __post_init__(self) -> None:
        _require_text("microtask_id", self.microtask_id)
        _require_text("task_id", self.task_id)
        _require_text("title", self.title)
        _require_text("goal", self.goal)
        if self.sequence < 1:
            raise ValueError("sequence must be >= 1")


@dataclass(slots=True)
class TaskPlanRecord:
    plan_id: str = field(default_factory=lambda: new_id("plan"))
    task_id: str = ""
    revision: int = 1
    microtask_ids: list[str] = field(default_factory=list)
    current_microtask_id: str | None = None
    schema_version: int = SCHEMA_VERSION
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def __post_init__(self) -> None:
        _require_text("plan_id", self.plan_id)
        _require_text("task_id", self.task_id)
        if self.revision < 1:
            raise ValueError("revision must be >= 1")
        if len(self.microtask_ids) != len(set(self.microtask_ids)):
            raise ValueError("microtask_ids must not contain duplicates")
        if self.current_microtask_id is not None and self.current_microtask_id not in self.microtask_ids:
            raise ValueError("current_microtask_id must belong to microtask_ids")


@dataclass(slots=True)
class ManifestRecord:
    manifest_id: str = field(default_factory=lambda: new_id("manifestset"))
    task_id: str = ""
    microtask_id: str = ""
    entry_ids: list[str] = field(default_factory=list)
    snapshot_ids: list[str] = field(default_factory=list)
    status: ManifestStatus = ManifestStatus.PREPARING
    schema_version: int = SCHEMA_VERSION
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def __post_init__(self) -> None:
        _require_text("manifest_id", self.manifest_id)
        _require_text("task_id", self.task_id)
        _require_text("microtask_id", self.microtask_id)
        if len(self.entry_ids) != len(set(self.entry_ids)):
            raise ValueError("entry_ids must not contain duplicates")
        if len(self.snapshot_ids) != len(set(self.snapshot_ids)):
            raise ValueError("snapshot_ids must not contain duplicates")
        if len(self.entry_ids) != len(self.snapshot_ids):
            raise ValueError("entry_ids and snapshot_ids must have equal length")


@dataclass(slots=True)
class ManifestEntry:
    manifest_entry_id: str = field(default_factory=lambda: new_id("manifest"))
    microtask_id: str = ""
    source_path: str = ""
    expected_change: str = ""
    exists_before: bool | None = None
    size_before: int | None = None
    sha256_before: str | None = None
    snapshot_path: str | None = None
    schema_version: int = SCHEMA_VERSION
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def __post_init__(self) -> None:
        _require_text("manifest_entry_id", self.manifest_entry_id)
        _require_text("microtask_id", self.microtask_id)
        _require_text("source_path", self.source_path)
        _require_text("expected_change", self.expected_change)


@dataclass(slots=True)
class SnapshotRecord:
    snapshot_id: str = field(default_factory=lambda: new_id("snapshot"))
    microtask_id: str = ""
    manifest_entry_id: str = ""
    source_path: str = ""
    exists_before: bool = False
    size_before: int | None = None
    sha256_before: str | None = None
    snapshot_path: str | None = None
    captured_at: str = field(default_factory=utc_now_iso)
    schema_version: int = SCHEMA_VERSION
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def __post_init__(self) -> None:
        _require_text("snapshot_id", self.snapshot_id)
        _require_text("microtask_id", self.microtask_id)
        _require_text("manifest_entry_id", self.manifest_entry_id)
        _require_text("source_path", self.source_path)
        if self.exists_before and not self.snapshot_path:
            raise ValueError("snapshot_path is required when exists_before is true")


@dataclass(slots=True)
class OperationRecord:
    operation_id: str = field(default_factory=lambda: new_id("op"))
    task_id: str = ""
    microtask_id: str = ""
    action: str = ""
    target: str = ""
    status: OperationStatus = OperationStatus.INTENT
    request_fingerprint: str | None = None
    expected_precondition_sha256: str | None = None
    result_summary: str | None = None
    schema_version: int = SCHEMA_VERSION
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    # RC-1 operation contract; absent in legacy JSON, so defaults mean contract v1.
    # Validated by operation_contract.validate_record, not by the global schema.
    contract_version: int = 1
    revision: int | None = None
    contract: dict[str, Any] | None = None
    receipt: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        _require_text("operation_id", self.operation_id)
        _require_text("task_id", self.task_id)
        _require_text("microtask_id", self.microtask_id)
        _require_text("action", self.action)
        _require_text("target", self.target)


@dataclass(slots=True)
class VerificationRecord:
    verification_id: str = field(default_factory=lambda: new_id("verify"))
    task_id: str = ""
    microtask_id: str = ""
    operation_id: str | None = None
    check_name: str = ""
    status: VerificationStatus = VerificationStatus.PENDING
    evidence: str | None = None
    verified_at: str | None = None
    schema_version: int = SCHEMA_VERSION
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def __post_init__(self) -> None:
        _require_text("verification_id", self.verification_id)
        _require_text("task_id", self.task_id)
        _require_text("microtask_id", self.microtask_id)
        _require_text("check_name", self.check_name)


@dataclass(slots=True)
class CheckpointRecord:
    checkpoint_id: str = field(default_factory=lambda: new_id("checkpoint"))
    task_id: str = ""
    workspace_id: str = ""
    last_verified_microtask_id: str | None = None
    current_microtask_id: str | None = None
    current_status: MicrotaskStatus = MicrotaskStatus.PLANNED
    snapshot_status: str = "NOT_PREPARED"
    last_operation_id: str | None = None
    next_safe_action: str = ""
    schema_version: int = SCHEMA_VERSION
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def __post_init__(self) -> None:
        _require_text("checkpoint_id", self.checkpoint_id)
        _require_text("task_id", self.task_id)
        _require_text("workspace_id", self.workspace_id)
        _require_text("snapshot_status", self.snapshot_status)
        _require_text("next_safe_action", self.next_safe_action)


@dataclass(slots=True)
class EventRecord:
    event_id: str = field(default_factory=lambda: new_id("event"))
    task_id: str = ""
    event_type: str = ""
    microtask_id: str | None = None
    operation_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    recorded_at: str = field(default_factory=utc_now_iso)
    schema_version: int = SCHEMA_VERSION
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def __post_init__(self) -> None:
        _require_text("event_id", self.event_id)
        _require_text("task_id", self.task_id)
        _require_text("event_type", self.event_type)


def record_to_dict(record: Any) -> dict[str, Any]:
    """Convert a schema dataclass to JSON-friendly primitives."""
    data = asdict(record)
    for key, value in list(data.items()):
        if isinstance(value, Enum):
            data[key] = value.value
    return data
