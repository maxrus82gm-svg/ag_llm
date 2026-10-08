"""Server-owned microtask state machine for Web Alarm Workspace WA-2.2."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .event_checkpoint_store import EventCheckpointStore, EventCheckpointStoreError
from .manifest_store import ManifestSnapshotStore, ManifestStoreError
from .models import (
    CheckpointRecord,
    ManifestRecord,
    MicrotaskRecord,
    MicrotaskStatus,
    record_to_dict,
)
from .task_store import MicrotaskStatusConflict, TaskStore, TaskStoreError


@dataclass(slots=True)
class TransitionRejected(RuntimeError):
    task_id: str
    microtask_id: str
    current_status: MicrotaskStatus
    requested_status: MicrotaskStatus
    reason: str
    next_safe_action: str

    def __str__(self) -> str:
        return (
            f"{self.current_status.value} -> {self.requested_status.value} rejected: "
            f"{self.reason}"
        )


class ServerStateMachineError(RuntimeError):
    """Raised when authoritative state cannot be read or persisted."""


class SnapshotNotVerified(ServerStateMachineError):
    """Pure snapshot verification found the restore point not intact (nothing was written)."""

    def __init__(self, task_id: str, microtask_id: str, reason: str) -> None:
        super().__init__(f"restore point of {task_id}/{microtask_id} is not verified: {reason}")
        self.task_id = task_id
        self.microtask_id = microtask_id
        self.reason = reason


class ServerStateMachine:
    """Authoritative WA-2.2 policy for Server-side microtask transitions."""

    _ALLOWED: dict[MicrotaskStatus, set[MicrotaskStatus]] = {
        # PREPARING/BACKUP_VERIFIED are produced only by prepare_microtask().
        # Public transition requests cannot manufacture snapshot progress.
        MicrotaskStatus.PLANNED: set(),
        MicrotaskStatus.PREPARING: set(),
        MicrotaskStatus.BACKUP_VERIFIED: {MicrotaskStatus.READY},
        MicrotaskStatus.READY: {MicrotaskStatus.ACTIVE},
        MicrotaskStatus.ACTIVE: {
            MicrotaskStatus.DONE,
            MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT,
        },
        MicrotaskStatus.DONE: {
            MicrotaskStatus.VERIFIED,
            MicrotaskStatus.FAILED_VERIFICATION,
            MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT,
        },
        MicrotaskStatus.VERIFIED: set(),
        MicrotaskStatus.BLOCKED_PREPARE: set(),
        MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT: {
            MicrotaskStatus.RECOVERY_REQUIRED,
        },
        MicrotaskStatus.RECOVERY_REQUIRED: set(),
        MicrotaskStatus.FAILED_VERIFICATION: {MicrotaskStatus.ACTIVE},
    }

    def __init__(self, storage_root: str | Path | None = None) -> None:
        self.tasks = TaskStore(storage_root)
        self.manifests = ManifestSnapshotStore(storage_root)
        self.state = EventCheckpointStore(storage_root)
        self._projection = None
        self.last_checkpoint_error: str | None = None

    def next_safe_action(
        self,
        task_id: str,
        microtask_id: str,
        *,
        status: MicrotaskStatus | None = None,
    ) -> str:
        micro = self.tasks.open_microtask(task_id, microtask_id)
        current = status or micro.status
        if current == MicrotaskStatus.PLANNED:
            return f"declare targets and prepare restore point for {microtask_id}"
        if current == MicrotaskStatus.PREPARING:
            return (
                f"restore-point preparation of {microtask_id} is running or was interrupted; real Workspace "
                "mutation is not allowed. Run recover: an interrupted preparation is reconciled from persistent "
                "evidence (a published restore point is re-verified and completed to BACKUP_VERIFIED; without "
                "one, the unpublished capture is discarded and the microtask becomes BLOCKED_PREPARE to be "
                "prepared again)"
            )
        if current == MicrotaskStatus.BACKUP_VERIFIED:
            return f"transition {microtask_id} to READY"
        if current == MicrotaskStatus.READY:
            return f"transition {microtask_id} to ACTIVE before implementation"
        if current == MicrotaskStatus.ACTIVE:
            return f"perform scoped implementation for {microtask_id}, then transition to DONE"
        if current == MicrotaskStatus.DONE:
            return f"run verification and transition {microtask_id} to VERIFIED with verification_evidence"
        if current == MicrotaskStatus.VERIFIED:
            plan = self.tasks.open_plan(task_id)
            try:
                index = plan.microtask_ids.index(microtask_id)
            except ValueError:
                return "reconcile TASK plan; verified microtask is missing from plan"
            if index + 1 < len(plan.microtask_ids):
                return f"prepare next microtask {plan.microtask_ids[index + 1]}"
            return "complete TASK or create the next planned microtask"
        if current == MicrotaskStatus.BLOCKED_PREPARE:
            if self._restore_point_exists(task_id, microtask_id):
                # Repair #4: prepare is refused while a (blocked) restore point exists
                return (
                    f"the restore point of {microtask_id} failed verification and is kept as evidence "
                    "(BLOCKED_PREPARE); prepare is refused while it exists: manual review and repair of "
                    "the restore point is required"
                )
            return "repair preparation blocker, then prepare the restore point again"
        if current == MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT:
            return "reconcile disk state; do not repeat the last operation"
        if current == MicrotaskStatus.RECOVERY_REQUIRED:
            return "run recovery reconciliation; mutation is not allowed"
        if current == MicrotaskStatus.FAILED_VERIFICATION:
            return "fix the current microtask from its verified restore point, then transition to ACTIVE"
        raise ServerStateMachineError(f"unsupported microtask status: {current}")

    def _restore_point_exists(self, task_id: str, microtask_id: str) -> bool:
        try:
            work_dir = self.tasks.microtask_directory(task_id, microtask_id)
        except TaskStoreError:
            return False
        return (work_dir / ManifestSnapshotStore.RESTORE_DIR).exists()

    def _write_checkpoint(
        self,
        task_id: str,
        microtask_id: str,
        *,
        last_operation_id: str | None = None,
    ) -> CheckpointRecord | None:
        """RC-5: authoritative state first, projection second.

        The checkpoint is rebuilt from the canonical projection; the caller's
        ``microtask_id`` / ``last_operation_id`` labels are history (events),
        never checkpoint content. A projection write failure does not undo the
        state change already persisted: it leaves the old checkpoint, which then
        validates as STALE, and is reported in ``last_checkpoint_error``.
        """
        from .projection import ProjectionError, ProjectionService

        if self._projection is None:
            self._projection = ProjectionService(self.tasks.storage_root)
        try:
            checkpoint = self._projection.rebuild_checkpoint(task_id)["checkpoint"]
        except ProjectionError as exc:
            self.last_checkpoint_error = str(exc)
            return None
        self.last_checkpoint_error = None
        return checkpoint

    def _transition_result(self, microtask: MicrotaskRecord, checkpoint: CheckpointRecord | None) -> dict[str, object]:
        result: dict[str, object] = {"microtask": microtask, "checkpoint": checkpoint}
        if checkpoint is not None:
            result["next_safe_action"] = checkpoint.next_safe_action
        else:
            result["next_safe_action"] = (
                "the state change is persistent but its checkpoint projection was not refreshed "
                f"({self.last_checkpoint_error}); rebuild the checkpoint, then re-read the projection"
            )
            result["checkpoint_error"] = self.last_checkpoint_error
        return result

    def _reject(
        self,
        task_id: str,
        microtask_id: str,
        requested: MicrotaskStatus,
        reason: str,
        *,
        operation_id: str | None = None,
    ) -> None:
        micro = self.tasks.open_microtask(task_id, microtask_id)
        next_action = self.next_safe_action(task_id, microtask_id)
        self.state.append_event(
            task_id,
            "MICROTASK_TRANSITION_REJECTED",
            microtask_id=microtask_id,
            operation_id=operation_id,
            payload={
                "current_status": micro.status.value,
                "requested_status": requested.value,
                "reason": reason,
                "next_safe_action": next_action,
            },
        )
        self._write_checkpoint(
            task_id,
            microtask_id,
            last_operation_id=operation_id,
        )
        raise TransitionRejected(
            task_id=task_id,
            microtask_id=microtask_id,
            current_status=micro.status,
            requested_status=requested,
            reason=reason,
            next_safe_action=next_action,
        )

    def _require_previous_verified(
        self,
        task_id: str,
        microtask_id: str,
        requested: MicrotaskStatus,
        *,
        operation_id: str | None = None,
    ) -> None:
        plan = self.tasks.open_plan(task_id)
        try:
            index = plan.microtask_ids.index(microtask_id)
        except ValueError:
            self._reject(
                task_id,
                microtask_id,
                requested,
                "microtask is not present in TASK plan",
                operation_id=operation_id,
            )
            return
        for previous_id in plan.microtask_ids[:index]:
            previous = self.tasks.open_microtask(task_id, previous_id)
            if previous.status != MicrotaskStatus.VERIFIED:
                self._reject(
                    task_id,
                    microtask_id,
                    requested,
                    f"previous microtask {previous_id} is {previous.status.value}, not VERIFIED",
                    operation_id=operation_id,
                )
    def _require_verified_snapshot(
        self,
        task_id: str,
        microtask_id: str,
        requested: MicrotaskStatus,
        *,
        operation_id: str | None = None,
        observed: MicrotaskStatus | None = None,
    ) -> ManifestRecord:
        try:
            return self.manifests.verify_restore_point(
                task_id,
                microtask_id,
                active_only=True,
                # an integrity failure blocks the microtask only if its status is
                # still the one this transition decided on (Repair #2A)
                expected_status=observed,
            )
        except (ManifestStoreError, TaskStoreError) as exc:
            self._reject(
                task_id,
                microtask_id,
                requested,
                f"verified restore point required: {exc}",
                operation_id=operation_id,
            )
            raise AssertionError("unreachable") from exc

    def prepare_microtask(
        self,
        task_id: str,
        microtask_id: str,
        targets: Iterable[tuple[str, str]],
        *,
        operation_id: str | None = None,
    ) -> dict[str, object]:
        micro = self.tasks.open_microtask(task_id, microtask_id)
        if micro.status not in {
            MicrotaskStatus.PLANNED,
            MicrotaskStatus.BLOCKED_PREPARE,
        }:
            self._reject(
                task_id,
                microtask_id,
                MicrotaskStatus.PREPARING,
                "prepare is allowed only from PLANNED or BLOCKED_PREPARE",
                operation_id=operation_id,
            )
        self._require_previous_verified(
            task_id,
            microtask_id,
            MicrotaskStatus.PREPARING,
            operation_id=operation_id,
        )
        try:
            manifest = self.manifests.prepare_microtask(
                task_id,
                microtask_id,
                targets,
                # Repair #2A: start only from the status checked above
                expected_status=micro.status,
            )
        except (ManifestStoreError, TaskStoreError) as exc:
            self.state.append_event(
                task_id,
                "MICROTASK_PREPARE_FAILED",
                microtask_id=microtask_id,
                operation_id=operation_id,
                payload={"reason": str(exc)},
            )
            self._write_checkpoint(
                task_id,
                microtask_id,
                last_operation_id=operation_id,
            )
            raise

        micro = self.tasks.open_microtask(task_id, microtask_id)
        self.state.append_event(
            task_id,
            "MICROTASK_PREPARED",
            microtask_id=microtask_id,
            operation_id=operation_id,
            payload={
                "status": micro.status.value,
                "manifest_id": manifest.manifest_id,
                "snapshot_status": "VERIFIED",
            },
        )
        checkpoint = self._write_checkpoint(
            task_id,
            microtask_id,
            last_operation_id=operation_id,
        )
        result: dict[str, object] = {
            "manifest": manifest,
            "microtask": micro,
            "checkpoint": checkpoint,
        }
        if checkpoint is None:
            result["checkpoint_error"] = self.last_checkpoint_error
        return result

    def verify_snapshot(
        self,
        task_id: str,
        microtask_id: str,
        *,
        operation_id: str | None = None,
    ) -> dict[str, object]:
        """Pure restore-point integrity verification (RC-5).

        Success or failure, nothing is written: no event, no checkpoint, no
        manifest/microtask status change (a corrupt snapshot is reported, not
        turned into BLOCKED_PREPARE). The transition path keeps blocking state
        when a real workflow step meets a broken restore point. ``operation_id``
        is accepted for API compatibility only.
        """
        micro = self.tasks.open_microtask(task_id, microtask_id)
        try:
            manifest = self.manifests.verify_restore_point(task_id, microtask_id)
        except (ManifestStoreError, TaskStoreError) as exc:
            raise SnapshotNotVerified(task_id, microtask_id, str(exc)) from exc
        checkpoint = None
        try:
            checkpoint = self.state.read_checkpoint(task_id)
        except EventCheckpointStoreError:
            checkpoint = None  # persisted projection is only shown, never needed here
        return {
            "manifest": manifest,
            "microtask": micro,
            "checkpoint": checkpoint,
            "integrity": "VERIFIED",
            "workflow_mutation_performed": False,
        }
    @staticmethod
    def _stale_reason(current: MicrotaskStatus, requested: MicrotaskStatus, exc: Exception) -> str:
        return (
            f"stale transition: {current.value} -> {requested.value} was decided on "
            f"{current.value}, but {exc}"
        )

    def _admit_verified(
        self,
        task_id: str,
        microtask_id: str,
        current: MicrotaskStatus,
    ) -> tuple[str | None, MicrotaskRecord | None]:
        """Repair #3 (F-B): VERIFIED only for a microtask without open recovery.

        The recovery picture is the canonical projection built while holding
        the operation TASK lock (Resolver acceptance, RC-6 settlement, operation
        lifecycle) and the mutation lock (microtask lifecycle), and the
        compare-and-set happens in that same section: an accepted recovery
        action and the verification of the same microtask can no longer race.
        Returns (refusal reason, None) or (None, updated record); the caller
        rejects only after the locks are released (``_reject`` rebuilds the
        checkpoint under the TASK lock).
        """
        from .microtask_gate import verification_refusal
        from .projection import ProjectionService

        if self._projection is None:
            self._projection = ProjectionService(self.tasks.storage_root)
        service = self._projection
        with service.operations.task_lock(task_id):
            with self.tasks.mutation_lock(task_id):
                try:
                    projection = service.build(task_id)
                except Exception as exc:  # unprovable recovery picture: fail closed
                    return f"recovery facts are unavailable: {type(exc).__name__}: {exc}", None
                refusal = verification_refusal(projection, microtask_id)
                if refusal is not None:
                    return f"open recovery blocks VERIFIED ({refusal[0]}): {refusal[1]}", None
                try:
                    updated = self.tasks.compare_and_set_microtask_status_locked(
                        task_id, microtask_id, expected=current, status=MicrotaskStatus.VERIFIED
                    )
                except MicrotaskStatusConflict as exc:
                    return self._stale_reason(current, MicrotaskStatus.VERIFIED, exc), None
        return None, updated

    def transition(
        self,
        task_id: str,
        microtask_id: str,
        requested_status: MicrotaskStatus | str,
        *,
        verification_evidence: str | None = None,
        operation_id: str | None = None,
        expected_status: MicrotaskStatus | str | None = None,
    ) -> dict[str, object]:
        """Apply one allowed transition as a compare-and-set (Repair #2A).

        The status read here is the basis of every check below; the final
        write re-reads it under the per-TASK mutation lock and is refused if
        it changed meanwhile, so a delayed or concurrent transition can never
        overwrite a newer authoritative status (RECOVERY_REQUIRED from a
        recovery settlement, VERIFIED, ...). ``expected_status`` lets a caller
        that decided on an earlier observation pin that basis explicitly.
        VERIFIED is additionally admitted only while no operation of the
        microtask has an open recovery (Repair #3, ``_admit_verified``).
        """
        requested = MicrotaskStatus(requested_status)
        micro = self.tasks.open_microtask(task_id, microtask_id)
        current = micro.status

        if expected_status is not None and MicrotaskStatus(expected_status) is not current:
            self._reject(
                task_id,
                microtask_id,
                requested,
                (
                    f"stale transition: the caller observed {MicrotaskStatus(expected_status).value}, "
                    f"but the microtask is {current.value}; nothing was written"
                ),
                operation_id=operation_id,
            )

        if requested == current:
            self._reject(
                task_id,
                microtask_id,
                requested,
                "requested status is already current",
                operation_id=operation_id,
            )

        if requested not in self._ALLOWED.get(current, set()):
            self._reject(
                task_id,
                microtask_id,
                requested,
                "transition is not allowed by the server state machine",
                operation_id=operation_id,
            )

        if requested in {
            MicrotaskStatus.PREPARING,
            MicrotaskStatus.BACKUP_VERIFIED,
            MicrotaskStatus.READY,
            MicrotaskStatus.ACTIVE,
        }:
            self._require_previous_verified(
                task_id,
                microtask_id,
                requested,
                operation_id=operation_id,
            )

        if requested in {
            MicrotaskStatus.BACKUP_VERIFIED,
            MicrotaskStatus.READY,
            MicrotaskStatus.ACTIVE,
        }:
            self._require_verified_snapshot(
                task_id,
                microtask_id,
                requested,
                operation_id=operation_id,
                observed=current,
            )

        if requested == MicrotaskStatus.ACTIVE:
            for other in self.tasks.list_microtasks(task_id):
                if (
                    other.microtask_id != microtask_id
                    and other.status == MicrotaskStatus.ACTIVE
                ):
                    self._reject(
                        task_id,
                        microtask_id,
                        requested,
                        f"another microtask {other.microtask_id} is already ACTIVE",
                        operation_id=operation_id,
                    )
            # the current pointer moves inside the locked compare-and-set below

        if requested == MicrotaskStatus.VERIFIED:
            if (
                not isinstance(verification_evidence, str)
                or not verification_evidence.strip()
            ):
                self._reject(
                    task_id,
                    microtask_id,
                    requested,
                    "verification_evidence is required for VERIFIED",
                    operation_id=operation_id,
                )
            refusal, updated = self._admit_verified(task_id, microtask_id, current)
            if refusal is not None:
                self._reject(task_id, microtask_id, requested, refusal, operation_id=operation_id)
        else:
            try:
                updated = self.tasks.compare_and_set_microtask_status(
                    task_id,
                    microtask_id,
                    expected=current,
                    status=requested,
                    activate=requested == MicrotaskStatus.ACTIVE,
                )
            except MicrotaskStatusConflict as exc:
                self._reject(
                    task_id,
                    microtask_id,
                    requested,
                    self._stale_reason(current, requested, exc),
                    operation_id=operation_id,
                )
        self.state.append_event(
            task_id,
            "MICROTASK_TRANSITION",
            microtask_id=microtask_id,
            operation_id=operation_id,
            payload={
                "from": current.value,
                "to": requested.value,
                "verification_evidence": (
                    verification_evidence.strip()
                    if isinstance(verification_evidence, str)
                    and verification_evidence.strip()
                    else None
                ),
            },
        )
        checkpoint = self._write_checkpoint(
            task_id,
            microtask_id,
            last_operation_id=operation_id,
        )
        return self._transition_result(updated, checkpoint)
