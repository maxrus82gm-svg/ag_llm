"""Server-owned microtask state machine for Web Alarm Workspace WA-2.2."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .event_checkpoint_store import (
    MICROTASK_ABANDONED,
    MICROTASK_INTENT,
    MICROTASK_REAFFIRMED,
    EventCheckpointStore,
    EventCheckpointStoreError,
    MicrotaskHistoryConflict,
    microtask_journal,
)
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


class HistoryUnreadable(ServerStateMachineError):
    """AUD-02b: the TASK event history is unreadable; the step was refused before any write."""

    def __init__(self, task_id: str, microtask_id: str, step: str, reason: str) -> None:
        super().__init__(
            f"{step} step of {task_id}/{microtask_id} refused: the TASK event history is unreadable "
            f"({reason}); nothing was written"
        )
        self.task_id = task_id
        self.microtask_id = microtask_id
        self.step = step
        self.reason = reason


class MicrotaskHistoryContradiction(ServerStateMachineError):
    """R-MT: an open transition intent cannot be resolved from durable facts; operator required."""


class TransitionJournalUnavailable(ServerStateMachineError):
    """R-MT: the write-ahead intent could not be recorded; the status was not changed."""


class ReaffirmationRefused(ServerStateMachineError):
    """A post-hoc re-verification was refused before any write (no proof is produced)."""


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

    def _transition_result(
        self,
        microtask: MicrotaskRecord,
        checkpoint: CheckpointRecord | None,
        history_error: str | None = None,
    ) -> dict[str, object]:
        result: dict[str, object] = {
            "microtask": microtask,
            "checkpoint": checkpoint,
            "event_recorded": history_error is None,
        }
        if checkpoint is None:
            result["checkpoint_error"] = self.last_checkpoint_error
        if history_error is not None:
            result["history_error"] = history_error
            result["next_safe_action"] = (
                f"the transition to {microtask.status.value} IS persisted, but its history event was not "
                f"recorded ({history_error}); do not repeat the transition: repair or reconcile the TASK "
                "event history by manual review, then re-read the projection"
            )
        elif checkpoint is not None:
            result["next_safe_action"] = checkpoint.next_safe_action
        else:
            result["next_safe_action"] = (
                "the state change is persistent but its checkpoint projection was not refreshed "
                f"({self.last_checkpoint_error}); rebuild the checkpoint, then re-read the projection"
            )
        return result

    def _require_readable_history(self, task_id: str, microtask_id: str, step: str) -> None:
        """AUD-02b: a lifecycle step is admitted only over a readable TASK history.

        Checked before the first durable write of a step, before any rejection
        event (which would be appended to a damaged log), and again under the
        lock of the compare-and-set: a status is never persisted while its
        history event is already known to be impossible.
        """
        try:
            self.state.read_events(task_id)
        except EventCheckpointStoreError as exc:
            raise HistoryUnreadable(task_id, microtask_id, step, str(exc)) from exc

    @staticmethod
    def _require_encodable(**fields: object) -> None:
        """Text recorded in the history must be valid Unicode (no unpaired surrogate)."""
        for name, value in fields.items():
            if isinstance(value, str):
                try:
                    value.encode("utf-8")
                except UnicodeEncodeError as exc:
                    raise ValueError(
                        f"{name} is not valid Unicode text (unpaired surrogate); nothing was written"
                    ) from exc

    def _record_transition(
        self,
        task_id: str,
        microtask_id: str,
        operation_id: str | None,
        payload: dict[str, object],
    ) -> str | None:
        """Append the event of a committed step while its compare-and-set lock is held.

        Returns None when recorded, else why not. The status IS persisted (the
        commit point passed), so this failure is reported with the result and
        never turned into a refusal of a step that already happened.
        """
        try:
            self.state.append_event(
                task_id,
                "MICROTASK_TRANSITION",
                microtask_id=microtask_id,
                operation_id=operation_id,
                payload=payload,
            )
        except (EventCheckpointStoreError, UnicodeEncodeError) as exc:
            return f"{type(exc).__name__}: {exc}"
        return None

    # --- R-MT: journaled lifecycle steps (AUD-02b-R) ----------------------------------------
    def _resolve_locked(self, task_id: str, microtask_id: str, step: str) -> list[dict[str, object]]:
        """Reconcile open intents of this microtask (caller holds the mutation lock).

        Reads the whole history, so it also proves it readable. Only the
        deterministic outcomes are written (see ``microtask_journal``).
        """
        try:
            return self.state.resolve_microtask_intents_locked(task_id, microtask_id)
        except MicrotaskHistoryConflict as exc:
            raise MicrotaskHistoryContradiction(
                f"{step} step of {task_id}/{microtask_id} refused: {exc}; nothing was written, "
                "operator review is required"
            ) from exc
        except EventCheckpointStoreError as exc:
            raise HistoryUnreadable(task_id, microtask_id, step, str(exc)) from exc

    def _resolve_entry(self, task_id: str, microtask_id: str, step: str) -> None:
        """A step continues only from a proven state: reconcile before any check or write."""
        with self.tasks.mutation_lock(task_id):
            self._resolve_locked(task_id, microtask_id, step)

    def _journaled_cas_locked(
        self,
        task_id: str,
        microtask_id: str,
        current: MicrotaskStatus,
        requested: MicrotaskStatus,
        payload: dict[str, object],
        operation_id: str | None,
        *,
        activate: bool = False,
    ) -> tuple[str | None, MicrotaskRecord | None, str | None]:
        """intent -> compare-and-set -> commit, all under the mutation lock held by the caller.

        The intent (from, to, verification evidence, the record's updated_at) is
        durable before the status moves, so a process death at any point leaves
        a state ``microtask_journal`` resolves from durable facts alone.
        Returns (refusal reason, None, None) or (None, updated record, history
        error or None).
        """
        self._resolve_locked(task_id, microtask_id, requested.value)
        record = self.tasks.open_microtask(task_id, microtask_id)
        if record.status is not current:
            conflict = MicrotaskStatusConflict(task_id, microtask_id, {current}, record.status)
            return self._stale_reason(current, requested, conflict), None, None
        try:
            intent = self.state.append_event(
                task_id, MICROTASK_INTENT, microtask_id=microtask_id, operation_id=operation_id,
                payload=dict(payload, basis_updated_at=record.updated_at),
            )
        except (EventCheckpointStoreError, UnicodeEncodeError) as exc:
            raise TransitionJournalUnavailable(
                f"{requested.value} step of {task_id}/{microtask_id} refused: its intent could not be "
                f"recorded ({exc}); the status was not changed"
            ) from exc

        def abandon(reason: str) -> None:
            try:
                self.state.append_event(
                    task_id, MICROTASK_ABANDONED, microtask_id=microtask_id, operation_id=operation_id,
                    payload={"intent_id": intent.event_id, "from": current.value, "to": requested.value,
                             "reason": reason},
                )
            except (EventCheckpointStoreError, UnicodeEncodeError):
                pass  # stays open; resolved later from the unchanged record

        try:
            updated = self.tasks.compare_and_set_microtask_status_locked(
                task_id, microtask_id, expected=current, status=requested, activate=activate
            )
        except MicrotaskStatusConflict as exc:
            abandon(f"compare-and-set refused: {exc}")
            return self._stale_reason(current, requested, exc), None, None
        except Exception as exc:
            abandon(f"status write failed: {type(exc).__name__}")
            raise
        return None, updated, self._record_transition(
            task_id, microtask_id, operation_id, dict(payload, intent_id=intent.event_id)
        )

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
        # AUD-02b: no restore point, status or rejection event over a history
        # that could not record the step. The manifest store takes its own
        # locks, so this is an entry check; a later history failure is reported.
        self._require_encodable(operation_id=operation_id)
        self._require_readable_history(task_id, microtask_id, "prepare")
        self._resolve_entry(task_id, microtask_id, "prepare")
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
        history_error = None
        try:  # the restore point and its status are persisted: report, never refuse
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
        except EventCheckpointStoreError as exc:
            history_error = f"{type(exc).__name__}: {exc}"
        checkpoint = self._write_checkpoint(
            task_id,
            microtask_id,
            last_operation_id=operation_id,
        )
        result: dict[str, object] = {
            "manifest": manifest,
            "microtask": micro,
            "checkpoint": checkpoint,
            "event_recorded": history_error is None,
        }
        if checkpoint is None:
            result["checkpoint_error"] = self.last_checkpoint_error
        if history_error is not None:
            result["history_error"] = history_error
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
        payload: dict[str, object],
        operation_id: str | None,
    ) -> tuple[str | None, MicrotaskRecord | None, str | None]:
        """Repair #3 (F-B): VERIFIED only for a microtask without open recovery.

        The recovery picture is the canonical projection built while holding
        the operation TASK lock (Resolver acceptance, RC-6 settlement, operation
        lifecycle) and the mutation lock (microtask lifecycle), and the
        compare-and-set happens in that same section: an accepted recovery
        action and the verification of the same microtask can no longer race.
        AUD-02b: the history is checked and the transition event appended in
        that section too. Returns (refusal reason, None, None) or (None,
        updated record, history error or None); the caller rejects only after
        the locks are released (``_reject`` rebuilds the checkpoint under the
        TASK lock).
        """
        from .microtask_gate import verification_refusal
        from .projection import ProjectionService

        if self._projection is None:
            self._projection = ProjectionService(self.tasks.storage_root)
        service = self._projection
        with service.operations.task_lock(task_id):
            with self.tasks.mutation_lock(task_id):
                self._resolve_locked(task_id, microtask_id, MicrotaskStatus.VERIFIED.value)
                try:
                    projection = service.build(task_id)
                except Exception as exc:  # unprovable recovery picture: fail closed
                    return f"recovery facts are unavailable: {type(exc).__name__}: {exc}", None, None
                refusal = verification_refusal(projection, microtask_id)
                if refusal is not None:
                    return f"open recovery blocks VERIFIED ({refusal[0]}): {refusal[1]}", None, None
                # R-MT: the verification evidence is durable (intent) before VERIFIED is
                return self._journaled_cas_locked(
                    task_id, microtask_id, current, MicrotaskStatus.VERIFIED, payload, operation_id
                )

    def _admit_active(
        self,
        task_id: str,
        microtask_id: str,
        current: MicrotaskStatus,
        payload: dict[str, object],
        operation_id: str | None,
    ) -> tuple[str | None, MicrotaskRecord | None, str | None]:
        """WA-014: ACTIVE only for a microtask that can still get mutation authority.

        The recovery disposition (``microtask_gate.activation_refusal``) is read
        while holding the operation TASK lock, which every writer of a
        disposition holds too (Resolver acceptance, RC-4 session creation,
        RC-6 settlement), and the activation compare-and-set (mutation lock;
        it re-checks the earlier microtasks and the single ACTIVE one, F4)
        happens inside that same TASK-locked section: an ABORT/ROLLBACK
        accepted before the activation refuses it, one accepted after it found
        an ACTIVE stage that could have had authority. AUD-02b: the history is
        checked and the transition event appended under the same mutation lock
        as the compare-and-set. Returns (refusal reason, None, None) or (None,
        updated record, history error or None); the caller rejects only after
        the lock is released.
        """
        from .microtask_gate import activation_refusal
        from .projection import ProjectionService

        if self._projection is None:
            self._projection = ProjectionService(self.tasks.storage_root)
        service = self._projection
        with service.operations.task_lock(task_id):
            refusal = activation_refusal(
                task_id,
                microtask_id,
                operations=service.operations,
                resolver=service.resolver,
                rollbacks=service.rollbacks,
            )
            if refusal is not None:
                return f"recovery disposition blocks ACTIVE ({refusal[0]}): {refusal[1]}", None, None
            return self._commit(
                task_id, microtask_id, current, MicrotaskStatus.ACTIVE, payload, operation_id, activate=True
            )

    def _commit(
        self,
        task_id: str,
        microtask_id: str,
        current: MicrotaskStatus,
        requested: MicrotaskStatus,
        payload: dict[str, object],
        operation_id: str | None,
        *,
        activate: bool = False,
    ) -> tuple[str | None, MicrotaskRecord | None, str | None]:
        """AUD-02b / R-MT: the locked commit of a step that is not VERIFIED.

        Under one mutation lock: open intents reconciled (history proven
        readable), write-ahead intent, compare-and-set (with ``activate`` the
        activation rules and plan pointer, F4) and the commit event. Returns
        (refusal reason, None, None) or (None, updated record, history error or
        None).
        """
        with self.tasks.mutation_lock(task_id):
            return self._journaled_cas_locked(
                task_id, microtask_id, current, requested, payload, operation_id, activate=activate
            )

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

        AUD-02b: the status and its MICROTASK_TRANSITION event are written in
        one locked section. A step whose event could not be recorded (text
        that is not valid Unicode, a history that is already unreadable) is
        refused before any write, a rejection event included; a history
        failure after the compare-and-set is reported as committed
        (``event_recorded`` false), never as a refusal.
        """
        requested = MicrotaskStatus(requested_status)
        micro = self.tasks.open_microtask(task_id, microtask_id)
        current = micro.status
        self._require_encodable(verification_evidence=verification_evidence, operation_id=operation_id)
        self._require_readable_history(task_id, microtask_id, requested.value)
        # R-MT: continue only from a proven state (an interrupted step is reconciled first)
        self._resolve_entry(task_id, microtask_id, requested.value)

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

        payload: dict[str, object] = {
            "from": current.value,
            "to": requested.value,
            "verification_evidence": (
                verification_evidence.strip()
                if isinstance(verification_evidence, str)
                and verification_evidence.strip()
                else None
            ),
        }
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
            refusal, updated, history_error = self._admit_verified(
                task_id, microtask_id, current, payload, operation_id
            )
        elif requested == MicrotaskStatus.ACTIVE:
            # WA-014: no ACTIVE over an ABORT/ROLLBACK disposition (checked under the locks)
            refusal, updated, history_error = self._admit_active(
                task_id, microtask_id, current, payload, operation_id
            )
        else:
            refusal, updated, history_error = self._commit(
                task_id, microtask_id, current, requested, payload, operation_id
            )
        if refusal is not None:
            self._reject(task_id, microtask_id, requested, refusal, operation_id=operation_id)
        checkpoint = self._write_checkpoint(
            task_id,
            microtask_id,
            last_operation_id=operation_id,
        )
        return self._transition_result(updated, checkpoint, history_error)

    def reaffirm_verification(
        self,
        task_id: str,
        microtask_id: str,
        verification_evidence: str,
        *,
        operation_id: str | None = None,
    ) -> dict[str, object]:
        """Safe post-hoc re-verification of a VERIFIED microtask whose evidence is not recorded.

        No physical mutation and no status change. The caller re-checked the
        result without mutating it and supplies new evidence; the same VERIFIED
        gates run under the same locks (no open operation fate or recovery for
        this microtask). The new event says it is a later re-verification
        (``original_evidence_recorded: false``): the lost original evidence is
        never reconstructed. Refused before any write when the microtask is not
        VERIFIED, already proven, or the gates do not hold.
        """
        from .microtask_gate import verification_refusal
        from .projection import ProjectionService

        if not isinstance(verification_evidence, str) or not verification_evidence.strip():
            raise ValueError("verification_evidence must be a non-empty string")
        self._require_encodable(verification_evidence=verification_evidence, operation_id=operation_id)
        self._require_readable_history(task_id, microtask_id, "reaffirm")
        if self._projection is None:
            self._projection = ProjectionService(self.tasks.storage_root)
        service = self._projection
        with service.operations.task_lock(task_id):
            with self.tasks.mutation_lock(task_id):
                self._resolve_locked(task_id, microtask_id, "reaffirm")
                record = self.tasks.open_microtask(task_id, microtask_id)
                if record.status is not MicrotaskStatus.VERIFIED:
                    raise ReaffirmationRefused(
                        f"reaffirm of {task_id}/{microtask_id} refused: it is {record.status.value}, not VERIFIED; "
                        "nothing was written"
                    )
                facts = microtask_journal(self.state.read_events(task_id), self.state.microtask_statuses(task_id))
                if microtask_id not in facts["unproven_verified"]:
                    raise ReaffirmationRefused(
                        f"reaffirm of {task_id}/{microtask_id} refused: its verification evidence is already "
                        "recorded; nothing was written"
                    )
                try:
                    projection = service.build(task_id)
                except Exception as exc:  # unprovable recovery picture: fail closed
                    raise ReaffirmationRefused(
                        f"reaffirm of {task_id}/{microtask_id} refused: recovery facts are unavailable "
                        f"({type(exc).__name__}: {exc}); nothing was written"
                    ) from exc
                refusal = verification_refusal(projection, microtask_id)
                if refusal is not None:
                    raise ReaffirmationRefused(
                        f"reaffirm of {task_id}/{microtask_id} refused: a safe re-check is not possible "
                        f"({refusal[0]}: {refusal[1]}); operator decision required; nothing was written"
                    )
                try:
                    event = self.state.append_event(
                        task_id, MICROTASK_REAFFIRMED, microtask_id=microtask_id, operation_id=operation_id,
                        payload={"verification_evidence": verification_evidence.strip(),
                                 "original_evidence_recorded": False,
                                 "status_updated_at": record.updated_at,
                                 "kind": "post-hoc re-verification without mutation"},
                    )
                except EventCheckpointStoreError as exc:
                    raise ReaffirmationRefused(
                        f"reaffirm of {task_id}/{microtask_id} refused: the evidence could not be recorded "
                        f"({exc}); nothing was proven"
                    ) from exc
        checkpoint = self._write_checkpoint(task_id, microtask_id, last_operation_id=operation_id)
        return {"microtask": record, "checkpoint": checkpoint, "event_id": event.event_id,
                "reaffirmed": True, "physical_mutation_performed": False}
