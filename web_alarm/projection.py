"""RC-5 canonical projection: authoritative persistent state -> pure projection.

The persisted checkpoint is a projection, never an authority. ``build`` derives
the current TASK picture only from the authoritative stores:

- TaskStore (TaskRecord, TaskPlanRecord, MicrotaskRecord);
- Manifest / restore-point integrity (pure verification);
- OperationStore (identity, status, revision, contract);
- ResolutionStore + Resolver freshness;
- RC-3 TargetClaimStore (active ownership);
- RC-4 RollbackStore (status, revision, receipts, claims_released, NEXT).

It never reads checkpoint.json to build the projection, never reads the event
history, takes no lock and writes nothing. A persisted checkpoint is only
compared with a freshly built projection (``validate_checkpoint``); an explicit
``rebuild_checkpoint`` (or a workflow mutation after its authoritative state
change) is the only normal writer of checkpoint.json / checkpoint.md.

NEXT SAFE ACTION precedence (one deterministic rule):
-. a COMPLETED / ARCHIVED (or moved) TASK -> read-only history; the recovery
   facts it may still carry stay diagnostics, never a NEXT (RC-5 Repair #2);
0. structural projection blocker (impossible plan state, unreadable store)
   -> fail-closed manual repair;
1. tracked RC-4 rollback session of the operation's authoritative ROLLBACK
   resolution -> the session's persistent NEXT;
2. the Resolver's authoritative resolution (accepted ABORT, else the latest
   fresh accepted, else a fresh rejection's advice) -> its persistent NEXT;
3. an accepted resolution that is no longer fresh -> never authority: a new
   reconciliation is required;
4. no applicable resolution and an operation (or microtask) in a recovery
   state -> advisory reconciliation;
5. normal state -> canonical microtask lifecycle (or the closeout gate once
   every microtask is VERIFIED).
Recovery Reports stay evidence/history and never override this order.

RC-6 refinements: a step that would advance a destructive rollback of a
VERIFIED or non-current stage is reported as ROLLBACK_STAGE_PROTECTED (R1),
and recovery settlements are judged against one aggregated disposition per
microtask (``settlement_lifecycle_target``), never one settlement alone (R2).
Repair #3 (F-B): a non-destructive settlement (ADOPT, ABORT) of an operation
whose microtask is already VERIFIED is administrative only; VERIFIED is its
disposition (``effective_settlement_target``). Only a ROLLBACK settlement on a
VERIFIED microtask is a SETTLEMENT_CONTRADICTION.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .event_checkpoint_store import EventCheckpointStore, EventCheckpointStoreError
from .manifest_store import ManifestSnapshotStore, ManifestStoreError
from .microtask_gate import (  # noqa: F401  (R2 rules live there since Repair #3; re-exported)
    authoritative_action,
    current_settlements_by_microtask,
    effective_settlement_target,
    rollback_stage_protected,
    settlement_lifecycle_satisfied,
    settlement_lifecycle_target,
)
from .models import CheckpointRecord, MicrotaskStatus, OperationStatus, TaskStatus, utc_now_iso
from .operation_store import OperationStore, OperationStoreError
from .reconciliation import ReconciliationEvidenceError
from .reconciliation_service import ReconciliationService
from .resolution_store import ResolutionAction, ResolutionResult, ResolutionStoreError
from .resolver_service import ResolverError, ResolverService
from .rollback_service import rollback_session_facts
from .rollback_store import APPLYING, CLOSED, FAILED, PARTIAL, PRESERVATION_FAILED, T_APPLYING, VERIFIED, RollbackStore, RollbackStoreError
from .state_machine import ServerStateMachine
from .target_claim_store import TargetClaimStore, TargetClaimStoreError
from .task_store import TaskStore, TaskStoreError

PROJECTION_VERSION = 1

# persisted checkpoint validation states
CHECKPOINT_VALID = "VALID"
CHECKPOINT_STALE = "STALE"
CHECKPOINT_INCONSISTENT = "INCONSISTENT"
CHECKPOINT_LEGACY = "LEGACY_UNVALIDATED"
CHECKPOINT_MISSING = "MISSING"
CHECKPOINT_CORRUPT = "CORRUPT"

_RECOVERY_MICROTASK_STATUSES = {
    MicrotaskStatus.BLOCKED_PREPARE,
    MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT,
    MicrotaskStatus.RECOVERY_REQUIRED,
    MicrotaskStatus.FAILED_VERIFICATION,
}
_MUTATION_FATE_OPEN = {OperationStatus.STARTED, OperationStatus.UNKNOWN_AFTER_DISCONNECT}
# a rollback session in one of these states needs no further rollback step
_ROLLBACK_SETTLED = {CLOSED, PRESERVATION_FAILED}
# RC-5 Repair #2: operation recovery states in which RC-6 still has to settle an
# accepted decision (administrative: lifecycle disposition, ownership release)
_SETTLEMENT_PENDING = frozenset({
    "ABORT_ACCEPTED",
    "ADOPT_ACCEPTED",
    "ABORT_OVER_SETTLEMENT",
    "ADOPT_SETTLED",
    "ABORT_SETTLED",
    "ROLLBACK_SETTLED",
})

# RC-6 Repair #2 (R1): a tracked rollback may make destructive progress only for
# an operation of the *current* stage (the first non-VERIFIED microtask in plan
# order).  A VERIFIED stage is protected history (doc 23 §11, invariant 5): no
# procedure authorizes rolling back an accepted stage, and a stage after the
# current one has not started (rollback_stage_protected, re-exported above from
# microtask_gate; since Repair #4B RC-4 applies it itself, rollback_refusal).

# recovery states whose next coordinator step can advance a destructive restore
# (prepare, then apply with per-target restore); finalize/release-only and
# close paths are not among them
ROLLBACK_DESTRUCTIVE_STATES = frozenset({
    "ROLLBACK_ACCEPTED",
    "ROLLBACK_PREPARED",
    "ROLLBACK_PRESERVED",
    "ROLLBACK_AUTHORIZED",
    "ROLLBACK_APPLYING",
})


class ProjectionError(RuntimeError):
    """The projection or its checkpoint cannot be built or persisted safely."""


def fingerprint(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _item(code: str, reason: str, **extra: Any) -> dict[str, Any]:
    return dict({"code": code, "reason": reason}, **extra)


# metadata: not covered by the projection fingerprint. ``advisory_reconciliation``
# holds the full advisory calculation(s) behind NEXT; their identity (evidence
# fingerprint + decision) is in the source basis, so nothing escapes validation.
_METADATA = (
    "source_basis", "source_fingerprint", "projection_fingerprint", "generated_at", "advisory_reconciliation",
)


def semantic(projection: dict[str, Any]) -> dict[str, Any]:
    """The part of a projection its fingerprint covers (no metadata, no clock)."""
    return {key: value for key, value in projection.items() if key not in _METADATA}


def checkpoint_fields(projection: dict[str, Any]) -> dict[str, Any]:
    """The legacy checkpoint fields a projection renders to (deterministic)."""
    position = projection["position"]
    try:
        status = MicrotaskStatus(position["current_status"])
    except ValueError:  # NO_MICROTASK: the legacy schema has no such status
        status = MicrotaskStatus.PLANNED
    snapshot = projection["restore_point"]["status"]
    return {
        "last_verified_microtask_id": position["last_verified"],
        "current_microtask_id": position["current_microtask_id"],
        "current_status": status.value,
        "snapshot_status": snapshot if snapshot in ("VERIFIED", "NOT_APPLICABLE") else "NOT_VERIFIED",
        "last_operation_id": projection["last_operation_id"],
        "next_safe_action": projection["next_safe_action"],
    }


def _checkpoint_meta(projection: dict[str, Any]) -> dict[str, Any]:
    return {
        "projection_version": projection["projection_version"],
        "source_fingerprint": projection["source_fingerprint"],
        "projection_fingerprint": projection["projection_fingerprint"],
        "authority_source": projection["authority_source"],
    }


class ProjectionService:
    def __init__(self, storage_root: str | Path | None = None, *, lock_timeout: float | None = None) -> None:
        self.tasks = TaskStore(storage_root)
        root = self.tasks.storage_root
        self.operations = (
            OperationStore(root) if lock_timeout is None else OperationStore(root, lock_timeout=lock_timeout)
        )
        self.manifests = ManifestSnapshotStore(root)
        self.state = EventCheckpointStore(root)
        self.resolver = ResolverService(root)
        self.rollbacks = RollbackStore(root)
        self.claims = TargetClaimStore(root)
        self.reconciliation = ReconciliationService(root)
        self.machine = ServerStateMachine(root)

    # --- facts ------------------------------------------------------------------------------

    def _position(self, plan, records, blockers, diagnostics) -> dict[str, Any]:
        last_verified = None
        first_open = None
        for micro in records:
            if first_open is None:
                if micro.status is MicrotaskStatus.VERIFIED:
                    last_verified = micro.microtask_id
                else:
                    first_open = micro.microtask_id
            elif micro.status is MicrotaskStatus.VERIFIED:
                blockers.append(_item(
                    "VERIFIED_OUT_OF_ORDER",
                    f"{micro.microtask_id} is VERIFIED after the non-VERIFIED {first_open}",
                    microtask_id=micro.microtask_id,
                ))
            elif micro.status is not MicrotaskStatus.PLANNED:
                blockers.append(_item(
                    "LATER_STAGE_STARTED",
                    f"{micro.microtask_id} is {micro.status.value} before {first_open} is VERIFIED",
                    microtask_id=micro.microtask_id,
                ))
        active = [m.microtask_id for m in records if m.status is MicrotaskStatus.ACTIVE]
        if len(active) > 1:
            blockers.append(_item("MULTIPLE_ACTIVE", f"more than one ACTIVE microtask: {active}", microtasks=active))
        all_verified = bool(records) and first_open is None
        current = first_open if first_open is not None else (records[-1].microtask_id if records else None)
        status = next((m.status.value for m in records if m.microtask_id == current), "NO_MICROTASK")
        order = [m.microtask_id for m in records]
        pointer = plan.current_microtask_id
        if pointer is None:
            pointer_state = "ABSENT"
        elif pointer == current:
            pointer_state = "CORROBORATED"
        elif current is not None and pointer in order and order.index(pointer) < order.index(current):
            pointer_state = "STALE_BEHIND_LIFECYCLE"
        else:
            pointer_state = "CONTRADICTS_LIFECYCLE"
        if pointer_state not in ("ABSENT", "CORROBORATED"):
            diagnostics.append(_item(
                "PLAN_POINTER_" + pointer_state,
                f"plan.current_microtask_id={pointer} is not authority; lifecycle current is {current}",
            ))
        return {
            "microtasks": [
                {"microtask_id": m.microtask_id, "sequence": m.sequence, "title": m.title, "status": m.status.value}
                for m in records
            ],
            "last_verified": last_verified,
            "current_microtask_id": current,
            "current_status": status,
            "all_verified": all_verified,
            "plan_pointer": pointer,
            "plan_pointer_state": pointer_state,
        }

    def _restore_point(self, task_id: str, microtask_id: str | None) -> tuple[dict[str, Any], list[Any]]:
        if microtask_id is None:
            return {"microtask_id": None, "status": "NOT_APPLICABLE", "manifest_id": None, "reason": None}, []
        try:
            work_dir = self.tasks.microtask_directory(task_id, microtask_id)
        except TaskStoreError as exc:
            view = {"microtask_id": microtask_id, "status": "NOT_VERIFIED", "manifest_id": None, "reason": str(exc)}
            return view, [view["status"], str(exc)]
        if not (work_dir / ManifestSnapshotStore.RESTORE_DIR / "manifest.json").is_file():
            return {"microtask_id": microtask_id, "status": "NOT_PREPARED", "manifest_id": None, "reason": None}, []
        try:
            # active_only=False: pure — an integrity failure only raises, it never blocks state
            manifest = self.manifests.verify_restore_point(task_id, microtask_id)
        except (ManifestStoreError, TaskStoreError) as exc:
            view = {"microtask_id": microtask_id, "status": "NOT_VERIFIED", "manifest_id": None, "reason": str(exc)}
            return view, ["NOT_VERIFIED", str(exc)]
        view = {"microtask_id": microtask_id, "status": "VERIFIED", "manifest_id": manifest.manifest_id, "reason": None}
        return view, ["VERIFIED", manifest.manifest_id, manifest.updated_at]

    def _claims(self, task_id: str) -> tuple[list[dict[str, Any]], str | None]:
        """Active RC-3 claims held for this TASK (its operations or its rollbacks); read-only scan."""
        if not self.claims.root.is_dir():
            return [], None
        active: list[dict[str, Any]] = []
        try:
            for path in sorted(self.claims.root.glob("*.json")):
                raw = json.loads(path.read_text(encoding="utf-8"))
                data = self.claims.load(raw["physical_key"])
                claim = data["active"]
                if claim is None or claim["task_id"] != task_id:
                    continue
                active.append({
                    "target_hash": data["target_hash"],
                    "target": claim["target"],
                    "claim_id": claim["claim_id"],
                    "generation": claim["generation"],
                    "operation_id": claim["operation_id"],
                    "owner": claim.get("owner") or {"kind": "OPERATION"},
                })
        except (OSError, ValueError, KeyError, TypeError, TargetClaimStoreError) as exc:
            return active, f"target claim store unreadable: {exc}"
        return active, None

    @staticmethod
    def _rollback_settled(session: dict[str, Any]) -> bool:
        """A tracked rollback no longer needs operational attention."""
        return session["status"] in _ROLLBACK_SETTLED or (
            session["status"] == VERIFIED and session["claims_released"]
        )

    @staticmethod
    def _aborted_rollback_recovery(session: dict[str, Any], abort_record) -> dict[str, Any]:
        """Composite authority: Resolver ABORT + a still-open RC-4 session.

        ABORT revokes destructive continuation but does not erase the tracked
        rollback lifecycle.  The session must still reach a safe terminal
        state.  An interrupted physical write is reconciled through RC-4's
        existing apply path before close; otherwise close is the next action.
        """
        rollback_id = session["rollback_id"]
        in_flight = list(session.get("in_flight") or [])
        own_effects = bool(session.get("own_effects_started"))
        needs_finalize = bool(session.get("needs_rc4_finalize"))
        release_pending = session["status"] == VERIFIED and not session["claims_released"]
        unsafe_final = session["status"] in {PARTIAL, FAILED}
        if release_pending:
            state = "ROLLBACK_ABORTED_RELEASE_PENDING"
            next_action = (
                f"rollback {rollback_id} is VERIFIED but ownership release was interrupted before ABORT "
                f"{abort_record.resolution_id}. Finish RC-4 release only; do not repeat any restore effect"
            )
        elif in_flight:
            state = "ROLLBACK_ABORTED_IN_FLIGHT"
            next_action = (
                f"rollback {rollback_id} is still open, but Resolver recovery was ABORTED by "
                f"{abort_record.resolution_id}; do not continue untouched destructive restore. "
                f"Reconcile only the already-interrupted target fate through RC-4 apply once ({in_flight}); "
                "RC-4 will refuse further destructive continuation under ABORT. Close the tracked session "
                "only if reconciliation proves no rollback effect landed; otherwise preserve its ownership "
                "for manual disposition"
            )
        elif needs_finalize:
            state = "ROLLBACK_ABORTED_NEEDS_FINALIZE"
            next_action = (
                f"rollback {rollback_id} has a persisted DRIFTED/FAILED target from an interrupted RC-4 "
                f"step and was then ABORTED by {abort_record.resolution_id}. Run RC-4 apply only to "
                "finalize the already-persisted outcome; do not continue untouched restore targets"
            )
        elif unsafe_final:
            state = "ROLLBACK_ABORTED_UNSAFE_FINAL"
            next_action = (
                f"rollback {rollback_id} is {session['status']} after a non-verified rollback outcome and "
                f"Resolver recovery is ABORTED by {abort_record.resolution_id}. Keep ownership; manual "
                "project-level disposition is required before close/release"
            )
        elif own_effects:
            state = "ROLLBACK_ABORTED_AFTER_EFFECTS"
            next_action = (
                f"rollback {rollback_id} already has persistent own restore effects, while Resolver recovery "
                f"was ABORTED by {abort_record.resolution_id}. Do not continue untouched restore and do not "
                "close/release ownership automatically; manual project-level disposition is required"
            )
        else:
            state = "ROLLBACK_ABORTED_OPEN"
            next_action = (
                f"rollback {rollback_id} is still open, but Resolver recovery was ABORTED by "
                f"{abort_record.resolution_id}; no rollback effect has started. Close the tracked "
                "rollback session to release recovery ownership; after it is terminal, the accepted "
                "ABORT may become the top-level recovery state"
            )
        return {
            "state": state,
            "source": "rollback",
            "resolution_id": abort_record.resolution_id,
            "rollback_id": rollback_id,
            "rollback_resolution_id": session["resolution_id"],
            "next_safe_action": next_action,
        }

    @staticmethod
    def _superseded_rollback_recovery(session: dict[str, Any], current_record) -> dict[str, Any]:
        """A newer accepted Resolver action superseded the basis of an open rollback."""
        rollback_id = session["rollback_id"]
        action = current_record.action.value
        in_flight = list(session.get("in_flight") or [])
        own_effects = bool(session.get("own_effects_started"))
        needs_finalize = bool(session.get("needs_rc4_finalize"))
        release_pending = session["status"] == VERIFIED and not session["claims_released"]
        unsafe_final = session["status"] in {PARTIAL, FAILED}
        if release_pending:
            state = "ROLLBACK_SUPERSEDED_RELEASE_PENDING"
            next_action = (
                f"rollback {rollback_id} is VERIFIED but ownership release was interrupted before newer "
                f"{action} resolution {current_record.resolution_id}. Finish RC-4 release only; do not "
                "repeat any restore effect before following the newer resolution"
            )
        elif in_flight:
            state = "ROLLBACK_SUPERSEDED_IN_FLIGHT"
            next_action = (
                f"rollback {rollback_id} is still open with interrupted target fate {in_flight}, while "
                f"newer accepted {action} resolution {current_record.resolution_id} superseded its recovery "
                "basis. Do not continue the old rollback, do not execute the newer action, and do not call "
                "rollback apply/close blindly: manual review of the interrupted target and RC-4 session is "
                f"required before the old session can be made terminal and {action} may be followed"
            )
        elif needs_finalize:
            state = "ROLLBACK_SUPERSEDED_NEEDS_FINALIZE"
            next_action = (
                f"rollback {rollback_id} has a persisted DRIFTED/FAILED target from an interrupted RC-4 "
                f"step and was superseded by accepted {action} resolution {current_record.resolution_id}. "
                "Run RC-4 apply only to finalize the already-persisted outcome; do not continue untouched "
                "restore targets"
            )
        elif unsafe_final:
            state = "ROLLBACK_SUPERSEDED_UNSAFE_FINAL"
            next_action = (
                f"rollback {rollback_id} is {session['status']} after a non-verified rollback outcome and "
                f"was superseded by accepted {action} resolution {current_record.resolution_id}. Keep "
                f"ownership; manual disposition is required before {action} or close/release"
            )
        elif own_effects:
            state = "ROLLBACK_SUPERSEDED_AFTER_EFFECTS"
            next_action = (
                f"rollback {rollback_id} already has persistent own restore effects and was superseded by "
                f"accepted {action} resolution {current_record.resolution_id}. Do not continue the old "
                "rollback and do not close/release ownership automatically; manual disposition is required "
                f"before {action} may be followed"
            )
        else:
            state = f"ROLLBACK_SUPERSEDED_BY_{action}"
            next_action = (
                f"rollback {rollback_id} is still open, but newer accepted {action} resolution "
                f"{current_record.resolution_id} superseded its recovery basis before any rollback effect. "
                "Close the tracked rollback session first; after it is terminal, follow the "
                f"accepted {action} resolution"
            )
        return {
            "state": state,
            "source": "rollback",
            "resolution_id": current_record.resolution_id,
            "rollback_id": rollback_id,
            "rollback_resolution_id": session["resolution_id"],
            "next_safe_action": next_action,
        }

    @staticmethod
    def _stale_rollback_recovery(session: dict[str, Any]) -> dict[str, Any]:
        """An open rollback whose original Resolver basis is no longer fresh."""
        rollback_id = session["rollback_id"]
        in_flight = list(session.get("in_flight") or [])
        if in_flight:
            state = "ROLLBACK_STALE_IN_FLIGHT"
            next_action = (
                f"rollback {rollback_id} is still open with interrupted target fate {in_flight}, and its "
                "Resolver basis is stale. Do not continue destructive restore and do not call rollback "
                "apply/close blindly: manual review of the interrupted target and RC-4 session is required "
                "before the session can be made terminal; then run a new reconciliation"
            )
        else:
            state = "ROLLBACK_STALE_OPEN"
            next_action = (
                f"rollback {rollback_id} is still open but its Resolver basis is stale. Do not apply the "
                "rollback. Close the tracked rollback session, then run a new reconciliation before any "
                "new recovery mutation"
            )
        return {
            "state": state,
            "source": "rollback",
            "resolution_id": session["resolution_id"],
            "rollback_id": rollback_id,
            "rollback_resolution_id": session["resolution_id"],
            "next_safe_action": next_action,
        }

    @staticmethod
    def _multiple_open_rollbacks_recovery(op, sessions, current_record) -> dict[str, Any]:
        """Fail closed if more than one tracked rollback for one operation is open."""
        ordered = sorted(sessions, key=lambda s: (s["updated_at"], s["rollback_id"]))
        chosen = ordered[-1]
        ids = [s["rollback_id"] for s in ordered]
        in_flight = sorted({target for s in ordered for target in (s.get("in_flight") or [])})
        current = (
            f"current Resolver action is accepted {current_record.action.value} "
            f"({current_record.resolution_id}); "
            if current_record is not None and current_record.result is ResolutionResult.ACCEPTED
            else ""
        )
        interrupt = (
            f"in-flight target fate exists ({in_flight}); manual review is required before any apply/close; "
            if in_flight
            else ""
        )
        return {
            "state": "ROLLBACK_MULTIPLE_OPEN",
            "source": "rollback",
            "resolution_id": (
                current_record.resolution_id
                if current_record is not None
                else chosen["resolution_id"]
            ),
            "rollback_id": chosen["rollback_id"],
            "open_rollback_ids": ids,
            "next_safe_action": (
                f"multiple tracked rollback sessions are still open for operation {op.operation_id}: {ids}; "
                f"{current}{interrupt}inspect and close each superseded/open session before following any "
                "new recovery action"
            ),
        }

    @staticmethod
    def _protect_stage(
        op,
        recovery: dict[str, Any] | None,
        sessions: list[dict[str, Any]],
        *,
        microtask_status: str,
        current_microtask_id: str | None,
    ) -> dict[str, Any] | None:
        """R1: never advance a destructive rollback of a VERIFIED / non-current stage.

        Only an operation of the current stage may get a rollback prepare/apply
        as its next step. Finalize-only of an already persisted RC-4 outcome
        restores nothing and stays allowed, like release-only and close.
        """
        if recovery is None or recovery["state"] not in ROLLBACK_DESTRUCTIVE_STATES:
            return recovery
        if recovery["state"] == "ROLLBACK_APPLYING":
            session = next(
                (s for s in sessions if s["rollback_id"] == recovery.get("rollback_id")),
                None,
            )
            if session is not None and session.get("needs_rc4_finalize"):
                return recovery
        if not rollback_stage_protected(op.microtask_id, microtask_status, current_microtask_id):
            return recovery
        target = recovery.get("rollback_id") or recovery.get("resolution_id")
        protected = dict(recovery)
        protected.update(
            state="ROLLBACK_STAGE_PROTECTED",
            protected_state=recovery["state"],
            next_safe_action=(
                f"operation {op.operation_id} belongs to microtask {op.microtask_id} ({microtask_status}), "
                f"not to the current stage ({current_microtask_id}). A VERIFIED or non-current stage is "
                "protected history: RC-6 never prepares, continues or applies a destructive rollback of it "
                f"({recovery['state']}, {target}). Do not run rollback prepare/apply; an explicit "
                "project-level decision is required"
            ),
        )
        return protected

    def _operation_recovery(
        self,
        op,
        records,
        actions,
        authoritative,
        sessions,
        *,
        microtask_status: str,
        own_claim_open: bool,
        microtask_settlements: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Recovery authority of one operation, by the precedence in the module docstring.

        A nonterminal RC-4 session is operational state in its own right.  It
        therefore stays visible even if the Resolver later records another
        action.  Accepted ABORT is special: it changes what is safe to do with
        the open session (cleanup/reconcile, never destructive continuation)
        but does not make that session disappear.
        """
        open_sessions = [s for s in sessions if not self._rollback_settled(s)]
        authoritative_record = None
        if authoritative is not None:
            rid = authoritative["resolution_id"]
            authoritative_record = next((r for r in records if r.resolution_id == rid), None)

        if open_sessions:
            # Prefer the session of the Resolver action still considered current;
            # otherwise the latest open tracked session is the recovery work that
            # must be made terminal before it can disappear from top-level NEXT.
            by_resolution = {s["resolution_id"]: s for s in open_sessions}
            session = (
                by_resolution.get(authoritative["resolution_id"])
                if authoritative is not None
                else None
            )
            if session is None:
                session = max(open_sessions, key=lambda s: (s["updated_at"], s["rollback_id"]))

            if len(open_sessions) > 1:
                return self._multiple_open_rollbacks_recovery(op, open_sessions, authoritative_record)

            # A later accepted action cannot erase the old tracked session.  It
            # supersedes what may safely happen next: clean up the old session
            # first, then expose/follow the newer Resolver authority.
            if (
                authoritative_record is not None
                and authoritative_record.result is ResolutionResult.ACCEPTED
                and authoritative_record.resolution_id != session["resolution_id"]
            ):
                if authoritative_record.action is ResolutionAction.ABORT:
                    return self._aborted_rollback_recovery(session, authoritative_record)
                return self._superseded_rollback_recovery(session, authoritative_record)

            session_action = next(
                (a for a in actions if a["resolution_id"] == session["resolution_id"]),
                None,
            )
            if session_action is None or not session_action["fresh"]:
                # RC-4 can be in a persisted restart/finalize phase whose
                # authority is receipts/current bytes rather than the literal
                # pre-rollback evidence fingerprint. Projection must mirror
                # that full resume rule, including DRIFTED-before-finalize.
                # PARTIAL/FAILED are persistent non-verified final outcomes:
                # they require explicit manual disposition and must never be
                # downgraded to stale cleanup that auto-releases ownership.
                if (
                    session["status"] not in {PARTIAL, FAILED}
                    and not session.get("resume_via_rc4_required")
                ):
                    return self._stale_rollback_recovery(session)

            return {
                "state": "ROLLBACK_" + session["status"],
                "source": "rollback",
                "resolution_id": session["resolution_id"],
                "rollback_id": session["rollback_id"],
                "next_safe_action": session["next_safe_action"],
            }

        settlement = op.recovery_settlement
        if settlement is not None and (
            authoritative is None or authoritative["resolution_id"] == settlement["resolution_id"]
        ):
            action = settlement["action"]
            # R2: the administrative lifecycle part of a settlement is judged
            # against the microtask's single aggregated disposition, never
            # against what this one settlement alone would want. Repair #3:
            # a VERIFIED microtask absorbs a non-destructive disposition.
            target = effective_settlement_target(microtask_settlements or [action], microtask_status)
            if target is MicrotaskStatus.RECOVERY_REQUIRED and microtask_status == MicrotaskStatus.VERIFIED.value:
                return {
                    "state": "SETTLEMENT_CONTRADICTION",
                    "source": "recovery_settlement",
                    "resolution_id": settlement["resolution_id"],
                    "rollback_id": None,
                    "settled_at": settlement["settled_at"],
                    "lifecycle_target": target.value,
                    "next_safe_action": (
                        f"microtask {op.microtask_id} is VERIFIED, but its operations carry a ROLLBACK "
                        f"recovery settlement (this operation {op.operation_id}: {action}): a rollback physically "
                        "undid work of a verified stage; RC-6 never moves a VERIFIED stage. Manual "
                        "project-level review of this contradiction is required before any recovery step"
                    ),
                }
            administrative_complete = (
                settlement_lifecycle_satisfied(target, microtask_status) and not own_claim_open
            )
            if target is MicrotaskStatus.VERIFIED:
                next_action = (
                    f"operation {op.operation_id} recovery is settled by {action} after its microtask "
                    f"{op.microtask_id} was VERIFIED: the settlement is administrative only and the verified "
                    "stage is unchanged; finish the ownership cleanup"
                )
            elif action == "ADOPT" and target is MicrotaskStatus.RECOVERY_REQUIRED:
                next_action = (
                    f"operation {op.operation_id} was adopted after exact post-state proof, but another "
                    f"operation of microtask {op.microtask_id} carries an ABORT/ROLLBACK settlement: the "
                    "microtask stays RECOVERY_REQUIRED; finish the administrative settlement cleanup only"
                )
            elif action == "ADOPT":
                next_action = (
                    f"operation {op.operation_id} was adopted after exact post-state proof; "
                    "the physical effect is not repeated; finish/verify the operation's microtask"
                )
            elif action == "ROLLBACK":
                next_action = (
                    f"operation {op.operation_id} has a verified rollback settlement; its old attempt was undone; "
                    "the microtask remains RECOVERY_REQUIRED pending an explicit new recovery/lifecycle decision"
                )
            else:
                next_action = (
                    f"operation {op.operation_id} recovery is durably ABORTED; the microtask remains "
                    "RECOVERY_REQUIRED and normal mutation is forbidden until an explicit lifecycle/replan decision"
                )

            # A completed settlement is durable history, not perpetual recovery
            # attention.  Suppress its matching consumed Resolver action here;
            # a later *different* accepted resolution still falls through below.
            if administrative_complete:
                return None

            return {
                "state": action + "_SETTLED",
                "source": "recovery_settlement",
                "resolution_id": settlement["resolution_id"],
                "rollback_id": None,
                "settled_at": settlement["settled_at"],
                "pending_admin": True,
                "lifecycle_target": target.value,
                "next_safe_action": next_action,
            }

        if (
            settlement is not None
            and authoritative_record is not None
            and authoritative_record.action is ResolutionAction.ABORT
            and authoritative_record.result is ResolutionResult.ACCEPTED
        ):
            # Repair #3 (F-B): an ABORT accepted after this operation was already
            # settled. The settlement stays its immutable record; the ABORT is
            # completed administratively by the microtask disposition alone.
            target = effective_settlement_target(microtask_settlements or ["ABORT"], microtask_status)
            if target is MicrotaskStatus.RECOVERY_REQUIRED and microtask_status == MicrotaskStatus.VERIFIED.value:
                return {
                    "state": "SETTLEMENT_CONTRADICTION",
                    "source": "recovery_settlement",
                    "resolution_id": authoritative_record.resolution_id,
                    "rollback_id": None,
                    "settled_at": settlement["settled_at"],
                    "lifecycle_target": target.value,
                    "next_safe_action": (
                        f"microtask {op.microtask_id} is VERIFIED, but its operations carry a ROLLBACK recovery "
                        "settlement: RC-6 never moves a VERIFIED stage. Manual project-level review of this "
                        "contradiction is required before any recovery step"
                    ),
                }
            if settlement_lifecycle_satisfied(target, microtask_status) and not own_claim_open:
                return None
            return {
                "state": "ABORT_OVER_SETTLEMENT",
                "source": "recovery_settlement",
                "resolution_id": authoritative_record.resolution_id,
                "rollback_id": None,
                "settled_at": settlement["settled_at"],
                "pending_admin": True,
                "lifecycle_target": target.value,
                "next_safe_action": (
                    f"operation {op.operation_id} was already settled by {settlement['action']}; the later "
                    f"accepted ABORT {authoritative_record.resolution_id} closes its recovery administratively: "
                    f"microtask {op.microtask_id} goes to {target.value} and the operation's ownership is released"
                ),
            }

        if authoritative is not None:
            rid = authoritative["resolution_id"]

            # A terminal RC-4 session remains the historical outcome of its own
            # Resolver ROLLBACK.  It no longer blocks a *newer* accepted action,
            # because that action has a different resolution_id, but when the
            # Resolver still points at this same ROLLBACK we surface the tracked
            # outcome rather than degrading it to RESOLUTION_STALE after its own
            # physical effects changed the evidence fingerprint.
            settled = next(
                (
                    session for session in sessions
                    if session["resolution_id"] == rid and self._rollback_settled(session)
                ),
                None,
            )
            if settled is not None:
                return {
                    "state": "ROLLBACK_" + settled["status"],
                    "source": "rollback",
                    "resolution_id": settled["resolution_id"],
                    "rollback_id": settled["rollback_id"],
                    "next_safe_action": settled["next_safe_action"],
                }

            record = next(r for r in records if r.resolution_id == rid)
            action = next(a for a in actions if a["resolution_id"] == rid)
            if record.result is ResolutionResult.ACCEPTED and (action["fresh"] or record.action is ResolutionAction.ABORT):
                state, source = f"{record.action.value}_ACCEPTED", "resolver"
            elif record.result is ResolutionResult.REJECTED and action["fresh"]:
                state, source = f"{record.action.value}_REJECTED", "resolver"
            else:
                state, source = "RESOLUTION_STALE", "resolver_stale"
            return {
                "state": state,
                "source": source,
                "resolution_id": rid,
                "rollback_id": None,
                "next_safe_action": authoritative["next_safe_action"],
            }
        if op.status in _MUTATION_FATE_OPEN:
            return {
                "state": "RECONCILIATION_REQUIRED",
                "source": "reconciliation",
                "resolution_id": None,
                "rollback_id": None,
                "next_safe_action": None,  # filled by the advisory reconciliation
            }
        return None

    def advise(self, task_id: str, microtask_id: str, operation_id: str) -> tuple[dict[str, Any] | None, str | None]:
        try:
            return self.reconciliation.reconcile(task_id, microtask_id, operation_id), None
        except (ReconciliationEvidenceError, OperationStoreError, ManifestStoreError, TaskStoreError) as exc:
            return None, str(exc)

    # --- build ---------------------------------------------------------------------------------

    def build(self, task_id: str) -> dict[str, Any]:
        """Pure: authoritative stores -> deterministic projection. No lock, no write."""
        task = self.tasks.open_task(task_id)
        task_dir = self.tasks.task_directory(task_id)
        location = "active" if task_dir.parent == self.tasks.active_dir else "completed"
        plan = self.tasks.open_plan(task_id)
        blockers: list[dict[str, Any]] = []
        diagnostics: list[dict[str, Any]] = []
        basis: dict[str, Any] = {
            "task": [task.task_id, task.workspace_id, task.status.value, task.plan_revision, task.updated_at, location],
            "plan": [plan.revision, list(plan.microtask_ids), plan.current_microtask_id, plan.updated_at],
        }

        try:
            records = self.tasks.list_microtasks(task_id)
            basis["microtasks"] = [[m.microtask_id, m.sequence, m.status.value, m.updated_at] for m in records]
        except TaskStoreError as exc:
            records = []
            basis["microtasks"] = ["UNREADABLE", str(exc)]
            blockers.append(_item("MICROTASKS_UNREADABLE", str(exc)))
        microtask_status = {m.microtask_id: m.status.value for m in records}
        on_disk = sorted(path.stem for path in (task_dir / "microtasks").glob("*.json"))
        orphans = [mid for mid in on_disk if mid not in plan.microtask_ids]
        basis["orphan_microtasks"] = orphans
        if orphans:
            diagnostics.append(_item("ORPHAN_MICROTASKS", f"microtask records outside the plan: {orphans}"))
        position = self._position(plan, records, blockers, diagnostics)
        restore_point, basis["restore_point"] = self._restore_point(task_id, position["current_microtask_id"])
        if (
            position["current_status"] == MicrotaskStatus.ACTIVE.value
            and restore_point["status"] != "VERIFIED"
        ):
            blockers.append(
                _item(
                    "RESTORE_POINT_NOT_VERIFIED",
                    (
                        f"ACTIVE microtask {position['current_microtask_id']} has restore point "
                        f"{restore_point['status']}: "
                        f"{restore_point['reason'] or 'verified restore evidence is unavailable'}"
                    ),
                    microtask_id=position["current_microtask_id"],
                )
            )

        try:
            operations = self.operations.list(task_id)
            basis["operations"] = [
                [op.operation_id, op.microtask_id, op.status.value, op.revision, op.contract_version,
                 op.request_fingerprint, op.recovery_settlement, op.updated_at]
                for op in operations
            ]
        except (OperationStoreError, TaskStoreError) as exc:
            operations = []
            basis["operations"] = ["UNREADABLE", str(exc)]
            blockers.append(_item("OPERATIONS_UNREADABLE", str(exc)))
        try:
            resolutions = self.resolver.store.list(task_id)
        except ResolutionStoreError as exc:
            resolutions = []
            blockers.append(_item("RESOLUTIONS_UNREADABLE", str(exc)))
        try:
            stored = self.rollbacks.list(task_id)
            sessions = []
            for item in stored:
                facts = rollback_session_facts(item)
                # Projection-only operational detail.  Receipts stay historical,
                # while an APPLYING target means close() cannot yet prove its fate.
                facts["in_flight"] = [
                    target["source_path"] for target in item["targets"]
                    if target["status"] == T_APPLYING
                ]
                sessions.append(facts)
            session_ops = {item["rollback_id"]: item["operation_id"] for item in stored}
        except RollbackStoreError as exc:
            sessions, session_ops = [], {}
            blockers.append(_item("ROLLBACKS_UNREADABLE", str(exc)))
        basis["rollbacks"] = [
            [s["rollback_id"], session_ops[s["rollback_id"]], s["resolution_id"], s["status"], s["revision"],
             s["claims_released"]]
            for s in sessions
        ]
        claims, claims_error = self._claims(task_id)
        basis["claims"] = [[c["target_hash"], c["claim_id"], c["generation"], c["operation_id"], c["owner"]] for c in claims]
        if claims_error is not None:
            basis["claims_error"] = claims_error
            diagnostics.append(_item("CLAIMS_UNREADABLE", claims_error))

        views: list[dict[str, Any]] = []
        basis_resolutions: list[Any] = []
        advisories: dict[str, Any] = {}
        advice_by_op: dict[str, Any] = {}
        resolved_ops = []
        for op in operations:
            records_for_op = [r for r in resolutions if r.operation_id == op.operation_id]
            actions: list[dict[str, Any]] = []
            authoritative = None
            if records_for_op:
                try:
                    facts = self.resolver.report_facts(task_id, op.microtask_id, op.operation_id)
                    actions, authoritative = facts["resolver_actions"], facts["next_safe_action"]
                except ResolverError as exc:
                    blockers.append(_item("RESOLVER_FACTS_UNAVAILABLE", str(exc), operation_id=op.operation_id))
            basis_resolutions.extend(
                [a["resolution_id"], op.operation_id, a["action"], a["result"], a["evidence_fingerprint"],
                 a["operation_revision"], a["fresh"], a["freshness_code"]]
                for a in actions
            )
            resolved_ops.append((op, records_for_op, actions, authoritative))
        # R2: one recovery disposition per microtask, from every *current*
        # settlement of its operations (a settlement whose operation has a newer
        # authoritative Resolver action no longer speaks for that operation).
        settlements_by_microtask = current_settlements_by_microtask(
            (op, authoritative_action({"next_safe_action": authoritative, "resolver_actions": actions}))
            for op, _, actions, authoritative in resolved_ops
        )
        for op, records_for_op, actions, authoritative in resolved_ops:
            op_sessions = [s for s in sessions if session_ops[s["rollback_id"]] == op.operation_id]
            op_micro_status = microtask_status.get(op.microtask_id, "MISSING")
            own_claim_open = any(
                claim["operation_id"] == op.operation_id
                and (claim.get("owner") or {}).get("kind") != "ROLLBACK"
                for claim in claims
            )
            recovery = self._operation_recovery(
                op,
                records_for_op,
                actions,
                authoritative,
                op_sessions,
                microtask_status=op_micro_status,
                own_claim_open=own_claim_open,
                microtask_settlements=settlements_by_microtask.get(op.microtask_id),
            )
            recovery = self._protect_stage(
                op,
                recovery,
                op_sessions,
                microtask_status=op_micro_status,
                current_microtask_id=position["current_microtask_id"],
            )
            if recovery is not None and recovery["source"] == "reconciliation":
                advice, error = self.advise(task_id, op.microtask_id, op.operation_id)
                if advice is None:
                    recovery["next_safe_action"] = (
                        f"reconciliation evidence for {op.operation_id} is unavailable ({error}); "
                        "manual review is required before any mutation"
                    )
                    advisories[op.operation_id] = ["UNAVAILABLE", error]
                else:
                    recovery["next_safe_action"] = advice["NEXT_SAFE_ACTION"]
                    recovery["decision"] = advice["DECISION"]["decision"]
                    advisories[op.operation_id] = [
                        advice["DECISION"]["evidence_fingerprint"], advice["DECISION"]["decision"],
                        advice["DECISION"]["reason_code"],
                    ]
                    advice_by_op[op.operation_id] = advice
            disposition = settlement_lifecycle_target(settlements_by_microtask.get(op.microtask_id, []))
            views.append({
                "operation_id": op.operation_id,
                "microtask_id": op.microtask_id,
                "microtask_status": op_micro_status,
                "microtask_disposition": disposition.value if disposition is not None else None,
                "status": op.status.value,
                "revision": op.revision,
                "contract_version": op.contract_version,
                "updated_at": op.updated_at,
                "recovery_settlement": (dict(op.recovery_settlement) if op.recovery_settlement else None),
                "resolutions": actions,
                "rollback_ids": [s["rollback_id"] for s in op_sessions],
                "recovery": recovery,
                "activity": max(
                    [op.updated_at]
                    + [r.created_at for r in records_for_op]
                    + [s["updated_at"] for s in op_sessions]
                ),
            })
        basis["resolutions"] = basis_resolutions
        basis["advisory_reconciliation"] = advisories  # NEXT may depend on it: part of the basis
        last_operation = max(operations, key=lambda op: (op.updated_at, op.operation_id), default=None)

        projection: dict[str, Any] = {
            "projection_version": PROJECTION_VERSION,
            "task": {
                "task_id": task.task_id,
                "workspace_id": task.workspace_id,
                "status": task.status.value,
                "location": location,
                "plan_revision": plan.revision,
            },
            "position": position,
            "restore_point": restore_point,
            "operations": views,
            "last_operation_id": last_operation.operation_id if last_operation is not None else None,
            "rollbacks": sessions,
            "ownership": {"active_claims": claims},
            "blockers": blockers,
            "diagnostics": diagnostics,
        }
        projection["advisory_reconciliation"] = advice_by_op
        self._decide(task_id, projection, task, advisories)
        projection["closeout"] = closeout_blockers(projection)
        if (
            projection["authority_source"] == "lifecycle"
            and position["all_verified"]
            and location == "active"
        ):
            gate = projection["closeout"]
            projection["next_safe_action"] = (
                "every microtask is VERIFIED and the closeout gate is clean: complete the TASK through "
                "the gated `task complete`, or create the next planned microtask"
                if not gate
                else f"every microtask is VERIFIED but closeout is blocked ({gate[0]['code']}): {gate[0]['next']}"
            )
            projection["authority_source"] = "closeout_gate"
        projection["source_basis"] = basis
        projection["source_fingerprint"] = fingerprint(basis)
        projection["projection_fingerprint"] = fingerprint(semantic(projection))
        projection["generated_at"] = utc_now_iso()
        return projection

    def _decide(self, task_id: str, projection: dict[str, Any], task, advisories: dict[str, Any]) -> None:
        """Set recovery, NEXT SAFE ACTION and its authority source (precedence in module docstring)."""
        position = projection["position"]
        attention = [view for view in projection["operations"] if view["recovery"] is not None]
        sessions = {session["rollback_id"]: session for session in projection["rollbacks"]}

        def open_rollback(view: dict[str, Any]) -> bool:
            """An unfinished tracked rollback (ownership held, sequence not closed) comes first."""
            session = sessions.get(view["recovery"]["rollback_id"])
            if view["recovery"]["source"] != "rollback" or session is None:
                return False
            settled = session["status"] in _ROLLBACK_SETTLED or (
                session["status"] == VERIFIED and session["claims_released"]
            )
            return not settled

        focus = max(
            attention,
            key=lambda view: (open_rollback(view), view["activity"], view["operation_id"]),
            default=None,
        )
        recovery: dict[str, Any] = {
            "state": "NORMAL",
            "source": "lifecycle",
            "operation_id": None,
            "resolution_id": None,
            "rollback_id": None,
            "attention": [view["operation_id"] for view in attention],
        }
        if focus is not None:
            # Preserve projection diagnostics such as rollback_resolution_id
            # and open_rollback_ids.  NEXT stays top-level to avoid two copies
            # of operational advice drifting apart.
            recovery.update(
                {
                    key: value
                    for key, value in focus["recovery"].items()
                    if key != "next_safe_action"
                }
            )
            recovery["operation_id"] = focus["operation_id"]
        closed = (
            task.status in (TaskStatus.COMPLETED, TaskStatus.ARCHIVED)
            or projection["task"]["location"] != "active"
        )
        if closed:
            # RC-5 Repair #2 (B): history comes first. No recovery step can run on a
            # closed TASK (its stores refuse writes, RC-6 stops at TASK_COMPLETED), so
            # the recovery facts it still carries are diagnostics, not a NEXT.
            next_action = f"TASK is {task.status.value}; its state is read-only history"
            if attention or projection["blockers"]:
                next_action += (
                    "; the recovery facts it still carries "
                    f"({[view['operation_id'] for view in attention]}) are historical evidence only: "
                    "no recovery action applies to a closed TASK (manual project-level review if they matter)"
                )
            source = "task_status"
        elif projection["blockers"]:
            first = projection["blockers"][0]
            next_action = (
                f"projection is blocked ({first['code']}: {first['reason']}); persistent state is "
                "inconsistent — repair it by manual review before any mutation"
            )
            source = "projection_blocker"
            recovery["state"] = "PROJECTION_BLOCKED"
        elif focus is not None:
            next_action = focus["recovery"]["next_safe_action"]
            source = focus["recovery"]["source"]
        else:
            current = position["current_microtask_id"]
            status = position["current_status"]
            if current is None:
                next_action = "create a microtask and define the TASK plan"
                source = "lifecycle"
            elif (
                MicrotaskStatus(status) is MicrotaskStatus.RECOVERY_REQUIRED
                and any(
                    view["microtask_id"] == current
                    and view["microtask_disposition"] == MicrotaskStatus.RECOVERY_REQUIRED.value
                    for view in projection["operations"]
                )
            ):
                next_action = (
                    f"microtask {current} is RECOVERY_REQUIRED after a durable recovery settlement; "
                    "normal mutation is forbidden. An explicit project-level replan/lifecycle decision "
                    "is required before this microtask can continue"
                )
                source = "lifecycle"
            elif MicrotaskStatus(status) in _RECOVERY_MICROTASK_STATUSES and any(
                view["microtask_id"] == current for view in projection["operations"]
            ):
                op = max(
                    (view for view in projection["operations"] if view["microtask_id"] == current),
                    key=lambda view: (view["updated_at"], view["operation_id"]),
                )
                advice, error = self.advise(task_id, current, op["operation_id"])
                if advice is None:
                    next_action = (
                        f"microtask {current} is {status}; reconciliation evidence for {op['operation_id']} "
                        f"is unavailable ({error}); manual review is required"
                    )
                    advisories[op["operation_id"]] = ["UNAVAILABLE", error]
                else:
                    next_action = advice["NEXT_SAFE_ACTION"]
                    recovery["decision"] = advice["DECISION"]["decision"]
                    projection["advisory_reconciliation"][op["operation_id"]] = advice
                    advisories[op["operation_id"]] = [
                        advice["DECISION"]["evidence_fingerprint"], advice["DECISION"]["decision"],
                        advice["DECISION"]["reason_code"],
                    ]
                recovery.update(state="RECONCILIATION_REQUIRED", source="reconciliation", operation_id=op["operation_id"])
                source = "reconciliation"
            else:
                next_action = self.machine.next_safe_action(task_id, current, status=MicrotaskStatus(status))
                source = "lifecycle"
        recovery["source"] = source
        projection["recovery"] = recovery
        projection["next_safe_action"] = next_action
        projection["authority_source"] = source

    # --- checkpoint ----------------------------------------------------------------------------

    def validate_checkpoint(self, task_id: str, projection: dict[str, Any] | None = None) -> dict[str, Any]:
        """Pure: classify the persisted checkpoint against a freshly built projection."""
        projection = projection or self.build(task_id)
        result: dict[str, Any] = {
            "status": None,
            "reasons": [],
            "authoritative": False,
            "persisted": None,
            "current_source_fingerprint": projection["source_fingerprint"],
            "current_projection_fingerprint": projection["projection_fingerprint"],
        }
        try:
            record = self.state.read_checkpoint(task_id)
        except EventCheckpointStoreError as exc:
            if "checkpoint is missing" in str(exc):
                result.update(status=CHECKPOINT_MISSING, reasons=["no persisted checkpoint"])
            else:
                result.update(status=CHECKPOINT_CORRUPT, reasons=[str(exc)])
            return result
        result["persisted"] = {
            "checkpoint_id": record.checkpoint_id,
            "updated_at": record.updated_at,
            "next_safe_action": record.next_safe_action,
            "projection": record.projection,
        }
        meta = record.projection
        if not isinstance(meta, dict) or meta.get("projection_version") != PROJECTION_VERSION:
            result.update(
                status=CHECKPOINT_LEGACY,
                reasons=["checkpoint has no RC-5 projection basis; its content is never authority"],
            )
            return result
        reasons = []
        stale = meta.get("source_fingerprint") != projection["source_fingerprint"]
        if stale:
            reasons.append("authoritative source changed since the checkpoint was built")
        expected = checkpoint_fields(projection)
        actual = {
            "last_verified_microtask_id": record.last_verified_microtask_id,
            "current_microtask_id": record.current_microtask_id,
            "current_status": record.current_status.value,
            "snapshot_status": record.snapshot_status,
            "last_operation_id": record.last_operation_id,
            "next_safe_action": record.next_safe_action,
        }
        inconsistent = []
        if not stale:
            inconsistent = [name for name in expected if expected[name] != actual[name]]
            if meta.get("projection_fingerprint") != projection["projection_fingerprint"]:
                inconsistent.append("projection_fingerprint")
            if meta != _checkpoint_meta(projection):
                inconsistent.append("projection_metadata")
        try:
            markdown = self.state.checkpoint_markdown(task_id)
        except EventCheckpointStoreError as exc:
            markdown = None
            reasons.append(str(exc))
        if markdown != self.state.render_checkpoint_md(record):
            inconsistent.append("checkpoint.md")
        if inconsistent:
            reasons.append("checkpoint content does not match its basis: " + ", ".join(sorted(set(inconsistent))))
        status = CHECKPOINT_STALE if stale else (CHECKPOINT_INCONSISTENT if inconsistent else CHECKPOINT_VALID)
        result.update(status=status, reasons=reasons, authoritative=False)
        return result

    def rebuild_checkpoint(self, task_id: str) -> dict[str, Any]:
        """Explicit projection write; serialized with operation writers by the TASK lock."""
        try:
            with self.operations.task_lock(task_id):
                return self.rebuild_checkpoint_locked(task_id)
        except OperationStoreError as exc:
            raise ProjectionError(str(exc)) from exc

    def rebuild_checkpoint_locked(self, task_id: str) -> dict[str, Any]:
        """Same as ``rebuild_checkpoint`` for a caller that already holds the TASK lock."""
        try:
            self.tasks.task_directory(task_id, active_only=True)
        except TaskStoreError as exc:
            raise ProjectionError(f"checkpoint rebuild is allowed only for an active TASK: {exc}") from exc
        try:
            projection = self.build(task_id)
        except Exception as exc:  # a projection write must never escape a workflow mutation raw
            raise ProjectionError(f"projection could not be built: {type(exc).__name__}: {exc}") from exc
        existing = None
        try:
            existing = self.state.read_checkpoint(task_id)
        except EventCheckpointStoreError:
            existing = None  # missing/corrupt/legacy: a modern projection replaces it
        fields = checkpoint_fields(projection)
        record = CheckpointRecord(
            task_id=task_id,
            workspace_id=projection["task"]["workspace_id"],
            last_verified_microtask_id=fields["last_verified_microtask_id"],
            current_microtask_id=fields["current_microtask_id"],
            current_status=MicrotaskStatus(fields["current_status"]),
            snapshot_status=fields["snapshot_status"],
            last_operation_id=fields["last_operation_id"],
            next_safe_action=fields["next_safe_action"],
            projection=_checkpoint_meta(projection),
        )
        if existing is not None:
            record.checkpoint_id = existing.checkpoint_id
            record.created_at = existing.created_at
        try:
            written = self.state.write_checkpoint(record)
        except (EventCheckpointStoreError, TaskStoreError) as exc:
            raise ProjectionError(f"checkpoint projection was not written: {exc}") from exc
        return {
            "checkpoint": written,
            "projection": projection,
            "validation": self.validate_checkpoint(task_id),
        }


