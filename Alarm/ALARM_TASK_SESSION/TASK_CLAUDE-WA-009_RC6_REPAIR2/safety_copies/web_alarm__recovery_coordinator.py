"""RC-6 project-level bounded recovery/resume orchestration.

The coordinator never executes a normal Workspace mutation. It composes the
authoritative RC-5 projection with existing Resolver, RC-3 ownership and RC-4
rollback services, performs only already-authorized recovery/administrative
steps, rebuilds the projection after every step and stops at a safe boundary.
"""

from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
from typing import Any

from .manifest_store import ManifestStoreError
from .models import MicrotaskStatus, TaskStatus
from .operation_store import OperationStore, OperationStoreError, OperationTransitionError
from .projection import ProjectionError, ProjectionService
from .resolution_store import ResolutionAction, ResolutionResult, ResolutionStoreError
from .resolver_service import ResolverError, ResolverService
from .rollback_service import RollbackError, RollbackService
from .rollback_store import (
    CLOSED,
    PRESERVATION_FAILED,
    VERIFIED,
    RollbackStoreError,
)
from .target_claim_service import TargetClaimError, TargetClaimService
from .target_claim_store import TargetClaimStoreError, physical_target_key
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
        for physical_key in sorted(unique):
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
        return plan

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
                    plan = self._lock_manifest_targets(
                        target_stack, task_id, microtask_id
                    )
                    micro = self.tasks.open_microtask(task_id, microtask_id)
                    if micro.status is not MicrotaskStatus.ACTIVE:
                        raise RecoveryCoordinatorBlocked(
                            f"microtask {microtask_id} changed during READY proof"
                        )
                    # Re-read integrity after the target set is protected.
                    plan = self.projection.manifests.restore_plan(task_id, microtask_id)
        return {
            "result": "READY_PROVED",
            "microtask_id": microtask_id,
            "manifest_id": plan["manifest_id"],
            "restore_point_fingerprint": plan["restore_point_fingerprint"],
            "physical_mutation_performed": False,
        }

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
                try:
                    self.projection.manifests.verify_restore_point(task_id, microtask_id)
                except ManifestStoreError as exc:
                    raise RecoveryCoordinatorBlocked(
                        f"restore point is not verified for RETRY: {exc}"
                    ) from exc

                with ExitStack() as target_stack:
                    self._lock_resolution_targets(
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
                        manifest = self.projection.manifests.verify_restore_point(
                            task_id, microtask_id
                        )
                    except ManifestStoreError as exc:
                        raise RecoveryCoordinatorBlocked(
                            f"restore point changed during RETRY READY proof: {exc}"
                        ) from exc
        return {
            "result": "READY_PROVED",
            "operation_id": operation_id,
            "resolution_id": resolution_id,
            "microtask_id": microtask_id,
            "manifest_id": manifest.manifest_id,
            "physical_mutation_performed": False,
        }

    def _lock_resolution_targets(
        self,
        stack: ExitStack,
        task_id: str,
        operation_id: str,
        resolution,
    ) -> None:
        """Lock every Resolver-basis target and reject foreign RC-3 ownership.

        The order is the canonical physical key order, so two coordinators that
        touch the same target set cannot deadlock by taking target locks in
        opposite orders. The caller already holds this TASK's operation lock.
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
        for physical_key in sorted(unique):
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
                # never a substitute for the operation's microtask.
                if action is ResolutionAction.ADOPT:
                    self._preflight_micro_locked(
                        task_id,
                        view["microtask_id"],
                        MicrotaskStatus.DONE,
                        allowed_from={
                            MicrotaskStatus.ACTIVE,
                            MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT,
                            MicrotaskStatus.RECOVERY_REQUIRED,
                            MicrotaskStatus.DONE,
                        },
                    )
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
                        micro = self._set_micro_locked(
                            task_id,
                            view["microtask_id"],
                            MicrotaskStatus.DONE,
                            allowed_from={
                                MicrotaskStatus.ACTIVE,
                                MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT,
                                MicrotaskStatus.RECOVERY_REQUIRED,
                                MicrotaskStatus.DONE,
                            },
                        )
                else:
                    self._preflight_micro_locked(
                        task_id,
                        view["microtask_id"],
                        MicrotaskStatus.RECOVERY_REQUIRED,
                        allowed_from={
                            MicrotaskStatus.ACTIVE,
                            MicrotaskStatus.DONE,
                            MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT,
                            MicrotaskStatus.RECOVERY_REQUIRED,
                            MicrotaskStatus.FAILED_VERIFICATION,
                        },
                    )
                    outcome = self.operations._settle_recovery_locked(
                        task_id,
                        operation_id,
                        action.value,
                        resolution_id=resolution_id,
                        expected_revision=resolution.basis["operation_revision"],
                    )
                    micro = self._set_micro_locked(
                        task_id,
                        view["microtask_id"],
                        MicrotaskStatus.RECOVERY_REQUIRED,
                        allowed_from={
                            MicrotaskStatus.ACTIVE,
                            MicrotaskStatus.DONE,
                            MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT,
                            MicrotaskStatus.RECOVERY_REQUIRED,
                            MicrotaskStatus.FAILED_VERIFICATION,
                        },
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
                if action == "ADOPT":
                    micro = self._set_micro_locked(
                        task_id,
                        view["microtask_id"],
                        MicrotaskStatus.DONE,
                        allowed_from={
                            MicrotaskStatus.ACTIVE,
                            MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT,
                            MicrotaskStatus.RECOVERY_REQUIRED,
                            MicrotaskStatus.DONE,
                        },
                        # Verification may legitimately win the race after the
                        # settlement/micro update but before claim release.
                        additionally_satisfied={MicrotaskStatus.VERIFIED},
                    )
                else:
                    micro = self._set_micro_locked(
                        task_id,
                        view["microtask_id"],
                        MicrotaskStatus.RECOVERY_REQUIRED,
                        allowed_from={
                            MicrotaskStatus.ACTIVE,
                            MicrotaskStatus.DONE,
                            MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT,
                            MicrotaskStatus.RECOVERY_REQUIRED,
                            MicrotaskStatus.FAILED_VERIFICATION,
                        },
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
                self._preflight_micro_locked(
                    task_id,
                    view["microtask_id"],
                    MicrotaskStatus.RECOVERY_REQUIRED,
                    allowed_from={
                        MicrotaskStatus.ACTIVE,
                        MicrotaskStatus.DONE,
                        MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT,
                        MicrotaskStatus.RECOVERY_REQUIRED,
                        MicrotaskStatus.FAILED_VERIFICATION,
                    },
                )
                outcome = self.operations._settle_recovery_locked(
                    task_id,
                    operation_id,
                    "ROLLBACK",
                    resolution_id=session["resolution_id"],
                    expected_revision=session["basis"]["operation_revision"],
                )
                micro = self._set_micro_locked(
                    task_id,
                    view["microtask_id"],
                    MicrotaskStatus.RECOVERY_REQUIRED,
                    allowed_from={
                        MicrotaskStatus.ACTIVE,
                        MicrotaskStatus.DONE,
                        MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT,
                        MicrotaskStatus.RECOVERY_REQUIRED,
                        MicrotaskStatus.FAILED_VERIFICATION,
                    },
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
            if state == "ADOPT_SETTLED":
                admin_satisfied = op_micro_status in {
                    MicrotaskStatus.DONE.value,
                    MicrotaskStatus.VERIFIED.value,
                }
            else:
                admin_satisfied = (
                    op_micro_status == MicrotaskStatus.RECOVERY_REQUIRED.value
                )
            if not admin_satisfied or own_claim:
                return {"step": "FINISH_SETTLEMENT"}
            # A fully completed settlement should normally have been demoted to
            # history by Projection.  Keep this fallback conservative.
            if state == "ADOPT_SETTLED":
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
    ) -> dict[str, Any]:
        return {
            "state": state,
            "reason": reason,
            "requires_human": requires_human,
            "ready_for_execution": state == READY_FOR_EXECUTION,
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
                try:
                    if proof == "RETRY_READY":
                        self._prove_retry_ready(task_id, current)
                    elif proof == "NORMAL_READY":
                        self._prove_normal_ready(task_id, current)
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

                # If authoritative state changed while the pure proof ran,
                # classify the fresh projection again instead of returning a
                # READY based on a stale logical picture.  Foreign ownership
                # that appears *after* the protected proof is a later race and
                # must be rechecked by WA4-E before physical mutation.
                current = fresh
                after = self._classify(current)
                if after.get("proof") == proof:
                    return self._result(
                        initial,
                        current,
                        state=READY_FOR_EXECUTION,
                        reason=current["next_safe_action"],
                        steps=steps,
                    )
                continue

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
            action = decision["step"]
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

        return self._result(
            initial,
            current,
            state=FAIL_CLOSED,
            reason="recovery loop terminated unexpectedly",
            steps=steps,
            requires_human=True,
            error="RECOVERY_LOOP_INTERNAL",
        )
