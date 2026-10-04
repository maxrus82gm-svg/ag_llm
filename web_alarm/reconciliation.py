"""Read-only reconciliation evidence for Web Alarm Workspace WA-3.3.1."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping

from .manifest_store import ManifestSnapshotStore, ManifestStoreError
from .models import ManifestEntry, OperationStatus, SnapshotRecord
from .operation_store import OperationStore, OperationStoreError
from .target_identity import TargetIdentityError, target_key
from .task_store import TaskStore, TaskStoreError
from .workspace_registry import WorkspaceRegistry, WorkspaceRegistryError


EVIDENCE_VERSION = 1

_DELETE_WORDS = {"delete", "deleted", "remove", "removed"}
_CREATE_WORDS = {"create", "created", "new", "add", "added"}


class ReconciliationEvidenceError(RuntimeError):
    """Identity or workspace failure that prevents safe evidence collection."""


@dataclass(slots=True)
class TargetEvidence:
    source_path: str
    expected_change: str
    exists_before: bool | None
    size_before: int | None
    sha256_before: str | None
    snapshot_path: str | None

    snapshot_valid: bool
    snapshot_error: str | None

    current_exists: bool | None
    current_is_file: bool | None
    current_size: int | None
    current_sha256: str | None
    path_error: str | None

    expected_post_exists: bool | None
    expected_post_sha256: str | None
    expected_post_source: str | None

    operation_target: bool
    operation_precondition_matches_manifest: bool | None

    matches_pre_state: bool | None
    matches_expected_post_state: bool | None
    drift_detected: bool | None
    classification: str
    missing_evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ReconciliationEvidence:
    evidence_version: int
    task_id: str
    microtask_id: str
    workspace_id: str
    workspace_root: str

    operation_id: str | None
    operation_status: str | None
    operation_action: str | None
    operation_target: str | None
    operation_request_fingerprint: str | None
    operation_expected_precondition_sha256: str | None
    operation_result_summary: str | None
    verification_evidence: str | None

    manifest_status: str
    snapshot_status: str
    evidence_complete: bool
    expected_post_complete: bool
    errors: list[str]
    targets: list[TargetEvidence]

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "targets": [item.to_dict() for item in self.targets],
        }


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _path_key(value: str) -> str | None:
    try:
        return target_key(value)
    except TargetIdentityError:
        return None


def _contract_post(operation: Any) -> Mapping[str, Any] | None:
    """Durable expected post-state of an RC-1 contract operation, if declared."""
    if operation is None or operation.contract_version < 2 or not operation.contract:
        return None
    return operation.contract.get("expected_post_state")


def _parse_expected_post(
    source_path: str,
    expected_change: str,
    supplied: Mapping[str, Mapping[str, Any]] | None,
) -> tuple[bool | None, str | None, str | None, list[str]]:
    missing: list[str] = []
    if supplied is not None and source_path in supplied:
        spec = supplied[source_path]
        if not isinstance(spec, Mapping):
            raise ReconciliationEvidenceError(
                f"expected post-state for {source_path} must be an object"
            )
        exists = spec.get("exists")
        sha = spec.get("sha256")
        if not isinstance(exists, bool):
            raise ReconciliationEvidenceError(
                f"expected post-state exists must be boolean: {source_path}"
            )
        if sha is not None and (not isinstance(sha, str) or not sha.strip()):
            raise ReconciliationEvidenceError(
                f"expected post-state sha256 must be a non-empty string: {source_path}"
            )
        if exists and sha is None:
            missing.append("expected_post_sha256")
        if not exists and sha is not None:
            raise ReconciliationEvidenceError(
                f"absent expected post-state cannot have sha256: {source_path}"
            )
        return exists, sha.strip() if isinstance(sha, str) else None, "supplied", missing

    change = expected_change.strip().lower()
    if change in _DELETE_WORDS:
        return False, None, "manifest.expected_change", missing
    if change in _CREATE_WORDS:
        missing.append("expected_post_sha256")
        return True, None, "manifest.expected_change", missing

    missing.append("expected_post_state")
    return None, None, None, missing


class ReconciliationEvidenceCollector:
    """Collect facts only. This class never restores, retries, or writes Workspace files."""

    def __init__(self, storage_root: str | Path | None = None) -> None:
        self.tasks = TaskStore(storage_root)
        self.registry = WorkspaceRegistry(self.tasks.storage_root)
        self.manifests = ManifestSnapshotStore(self.tasks.storage_root)
        self.operations = OperationStore(self.tasks.storage_root)

    def _workspace(self, task_id: str) -> tuple[str, Path]:
        try:
            task = self.tasks.open_task(task_id)
            workspace = self.registry.get(task.workspace_id)
            root = Path(workspace.workspace_root).resolve(strict=True)
        except (TaskStoreError, WorkspaceRegistryError, OSError) as exc:
            raise ReconciliationEvidenceError(
                f"cannot resolve task workspace: {task_id}"
            ) from exc
        if not root.is_dir():
            raise ReconciliationEvidenceError(
                f"workspace_root is not a directory: {root}"
            )
        return workspace.workspace_id, root

    def _target_path(
        self,
        workspace_root: Path,
        source_path: str,
    ) -> tuple[Path | None, str | None]:
        if not isinstance(source_path, str) or not source_path.strip():
            return None, "source_path is empty"
        supplied = Path(source_path)
        if supplied.is_absolute():
            return None, "manifest source_path must be workspace-relative"
        candidate = workspace_root / supplied
        if candidate.is_symlink():
            return None, "target is a symlink"
        try:
            resolved = candidate.resolve(strict=False)
            resolved.relative_to(workspace_root)
        except (OSError, ValueError):
            return None, "target escapes or cannot resolve inside workspace"
        if resolved.exists() and not resolved.is_file():
            return None, "target exists but is not a file"
        return resolved, None

    def _current_file_state(
        self,
        workspace_root: Path,
        source_path: str,
    ) -> tuple[
        bool | None,
        bool | None,
        int | None,
        str | None,
        str | None,
    ]:
        target, path_error = self._target_path(workspace_root, source_path)
        if path_error is not None or target is None:
            return None, None, None, None, path_error
        if not target.exists():
            return False, False, None, None, None
        try:
            stat_before = target.stat()
            data = target.read_bytes()
            stat_after = target.stat()
        except OSError as exc:
            return True, True, None, None, f"cannot read current target: {exc}"
        if (
            stat_before.st_size != stat_after.st_size
            or stat_before.st_mtime_ns != stat_after.st_mtime_ns
        ):
            return (
                True,
                True,
                len(data),
                _sha256(data),
                "current target changed during evidence read",
            )
        return True, True, len(data), _sha256(data), None

    def _snapshot_integrity(
        self,
        restore_dir: Path,
        entry: ManifestEntry,
        snapshot: SnapshotRecord,
    ) -> tuple[bool, str | None]:
        if snapshot.manifest_entry_id != entry.manifest_entry_id:
            return False, "entry/snapshot identity mismatch"
        if snapshot.source_path != entry.source_path:
            return False, "entry/snapshot source_path mismatch"
        if snapshot.exists_before != entry.exists_before:
            return False, "entry/snapshot exists_before mismatch"
        if snapshot.size_before != entry.size_before:
            return False, "entry/snapshot size_before mismatch"
        if snapshot.sha256_before != entry.sha256_before:
            return False, "entry/snapshot sha256_before mismatch"

        if snapshot.exists_before:
            if not snapshot.snapshot_path:
                return False, "missing snapshot_path"
            if snapshot.sha256_before is None or snapshot.size_before is None:
                return False, "missing snapshot pre-state metadata"
            candidate = restore_dir / snapshot.snapshot_path
            try:
                resolved = candidate.resolve(strict=False)
                resolved.relative_to(restore_dir.resolve(strict=True))
            except (OSError, ValueError):
                return False, "snapshot_path escapes restore point"
            if not resolved.is_file():
                return False, "snapshot binary is missing"
            try:
                data = resolved.read_bytes()
            except OSError as exc:
                return False, f"cannot read snapshot binary: {exc}"
            if len(data) != snapshot.size_before:
                return False, "snapshot size mismatch"
            if _sha256(data) != snapshot.sha256_before:
                return False, "snapshot hash mismatch"
            return True, None

        if snapshot.snapshot_path is not None:
            return False, "new target unexpectedly has snapshot_path"
        if snapshot.size_before is not None or snapshot.sha256_before is not None:
            return False, "new target unexpectedly has pre-state metadata"
        return True, None

    @staticmethod
    def _matches_pre(
        entry: ManifestEntry,
        snapshot_valid: bool,
        current_exists: bool | None,
        current_sha256: str | None,
    ) -> bool | None:
        if not snapshot_valid or entry.exists_before is None or current_exists is None:
            return None
        if entry.exists_before is False:
            return current_exists is False
        if entry.sha256_before is None:
            return None
        return current_exists is True and current_sha256 == entry.sha256_before

    @staticmethod
    def _matches_expected(
        expected_exists: bool | None,
        expected_sha256: str | None,
        current_exists: bool | None,
        current_sha256: str | None,
    ) -> bool | None:
        if expected_exists is None or current_exists is None:
            return None
        if expected_exists is False:
            return current_exists is False
        if expected_sha256 is None:
            return None
        return current_exists is True and current_sha256 == expected_sha256


    @staticmethod
    def _classification(
        *,
        snapshot_valid: bool,
        path_error: str | None,
        matches_pre: bool | None,
        matches_expected: bool | None,
    ) -> tuple[str, bool | None]:
        if path_error is not None or not snapshot_valid:
            return "MISSING_EVIDENCE", None
        if matches_pre is True:
            return "PRE_STATE", False
        if matches_expected is True:
            return "EXPECTED_POST_STATE", False
        if matches_pre is False and matches_expected is False:
            return "DRIFT", True
        if matches_pre is False and matches_expected is None:
            return "CHANGED_UNCLASSIFIED", None
        return "MISSING_EVIDENCE", None

    def _empty_result(
        self,
        *,
        task_id: str,
        microtask_id: str,
        workspace_id: str,
        workspace_root: Path,
        operation: Any,
        errors: list[str],
    ) -> ReconciliationEvidence:
        return ReconciliationEvidence(
            evidence_version=EVIDENCE_VERSION,
            task_id=task_id,
            microtask_id=microtask_id,
            workspace_id=workspace_id,
            workspace_root=str(workspace_root),
            operation_id=getattr(operation, "operation_id", None),
            operation_status=(
                getattr(getattr(operation, "status", None), "value", None)
            ),
            operation_action=getattr(operation, "action", None),
            operation_target=getattr(operation, "target", None),
            operation_request_fingerprint=getattr(
                operation, "request_fingerprint", None
            ),
            operation_expected_precondition_sha256=getattr(
                operation, "expected_precondition_sha256", None
            ),
            operation_result_summary=getattr(operation, "result_summary", None),
            verification_evidence=(
                getattr(operation, "result_summary", None)
                if getattr(operation, "status", None) == OperationStatus.VERIFIED
                else None
            ),
            manifest_status="UNAVAILABLE",
            snapshot_status="UNAVAILABLE",
            evidence_complete=False,
            expected_post_complete=False,
            errors=errors,
            targets=[],
        )

    def collect(
        self,
        task_id: str,
        microtask_id: str,
        *,
        operation_id: str | None = None,
        expected_post_state: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> ReconciliationEvidence:
        try:
            self.tasks.open_microtask(task_id, microtask_id)
            self.tasks.task_directory(task_id, active_only=True)
        except TaskStoreError as exc:
            raise ReconciliationEvidenceError(
                f"cannot open active task/microtask: {task_id}/{microtask_id}"
            ) from exc

        workspace_id, workspace_root = self._workspace(task_id)
        errors: list[str] = []
        operation = None
        if operation_id is not None:
            try:
                operation = self.operations.get(task_id, operation_id)
            except OperationStoreError as exc:
                errors.append(f"operation evidence unavailable: {exc}")
            else:
                if operation.microtask_id != microtask_id:
                    errors.append(
                        "operation microtask_id does not match requested microtask"
                    )

        try:
            manifest = self.manifests.open_manifest(
                task_id, microtask_id, active_only=True
            )
            entries = self.manifests.list_entries(
                task_id, microtask_id, active_only=True
            )
            snapshots = self.manifests.list_snapshots(
                task_id, microtask_id, active_only=True
            )
            restore_dir = (
                self.tasks.microtask_directory(
                    task_id, microtask_id, active_only=True
                )
                / self.manifests.RESTORE_DIR
            )
        except (ManifestStoreError, TaskStoreError) as exc:
            errors.append(f"manifest evidence unavailable: {exc}")
            return self._empty_result(
                task_id=task_id,
                microtask_id=microtask_id,
                workspace_id=workspace_id,
                workspace_root=workspace_root,
                operation=operation,
                errors=errors,
            )

        snapshot_by_entry: dict[str, SnapshotRecord] = {}
        for snapshot in snapshots:
            if snapshot.manifest_entry_id in snapshot_by_entry:
                errors.append(
                    f"duplicate snapshot for manifest entry: "
                    f"{snapshot.manifest_entry_id}"
                )
                continue
            snapshot_by_entry[snapshot.manifest_entry_id] = snapshot

        supplied_paths = set(expected_post_state or {})
        declared_paths = {entry.source_path for entry in entries}
        for extra in sorted(supplied_paths - declared_paths):
            errors.append(
                f"expected post-state path is not declared in manifest: {extra}"
            )

        target_results: list[TargetEvidence] = []
        any_operation_target = False
        for entry in entries:
            missing: list[str] = []
            snapshot = snapshot_by_entry.get(entry.manifest_entry_id)
            if snapshot is None:
                snapshot_valid = False
                snapshot_error = "snapshot metadata missing for manifest entry"
                missing.append("snapshot_record")
            else:
                snapshot_valid, snapshot_error = self._snapshot_integrity(
                    restore_dir, entry, snapshot
                )
                if not snapshot_valid:
                    missing.append("valid_snapshot")

            (
                current_exists,
                current_is_file,
                current_size,
                current_sha256,
                path_error,
            ) = self._current_file_state(workspace_root, entry.source_path)
            if path_error is not None:
                missing.append("current_target_state")

            operation_target = False
            if operation is not None:
                entry_key = _path_key(entry.source_path)
                operation_target = (
                    entry_key is not None and _path_key(operation.target) == entry_key
                )
                any_operation_target = any_operation_target or operation_target

            (
                expected_exists,
                expected_sha,
                expected_source,
                expected_missing,
            ) = _parse_expected_post(
                entry.source_path,
                entry.expected_change,
                expected_post_state,
            )
            contract_post = _contract_post(operation) if operation_target else None
            if contract_post is not None:
                # RC-1: the persisted contract is authoritative; a caller value may
                # only repeat it, a contradiction is surfaced and fails closed.
                if expected_source == "supplied" and (
                    expected_exists != contract_post["exists"]
                    or (
                        expected_sha is not None
                        and expected_sha != contract_post["sha256"]
                    )
                ):
                    errors.append(
                        "supplied expected post-state contradicts operation contract: "
                        f"{entry.source_path}"
                    )
                expected_exists = contract_post["exists"]
                expected_sha = contract_post["sha256"]
                expected_source = "operation.contract"
                expected_missing = []
            missing.extend(expected_missing)

            matches_pre = self._matches_pre(
                entry,
                snapshot_valid,
                current_exists,
                current_sha256,
            )
            matches_expected = self._matches_expected(
                expected_exists,
                expected_sha,
                current_exists,
                current_sha256,
            )

            precondition_match: bool | None = None
            if operation is not None:
                if (
                    operation_target
                    and operation.expected_precondition_sha256 is not None
                ):
                    if entry.sha256_before is None:
                        precondition_match = False
                    else:
                        precondition_match = (
                            operation.expected_precondition_sha256
                            == entry.sha256_before
                        )
                    if precondition_match is False:
                        missing.append("operation_precondition_binding")

            classification, drift = self._classification(
                snapshot_valid=snapshot_valid,
                path_error=path_error,
                matches_pre=matches_pre,
                matches_expected=matches_expected,
            )

            target_results.append(
                TargetEvidence(
                    source_path=entry.source_path,
                    expected_change=entry.expected_change,
                    exists_before=entry.exists_before,
                    size_before=entry.size_before,
                    sha256_before=entry.sha256_before,
                    snapshot_path=entry.snapshot_path,
                    snapshot_valid=snapshot_valid,
                    snapshot_error=snapshot_error,
                    current_exists=current_exists,
                    current_is_file=current_is_file,
                    current_size=current_size,
                    current_sha256=current_sha256,
                    path_error=path_error,
                    expected_post_exists=expected_exists,
                    expected_post_sha256=expected_sha,
                    expected_post_source=expected_source,
                    operation_target=operation_target,
                    operation_precondition_matches_manifest=precondition_match,
                    matches_pre_state=matches_pre,
                    matches_expected_post_state=matches_expected,
                    drift_detected=drift,
                    classification=classification,
                    missing_evidence=sorted(set(missing)),
                )
            )

        if operation is not None and not any_operation_target:
            errors.append("operation target is not declared in manifest")

        if len(entries) != len(snapshots):
            errors.append("manifest entry/snapshot counts differ")

        all_snapshot_valid = bool(target_results) and all(
            item.snapshot_valid for item in target_results
        )
        all_current_readable = bool(target_results) and all(
            item.path_error is None and item.current_exists is not None
            for item in target_results
        )
        expected_post_complete = bool(target_results) and all(
            item.expected_post_exists is False
            or (
                item.expected_post_exists is True
                and item.expected_post_sha256 is not None
            )
            for item in target_results
        )
        evidence_complete = (
            manifest.status.value == "VERIFIED"
            and all_snapshot_valid
            and all_current_readable
            and not errors
        )

        return ReconciliationEvidence(
            evidence_version=EVIDENCE_VERSION,
            task_id=task_id,
            microtask_id=microtask_id,
            workspace_id=workspace_id,
            workspace_root=str(workspace_root),
            operation_id=getattr(operation, "operation_id", operation_id),
            operation_status=(
                operation.status.value if operation is not None else None
            ),
            operation_action=(
                operation.action if operation is not None else None
            ),
            operation_target=(
                operation.target if operation is not None else None
            ),
            operation_request_fingerprint=(
                operation.request_fingerprint
                if operation is not None
                else None
            ),
            operation_expected_precondition_sha256=(
                operation.expected_precondition_sha256
                if operation is not None
                else None
            ),
            operation_result_summary=(
                operation.result_summary if operation is not None else None
            ),
            verification_evidence=(
                operation.result_summary
                if operation is not None
                and operation.status == OperationStatus.VERIFIED
                and operation.result_summary
                else None
            ),
            manifest_status=manifest.status.value,
            snapshot_status=(
                "VERIFIED"
                if manifest.status.value == "VERIFIED" and all_snapshot_valid
                else "INVALID"
            ),
            evidence_complete=evidence_complete,
            expected_post_complete=expected_post_complete,
            errors=errors,
            targets=target_results,
        )