def closeout_blockers(projection: dict[str, Any]) -> list[dict[str, Any]]:
    """Why this TASK may not be completed now (conservative; empty list = eligible).

    Operation rule (existing RC-2/RC-3 contracts, nothing new is invented):
    - an accepted ABORT closes Resolver-level recovery of its operation;
    - STARTED / UNKNOWN_AFTER_DISCONNECT have an open mutation fate until an
      accepted ABORT or a fresh accepted ADOPT (the RC-3 release rule);
    - INTENT is a pending declared mutation; DONE is not VERIFIED;
    - VERIFIED and FAILED are terminal operation outcomes (an older resolution
      that went stale does not reopen them);
    - a fresh accepted RETRY is a pending future execution;
    - an authoritative ROLLBACK without a VERIFIED rollback whose ownership is
      released has no terminal safe outcome (also when RC-6 R1 reports it as
      ROLLBACK_STAGE_PROTECTED: protected_state keeps ROLLBACK_ACCEPTED).

    RC-5 Repair #2 — with RC-6 the gate is judged on the operation's recovery
    view, the one RC-6 acts on:
    - an accepted ABORT / ADOPT is complete only once RC-6 has settled it and
      finished the settlement administration (RECOVERY_SETTLEMENT_PENDING);
    - a settlement that contradicts a VERIFIED stage blocks (manual review);
    - any other recovery state not reported by a more specific blocker blocks
      as RECOVERY_OPEN (fail-closed for states this rule does not know), except
      advice only: a fresh rejection or a stale, non-authoritative resolution.
    """
    blockers: list[dict[str, Any]] = []
    task = projection["task"]
    position = projection["position"]

    def add(code: str, reason: str, next_action: str, **extra: Any) -> None:
        blockers.append(dict(_item(code, reason, **extra), next=next_action))

    if task["location"] != "active" or task["status"] in (TaskStatus.COMPLETED.value, TaskStatus.ARCHIVED.value):
        add("TASK_NOT_ACTIVE", f"TASK is {task['status']} ({task['location']})", "nothing to complete")
    for item in projection["blockers"]:
        add("PROJECTION_" + item["code"], item["reason"], "repair the persistent plan/state by manual review")
    for item in projection["diagnostics"]:
        if item["code"] in ("ORPHAN_MICROTASKS", "CLAIMS_UNREADABLE"):
            add(item["code"], item["reason"], "repair the persistent state by manual review")
    if not position["microtasks"]:
        add("NO_MICROTASKS", "the TASK plan has no microtask; nothing was verified", "create and verify microtasks")
    for micro in position["microtasks"]:
        if micro["status"] != MicrotaskStatus.VERIFIED.value:
            add("MICROTASK_NOT_VERIFIED", f"{micro['microtask_id']} is {micro['status']}",
                f"bring {micro['microtask_id']} to VERIFIED through the server state machine",
                microtask_id=micro["microtask_id"])
    for view in projection["operations"]:
        op_id, status = view["operation_id"], view["status"]
        actions = view["resolutions"]
        accepted = [a for a in actions if a["result"] == ResolutionResult.ACCEPTED.value]
        aborted = any(a["action"] == ResolutionAction.ABORT.value for a in accepted)
        fresh_adopt = any(a["action"] == ResolutionAction.ADOPT.value and a["fresh"] for a in accepted)
        recovery = view["recovery"]
        if not aborted:
            if status == OperationStatus.INTENT.value:
                add("OPERATION_OPEN", f"{op_id} is INTENT (declared, not executed)",
                    f"transition {op_id} to FAILED or record an accepted ABORT", operation_id=op_id)
            elif status in (OperationStatus.STARTED.value, OperationStatus.UNKNOWN_AFTER_DISCONNECT.value) and not fresh_adopt:
                if recovery is not None and recovery["state"] == "ROLLBACK_" + VERIFIED:
                    advice = (
                        f"its microtask was rolled back and verified, but {op_id} itself stays {status}: "
                        "the operation lifecycle after a rollback is not defined yet; close its recovery "
                        "with an accepted ABORT"
                    )
                else:
                    advice = (recovery or {}).get("next_safe_action") or (
                        f"reconcile {op_id}, then record a fresh accepted ADOPT or an accepted ABORT"
                    )
                add("OPERATION_UNRESOLVED", f"{op_id} is {status}: its mutation fate is open", advice,
                    operation_id=op_id)
            elif status == OperationStatus.DONE.value:
                add("OPERATION_NOT_VERIFIED", f"{op_id} is DONE, not VERIFIED",
                    f"verify {op_id} and transition it DONE -> VERIFIED", operation_id=op_id)
        if recovery is not None and recovery["state"] == "RETRY_ACCEPTED":
            add("RETRY_PENDING", f"{op_id} has a fresh accepted RETRY: a future execution is pending",
                recovery["next_safe_action"], operation_id=op_id, resolution_id=recovery["resolution_id"])
        if recovery is not None and "ROLLBACK_ACCEPTED" in (recovery["state"], recovery.get("protected_state")):
            add("ROLLBACK_PENDING", f"{op_id}: accepted ROLLBACK has no tracked rollback outcome yet",
                recovery["next_safe_action"], operation_id=op_id, resolution_id=recovery["resolution_id"])
        if recovery is not None and recovery["state"] in _SETTLEMENT_PENDING:
            add("RECOVERY_SETTLEMENT_PENDING",
                f"{op_id}: {recovery['state']} is not settled by RC-6 recover yet",
                "run recover: it settles the accepted recovery decision (administrative: lifecycle "
                "disposition and ownership release, no physical mutation)",
                operation_id=op_id, resolution_id=recovery["resolution_id"])
        if recovery is not None and recovery["state"] == "SETTLEMENT_CONTRADICTION":
            add("SETTLEMENT_CONTRADICTION", f"{op_id}: its recovery settlement contradicts a VERIFIED stage",
                recovery["next_safe_action"], operation_id=op_id, resolution_id=recovery["resolution_id"])
    for session in projection["rollbacks"]:
        status = session["status"]
        if status == VERIFIED and not session["claims_released"]:
            add("ROLLBACK_RELEASE_PENDING", f"rollback {session['rollback_id']} is VERIFIED but its ownership "
                "release is incomplete", session["next_safe_action"], rollback_id=session["rollback_id"])
        elif status != VERIFIED and status not in _ROLLBACK_SETTLED:
            add("ROLLBACK_OPEN", f"rollback {session['rollback_id']} is {status}", session["next_safe_action"],
                rollback_id=session["rollback_id"])
    for claim in projection["ownership"]["active_claims"]:
        add("ACTIVE_CLAIM", f"target {claim['target']} is owned by {claim['owner']['kind']} "
            f"({claim['operation_id']}, {claim['claim_id']})",
            "finish or release the owning operation / rollback first", claim_id=claim["claim_id"])
    # Repair #2: fail closed for every other recovery state (one a later stage may add)
    for view in projection["operations"]:
        recovery = view["recovery"]
        if recovery is None or recovery["state"].endswith("_REJECTED") or recovery["state"] == "RESOLUTION_STALE":
            continue
        rollback_ids = set(view.get("rollback_ids") or [])
        if any(item.get("operation_id") == view["operation_id"] or item.get("rollback_id") in rollback_ids
               for item in blockers):
            continue
        add("RECOVERY_OPEN", f"{view['operation_id']} has an open recovery ({recovery['state']})",
            recovery["next_safe_action"] or "finish its recovery through recover",
            operation_id=view["operation_id"])
    return blockers
