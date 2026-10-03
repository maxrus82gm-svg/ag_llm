"""Persistent machine-usable Recovery Report contract/store for WA-3.6 M001."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from .models import SCHEMA_VERSION, new_id, utc_now_iso
from .task_store import TaskStore, TaskStoreError
from .workspace_registry import default_storage_root


REPORT_VERSION = 1


class RecoveryReportStoreError(RuntimeError):
    """Raised when recovery report state is missing, invalid, or unsafe."""


class RecoveryReportConflictError(RecoveryReportStoreError):
    """Raised when an existing report_id is reused for different evidence."""


class SideEffectScope(str, Enum):
    NONE = "none"
    PARTIAL = "partial"
    FULL = "full"
    AMBIGUOUS = "ambiguous"


def _require_text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _optional_text(name: str, value: str | None) -> str | None:
    if value is None:
        return None
    return _require_text(name, value)


def _require_json(name: str, value: Any) -> None:
    try:
        json.dumps(value, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be JSON-serializable") from exc


def _require_dict(name: str, value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    _require_json(name, value)
    return value


def _require_dict_list(name: str, value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")
    result: list[dict[str, Any]] = []
    for item in value:
        result.append(_require_dict(f"{name} item", item))
    return result


def _require_text_list(name: str, value: Any) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")
    return [_require_text(f"{name} item", item) for item in value]


def _safe_component(name: str, value: str) -> str:
    value = _require_text(name, value)
    if Path(value).name != value or "/" in value or "\\" in value:
        raise RecoveryReportStoreError(f"{name} must not contain path separators")
    return value


@dataclass(slots=True)
class RecoveryTargetSummary:
    source_path: str
    pre_state: dict[str, Any] | None = None
    current_state: dict[str, Any] | None = None
    expected_post_state: dict[str, Any] | None = None
    classification: str | None = None
    evidence_identity: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.source_path = _require_text("source_path", self.source_path)
        for name in ("pre_state", "current_state", "expected_post_state"):
            value = getattr(self, name)
            if value is not None:
                setattr(self, name, _require_dict(name, value))
        self.classification = _optional_text("classification", self.classification)
        self.evidence_identity = _require_dict(
            "evidence_identity",
            self.evidence_identity,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RecoveryReportRecord:
    incident_id: str
    task_id: str
    side_effect_scope: SideEffectScope
    next_safe_action: str
    report_id: str = field(default_factory=lambda: new_id("recovery_report"))
    microtask_id: str | None = None
    operation_id: str | None = None
    caller_error_class: str | None = None
    transport_evidence: list[dict[str, Any]] = field(default_factory=list)
    process_evidence: list[dict[str, Any]] = field(default_factory=list)
    process_restarted: bool = False
    last_persistent_operation_state: str | None = None
    checkpoint_identity: dict[str, Any] | None = None
    affected_targets: list[RecoveryTargetSummary] = field(default_factory=list)
    evidence_identity: dict[str, Any] = field(default_factory=dict)
    reconciliation_decision: str | None = None
    reconciliation_reason: str | None = None
    accepted_as_already_done: list[str] = field(default_factory=list)
    actually_retried: list[str] = field(default_factory=list)
    actually_rolled_back: list[str] = field(default_factory=list)
    untouched_or_unresolved: list[str] = field(default_factory=list)
    fresh_process_reopen_result: str | None = None
    authority: str = "evidence_only"
    automatic_mutation_authorized: bool = False
    report_version: int = REPORT_VERSION
    schema_version: int = SCHEMA_VERSION
    created_at: str = field(default_factory=utc_now_iso)

    def __post_init__(self) -> None:
        self.report_id = _require_text("report_id", self.report_id)
        self.incident_id = _require_text("incident_id", self.incident_id)
        self.task_id = _require_text("task_id", self.task_id)
        self.microtask_id = _optional_text("microtask_id", self.microtask_id)
        self.operation_id = _optional_text("operation_id", self.operation_id)
        self.caller_error_class = _optional_text(
            "caller_error_class",
            self.caller_error_class,
        )
        self.last_persistent_operation_state = _optional_text(
            "last_persistent_operation_state",
            self.last_persistent_operation_state,
        )
        self.reconciliation_decision = _optional_text(
            "reconciliation_decision",
            self.reconciliation_decision,
        )
        self.reconciliation_reason = _optional_text(
            "reconciliation_reason",
            self.reconciliation_reason,
        )
        self.fresh_process_reopen_result = _optional_text(
            "fresh_process_reopen_result",
            self.fresh_process_reopen_result,
        )
        self.next_safe_action = _require_text(
            "next_safe_action",
            self.next_safe_action,
        )
        self.created_at = _require_text("created_at", self.created_at)

        if not isinstance(self.side_effect_scope, SideEffectScope):
            self.side_effect_scope = SideEffectScope(self.side_effect_scope)
        if not isinstance(self.process_restarted, bool):
            raise ValueError("process_restarted must be boolean")
        if self.authority != "evidence_only":
            raise ValueError("Recovery Report authority must remain evidence_only")
        if self.automatic_mutation_authorized:
            raise ValueError("Recovery Report must not authorize automatic mutation")
        if self.report_version != REPORT_VERSION:
            raise ValueError("unsupported report_version")
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("unsupported schema_version")

        self.transport_evidence = _require_dict_list(
            "transport_evidence",
            self.transport_evidence,
        )
        self.process_evidence = _require_dict_list(
            "process_evidence",
            self.process_evidence,
        )
        if self.checkpoint_identity is not None:
            self.checkpoint_identity = _require_dict(
                "checkpoint_identity",
                self.checkpoint_identity,
            )
        self.evidence_identity = _require_dict(
            "evidence_identity",
            self.evidence_identity,
        )

        normalized_targets: list[RecoveryTargetSummary] = []
        for target in self.affected_targets:
            if isinstance(target, RecoveryTargetSummary):
                normalized_targets.append(target)
            elif isinstance(target, dict):
                normalized_targets.append(RecoveryTargetSummary(**target))
            else:
                raise ValueError(
                    "affected_targets items must be RecoveryTargetSummary objects"
                )
        self.affected_targets = normalized_targets

        self.accepted_as_already_done = _require_text_list(
            "accepted_as_already_done",
            self.accepted_as_already_done,
        )
        self.actually_retried = _require_text_list(
            "actually_retried",
            self.actually_retried,
        )
        self.actually_rolled_back = _require_text_list(
            "actually_rolled_back",
            self.actually_rolled_back,
        )
        self.untouched_or_unresolved = _require_text_list(
            "untouched_or_unresolved",
            self.untouched_or_unresolved,
        )
        _require_json("Recovery Report", self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["side_effect_scope"] = self.side_effect_scope.value
        return data

    def semantic_dict(self) -> dict[str, Any]:
        data = self.to_dict()
        data.pop("created_at", None)
        return data

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "RecoveryReportRecord":
        if not isinstance(raw, dict):
            raise ValueError("Recovery Report must be an object")
        if raw.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("unsupported Recovery Report schema_version")
        if raw.get("report_version") != REPORT_VERSION:
            raise ValueError("unsupported Recovery Report report_version")
        return cls(**raw)


class RecoveryReportStore:
    """Disk-backed append-only Recovery Reports with conflict-safe report identity."""

    def __init__(self, storage_root: str | Path | None = None) -> None:
        root = Path(storage_root) if storage_root is not None else default_storage_root()
        self.storage_root = root.expanduser().resolve(strict=False)
        self.reports_root = self.storage_root / "recovery_reports"
        self.tasks = TaskStore(self.storage_root)

    def _task_reports_dir(self, task_id: str, *, create: bool = False) -> Path:
        task_id = _safe_component("task_id", task_id)
        path = self.reports_root / task_id
        if create:
            path.mkdir(parents=True, exist_ok=True)
        return path

    def report_path(self, task_id: str, report_id: str) -> Path:
        task_id = _safe_component("task_id", task_id)
        report_id = _safe_component("report_id", report_id)
        return self.reports_root / task_id / f"{report_id}.json"

    def _load_path(
        self,
        path: Path,
        task_id: str,
        report_id: str,
    ) -> RecoveryReportRecord:
        if not path.is_file():
            raise RecoveryReportStoreError(f"unknown report_id: {report_id}")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            record = RecoveryReportRecord.from_dict(raw)
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise RecoveryReportStoreError(
                f"cannot read Recovery Report: {path}"
            ) from exc
        if record.task_id != task_id or record.report_id != report_id:
            raise RecoveryReportStoreError(
                "Recovery Report identity does not match requested record"
            )
        return record

    def append(self, record: RecoveryReportRecord) -> RecoveryReportRecord:
        if not isinstance(record, RecoveryReportRecord):
            raise RecoveryReportStoreError(
                "append requires a RecoveryReportRecord"
            )
        try:
            self.tasks.open_task(record.task_id)
        except TaskStoreError as exc:
            raise RecoveryReportStoreError(
                f"unknown task_id: {record.task_id}"
            ) from exc

        directory = self._task_reports_dir(record.task_id, create=False)
        path = self.report_path(record.task_id, record.report_id)
        if path.exists():
            existing = self._load_path(
                path,
                record.task_id,
                record.report_id,
            )
            if existing.semantic_dict() == record.semantic_dict():
                return existing
            raise RecoveryReportConflictError(
                "report_id already exists with different Recovery Report evidence"
            )

        directory.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(
            record.to_dict(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n"
        temp = directory / f".{record.report_id}.{new_id('tmp')}.tmp"
        try:
            with temp.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, path)
        except OSError as exc:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass
            raise RecoveryReportStoreError(
                f"cannot persist Recovery Report: {path}"
            ) from exc
        return self._load_path(path, record.task_id, record.report_id)

    def get(self, task_id: str, report_id: str) -> RecoveryReportRecord:
        try:
            self.tasks.open_task(task_id)
        except TaskStoreError as exc:
            raise RecoveryReportStoreError(f"unknown task_id: {task_id}") from exc
        return self._load_path(
            self.report_path(task_id, report_id),
            _safe_component("task_id", task_id),
            _safe_component("report_id", report_id),
        )

    def list_reports(self, task_id: str) -> list[RecoveryReportRecord]:
        try:
            self.tasks.open_task(task_id)
        except TaskStoreError as exc:
            raise RecoveryReportStoreError(f"unknown task_id: {task_id}") from exc
        directory = self._task_reports_dir(task_id)
        if not directory.is_dir():
            return []
        records = [
            self._load_path(path, task_id, path.stem)
            for path in sorted(directory.glob("*.json"))
        ]
        return sorted(
            records,
            key=lambda item: (item.created_at, item.report_id),
        )
