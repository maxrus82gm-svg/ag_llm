"""RC-6 project-level bounded recovery/resume orchestration.

The coordinator never executes a normal Workspace mutation. It composes the
authoritative RC-5 projection with existing Resolver, RC-3 ownership and RC-4
rollback services, performs only already-authorized recovery/administrative
steps, rebuilds the projection after every step and stops at a safe boundary.
"""

from __future__ import annotations

import hashlib
import json
from contextlib import ExitStack
from pathlib import Path
from typing import Any

from .manifest_store import ManifestStoreError
from .models import MicrotaskStatus, TaskStatus
from .operation_store import OperationStore, OperationStoreError, OperationTransitionError
from .projection import (
    ProjectionError,
    ProjectionService,
    current_settlements_by_microtask,
    rollback_stage_protected,
    settlement_lifecycle_satisfied,
    settlement_lifecycle_target,
)
from .resolution_store import ResolutionAction, ResolutionResult, ResolutionStoreError
from .resolver_service import ResolverError, ResolverService
from .rollback_service import (
    BLOCKED,
    REJECTED,
    RollbackError,
    RollbackService,
    rollback_needs_rc4_finalize,
)
from .rollback_store import (
    APPLYING,
    AUTHORIZED,
    CLOSED,
    PRESERVATION_FAILED,
    PRESERVED,
    VERIFIED,
    RollbackStoreError,
)
from .target_claim_service import TargetClaimError, TargetClaimService
from .target_claim_store import TargetClaimStoreError, physical_target_key, target_lock_order
from .target_identity import TargetIdentityError, canonical_target
from .task_store import TaskStore, TaskStoreError
from .workspace_registry import WorkspaceRegistryError

READY_FOR_EXECUTION = "READY_FOR_EXECUTION"
READY_FOR_VERIFICATION = "READY_FOR_VERIFICATION"
MANUAL_DECISION_REQUIRED = "MANUAL_DECISION_REQUIRED"
RECOVERY_IN_PROGRESS = "RECOVERY_IN_PROGRESS"
RECOVERY_BLOCKED = "RECOVERY_BLOCKED"
TASK_COMPLETED = "TASK_COMPLETED"
TASK_READY_TO_CLOSE = "TASK_READY_TO_CLOSE"
NO_ACTION_REQUIRED = "NO_ACTION_REQUIRED"
FAIL_CLOSED = "FAIL_CLOSED"

_SETTLED_ROLLBACK = {CLOSED, PRESERVATION_FAILED}
_RECOVERY_MICRO = {
    MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT.value,
    MicrotaskStatus.RECOVERY_REQUIRED.value,
    MicrotaskStatus.FAILED_VERIFICATION.value,
}
# Lifecycle statuses from which the single aggregated settlement disposition of
# a microtask (projection.settlement_lifecycle_target) may be applied.
_TO_DONE_FROM = {
    MicrotaskStatus.ACTIVE,
    MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT,
    MicrotaskStatus.RECOVERY_REQUIRED,
    MicrotaskStatus.DONE,
}
_TO_RECOVERY_REQUIRED_FROM = {
    MicrotaskStatus.ACTIVE,
    MicrotaskStatus.DONE,
    MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT,
    MicrotaskStatus.RECOVERY_REQUIRED,
    MicrotaskStatus.FAILED_VERIFICATION,
}
# RC-4 phases in which rollback apply() can still perform a per-target restore
_ROLLBACK_RESTORE_PHASES = {PRESERVED, AUTHORIZED, APPLYING}
# RC-4 step outcomes that are terminal for the current recover invocation
_STEP_BLOCKED_RESULTS = {BLOCKED, REJECTED}


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


class RecoveryCoordinatorError(RuntimeError):
    """Authoritative recovery state cannot be safely read or advanced."""


class RecoveryCoordinatorBlocked(RecoveryCoordinatorError):
    """A proven ownership/recovery conflict blocks automatic continuation."""


