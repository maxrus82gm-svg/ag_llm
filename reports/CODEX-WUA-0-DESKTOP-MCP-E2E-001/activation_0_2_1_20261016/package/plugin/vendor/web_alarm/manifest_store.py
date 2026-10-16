"""Manifest and snapshot storage for Web Alarm Workspace WA-1.4."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Iterable

from .models import (
    SCHEMA_VERSION,
    ManifestEntry,
    ManifestRecord,
    ManifestStatus,
    MicrotaskStatus,
    SnapshotRecord,
    new_id,
    record_to_dict,
    utc_now_iso,
)
from .store_lock import DEFAULT_LOCK_TIMEOUT_SECONDS, InterProcessLock, StoreLockTimeout
from .task_store import TaskStore, TaskStoreError
from .workspace_registry import WorkspaceRegistry, WorkspaceRegistryError


class ManifestStoreError(RuntimeError):
    """Raised when a restore point cannot be prepared, verified or restored."""


# statuses a restore point may be prepared from (the server state machine rule)
_PREPARE_FROM = frozenset({MicrotaskStatus.PLANNED, MicrotaskStatus.BLOCKED_PREPARE})


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_component(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ManifestStoreError(f"{name} must be a non-empty string")
    if Path(value).name != value or "/" in value or "\\" in value:
        raise ManifestStoreError(f"{name} must not contain path separators")
    return value


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifestStoreError(f"cannot read JSON record: {path}") from exc
    if not isinstance(value, dict):
        raise ManifestStoreError(f"JSON record is not an object: {path}")
    if value.get("schema_version") != SCHEMA_VERSION:
        raise ManifestStoreError(
            f"unsupported schema_version in {path}: {value.get('schema_version')!r}"
        )
    return value


def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.parent / f".{path.name}.{new_id('tmp')}.tmp"
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    try:
        with temp.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    except OSError as exc:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass
        raise ManifestStoreError(f"cannot persist JSON record: {path}") from exc


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.parent / f".{path.name}.{new_id('tmp')}.tmp"
    try:
        with temp.open("wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    except OSError as exc:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass
        raise ManifestStoreError(f"cannot persist snapshot bytes: {path}") from exc


class ManifestSnapshotStore:
    """Per-microtask manifest, verified snapshot and explicit restore storage."""

    RESTORE_DIR = "restore_point"
    def __init__(self, storage_root: str | os.PathLike[str] | None = None) -> None:
        self.task_store = TaskStore(storage_root)
        self.workspace_registry = WorkspaceRegistry(self.task_store.storage_root)

    def _work_dir(self, task_id: str, microtask_id: str) -> Path:
        return self.task_store.microtask_directory(
            task_id, microtask_id, active_only=True
        )

    def _restore_dir(
        self, task_id: str, microtask_id: str, *, active_only: bool = False
    ) -> Path:
        work_dir = self.task_store.microtask_directory(
            task_id, microtask_id, active_only=active_only
        )
        return work_dir / self.RESTORE_DIR

    def _workspace_root(self, task_id: str) -> Path:
        task = self.task_store.open_task(task_id)
        try:
            workspace = self.workspace_registry.get(task.workspace_id)
        except WorkspaceRegistryError as exc:
            raise ManifestStoreError(
                f"task references unknown workspace_id: {task.workspace_id}"
            ) from exc
        try:
            return Path(workspace.workspace_root).resolve(strict=True)
        except OSError as exc:
            raise ManifestStoreError(
                f"registered workspace_root is unavailable: {workspace.workspace_root}"
            ) from exc

    def _resolve_target(self, workspace_root: Path, source_path: str) -> tuple[Path, str]:
        if not isinstance(source_path, str) or not source_path.strip():
            raise ManifestStoreError("source_path must be a non-empty string")
        supplied = Path(source_path)
        candidate = supplied if supplied.is_absolute() else workspace_root / supplied
        if candidate.is_symlink():
            raise ManifestStoreError(f"symlink targets are not supported: {source_path}")
        resolved = candidate.expanduser().resolve(strict=False)
        try:
            relative = resolved.relative_to(workspace_root)
        except ValueError as exc:
            raise ManifestStoreError(
                f"target escapes registered workspace: {source_path}"
            ) from exc
        if not resolved.parent.is_dir():
            raise ManifestStoreError(
                f"target parent directory does not exist: {source_path}"
            )
        if resolved.exists() and not resolved.is_file():
            raise ManifestStoreError(f"target is not a file: {source_path}")
        return resolved, str(relative)

    def _manifest_path(self, restore_dir: Path) -> Path:
        return restore_dir / "manifest.json"

    def _entry_path(self, restore_dir: Path, entry_id: str) -> Path:
        entry_id = _safe_component("manifest_entry_id", entry_id)
        return restore_dir / "manifest_entries" / f"{entry_id}.json"

    def _snapshot_meta_path(self, restore_dir: Path, snapshot_id: str) -> Path:
        snapshot_id = _safe_component("snapshot_id", snapshot_id)
        return restore_dir / "snapshots" / f"{snapshot_id}.json"

    def _snapshot_binary_path(self, restore_dir: Path, snapshot_id: str) -> Path:
        snapshot_id = _safe_component("snapshot_id", snapshot_id)
        return restore_dir / "snapshots" / f"{snapshot_id}.bin"

    def _write_manifest(self, restore_dir: Path, record: ManifestRecord) -> None:
        _atomic_write_json(self._manifest_path(restore_dir), record_to_dict(record))

    def _best_effort_microtask_status(
        self,
        task_id: str,
        microtask_id: str,
        status: MicrotaskStatus,
        *,
        expected: Iterable[MicrotaskStatus] | MicrotaskStatus | None = None,
    ) -> None:
        """Best-effort status write; with ``expected`` it never overwrites a newer status."""
        try:
            if expected is None:
                self.task_store.set_microtask_status(task_id, microtask_id, status)
            else:
                self.task_store.compare_and_set_microtask_status(
                    task_id, microtask_id, expected=expected, status=status
                )
        except (TaskStoreError, ValueError):
            pass

    def open_manifest(
        self, task_id: str, microtask_id: str, *, active_only: bool = False
    ) -> ManifestRecord:
        restore_dir = self._restore_dir(
            task_id, microtask_id, active_only=active_only
        )
        raw = _read_json(self._manifest_path(restore_dir))
        try:
            raw["status"] = ManifestStatus(raw["status"])
            record = ManifestRecord(**raw)
        except (KeyError, TypeError, ValueError) as exc:
            raise ManifestStoreError(
                f"invalid manifest record: {self._manifest_path(restore_dir)}"
            ) from exc
        if record.task_id != task_id or record.microtask_id != microtask_id:
            raise ManifestStoreError("manifest identity does not match requested microtask")
        return record

    def list_entries(
        self, task_id: str, microtask_id: str, *, active_only: bool = False
    ) -> list[ManifestEntry]:
        manifest = self.open_manifest(
            task_id, microtask_id, active_only=active_only
        )
        restore_dir = self._restore_dir(
            task_id, microtask_id, active_only=active_only
        )
        records: list[ManifestEntry] = []
        for entry_id in manifest.entry_ids:
            raw = _read_json(self._entry_path(restore_dir, entry_id))
            try:
                entry = ManifestEntry(**raw)
            except (TypeError, ValueError) as exc:
                raise ManifestStoreError(f"invalid manifest entry: {entry_id}") from exc
            if entry.microtask_id != microtask_id:
                raise ManifestStoreError(f"entry microtask mismatch: {entry_id}")
            records.append(entry)
        return records

    def list_snapshots(
        self, task_id: str, microtask_id: str, *, active_only: bool = False
    ) -> list[SnapshotRecord]:
        manifest = self.open_manifest(
            task_id, microtask_id, active_only=active_only
        )
        restore_dir = self._restore_dir(
            task_id, microtask_id, active_only=active_only
        )
        records: list[SnapshotRecord] = []
        for snapshot_id in manifest.snapshot_ids:
            raw = _read_json(self._snapshot_meta_path(restore_dir, snapshot_id))
            try:
                snapshot = SnapshotRecord(**raw)
            except (TypeError, ValueError) as exc:
                raise ManifestStoreError(
                    f"invalid snapshot record: {snapshot_id}"
                ) from exc
            if snapshot.microtask_id != microtask_id:
                raise ManifestStoreError(
                    f"snapshot microtask mismatch: {snapshot_id}"
                )
            records.append(snapshot)
        return records

    def _block_restore_point(
        self,
        task_id: str,
        microtask_id: str,
        restore_dir: Path,
        *,
        expected_status: MicrotaskStatus | None = None,
    ) -> None:
        """Persist a failed restore-point verification (manifest + microtask BLOCKED_PREPARE).

        Repair #3: with ``expected_status`` (the state-machine path) both
        writes happen in one section under the per-TASK mutation lock, and only
        while the microtask still has the status the failing verification was
        decided on. A stale verification never touches the restore point of a
        microtask that moved on (pure verification keeps reporting a real
        integrity failure anyway). A crash between the two writes leaves the
        manifest BLOCKED_PREPARE and the microtask at that status: the restore
        point is NOT_VERIFIED in every projection and the next transition that
        needs it repeats this block and completes it.
        """
        if expected_status is None:
            # storage primitive (legacy restore path): unchanged best effort
            self._write_blocked_manifest(task_id, microtask_id, restore_dir)
            self._best_effort_microtask_status(task_id, microtask_id, MicrotaskStatus.BLOCKED_PREPARE)
            return
        try:
            with self.task_store.mutation_lock(task_id):
                current = self.task_store.open_microtask(task_id, microtask_id)
                if current.status is not MicrotaskStatus(expected_status):
                    return
                self._write_blocked_manifest(task_id, microtask_id, restore_dir)
                self.task_store.compare_and_set_microtask_status_locked(
                    task_id, microtask_id, expected=expected_status, status=MicrotaskStatus.BLOCKED_PREPARE
                )
        except (TaskStoreError, ValueError):
            pass

    def _write_blocked_manifest(self, task_id: str, microtask_id: str, restore_dir: Path) -> None:
        try:
            manifest = self.open_manifest(task_id, microtask_id)
            manifest.status = ManifestStatus.BLOCKED_PREPARE
            manifest.updated_at = utc_now_iso()
            self._write_manifest(restore_dir, manifest)
        except ManifestStoreError:
            pass

    # --- preparation (Repair #4: restart-safe) ------------------------------------------

    STAGE_PREFIX = ".restore."

    def _prepare_lock(self, task_id: str, microtask_id: str, *, timeout: float) -> InterProcessLock:
        """Held for a whole preparation; the OS releases it when its process dies.

        While it is free, a PREPARING microtask is an interrupted preparation,
        never a running one (Repair #4).
        """
        task_id = _safe_component("task_id", task_id)
        microtask_id = _safe_component("microtask_id", microtask_id)
        return InterProcessLock(
            self.task_store.storage_root / "locks" / "prepare" / task_id / f"{microtask_id}.lock",
            timeout=timeout,
        )

    def _discard_stages(self, work_dir: Path) -> int:
        """Remove unpublished stage directories (never authoritative); the caller holds the lock."""
        discarded = 0
        for stage in sorted(work_dir.glob(self.STAGE_PREFIX + "*")):
            if stage.is_dir():
                shutil.rmtree(stage, ignore_errors=True)
                discarded += 0 if stage.exists() else 1
        return discarded

    def prepare_microtask(
        self,
        task_id: str,
        microtask_id: str,
        targets: Iterable[tuple[str, str]],
        *,
        expected_status: MicrotaskStatus | None = None,
        lock_timeout: float = DEFAULT_LOCK_TIMEOUT_SECONDS,
    ) -> ManifestRecord:
        """Capture, verify and publish the restore point of one microtask.

        Repair #4: the whole preparation holds the microtask's preparation lock.
        Persistent evidence of a preparation that died is unambiguous:
        - W1: PREPARING without a published ``restore_point`` (at most stage
          directories, which are never authoritative);
        - W2: PREPARING with a published ``restore_point``.
        ``reconcile_interrupted_preparation`` resolves both after a restart.
        Once the restore point is published it is the authority: a later
        failure never blocks the microtask blindly; it stays PREPARING (W2).
        """
        try:
            lock = self._prepare_lock(task_id, microtask_id, timeout=lock_timeout)
            lock.acquire()
        except StoreLockTimeout as exc:
            raise ManifestStoreError(f"restore-point preparation is already running: {exc}") from exc
        try:
            return self._prepare_locked(task_id, microtask_id, list(targets), expected_status=expected_status)
        finally:
            lock.release()

    def _prepare_locked(
        self,
        task_id: str,
        microtask_id: str,
        target_specs: list[tuple[str, str]],
        *,
        expected_status: MicrotaskStatus | None,
    ) -> ManifestRecord:
        work_dir = self._work_dir(task_id, microtask_id)
        final_dir = work_dir / self.RESTORE_DIR
        if final_dir.exists():
            raise ManifestStoreError(
                "restore point already exists; original pre-state will not be overwritten"
            )
        if not target_specs:
            raise ManifestStoreError("manifest must contain at least one target")

        workspace_root = self._workspace_root(task_id)
        self._discard_stages(work_dir)  # leftovers of an attempt that died before publication
        stage_dir = work_dir / f"{self.STAGE_PREFIX}{new_id('stage')}"
        (stage_dir / "manifest_entries").mkdir(parents=True, exist_ok=False)
        (stage_dir / "snapshots").mkdir(parents=True, exist_ok=False)
        manifest = ManifestRecord(
            task_id=task_id,
            microtask_id=microtask_id,
            status=ManifestStatus.PREPARING,
        )
        if expected_status is None:
            # storage primitive (fixtures, legacy callers): unchanged best effort
            self._best_effort_microtask_status(
                task_id, microtask_id, MicrotaskStatus.PREPARING
            )
        else:
            # Repair #2A: the state-machine path starts only from the status it
            # decided on; a late duplicate never rewinds a prepared microtask.
            try:
                self.task_store.compare_and_set_microtask_status(
                    task_id, microtask_id, expected=expected_status, status=MicrotaskStatus.PREPARING
                )
            except TaskStoreError as exc:
                shutil.rmtree(stage_dir, ignore_errors=True)
                raise ManifestStoreError(f"prepare refused: {exc}") from exc
        seen_paths: set[str] = set()
        published = False

        try:
            for source_path, expected_change in target_specs:
                if not isinstance(expected_change, str) or not expected_change.strip():
                    raise ManifestStoreError(
                        "expected_change must be a non-empty string"
                    )
                target, relative_path = self._resolve_target(
                    workspace_root, source_path
                )
                key = os.path.normcase(str(target))
                if key in seen_paths:
                    raise ManifestStoreError(
                        f"duplicate manifest target: {source_path}"
                    )
                seen_paths.add(key)

                entry_id = new_id("manifest")
                snapshot_id = new_id("snapshot")
                exists_before = target.is_file()
                snapshot_rel: str | None = None
                size_before: int | None = None
                sha_before: str | None = None
                if exists_before:
                    before = target.read_bytes()
                    size_before = len(before)
                    sha_before = _sha256(before)
                    binary_path = self._snapshot_binary_path(
                        stage_dir, snapshot_id
                    )
                    _atomic_write_bytes(binary_path, before)
                    copied = binary_path.read_bytes()
                    if len(copied) != size_before or _sha256(copied) != sha_before:
                        raise ManifestStoreError(
                            f"snapshot verification failed: {relative_path}"
                        )
                    after = target.read_bytes()
                    if len(after) != size_before or _sha256(after) != sha_before:
                        raise ManifestStoreError(
                            f"source changed during snapshot capture: {relative_path}"
                        )
                    snapshot_rel = str(
                        binary_path.relative_to(stage_dir)
                    )

                entry = ManifestEntry(
                    manifest_entry_id=entry_id,
                    microtask_id=microtask_id,
                    source_path=relative_path,
                    expected_change=expected_change.strip(),
                    exists_before=exists_before,
                    size_before=size_before,
                    sha256_before=sha_before,
                    snapshot_path=snapshot_rel,
                )
                snapshot = SnapshotRecord(
                    snapshot_id=snapshot_id,
                    microtask_id=microtask_id,
                    manifest_entry_id=entry_id,
                    source_path=relative_path,
                    exists_before=exists_before,
                    size_before=size_before,
                    sha256_before=sha_before,
                    snapshot_path=snapshot_rel,
                )
                _atomic_write_json(
                    self._entry_path(stage_dir, entry_id),
                    record_to_dict(entry),
                )
                _atomic_write_json(
                    self._snapshot_meta_path(stage_dir, snapshot_id),
                    record_to_dict(snapshot),
                )
                manifest.entry_ids.append(entry_id)
                manifest.snapshot_ids.append(snapshot_id)

            manifest.status = ManifestStatus.VERIFIED
            manifest.updated_at = utc_now_iso()
            self._write_manifest(stage_dir, manifest)
            os.replace(stage_dir, final_dir)
            published = True
            if expected_status is None:
                self.task_store.set_microtask_status(
                    task_id, microtask_id, MicrotaskStatus.BACKUP_VERIFIED
                )
            else:
                self.task_store.compare_and_set_microtask_status(
                    task_id, microtask_id, expected=MicrotaskStatus.PREPARING,
                    status=MicrotaskStatus.BACKUP_VERIFIED,
                )
            self.verify_restore_point(task_id, microtask_id)
            return self.open_manifest(task_id, microtask_id)
        except Exception as exc:
            if not published:
                shutil.rmtree(stage_dir, ignore_errors=True)
                self._best_effort_microtask_status(
                    task_id, microtask_id, MicrotaskStatus.BLOCKED_PREPARE,
                    expected=_PREPARE_FROM | {MicrotaskStatus.PREPARING},
                )
            # published: the restore point is the authority now. A failed status
            # write leaves PREPARING (W2, reconciled after re-verification); a
            # failed verification of a just written BACKUP_VERIFIED blocks it the
            # usual way (manifest + microtask, under the mutation lock).
            elif self.task_store.open_microtask(task_id, microtask_id).status is MicrotaskStatus.BACKUP_VERIFIED:
                self._block_restore_point(
                    task_id, microtask_id, final_dir, expected_status=MicrotaskStatus.BACKUP_VERIFIED
                )
            if isinstance(exc, ManifestStoreError):
                raise
            raise ManifestStoreError(
                f"cannot prepare restore point for {task_id}/{microtask_id}"
            ) from exc

    def reconcile_interrupted_preparation(
        self,
        task_id: str,
        microtask_id: str,
        *,
        lock_timeout: float = 1.0,
    ) -> dict:
        """Repair #4: deterministic restart recovery of a preparation that died.

        Decided from persistent evidence only, under the preparation lock (a
        running preparation is never touched: PREPARATION_IN_PROGRESS):
        - W2, a published restore point: re-verified (pure); intact ->
          BACKUP_VERIFIED (the captured original pre-state is kept, never
          recaptured); corrupt or unreadable -> fail-closed BLOCKED_PREPARE,
          the restore point stays as evidence;
        - W1, nothing published: the unpublished stage directories are
          discarded and the microtask becomes BLOCKED_PREPARE, from which the
          state machine prepares again (the microtask was never ACTIVE, so no
          normal mutation could have changed its pre-state through the server).
        Idempotent: a microtask that is no longer PREPARING is left as it is.
        """
        try:
            lock = self._prepare_lock(task_id, microtask_id, timeout=lock_timeout)
            lock.acquire()
        except StoreLockTimeout:
            return {
                "result": "PREPARATION_IN_PROGRESS",
                "microtask_id": microtask_id,
                "physical_mutation_performed": False,
            }
        try:
            micro = self.task_store.open_microtask(task_id, microtask_id)
            outcome = {"microtask_id": microtask_id, "physical_mutation_performed": False}
            if micro.status is not MicrotaskStatus.PREPARING:
                return dict(outcome, result="NOT_INTERRUPTED", microtask_status=micro.status.value)
            work_dir = self._work_dir(task_id, microtask_id)
            final_dir = work_dir / self.RESTORE_DIR
            discarded = self._discard_stages(work_dir)
            if final_dir.exists():
                try:
                    manifest = self.verify_restore_point(task_id, microtask_id)
                except ManifestStoreError as exc:
                    self._block_restore_point(
                        task_id, microtask_id, final_dir, expected_status=MicrotaskStatus.PREPARING
                    )
                    return dict(
                        outcome,
                        result="PREPARATION_BLOCKED",
                        evidence="PUBLISHED_RESTORE_POINT_INVALID",
                        reason=str(exc),
                        discarded_stages=discarded,
                        microtask_status=self.task_store.open_microtask(task_id, microtask_id).status.value,
                    )
                self.task_store.compare_and_set_microtask_status(
                    task_id, microtask_id, expected=MicrotaskStatus.PREPARING,
                    status=MicrotaskStatus.BACKUP_VERIFIED,
                )
                return dict(
                    outcome,
                    result="PREPARATION_COMPLETED",
                    evidence="PUBLISHED_RESTORE_POINT",
                    manifest_id=manifest.manifest_id,
                    discarded_stages=discarded,
                    microtask_status=MicrotaskStatus.BACKUP_VERIFIED.value,
                )
            self.task_store.compare_and_set_microtask_status(
                task_id, microtask_id, expected=MicrotaskStatus.PREPARING,
                status=MicrotaskStatus.BLOCKED_PREPARE,
            )
            return dict(
                outcome,
                result="PREPARATION_DISCARDED",
                evidence="NO_PUBLISHED_RESTORE_POINT",
                discarded_stages=discarded,
                microtask_status=MicrotaskStatus.BLOCKED_PREPARE.value,
            )
        finally:
            lock.release()

    def _load_paired_records(
        self, task_id: str, microtask_id: str, *, active_only: bool = False
    ) -> tuple[ManifestRecord, list[tuple[ManifestEntry, SnapshotRecord]], Path]:
        manifest = self.open_manifest(
            task_id, microtask_id, active_only=active_only
        )
        entries = self.list_entries(
            task_id, microtask_id, active_only=active_only
        )
        snapshots = self.list_snapshots(
            task_id, microtask_id, active_only=active_only
        )
        restore_dir = self._restore_dir(
            task_id, microtask_id, active_only=active_only
        )
        if len(entries) != len(snapshots):
            raise ManifestStoreError("manifest entry/snapshot counts differ")
        pairs: list[tuple[ManifestEntry, SnapshotRecord]] = []
        for entry, snapshot in zip(entries, snapshots):
            if snapshot.manifest_entry_id != entry.manifest_entry_id:
                raise ManifestStoreError("entry/snapshot identity mismatch")
            if snapshot.source_path != entry.source_path:
                raise ManifestStoreError("entry/snapshot source_path mismatch")
            if snapshot.exists_before != entry.exists_before:
                raise ManifestStoreError("entry/snapshot pre-state mismatch")
            pairs.append((entry, snapshot))
        return manifest, pairs, restore_dir

    def verify_restore_point(
        self,
        task_id: str,
        microtask_id: str,
        *,
        active_only: bool = False,
        expected_status: MicrotaskStatus | None = None,
    ) -> ManifestRecord:
        try:
            manifest, pairs, restore_dir = self._load_paired_records(
                task_id, microtask_id, active_only=active_only
            )
            if manifest.status != ManifestStatus.VERIFIED:
                raise ManifestStoreError(
                    f"restore point is not VERIFIED: {manifest.status.value}"
                )
            for entry, snapshot in pairs:
                if snapshot.exists_before:
                    if not snapshot.snapshot_path:
                        raise ManifestStoreError(
                            f"missing snapshot_path: {entry.source_path}"
                        )
                    binary_path = self._snapshot_binary_path(
                        restore_dir, snapshot.snapshot_id
                    )
                    expected_rel = str(binary_path.relative_to(restore_dir))
                    if snapshot.snapshot_path != expected_rel:
                        raise ManifestStoreError(
                            f"snapshot_path mismatch: {entry.source_path}"
                        )
                    if not binary_path.is_file():
                        raise ManifestStoreError(
                            f"snapshot binary is missing: {entry.source_path}"
                        )
                    data = binary_path.read_bytes()
                    if len(data) != snapshot.size_before:
                        raise ManifestStoreError(
                            f"snapshot size mismatch: {entry.source_path}"
                        )
                    if _sha256(data) != snapshot.sha256_before:
                        raise ManifestStoreError(
                            f"snapshot hash mismatch: {entry.source_path}"
                        )
                elif snapshot.snapshot_path is not None:
                    raise ManifestStoreError(
                        f"new target unexpectedly has snapshot bytes: {entry.source_path}"
                    )
            return manifest
        except ManifestStoreError:
            if active_only:
                try:
                    restore_dir = self._restore_dir(
                        task_id, microtask_id, active_only=True
                    )
                    self._block_restore_point(
                        task_id, microtask_id, restore_dir, expected_status=expected_status
                    )
                except (ManifestStoreError, TaskStoreError):
                    pass
            raise

    def restore_plan(self, task_id: str, microtask_id: str) -> dict:
        """Verified, side-effect-free restore point view for tracked rollback (RC-4).

        Unlike ``verify_restore_point(active_only=True)`` this never blocks the
        manifest or changes microtask status: any integrity problem only raises.
        Returns the manifest identity, a fingerprint of the restore point and,
        per entry, the exact pre-state plus verified snapshot bytes.
        """
        manifest, pairs, restore_dir = self._load_paired_records(
            task_id, microtask_id, active_only=True
        )
        if manifest.status != ManifestStatus.VERIFIED:
            raise ManifestStoreError(
                f"restore point is not VERIFIED: {manifest.status.value}"
            )
        items = []
        for entry, snapshot in pairs:
            if snapshot.size_before != entry.size_before or snapshot.sha256_before != entry.sha256_before:
                raise ManifestStoreError(f"entry/snapshot pre-state mismatch: {entry.source_path}")
            data: bytes | None = None
            if snapshot.exists_before:
                binary_path = self._snapshot_binary_path(restore_dir, snapshot.snapshot_id)
                if snapshot.snapshot_path != str(binary_path.relative_to(restore_dir)):
                    raise ManifestStoreError(f"snapshot_path mismatch: {entry.source_path}")
                try:
                    data = binary_path.read_bytes()
                except OSError as exc:
                    raise ManifestStoreError(
                        f"snapshot binary is unreadable: {entry.source_path}"
                    ) from exc
                if len(data) != snapshot.size_before or _sha256(data) != snapshot.sha256_before:
                    raise ManifestStoreError(f"snapshot integrity failure: {entry.source_path}")
            elif snapshot.snapshot_path is not None or snapshot.sha256_before is not None:
                raise ManifestStoreError(
                    f"new target unexpectedly has snapshot bytes: {entry.source_path}"
                )
            items.append(
                {
                    "manifest_entry_id": entry.manifest_entry_id,
                    "snapshot_id": snapshot.snapshot_id,
                    "source_path": entry.source_path,
                    "expected_change": entry.expected_change,
                    "exists_before": snapshot.exists_before,
                    "size_before": snapshot.size_before,
                    "sha256_before": snapshot.sha256_before,
                    "snapshot_bytes": data,
                }
            )
        identity = [
            [
                item["manifest_entry_id"],
                item["snapshot_id"],
                item["source_path"],
                item["exists_before"],
                item["size_before"],
                item["sha256_before"],
            ]
            for item in items
        ]
        fingerprint = _sha256(
            json.dumps([manifest.manifest_id, identity], separators=(",", ":")).encode("utf-8")
        )
        return {
            "manifest_id": manifest.manifest_id,
            "restore_point_fingerprint": fingerprint,
            "items": items,
        }

    def restore_microtask(self, task_id: str, microtask_id: str) -> ManifestRecord:
        manifest = self.verify_restore_point(
            task_id, microtask_id, active_only=True
        )
        try:
            _, pairs, restore_dir = self._load_paired_records(
                task_id, microtask_id, active_only=True
            )
            workspace_root = self._workspace_root(task_id)
            actions: list[tuple[Path, SnapshotRecord, bytes | None]] = []

            for entry, snapshot in pairs:
                target, relative = self._resolve_target(
                    workspace_root, entry.source_path
                )
                if relative != entry.source_path:
                    raise ManifestStoreError(
                        f"target normalization drift: {entry.source_path}"
                    )
                if snapshot.exists_before:
                    if target.exists() and not target.is_file():
                        raise ManifestStoreError(
                            f"restore target is not a file: {entry.source_path}"
                        )
                    if not target.parent.is_dir():
                        raise ManifestStoreError(
                            f"restore parent missing: {entry.source_path}"
                        )
                    binary_path = self._snapshot_binary_path(
                        restore_dir, snapshot.snapshot_id
                    )
                    expected_rel = str(binary_path.relative_to(restore_dir))
                    if snapshot.snapshot_path != expected_rel:
                        raise ManifestStoreError(
                            f"snapshot_path mismatch: {entry.source_path}"
                        )
                    data = binary_path.read_bytes()
                    actions.append((target, snapshot, data))
                else:
                    if target.exists() and target.is_dir():
                        raise ManifestStoreError(
                            f"new-file restore target became a directory: {entry.source_path}"
                        )
                    actions.append((target, snapshot, None))

            for target, snapshot, data in actions:
                if snapshot.exists_before:
                    assert data is not None
                    _atomic_write_bytes(target, data)
                    restored = target.read_bytes()
                    if _sha256(restored) != snapshot.sha256_before:
                        raise ManifestStoreError(
                            f"restored hash mismatch: {snapshot.source_path}"
                        )
                elif target.exists() or target.is_symlink():
                    target.unlink()

            for target, snapshot, _ in actions:
                if snapshot.exists_before:
                    if not target.is_file():
                        raise ManifestStoreError(
                            f"restored file is missing: {snapshot.source_path}"
                        )
                elif target.exists() or target.is_symlink():
                    raise ManifestStoreError(
                        f"new-file rollback did not remove target: {snapshot.source_path}"
                    )
        except Exception as exc:
            self._best_effort_microtask_status(
                task_id, microtask_id, MicrotaskStatus.RECOVERY_REQUIRED
            )
            if isinstance(exc, ManifestStoreError):
                raise
            raise ManifestStoreError(
                f"restore failed for {task_id}/{microtask_id}"
            ) from exc

        self.task_store.set_microtask_status(
            task_id, microtask_id, MicrotaskStatus.BACKUP_VERIFIED
        )
        return manifest