class RecoveryCoordinator:
    """One bounded project-level recovery entry point for one TASK."""

    def __init__(
        self,
        storage_root: str | Path | None = None,
        *,
        lock_timeout: float | None = None,
        default_max_steps: int = 8,
    ) -> None:
        if isinstance(default_max_steps, bool) or not isinstance(default_max_steps, int) or default_max_steps < 1:
            raise ValueError("default_max_steps must be a positive integer")
        self.default_max_steps = default_max_steps
        self.projection = ProjectionService(storage_root, lock_timeout=lock_timeout)
        root = self.projection.tasks.storage_root
        if lock_timeout is None:
            self.operations = OperationStore(root)
            self.tasks = TaskStore(root)
            self.rollbacks = RollbackService(root)
            self.claims = TargetClaimService(root)
        else:
            self.operations = OperationStore(root, lock_timeout=lock_timeout)
            self.tasks = TaskStore(root, lock_timeout=lock_timeout)
            self.rollbacks = RollbackService(root, lock_timeout=lock_timeout)
            self.claims = TargetClaimService(root, lock_timeout=lock_timeout)
        self.resolver = ResolverService(root)

    @staticmethod
    def _step_summary(value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            return {"result": type(value).__name__}
        keys = (
            "result",
            "result_code",
            "reason",
            "changed",
            "replayed",
            "settlement",
            "resolution_id",
            "next_safe_action",
        )
        return {key: value[key] for key in keys if key in value}

    @staticmethod
    def _view(projection: dict[str, Any], operation_id: str | None) -> dict[str, Any] | None:
        if operation_id is None:
            return None
        return next(
            (item for item in projection["operations"] if item["operation_id"] == operation_id),
            None,
        )

    @staticmethod
    def _rollback(projection: dict[str, Any], rollback_id: str | None) -> dict[str, Any] | None:
        if rollback_id is None:
            return None
        return next(
            (item for item in projection["rollbacks"] if item["rollback_id"] == rollback_id),
            None,
        )

    @staticmethod
    def _unexpected_claims(
        projection: dict[str, Any],
        *,
        expected_operation_id: str | None = None,
    ) -> list[dict[str, Any]]:
        result = []
        for claim in projection["ownership"]["active_claims"]:
            owner = claim.get("owner") or {}
            if owner.get("kind") == "ROLLBACK":
                result.append(claim)
                continue
            if expected_operation_id is not None and claim["operation_id"] == expected_operation_id:
                continue
            result.append(claim)
        return result

    def _accepted_resolution_locked(
        self,
        task_id: str,
        operation_id: str,
        resolution_id: str,
        expected_action: ResolutionAction,
        *,
        require_fresh: bool,
    ):
        try:
            record = self.resolver.store.get(task_id, resolution_id)
        except ResolutionStoreError as exc:
            raise RecoveryCoordinatorError(str(exc)) from exc
        if record.operation_id != operation_id or record.action is not expected_action:
            raise RecoveryCoordinatorError("resolution identity/action changed before recovery step")
        if record.result is not ResolutionResult.ACCEPTED:
            raise RecoveryCoordinatorError("recovery step no longer has an accepted resolution")
        if require_fresh:
            fresh = self.resolver.freshness(record)
            if not fresh["fresh"]:
                raise RecoveryCoordinatorError(
                    f"{expected_action.value} resolution is stale ({fresh['code']})"
                )
        try:
            facts = self.resolver.report_facts(
                task_id, record.microtask_id, operation_id
            )
        except ResolverError as exc:
            raise RecoveryCoordinatorError(str(exc)) from exc
        authoritative = facts["next_safe_action"]
        if authoritative is None or authoritative["resolution_id"] != resolution_id:
            chosen = authoritative["resolution_id"] if authoritative is not None else "none"
            raise RecoveryCoordinatorError(
                f"resolution {resolution_id} is no longer authoritative; current is {chosen}"
            )
        return record

    @staticmethod
    def _rollback_open(record: dict[str, Any]) -> bool:
        return not (
            record["status"] in _SETTLED_ROLLBACK
            or (record["status"] == VERIFIED and record["claims_released"])
        )

    def _no_open_rollback_locked(self, task_id: str, operation_id: str) -> None:
        try:
            open_sessions = [
                item
                for item in self.rollbacks.store.list(task_id, operation_id=operation_id)
                if self._rollback_open(item)
            ]
        except RollbackStoreError as exc:
            raise RecoveryCoordinatorError(str(exc)) from exc
        if open_sessions:
            raise RecoveryCoordinatorError(
                "tracked rollback is still open: "
                + ", ".join(item["rollback_id"] for item in open_sessions)
            )

    def _preflight_micro_locked(
        self,
        task_id: str,
        microtask_id: str,
        target: MicrotaskStatus,
        *,
        allowed_from: set[MicrotaskStatus],
        additionally_satisfied: set[MicrotaskStatus] | None = None,
    ):
        """Prove a recovery lifecycle update before any settlement write."""
        current = self.tasks.open_microtask(task_id, microtask_id)
        satisfied = additionally_satisfied or set()
        if current.status is target or current.status in satisfied:
            return current
        if current.status not in allowed_from:
            raise RecoveryCoordinatorError(
                f"microtask {microtask_id} is {current.status.value}; "
                f"cannot recovery-set it to {target.value}"
            )
        return current

    def _set_micro_locked(
        self,
        task_id: str,
        microtask_id: str,
        target: MicrotaskStatus,
        *,
        allowed_from: set[MicrotaskStatus],
        additionally_satisfied: set[MicrotaskStatus] | None = None,
    ) -> dict[str, Any]:
        current = self._preflight_micro_locked(
            task_id,
            microtask_id,
            target,
            allowed_from=allowed_from,
            additionally_satisfied=additionally_satisfied,
        )
        satisfied = additionally_satisfied or set()
        if current.status is target or current.status in satisfied:
            return {
                "changed": False,
                "replayed": True,
                "microtask_status": current.status.value,
            }
        updated = self.tasks.set_microtask_status_locked(task_id, microtask_id, target)
        return {"changed": True, "replayed": False, "microtask_status": updated.status.value}

    def _lock_manifest_targets(
        self,
        stack: ExitStack,
        task_id: str,
        microtask_id: str,
    ) -> dict[str, Any]:
        """Pure final READY proof over every restore-point target.

        Any active RC-3 owner is incompatible with a normal not-yet-authorized
        execution boundary.  Target locks are ephemeral and no claim is written.
        """
        try:
            plan = self.projection.manifests.restore_plan(task_id, microtask_id)
            task = self.tasks.open_task(task_id)
            workspace = self.operations.registry.get(task.workspace_id)
            root = Path(workspace.workspace_root)
            targets = []
            for item in plan["items"]:
                canonical = canonical_target(root, item["source_path"])
                targets.append((physical_target_key(canonical.path), item["source_path"]))
        except (
            ManifestStoreError,
            TaskStoreError,
            WorkspaceRegistryError,
            TargetIdentityError,
            KeyError,
            TypeError,
        ) as exc:
            raise RecoveryCoordinatorBlocked(
                f"restore point is not safe for execution: {exc}"
            ) from exc

        unique: dict[str, str] = {}
        for physical_key, source_path in targets:
            unique.setdefault(physical_key, source_path)
        ordered = target_lock_order(unique)
        for physical_key in ordered:
            stack.enter_context(self.claims._target_lock(physical_key))
            try:
                data = self.claims.claims.load(physical_key)
            except TargetClaimStoreError as exc:
                raise RecoveryCoordinatorError(str(exc)) from exc
            active = data["active"]
            if active is not None:
                raise RecoveryCoordinatorBlocked(
                    "execution target is already owned: "
                    f"{unique[physical_key]} -> "
                    f"{active.get('task_id')}/{active.get('operation_id')}"
                )
        return plan, ordered

    @staticmethod
    def _proof(
        kind: str,
        task_id: str,
        micro,
        plan: dict[str, Any],
        target_keys: list[str],
        *,
        operation=None,
        resolution_id: str | None = None,
    ) -> dict[str, Any]:
        """Immutable identity of what a protected READY proof actually proved."""
        return {
            "result": "READY_PROVED",
            "kind": kind,
            "task_id": task_id,
            "microtask_id": micro.microtask_id,
            "microtask_status": micro.status.value,
            "microtask_updated_at": micro.updated_at,
            "manifest_id": plan["manifest_id"],
            "restore_point_fingerprint": plan["restore_point_fingerprint"],
            "target_set_fingerprint": _digest(target_keys),
            "operation_id": operation.operation_id if operation is not None else None,
            "operation_revision": operation.revision if operation is not None else None,
            "resolution_id": resolution_id,
            "physical_mutation_performed": False,
        }

    @staticmethod
    def _proof_matches(proof: dict[str, Any], projection: dict[str, Any]) -> bool:
        """Is the fresh projection's execution basis exactly the proved one? (R3)"""
        position = projection["position"]
        if position["current_microtask_id"] != proof["microtask_id"]:
            return False
        if projection["restore_point"].get("manifest_id") != proof["manifest_id"]:
            return False
        if proof["kind"] == "RETRY":
            recovery = projection["recovery"]
            view = next(
                (v for v in projection["operations"] if v["operation_id"] == proof["operation_id"]),
                None,
            )
            return (
                recovery.get("operation_id") == proof["operation_id"]
                and recovery.get("resolution_id") == proof["resolution_id"]
                and view is not None
                and view["revision"] == proof["operation_revision"]
            )
        return projection["recovery"]["state"] == "NORMAL"

    def _prove_normal_ready(
        self,
        task_id: str,
        projection: dict[str, Any],
    ) -> dict[str, Any]:
        microtask_id = projection["position"]["current_microtask_id"]
        if microtask_id is None:
            raise RecoveryCoordinatorError("normal READY proof has no current microtask")
        with self.operations.task_lock(task_id):
            with self.tasks.mutation_lock(task_id):
                micro = self.tasks.open_microtask(task_id, microtask_id)
                if micro.status is not MicrotaskStatus.ACTIVE:
                    raise RecoveryCoordinatorBlocked(
                        f"microtask {microtask_id} is no longer ACTIVE"
                    )
                with ExitStack() as target_stack:
                    plan, target_keys = self._lock_manifest_targets(
                        target_stack, task_id, microtask_id
                    )
                    micro = self.tasks.open_microtask(task_id, microtask_id)
                    if micro.status is not MicrotaskStatus.ACTIVE:
                        raise RecoveryCoordinatorBlocked(
                            f"microtask {microtask_id} changed during READY proof"
                        )
                    # Re-read integrity after the target set is protected.
                    plan = self.projection.manifests.restore_plan(task_id, microtask_id)
        return self._proof("NORMAL", task_id, micro, plan, target_keys)

    def _prove_retry_ready(
        self,
        task_id: str,
        projection: dict[str, Any],
    ) -> dict[str, Any]:
        recovery = projection["recovery"]
        operation_id = recovery["operation_id"]
        resolution_id = recovery["resolution_id"]
        view = self._view(projection, operation_id)
        if view is None or resolution_id is None:
            raise RecoveryCoordinatorError("projection lost RETRY readiness identity")
        microtask_id = view["microtask_id"]

        with self.operations.task_lock(task_id):
            with self.tasks.mutation_lock(task_id):
                resolution = self._accepted_resolution_locked(
                    task_id,
                    operation_id,
                    resolution_id,
                    ResolutionAction.RETRY,
                    require_fresh=True,
                )
                self._no_open_rollback_locked(task_id, operation_id)
                operation = self.operations.get(task_id, operation_id)
                if operation.microtask_id != microtask_id:
                    raise RecoveryCoordinatorError("operation microtask identity changed")
                if operation.revision != resolution.basis["operation_revision"]:
                    raise RecoveryCoordinatorError("operation revision changed before RETRY READY proof")
                micro = self.tasks.open_microtask(task_id, microtask_id)
                if micro.status is not MicrotaskStatus.ACTIVE:
                    raise RecoveryCoordinatorBlocked(
                        f"RETRY operation microtask {microtask_id} is {micro.status.value}, not ACTIVE"
                    )
                self._require_no_manual_disposition_locked(task_id, microtask_id, "RETRY READY")
                try:
                    self.projection.manifests.verify_restore_point(task_id, microtask_id)
                except ManifestStoreError as exc:
                    raise RecoveryCoordinatorBlocked(
                        f"restore point is not verified for RETRY: {exc}"
                    ) from exc

                with ExitStack() as target_stack:
                    target_keys = self._lock_resolution_targets(
                        target_stack, task_id, operation_id, resolution
                    )
                    resolution = self._accepted_resolution_locked(
                        task_id,
                        operation_id,
                        resolution_id,
                        ResolutionAction.RETRY,
                        require_fresh=True,
                    )
                    operation = self.operations.get(task_id, operation_id)
                    micro = self.tasks.open_microtask(task_id, microtask_id)
                    if operation.revision != resolution.basis["operation_revision"]:
                        raise RecoveryCoordinatorError(
                            "operation revision changed at RETRY READY boundary"
                        )
                    if micro.status is not MicrotaskStatus.ACTIVE:
                        raise RecoveryCoordinatorBlocked(
                            f"RETRY operation microtask {microtask_id} changed during READY proof"
                        )
                    try:
                        plan = self.projection.manifests.restore_plan(task_id, microtask_id)
                    except ManifestStoreError as exc:
                        raise RecoveryCoordinatorBlocked(
                            f"restore point changed during RETRY READY proof: {exc}"
                        ) from exc
        return self._proof(
            "RETRY",
            task_id,
            micro,
            plan,
            target_keys,
            operation=operation,
            resolution_id=resolution_id,
        )

    def _lock_resolution_targets(
        self,
        stack: ExitStack,
        task_id: str,
        operation_id: str,
        resolution,
    ) -> list[str]:
        """Lock every Resolver-basis target and reject foreign RC-3 ownership.

        The order is the canonical cross-subsystem target lock order
        (target_claim_store.target_lock_order, the one RC-4 uses), so neither a
        coordinator nor a rollback of another TASK touching the same targets can
        form a wait cycle with it. The caller already holds this TASK's
        operation lock. Returns the locked physical keys in lock order.
        """
        try:
            operation = self.operations.get(task_id, operation_id)
            contract = operation.contract or {}
            workspace = self.operations.registry.get(contract["workspace_id"])
            root = Path(workspace.workspace_root)
            targets = []
            for source_path in resolution.basis["affected_targets"]:
                canonical = canonical_target(root, source_path)
                targets.append((physical_target_key(canonical.path), source_path))
        except (
            OperationStoreError,
            WorkspaceRegistryError,
            TargetIdentityError,
            KeyError,
            TypeError,
        ) as exc:
            raise RecoveryCoordinatorError(
                f"cannot lock recovery target set: {exc}"
            ) from exc

        unique = {}
        for physical_key, source_path in targets:
            unique.setdefault(physical_key, source_path)
        ordered = target_lock_order(unique)
        for physical_key in ordered:
            stack.enter_context(self.claims._target_lock(physical_key))
            try:
                data = self.claims.claims.load(physical_key)
            except TargetClaimStoreError as exc:
                raise RecoveryCoordinatorError(str(exc)) from exc
            active = data["active"]
            if active is None:
                continue
            ours = (
                active.get("owner") is None
                and active["task_id"] == task_id
                and active["operation_id"] == operation_id
            )
            if not ours:
                raise RecoveryCoordinatorBlocked(
                    "recovery target is owned by another operation: "
                    f"{unique[physical_key]} -> "
                    f"{active.get('task_id')}/{active.get('operation_id')}"
                )
        return ordered

    def _settlement_target_locked(
        self,
        task_id: str,
        microtask_id: str,
        pending: str | None = None,
    ) -> MicrotaskStatus:
        """R2: the one disposition all settlements of this microtask require.

        Read from the persistent operation and Resolver records under the
        caller's TASK lock (same rule as the projection), plus the settlement
        about to be written (``pending``).
        """
        actions = self._current_settlements_locked(task_id, microtask_id)
        if pending is not None:
            actions.append(pending)
        target = settlement_lifecycle_target(actions)
        if target is None:
            raise RecoveryCoordinatorError(
                f"microtask {microtask_id} has no recovery settlement to apply"
            )
        return target

    def _require_no_manual_disposition_locked(self, task_id: str, microtask_id: str, what: str) -> None:
        """R2: an ABORT/ROLLBACK settlement keeps its microtask at the manual boundary."""
        target = settlement_lifecycle_target(self._current_settlements_locked(task_id, microtask_id))
        if target is MicrotaskStatus.RECOVERY_REQUIRED:
            raise RecoveryCoordinatorBlocked(
                f"{what} refused: microtask {microtask_id} carries an ABORT/ROLLBACK recovery settlement "
                "of another operation and stays RECOVERY_REQUIRED until an explicit project-level decision"
            )

    def _current_settlements_locked(self, task_id: str, microtask_id: str) -> list[str]:
        pairs = []
        for record in self.operations.list(task_id):
            if record.microtask_id != microtask_id or not record.recovery_settlement:
                continue
            try:
                facts = self.resolver.report_facts(task_id, microtask_id, record.operation_id)
            except ResolverError as exc:
                raise RecoveryCoordinatorError(str(exc)) from exc
            pairs.append((record, facts["next_safe_action"]))
        return current_settlements_by_microtask(pairs).get(microtask_id, [])

    @staticmethod
    def _settlement_rule(target: MicrotaskStatus, *, finishing: bool) -> dict[str, Any]:
        """allowed_from / additionally_satisfied for applying a settlement disposition."""
        if target is MicrotaskStatus.DONE:
            return {
                "allowed_from": _TO_DONE_FROM,
                # Verification may legitimately win the race after the
                # settlement/micro update but before claim release.  A new
                # settlement never accepts an already VERIFIED microtask (B3).
                "additionally_satisfied": {MicrotaskStatus.VERIFIED} if finishing else None,
            }
        return {"allowed_from": _TO_RECOVERY_REQUIRED_FROM, "additionally_satisfied": None}

    def _apply_settlement_lifecycle_locked(
        self,
        task_id: str,
        microtask_id: str,
        target: MicrotaskStatus,
        *,
        finishing: bool,
        preflight_only: bool = False,
    ):
        rule = self._settlement_rule(target, finishing=finishing)
        if preflight_only:
            return self._preflight_micro_locked(task_id, microtask_id, target, **rule)
        return self._set_micro_locked(task_id, microtask_id, target, **rule)

    def _current_microtask_locked(self, task_id: str) -> str | None:
        """Lifecycle position: the first non-VERIFIED microtask in plan order."""
        for micro in self.tasks.list_microtasks(task_id):
            if micro.status is not MicrotaskStatus.VERIFIED:
                return micro.microtask_id
        return None

    def _rollback_stage_preflight(
        self,
        task_id: str,
        operation_id: str,
        action: str,
        rollback_id: str | None,
    ) -> None:
        """R1 defense in depth: no destructive rollback step for a protected stage.

        Re-proved from persistent facts under the TASK serialization right
        before RC-4 prepare/apply, independent of the projection that chose the
        step. Steps in which RC-4 restores nothing (release-only of a VERIFIED
        session, finalize of a persisted DRIFTED/FAILED outcome, apply under an
        accepted ABORT which RC-4 refuses to continue) are not destructive.
        """
        if action == "APPLY_ROLLBACK" and rollback_id is None:
            raise RecoveryCoordinatorError("rollback action has no rollback_id")
        with self.operations.task_lock(task_id):
            with self.tasks.mutation_lock(task_id):
                if action == "APPLY_ROLLBACK":
                    try:
                        session = self.rollbacks.store.get(task_id, rollback_id)
                        aborted = any(
                            record.action is ResolutionAction.ABORT
                            and record.result is ResolutionResult.ACCEPTED
                            for record in self.resolver.store.list(task_id, operation_id=operation_id)
                        )
                    except (RollbackStoreError, ResolutionStoreError) as exc:
                        raise RecoveryCoordinatorError(str(exc)) from exc
                    if (
                        session["status"] not in _ROLLBACK_RESTORE_PHASES
                        or rollback_needs_rc4_finalize(session)
                        or aborted
                    ):
                        return
                operation = self.operations.get(task_id, operation_id)
                micro = self.tasks.open_microtask(task_id, operation.microtask_id)
                current = self._current_microtask_locked(task_id)
        if rollback_stage_protected(operation.microtask_id, micro.status.value, current):
            raise RecoveryCoordinatorBlocked(
                f"{action} refused before any rollback step: operation {operation_id} belongs to "
                f"microtask {operation.microtask_id} ({micro.status.value}), not to the current stage "
                f"({current}); a VERIFIED or non-current stage is never rolled back"
            )

    def _settle_resolution(
        self,
        task_id: str,
        projection: dict[str, Any],
        action: ResolutionAction,
    ) -> dict[str, Any]:
        recovery = projection["recovery"]
        operation_id = recovery["operation_id"]
        resolution_id = recovery["resolution_id"]
        view = self._view(projection, operation_id)
        if view is None or resolution_id is None:
            raise RecoveryCoordinatorError("projection lost recovery operation/resolution identity")
        with self.operations.task_lock(task_id):
            with self.tasks.mutation_lock(task_id):
                resolution = self._accepted_resolution_locked(
                    task_id,
                    operation_id,
                    resolution_id,
                    action,
                    require_fresh=(action is ResolutionAction.ADOPT),
                )
                self._no_open_rollback_locked(task_id, operation_id)

                # Prove the operation's own microtask lifecycle before the
                # durable settlement write.  A later/current TASK microtask is
                # never a substitute for the operation's microtask, and the
                # status written is the microtask's single aggregated
                # disposition including this settlement (R2).
                target = self._settlement_target_locked(
                    task_id, view["microtask_id"], pending=action.value
                )
                self._apply_settlement_lifecycle_locked(
                    task_id, view["microtask_id"], target, finishing=False, preflight_only=True
                )
                if action is ResolutionAction.ADOPT:
                    with ExitStack() as target_stack:
                        self._lock_resolution_targets(
                            target_stack, task_id, operation_id, resolution
                        )
                        # Re-prove authority/freshness after every affected
                        # target is protected from compliant RC-3 writers.
                        resolution = self._accepted_resolution_locked(
                            task_id,
                            operation_id,
                            resolution_id,
                            action,
                            require_fresh=True,
                        )
                        outcome = self.operations._settle_recovery_locked(
                            task_id,
                            operation_id,
                            action.value,
                            resolution_id=resolution_id,
                            expected_revision=resolution.basis["operation_revision"],
                        )
                        micro = self._apply_settlement_lifecycle_locked(
                            task_id, view["microtask_id"], target, finishing=False
                        )
                else:
                    outcome = self.operations._settle_recovery_locked(
                        task_id,
                        operation_id,
                        action.value,
                        resolution_id=resolution_id,
                        expected_revision=resolution.basis["operation_revision"],
                    )
                    micro = self._apply_settlement_lifecycle_locked(
                        task_id, view["microtask_id"], target, finishing=False
                    )
        release = self.claims.release(
            task_id,
            operation_id,
            reason=f"RC6_{action.value}_SETTLED",
            channel="recovery_coordinator",
        )
        return {
            "result": "SETTLED",
            "settlement": action.value,
            "resolution_id": resolution_id,
            "operation": self._step_summary(outcome),
            "microtask": micro,
            "claim_release": self._step_summary(release),
        }

    def _finish_settlement(
        self,
        task_id: str,
        projection: dict[str, Any],
    ) -> dict[str, Any]:
        recovery = projection["recovery"]
        operation_id = recovery["operation_id"]
        view = self._view(projection, operation_id)
        if view is None or view["recovery_settlement"] is None:
            raise RecoveryCoordinatorError("settlement projection has no durable settlement")
        action = view["recovery_settlement"]["action"]
        with self.operations.task_lock(task_id):
            with self.tasks.mutation_lock(task_id):
                current = self.operations.get(task_id, operation_id)
                settlement = current.recovery_settlement
                if settlement is None or settlement["action"] != action:
                    raise RecoveryCoordinatorError("recovery settlement changed while finishing it")
                # R2: finish towards the microtask's one aggregated disposition,
                # so sibling settlements can never steer it back and forth.
                target = self._settlement_target_locked(task_id, view["microtask_id"])
                micro = self._apply_settlement_lifecycle_locked(
                    task_id, view["microtask_id"], target, finishing=True
                )
        release = self.claims.release(
            task_id,
            operation_id,
            reason=f"RC6_{action}_SETTLED",
            channel="recovery_coordinator",
        )
        return {
            "result": "SETTLEMENT_FINISHED",
            "settlement": action,
            "microtask": micro,
            "claim_release": self._step_summary(release),
        }

    def _rearm_retry(self, task_id: str, projection: dict[str, Any]) -> dict[str, Any]:
        recovery = projection["recovery"]
        operation_id = recovery["operation_id"]
        resolution_id = recovery["resolution_id"]
        view = self._view(projection, operation_id)
        if view is None or resolution_id is None:
            raise RecoveryCoordinatorError("projection lost RETRY identity")
        with self.operations.task_lock(task_id):
            with self.tasks.mutation_lock(task_id):
                resolution = self._accepted_resolution_locked(
                    task_id,
                    operation_id,
                    resolution_id,
                    ResolutionAction.RETRY,
                    require_fresh=True,
                )
                self._no_open_rollback_locked(task_id, operation_id)
                operation = self.operations.get(task_id, operation_id)
                if operation.revision != resolution.basis["operation_revision"]:
                    raise RecoveryCoordinatorError("operation revision changed before RETRY re-arm")
                with ExitStack() as target_stack:
                    self._lock_resolution_targets(
                        target_stack, task_id, operation_id, resolution
                    )
                    # The accepted RETRY must still be the current authority on
                    # the same protected target set at the re-arm boundary.
                    resolution = self._accepted_resolution_locked(
                        task_id,
                        operation_id,
                        resolution_id,
                        ResolutionAction.RETRY,
                        require_fresh=True,
                    )
                    operation = self.operations.get(task_id, operation_id)
                    if operation.revision != resolution.basis["operation_revision"]:
                        raise RecoveryCoordinatorError(
                            "operation revision changed at RETRY re-arm boundary"
                        )
                    self._require_no_manual_disposition_locked(
                        task_id, view["microtask_id"], "RETRY re-arm"
                    )
                    micro = self._set_micro_locked(
                        task_id,
                        view["microtask_id"],
                        MicrotaskStatus.ACTIVE,
                        allowed_from={
                            MicrotaskStatus.ACTIVE,
                            MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT,
                            MicrotaskStatus.RECOVERY_REQUIRED,
                            MicrotaskStatus.FAILED_VERIFICATION,
                        },
                    )
        return {
            "result": "REARMED",
            "resolution_id": resolution_id,
            "operation_id": operation_id,
            "microtask": micro,
            "physical_mutation_performed": False,
        }

    def _settle_verified_rollback(
        self,
        task_id: str,
        projection: dict[str, Any],
    ) -> dict[str, Any]:
        recovery = projection["recovery"]
        operation_id = recovery["operation_id"]
        rollback_id = recovery["rollback_id"]
        view = self._view(projection, operation_id)
        if view is None or rollback_id is None:
            raise RecoveryCoordinatorError("projection lost verified rollback identity")
        with self.operations.task_lock(task_id):
            with self.tasks.mutation_lock(task_id):
                try:
                    session = self.rollbacks.store.get(task_id, rollback_id)
                except RollbackStoreError as exc:
                    raise RecoveryCoordinatorError(str(exc)) from exc
                if session["status"] != VERIFIED or not session["claims_released"]:
                    raise RecoveryCoordinatorError("rollback is not durably VERIFIED with ownership released")
                if session["operation_id"] != operation_id:
                    raise RecoveryCoordinatorError("rollback operation identity changed")
                target = self._settlement_target_locked(
                    task_id, view["microtask_id"], pending="ROLLBACK"
                )
                self._apply_settlement_lifecycle_locked(
                    task_id, view["microtask_id"], target, finishing=False, preflight_only=True
                )
                outcome = self.operations._settle_recovery_locked(
                    task_id,
                    operation_id,
                    "ROLLBACK",
                    resolution_id=session["resolution_id"],
                    expected_revision=session["basis"]["operation_revision"],
                )
                micro = self._apply_settlement_lifecycle_locked(
                    task_id, view["microtask_id"], target, finishing=False
                )
        return {
            "result": "SETTLED",
            "settlement": "ROLLBACK",
            "resolution_id": session["resolution_id"],
            "operation": self._step_summary(outcome),
            "microtask": micro,
        }

    def _perform(
        self,
        task_id: str,
        projection: dict[str, Any],
        action: str,
    ) -> dict[str, Any]:
        recovery = projection["recovery"]
        rollback_id = recovery.get("rollback_id")
        if action in ("PREPARE_ROLLBACK", "APPLY_ROLLBACK"):
            # R1: re-proved from persistent facts before the first RC-4 step.
            self._rollback_stage_preflight(task_id, recovery["operation_id"], action, rollback_id)
        if action == "SETTLE_ADOPT":
            return self._settle_resolution(task_id, projection, ResolutionAction.ADOPT)
        if action == "SETTLE_ABORT":
            return self._settle_resolution(task_id, projection, ResolutionAction.ABORT)
        if action == "FINISH_SETTLEMENT":
            return self._finish_settlement(task_id, projection)
        if action == "REARM_RETRY":
            return self._rearm_retry(task_id, projection)
        if action == "PREPARE_ROLLBACK":
            view = self._view(projection, recovery["operation_id"])
            if view is None:
                raise RecoveryCoordinatorError("rollback operation view is missing")
            return self.rollbacks.prepare(
                task_id,
                view["microtask_id"],
                recovery["operation_id"],
                recovery["resolution_id"],
                channel="recovery_coordinator",
            )
        if rollback_id is None:
            raise RecoveryCoordinatorError("rollback action has no rollback_id")
        if action == "APPLY_ROLLBACK":
            return self.rollbacks.apply(task_id, rollback_id)
        if action == "CLOSE_ROLLBACK":
            return self.rollbacks.close(task_id, rollback_id, reason="RC6_RECOVERY_CLOSURE")
        if action == "SETTLE_ROLLBACK":
            return self._settle_verified_rollback(task_id, projection)
        raise RecoveryCoordinatorError(f"unknown coordinator step: {action}")

    def _classify(self, projection: dict[str, Any]) -> dict[str, Any]:
        task = projection["task"]
        position = projection["position"]
        recovery = projection["recovery"]
        state = recovery["state"]

        if task["location"] != "active" or task["status"] in {
            TaskStatus.COMPLETED.value,
            TaskStatus.ARCHIVED.value,
        }:
            return {"stop": TASK_COMPLETED, "reason": projection["next_safe_action"]}

        if projection["blockers"]:
            first = projection["blockers"][0]
            return {
                "stop": FAIL_CLOSED,
                "reason": f"{first['code']}: {first['reason']}",
                "requires_human": True,
            }
        dangerous_diagnostics = [
            item for item in projection["diagnostics"]
            if item["code"] in {"CLAIMS_UNREADABLE", "ORPHAN_MICROTASKS"}
        ]
        if dangerous_diagnostics:
            first = dangerous_diagnostics[0]
            return {
                "stop": FAIL_CLOSED,
                "reason": f"{first['code']}: {first['reason']}",
                "requires_human": True,
            }

        if state == "RETRY_ACCEPTED":
            view = self._view(projection, recovery["operation_id"])
            if view is None:
                return {
                    "stop": FAIL_CLOSED,
                    "reason": "accepted RETRY has no operation view",
                    "requires_human": True,
                }
            op_micro_status = view["microtask_status"]
            if view.get("microtask_disposition") == MicrotaskStatus.RECOVERY_REQUIRED.value:
                return {
                    "stop": RECOVERY_BLOCKED,
                    "reason": (
                        f"accepted RETRY cannot proceed: microtask {view['microtask_id']} carries an "
                        "ABORT/ROLLBACK recovery settlement of another operation and stays "
                        "RECOVERY_REQUIRED until an explicit project-level decision"
                    ),
                    "requires_human": True,
                }
            if op_micro_status == MicrotaskStatus.ACTIVE.value:
                if position["current_microtask_id"] != view["microtask_id"]:
                    return {
                        "stop": RECOVERY_BLOCKED,
                        "reason": (
                            f"accepted RETRY belongs to historical microtask {view['microtask_id']}, "
                            f"while current microtask is {position['current_microtask_id']}"
                        ),
                        "requires_human": True,
                    }
                # Global target ownership and restore-point integrity are not
                # provable from task-local Projection alone; perform a pure
                # lock/read proof immediately before returning READY.
                return {"proof": "RETRY_READY"}
            if op_micro_status in _RECOVERY_MICRO:
                if position["current_microtask_id"] != view["microtask_id"]:
                    return {
                        "stop": RECOVERY_BLOCKED,
                        "reason": (
                            f"accepted RETRY belongs to non-current microtask {view['microtask_id']} "
                            f"({op_micro_status})"
                        ),
                        "requires_human": True,
                    }
                return {"step": "REARM_RETRY"}
            return {
                "stop": RECOVERY_BLOCKED,
                "reason": (
                    f"accepted RETRY cannot re-arm operation microtask {view['microtask_id']} "
                    f"from {op_micro_status}"
                ),
                "requires_human": True,
            }

        if state == "ADOPT_ACCEPTED":
            return {"step": "SETTLE_ADOPT"}
        if state == "ABORT_ACCEPTED":
            return {"step": "SETTLE_ABORT"}
        if state == "ROLLBACK_ACCEPTED":
            return {"step": "PREPARE_ROLLBACK"}

        if state in {"ADOPT_SETTLED", "ABORT_SETTLED", "ROLLBACK_SETTLED"}:
            view = self._view(projection, recovery["operation_id"])
            if view is None:
                return {
                    "stop": FAIL_CLOSED,
                    "reason": "settled recovery has no operation view",
                    "requires_human": True,
                }
            own_claim = any(
                claim["operation_id"] == recovery["operation_id"]
                and not (claim.get("owner") or {}).get("rollback_id")
                for claim in projection["ownership"]["active_claims"]
            )
            op_micro_status = view["microtask_status"]
            # R2: judged against the microtask's single aggregated disposition.
            target = MicrotaskStatus(
                recovery.get("lifecycle_target")
                or (
                    MicrotaskStatus.DONE.value
                    if state == "ADOPT_SETTLED"
                    else MicrotaskStatus.RECOVERY_REQUIRED.value
                )
            )
            admin_satisfied = settlement_lifecycle_satisfied(target, op_micro_status)
            if not admin_satisfied or own_claim:
                return {"step": "FINISH_SETTLEMENT"}
            # A fully completed settlement should normally have been demoted to
            # history by Projection.  Keep this fallback conservative.
            if target is MicrotaskStatus.DONE:
                if op_micro_status == MicrotaskStatus.DONE.value:
                    return {
                        "stop": READY_FOR_VERIFICATION,
                        "reason": projection["next_safe_action"],
                    }
                return {
                    "stop": NO_ACTION_REQUIRED,
                    "reason": projection["next_safe_action"],
                }
            return {
                "stop": MANUAL_DECISION_REQUIRED,
                "reason": projection["next_safe_action"],
                "requires_human": True,
            }

        if state in {"RECONCILIATION_REQUIRED", "RESOLUTION_STALE"} or state.endswith("_REJECTED"):
            return {
                "stop": MANUAL_DECISION_REQUIRED,
                "reason": projection["next_safe_action"],
                "requires_human": True,
            }

        if state in {
            "ROLLBACK_STAGE_PROTECTED",
            "SETTLEMENT_CONTRADICTION",
            "ROLLBACK_MULTIPLE_OPEN",
            "ROLLBACK_SUPERSEDED_IN_FLIGHT",
            "ROLLBACK_STALE_IN_FLIGHT",
            "ROLLBACK_SUPERSEDED_AFTER_EFFECTS",
            "ROLLBACK_ABORTED_AFTER_EFFECTS",
            "ROLLBACK_SUPERSEDED_UNSAFE_FINAL",
            "ROLLBACK_ABORTED_UNSAFE_FINAL",
        }:
            return {
                "stop": RECOVERY_BLOCKED,
                "reason": projection["next_safe_action"],
                "requires_human": True,
            }

        if state in {
            "ROLLBACK_ABORTED_IN_FLIGHT",
            "ROLLBACK_ABORTED_NEEDS_FINALIZE",
            "ROLLBACK_SUPERSEDED_NEEDS_FINALIZE",
            "ROLLBACK_ABORTED_RELEASE_PENDING",
            "ROLLBACK_SUPERSEDED_RELEASE_PENDING",
        }:
            return {"step": "APPLY_ROLLBACK"}
        if state == "ROLLBACK_ABORTED_OPEN" or state == "ROLLBACK_STALE_OPEN":
            return {"step": "CLOSE_ROLLBACK"}
        if state.startswith("ROLLBACK_SUPERSEDED_BY_"):
            return {"step": "CLOSE_ROLLBACK"}

        if state == "ROLLBACK_PREPARED":
            return {"step": "PREPARE_ROLLBACK"}
        if state in {"ROLLBACK_PRESERVED", "ROLLBACK_AUTHORIZED", "ROLLBACK_APPLYING"}:
            return {"step": "APPLY_ROLLBACK"}
        if state == "ROLLBACK_VERIFIED":
            session = self._rollback(projection, recovery["rollback_id"])
            if session is None:
                return {"stop": FAIL_CLOSED, "reason": "verified rollback record is missing"}
            if session["claims_released"]:
                return {"step": "SETTLE_ROLLBACK"}
            return {"step": "APPLY_ROLLBACK"}
        if state in {"ROLLBACK_PARTIAL", "ROLLBACK_FAILED"}:
            # RC-4 has already recorded a non-verified physical outcome.  Do
            # not release ownership automatically; a human/new recovery
            # decision must precede close.
            return {
                "stop": RECOVERY_BLOCKED,
                "reason": projection["next_safe_action"],
                "requires_human": True,
            }
        if state in {"ROLLBACK_CLOSED", "ROLLBACK_PRESERVATION_FAILED"}:
            return {
                "stop": MANUAL_DECISION_REQUIRED,
                "reason": projection["next_safe_action"],
                "requires_human": True,
            }

        if state != "NORMAL":
            return {
                "stop": RECOVERY_BLOCKED,
                "reason": f"unhandled recovery state {state}: {projection['next_safe_action']}",
                "requires_human": True,
            }

        if position["all_verified"]:
            if projection["closeout"]:
                return {"stop": NO_ACTION_REQUIRED, "reason": projection["next_safe_action"]}
            return {"stop": TASK_READY_TO_CLOSE, "reason": projection["next_safe_action"]}

        status = position["current_status"]
        if status == MicrotaskStatus.ACTIVE.value:
            if projection["restore_point"]["status"] != "VERIFIED":
                return {
                    "stop": RECOVERY_BLOCKED,
                    "reason": (
                        "current ACTIVE microtask has no verified restore point: "
                        f"{projection['restore_point']['reason'] or projection['restore_point']['status']}"
                    ),
                    "requires_human": True,
                }
            unexpected = self._unexpected_claims(projection)
            if unexpected:
                return {
                    "stop": RECOVERY_BLOCKED,
                    "reason": "unexpected recovery ownership remains before execution",
                    "requires_human": True,
                }
            return {"proof": "NORMAL_READY"}
        if status == MicrotaskStatus.DONE.value:
            return {"stop": READY_FOR_VERIFICATION, "reason": projection["next_safe_action"]}
        if status in _RECOVERY_MICRO:
            return {
                "stop": MANUAL_DECISION_REQUIRED,
                "reason": projection["next_safe_action"],
                "requires_human": True,
            }
        return {"stop": NO_ACTION_REQUIRED, "reason": projection["next_safe_action"]}

    @staticmethod
    def _result(
        initial: dict[str, Any],
        final: dict[str, Any],
        *,
        state: str,
        reason: str,
        steps: list[dict[str, Any]],
        requires_human: bool = False,
        error: str | None = None,
        ready_proof: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "state": state,
            "reason": reason,
            "requires_human": requires_human,
            "ready_for_execution": state == READY_FOR_EXECUTION,
            # identity of the execution basis a READY was proved for (R3);
            # WA4-E must still re-acquire and re-check before any write
            "ready_proof": ready_proof if state == READY_FOR_EXECUTION else None,
            "initial_projection_fingerprint": initial["projection_fingerprint"],
            "final_projection_fingerprint": final["projection_fingerprint"],
            "performed_steps": steps,
            "blocked_by": (
                [item["code"] for item in final["blockers"]]
                if final["blockers"]
                else []
            ),
            "next_safe_action": final["next_safe_action"],
            "authority_source": final["authority_source"],
            "task_id": final["task"]["task_id"],
            "recovery_state": final["recovery"]["state"],
            "projection": final,
            "error": error,
        }

    def recover(
        self,
        task_id: str,
        *,
        max_recovery_steps: int | None = None,
    ) -> dict[str, Any]:
        """Run bounded safe recovery and stop before any WA4-E normal mutation."""
        limit = self.default_max_steps if max_recovery_steps is None else max_recovery_steps
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("max_recovery_steps must be a positive integer")
        try:
            initial = self.projection.build(task_id)
        except (ProjectionError, TaskStoreError, OperationStoreError, ValueError, OSError) as exc:
            raise RecoveryCoordinatorError(str(exc)) from exc

        current = initial
        steps: list[dict[str, Any]] = []
        # F-E: a step RC-4 refused (BLOCKED/REJECTED) is not repeated within
        # one invocation; key -> the refusing outcome
        refused: dict[tuple[Any, ...], dict[str, Any]] = {}
        for index in range(limit + 1):
            decision = self._classify(current)
            if "stop" in decision:
                return self._result(
                    initial,
                    current,
                    state=decision["stop"],
                    reason=decision["reason"],
                    steps=steps,
                    requires_human=decision.get("requires_human", False),
                )

            if "proof" in decision:
                proof = decision["proof"]
                basis = current["source_fingerprint"]
                try:
                    if proof == "RETRY_READY":
                        proved = self._prove_retry_ready(task_id, current)
                    elif proof == "NORMAL_READY":
                        proved = self._prove_normal_ready(task_id, current)
                    else:
                        raise RecoveryCoordinatorError(
                            f"unknown READY proof: {proof}"
                        )
                    fresh = self.projection.build(task_id)
                except RecoveryCoordinatorBlocked as exc:
                    try:
                        current = self.projection.build(task_id)
                    except Exception:
                        current = current
                    return self._result(
                        initial,
                        current,
                        state=RECOVERY_BLOCKED,
                        reason=f"{proof} blocked: {exc}",
                        steps=steps,
                        requires_human=True,
                        error=type(exc).__name__,
                    )
                except (
                    RecoveryCoordinatorError,
                    ResolverError,
                    ResolutionStoreError,
                    RollbackError,
                    RollbackStoreError,
                    TargetClaimError,
                    OperationStoreError,
                    OperationTransitionError,
                    TaskStoreError,
                    ProjectionError,
                    ManifestStoreError,
                    ValueError,
                    OSError,
                ) as exc:
                    try:
                        current = self.projection.build(task_id)
                    except Exception:
                        current = current
                    return self._result(
                        initial,
                        current,
                        state=FAIL_CLOSED,
                        reason=f"{proof} failed closed: {exc}",
                        steps=steps,
                        requires_human=True,
                        error=type(exc).__name__,
                    )

                # R3: READY only for exactly the basis the protected proof
                # covered.  If anything authoritative changed between the
                # projection that chose the proof and the fresh one (another
                # microtask became current, restore point, operation or
                # resolution changed), classify again and prove the new basis
                # instead of reusing this proof.  Foreign ownership that
                # appears *after* the protected proof is a later race and must
                # be rechecked by WA4-E before physical mutation.
                current = fresh
                after = self._classify(current)
                if (
                    after.get("proof") == proof
                    and current["source_fingerprint"] == basis
                    and self._proof_matches(proved, current)
                ):
                    return self._result(
                        initial,
                        current,
                        state=READY_FOR_EXECUTION,
                        reason=current["next_safe_action"],
                        steps=steps,
                        ready_proof=dict(proved, source_fingerprint=basis),
                    )
                continue

            action = decision["step"]
            step_key = (
                action,
                current["recovery"].get("operation_id"),
                current["recovery"].get("rollback_id"),
            )
            if step_key in refused:
                outcome = refused[step_key]
                return self._result(
                    initial,
                    current,
                    state=RECOVERY_BLOCKED,
                    reason=(
                        f"{action} was refused by RC-4 in this recover call "
                        f"({outcome.get('result_code')}: {outcome.get('reason')}); "
                        "it is not repeated: resolve the blocker, then call recover again"
                    ),
                    steps=steps,
                    requires_human=True,
                    error="RECOVERY_STEP_REFUSED",
                )

            if index >= limit:
                return self._result(
                    initial,
                    current,
                    state=FAIL_CLOSED,
                    reason=f"recovery step budget exhausted after {limit} step(s)",
                    steps=steps,
                    requires_human=True,
                    error="RECOVERY_STEP_BUDGET_EXHAUSTED",
                )

            before = current["projection_fingerprint"]
            try:
                outcome = self._perform(task_id, current, action)
                current = self.projection.build(task_id)
            except RecoveryCoordinatorBlocked as exc:
                try:
                    current = self.projection.build(task_id)
                except Exception:
                    current = current
                return self._result(
                    initial,
                    current,
                    state=RECOVERY_BLOCKED,
                    reason=f"{action} blocked: {exc}",
                    steps=steps,
                    requires_human=True,
                    error=type(exc).__name__,
                )
            except (
                RecoveryCoordinatorError,
                ResolverError,
                ResolutionStoreError,
                RollbackError,
                RollbackStoreError,
                TargetClaimError,
                OperationStoreError,
                OperationTransitionError,
                TaskStoreError,
                ProjectionError,
                ValueError,
                OSError,
            ) as exc:
                try:
                    current = self.projection.build(task_id)
                except Exception:
                    current = current
                return self._result(
                    initial,
                    current,
                    state=FAIL_CLOSED,
                    reason=f"{action} failed closed: {exc}",
                    steps=steps,
                    requires_human=True,
                    error=type(exc).__name__,
                )
            steps.append(
                {
                    "index": index + 1,
                    "action": action,
                    "before_projection_fingerprint": before,
                    "after_projection_fingerprint": current["projection_fingerprint"],
                    "outcome": self._step_summary(outcome),
                }
            )
            if isinstance(outcome, dict) and outcome.get("result") in _STEP_BLOCKED_RESULTS:
                refused[step_key] = outcome

        return self._result(
            initial,
            current,
            state=FAIL_CLOSED,
            reason="recovery loop bound reached without a terminal state or a stable READY basis",
            steps=steps,
            requires_human=True,
            error="RECOVERY_LOOP_INTERNAL",
        )
