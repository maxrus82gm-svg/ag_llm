"""Persistent Resolver: tracked recovery actions bound to evidence (RC-2).

The Resolver turns a recovery choice into a durable, idempotent record that is
valid only for the exact evidence fingerprint and operation revision on which it
was evaluated. Before recording a result it re-reads the OperationRecord,
re-collects reconciliation evidence from the current Workspace (persisted
contract/manifest only, never caller-declared post-state), recomputes the
fingerprint and the deterministic decision.

It never executes a project mutation and never changes OperationStatus:
- ADOPT records that the existing Workspace state is accepted as recovery fact;
- RETRY only re-arms the same operation_id for a future authoritative executor
  (WA4-E); nothing is written;
- ROLLBACK only records a request; physical safe rollback belongs to RC-4;
- ABORT closes Resolver-level recovery of the operation.

RC-3 CAS does not exist yet, so a recorded resolution cannot lock its target:
its freshness is re-checkable (``freshness``) and a stale resolution is never
authority.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import utc_now_iso
from .operation_store import OperationStore, OperationStoreError
from .reconciliation import ReconciliationEvidenceCollector, ReconciliationEvidenceError
from .reconciliation_decision import (
    ADOPT_CURRENT_STATE,
    RETRY_SAFE,
    ROLLBACK_CURRENT_MICROTASK,
    ReconciliationDecision,
    ReconciliationDecisionEngine,
)
from .resolution_store import (
    EFFECTS,
    ResolutionAction,
    ResolutionConflictError,
    ResolutionRecord,
    ResolutionResult,
    ResolutionStore,
    ResolutionStoreError,
    logical_identity,
    logical_resolution_id,
    requested_basis,
)

_REQUIRED_DECISION = {
    ResolutionAction.ADOPT: ADOPT_CURRENT_STATE,
    ResolutionAction.RETRY: RETRY_SAFE,
    ResolutionAction.ROLLBACK: ROLLBACK_CURRENT_MICROTASK,
    ResolutionAction.ABORT: None,
}

# RC-6 Repair #4: the one settlement-supersession policy. An operation keeps a
# single durable recovery settlement (immutable history); after it, only the
# actions RC-6 can still carry out for that operation may become authority:
# - ABORT after ADOPT / ROLLBACK: the late ABORT of Repair #3 (lifecycle-only);
# - RETRY after ROLLBACK: re-arm of the rolled-back operation (no new settlement).
# A second ADOPT or ROLLBACK (a second settlement, a second physical restore)
# and RETRY over an adopted or aborted operation are refused before acceptance.
SETTLEMENT_ADMITS = {
    "ADOPT": frozenset({"ABORT"}),
    "ABORT": frozenset(),
    "ROLLBACK": frozenset({"ABORT", "RETRY"}),
}


def settlement_admits(settlement_action: str, action: str) -> bool:
    """May ``action`` follow a recovery settlement ``settlement_action`` of the same operation?"""
    return action in SETTLEMENT_ADMITS.get(settlement_action, frozenset())


class ResolverError(RuntimeError):
    """Authoritative state needed by the Resolver cannot be read safely."""


class ResolverInputError(ResolverError):
    """The resolution request itself is malformed."""


class ResolverService:
    def __init__(self, storage_root: str | Path | None = None) -> None:
        self.operations = OperationStore(storage_root)
        root = self.operations.tasks.storage_root
        self.collector = ReconciliationEvidenceCollector(root)
        self.engine = ReconciliationDecisionEngine()
        self.store = ResolutionStore(root)
        self.events = self.operations.events

    # --- authoritative basis ------------------------------------------------

    def current_basis(
        self,
        task_id: str,
        microtask_id: str,
        operation_id: str,
    ) -> tuple[dict[str, Any], ReconciliationDecision]:
        try:
            record = self.operations.get(task_id, operation_id)
        except OperationStoreError as exc:
            raise ResolverError(f"operation state unavailable: {exc}") from exc
        if record.microtask_id != microtask_id:
            raise ResolverInputError("operation does not belong to the requested microtask")
        try:
            evidence = self.collector.collect(
                task_id, microtask_id, operation_id=operation_id
            )
        except ReconciliationEvidenceError as exc:
            raise ResolverError(f"reconciliation evidence unavailable: {exc}") from exc
        decision = self.engine.decide(evidence)
        basis = {
            "evidence_version": evidence.evidence_version,
            "evidence_fingerprint": decision.evidence_fingerprint,
            "decision_version": decision.decision_version,
            "decision": decision.decision,
            "reason_code": decision.reason_code,
            "operation_status": record.status.value,
            "operation_contract_version": record.contract_version,
            "operation_revision": record.revision,
            "operation_request_fingerprint": record.request_fingerprint,
            "affected_targets": list(decision.affected_targets),
        }
        return basis, decision

    @staticmethod
    def _basis_change(requested: dict[str, Any], basis: dict[str, Any]) -> str | None:
        if requested["operation_revision"] != basis["operation_revision"]:
            return "OPERATION_REVISION_CHANGED"
        if requested["evidence_fingerprint"] != basis["evidence_fingerprint"]:
            return "EVIDENCE_FINGERPRINT_CHANGED"
        return None

    def freshness(self, resolution: ResolutionRecord) -> dict[str, Any]:
        """Is the resolution's evaluated basis still the current authoritative basis?"""
        try:
            basis, _ = self.current_basis(
                resolution.task_id, resolution.microtask_id, resolution.operation_id
            )
        except ResolverError as exc:
            return {"fresh": False, "code": "BASIS_UNAVAILABLE", "reason": str(exc)}
        change = self._basis_change(
            {
                "evidence_fingerprint": resolution.basis["evidence_fingerprint"],
                "operation_revision": resolution.basis["operation_revision"],
            },
            basis,
        )
        if change is not None:
            return {"fresh": False, "code": change, "reason": "basis changed since resolution"}
        return {"fresh": True, "code": "BASIS_UNCHANGED", "reason": "basis is current"}

    # --- apply ----------------------------------------------------------------

    def _evaluate(
        self,
        action: ResolutionAction,
        requested: dict[str, Any],
        basis: dict[str, Any],
        decision: ReconciliationDecision,
        aborted_by: ResolutionRecord | None,
        task_id: str,
        operation_id: str,
        settlement: dict[str, Any] | None = None,
    ) -> tuple[ResolutionResult, str, str, bool | None, str]:
        if aborted_by is not None:
            code = (
                "RECOVERY_ALREADY_ABORTED"
                if action is ResolutionAction.ABORT
                else "RECOVERY_ABORTED"
            )
            return (
                ResolutionResult.REJECTED,
                code,
                f"recovery of this operation was aborted by {aborted_by.resolution_id}",
                None,
                "recovery was aborted; manual review or a new operation is required",
            )
        if settlement is not None and not settlement_admits(settlement["action"], action.value):
            allowed = sorted(SETTLEMENT_ADMITS.get(settlement["action"], ()))
            return (
                ResolutionResult.REJECTED,
                "RECOVERY_ALREADY_SETTLED",
                f"recovery of this operation is already settled by {settlement['action']} via "
                f"{settlement['resolution_id']}; a later {action.value} cannot be carried out for it "
                f"(admitted after {settlement['action']}: {', '.join(allowed) or 'nothing'})",
                None,
                f"the {settlement['action']} settlement of operation {operation_id} stays its recovery "
                "outcome; nothing changes. "
                + (
                    "To stop its microtask instead, record ABORT"
                    if "ABORT" in allowed
                    else "Continue through the microtask lifecycle"
                ),
            )
        change = self._basis_change(requested, basis)
        if change is not None:
            return (
                ResolutionResult.STALE,
                change,
                "requested basis is no longer the current authoritative basis",
                None,
                "run a new reconciliation and resolve on its fresh "
                "evidence_fingerprint and operation_revision",
            )
        required = _REQUIRED_DECISION[action]
        if required is not None and decision.decision != required:
            return (
                ResolutionResult.REJECTED,
                "ACTION_DECISION_MISMATCH",
                f"{action.value} requires {required}; current decision is "
                f"{decision.decision} ({decision.reason_code})",
                None,
                decision.next_safe_action,
            )
        payload_verified: bool | None = None
        if action is ResolutionAction.RETRY:
            status = self.operations.contract_status(task_id, operation_id)
            payload_verified = status["payload_verified"]
            if status["legacy"]:
                return (
                    ResolutionResult.REJECTED,
                    "LEGACY_CONTRACT",
                    "legacy contract v1 is never sufficient for RETRY re-arm",
                    payload_verified,
                    "manual review: a legacy operation cannot be re-armed",
                )
            if payload_verified is False:
                return (
                    ResolutionResult.REJECTED,
                    "PAYLOAD_INTEGRITY_FAILURE",
                    "durable payload does not match its contract reference",
                    payload_verified,
                    "manual review: payload integrity failed; do not re-arm",
                )
            if not status["rearm_contract_sufficient"]:
                return (
                    ResolutionResult.REJECTED,
                    "CONTRACT_INSUFFICIENT",
                    "contract is insufficient for re-arm: " + ", ".join(status["issues"]),
                    payload_verified,
                    "manual review: the operation contract cannot support a re-arm",
                )
        return (
            ResolutionResult.ACCEPTED,
            "BASIS_FRESH_ACTION_ALLOWED",
            f"{action.value} is allowed by decision {decision.decision} on the current basis",
            payload_verified,
            self._accepted_next_action(action, operation_id, decision),
        )

    @staticmethod
    def _accepted_next_action(
        action: ResolutionAction,
        operation_id: str,
        decision: ReconciliationDecision,
    ) -> str:
        if action is ResolutionAction.ADOPT:
            return (
                "existing Workspace state is adopted as a tracked recovery fact on this "
                "basis; no mutation was performed and the operation lifecycle is "
                "unchanged; continue verification/closeout through the normal workflow"
            )
        if action is ResolutionAction.RETRY:
            return (
                f"operation {operation_id} is re-armed for a future authoritative "
                "executor (WA4-E) under the same operation_id; nothing was executed; "
                "the executor must re-check this basis before any write"
            )
        if action is ResolutionAction.ROLLBACK:
            return (
                f"rollback of microtask {decision.microtask_id} is requested and "
                "tracked; nothing was restored; physical safe rollback belongs to RC-4"
            )
        return (
            f"Resolver-level recovery of operation {operation_id} is closed; no further "
            "ADOPT/RETRY/ROLLBACK will be accepted for it"
        )

    def apply(
        self,
        task_id: str,
        microtask_id: str,
        operation_id: str,
        action: ResolutionAction | str,
        *,
        evidence_fingerprint: str,
        operation_revision: int | None,
        resolution_id: str | None = None,
        agent: str | None = None,
        channel: str | None = None,
    ) -> dict[str, Any]:
        try:
            action = ResolutionAction(action)
            requested = requested_basis(evidence_fingerprint, operation_revision)
        except ValueError as exc:
            raise ResolverInputError(str(exc)) from exc
        for name, value in (
            ("task_id", task_id),
            ("microtask_id", microtask_id),
            ("operation_id", operation_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ResolverInputError(f"{name} must be a non-empty string")
        for name, value in (("agent", agent), ("channel", channel)):
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ResolverInputError(f"{name} must be a non-empty string when provided")
        identity = logical_identity(task_id, microtask_id, operation_id, action, requested)
        chosen_id = resolution_id or logical_resolution_id(identity)

        with self.operations.task_lock(task_id):
            try:
                existing = self.store.find(task_id, chosen_id)
                if existing is not None:
                    if existing.logical_identity() != identity:
                        raise ResolutionConflictError(
                            "resolution_id already exists with a different action or basis"
                        )
                    return self._result(existing, created=False)
                prior = self.store.list(task_id, operation_id=operation_id)
            except ResolutionStoreError as exc:
                if isinstance(exc, ResolutionConflictError):
                    raise
                raise ResolverError(str(exc)) from exc
            for other in prior:
                if other.logical_identity() == identity:
                    raise ResolutionConflictError(
                        f"logical resolution is already recorded as {other.resolution_id}"
                    )
            aborted_by = next(
                (
                    item
                    for item in prior
                    if item.action is ResolutionAction.ABORT
                    and item.result is ResolutionResult.ACCEPTED
                ),
                None,
            )

            basis, decision = self.current_basis(task_id, microtask_id, operation_id)
            try:
                settlement = self.operations.get(task_id, operation_id).recovery_settlement
            except OperationStoreError as exc:
                raise ResolverError(f"operation state unavailable: {exc}") from exc
            result, code, reason, payload_verified, next_action = self._evaluate(
                action, requested, basis, decision, aborted_by, task_id, operation_id,
                settlement=settlement,
            )
            record = ResolutionRecord(
                resolution_id=chosen_id,
                task_id=task_id,
                microtask_id=microtask_id,
                operation_id=operation_id,
                action=action,
                requested_basis=requested,
                basis=basis,
                result=result,
                result_code=code,
                result_reason=reason,
                effect=EFFECTS[action] if result is ResolutionResult.ACCEPTED else None,
                next_safe_action=next_action,
                provenance={
                    "agent": agent.strip() if agent else None,
                    "channel": channel.strip() if channel else None,
                    "authority": "claimed",
                },
                payload_verified=payload_verified,
                created_at=utc_now_iso(),
            )
            try:
                self.store.write_new(record)
            except ResolutionStoreError as exc:
                raise ResolverError(str(exc)) from exc
            self.events.append_event(
                task_id,
                f"RESOLUTION_{result.value}",
                microtask_id=microtask_id,
                operation_id=operation_id,
                payload={
                    "resolution_id": chosen_id,
                    "action": action.value,
                    "result_code": code,
                    "effect": record.effect,
                    "evidence_fingerprint": basis["evidence_fingerprint"],
                    "operation_revision": basis["operation_revision"],
                    "decision": basis["decision"],
                    "physical_mutation_performed": False,
                },
            )
            return self._result(record, created=True)

    @staticmethod
    def _result(record: ResolutionRecord, *, created: bool) -> dict[str, Any]:
        return {
            "resolution": record,
            "created": created,
            "replayed": not created,
            "accepted": record.result is ResolutionResult.ACCEPTED,
            "physical_mutation_performed": False,
        }

    # --- facts for Recovery Report ------------------------------------------------

    def report_facts(
        self,
        task_id: str,
        microtask_id: str,
        operation_id: str,
    ) -> dict[str, Any]:
        """Recovery action facts derived only from persisted resolutions.

        ``resolver_actions`` lists every persisted outcome (ACCEPTED / STALE /
        REJECTED). Authority stays fail-closed: only an accepted resolution has
        it (an accepted ABORT keeps it even when its basis aged), and a fresh
        accepted ADOPT is the only source of ``accepted_as_already_done``.
        RC-2 never executes a retry or rollback, so those facts stay empty.
        """
        try:
            resolutions = [
                item
                for item in self.store.list(task_id, operation_id=operation_id)
                if item.microtask_id == microtask_id
            ]
        except ResolutionStoreError as exc:
            raise ResolverError(str(exc)) from exc
        current: dict[str, Any] | None = None
        settlement: dict[str, Any] | None = None
        if resolutions:
            try:
                current, _ = self.current_basis(task_id, microtask_id, operation_id)
            except ResolverError:
                current = None
            try:
                settlement = self.operations.get(task_id, operation_id).recovery_settlement
            except OperationStoreError:
                settlement = None
        # Repair #4: after a settlement only the actions it admits can be authority
        settled_at_index = next(
            (
                index
                for index, item in enumerate(resolutions)
                if settlement is not None and item.resolution_id == settlement["resolution_id"]
            ),
            None,
        )
        accepted: list[str] = []
        actions: list[dict[str, Any]] = []
        for index, item in enumerate(resolutions):
            change = (
                "BASIS_UNAVAILABLE"
                if current is None
                else self._basis_change(
                    {
                        "evidence_fingerprint": item.basis["evidence_fingerprint"],
                        "operation_revision": item.basis["operation_revision"],
                    },
                    current,
                )
            )
            fresh = change is None
            admissible = (
                settled_at_index is None
                or index <= settled_at_index
                or settlement_admits(settlement["action"], item.action.value)
            )
            authority = admissible and item.result is ResolutionResult.ACCEPTED and (
                fresh or item.action is ResolutionAction.ABORT
            )
            if authority and fresh and item.action is ResolutionAction.ADOPT:
                accepted.extend(
                    path for path in item.basis["affected_targets"] if path not in accepted
                )
            actions.append(
                {
                    "resolution_id": item.resolution_id,
                    "action": item.action.value,
                    "result": item.result.value,
                    "result_code": item.result_code,
                    "effect": item.effect,
                    "authority": authority,
                    "fresh": fresh,
                    "freshness_code": change or "BASIS_UNCHANGED",
                    "evidence_fingerprint": item.basis["evidence_fingerprint"],
                    "operation_revision": item.basis["operation_revision"],
                    "created_at": item.created_at,
                    "physical_mutation_performed": False,
                }
            )
        return {
            "accepted_as_already_done": accepted,
            "actually_retried": [],
            "actually_rolled_back": [],
            "resolver_actions": actions,
            "next_safe_action": self._authoritative_next_action(
                resolutions, actions, settled_at_index=settled_at_index, settlement=settlement
            ),
        }

    @staticmethod
    def _stale_advice(record: ResolutionRecord, code: str) -> dict[str, str]:
        return {
            "resolution_id": record.resolution_id,
            "next_safe_action": (
                f"resolution {record.resolution_id} ({record.action.value} / "
                f"{record.result.value}) is not authority: its basis is stale "
                f"({code}); run a new reconciliation and resolve on its fresh "
                "evidence_fingerprint and operation_revision"
            ),
        }

    @classmethod
    def _authoritative_next_action(
        cls,
        resolutions: list[ResolutionRecord],
        actions: list[dict[str, Any]],
        *,
        settled_at_index: int | None = None,
        settlement: dict[str, Any] | None = None,
    ) -> dict[str, str] | None:
        """NEXT SAFE ACTION implied by persisted Resolver state, or None.

        Precedence: accepted ABORT (recovery closed) > latest fresh accepted
        resolution (its persisted semantics) > latest outcome: a fresh rejection
        keeps its persisted advice, anything stale demands a new reconciliation.
        Without resolutions the deterministic reconciliation advice stays.

        Repair #4: once the operation has a recovery settlement, the authority
        is an accepted ABORT, else the latest accepted resolution among the
        settlement's own one and later ones the settlement admits
        (``settlement_admits``), fresh first. A later rejected or stale outcome
        and an action the settlement does not admit (legacy data) are history
        only: they never become recovery attention over a settled operation.
        """
        pairs = list(zip(resolutions, actions))
        if not pairs:
            return None
        chosen = next(
            (
                record
                for record, _ in pairs
                if record.action is ResolutionAction.ABORT
                and record.result is ResolutionResult.ACCEPTED
            ),
            None,
        )
        if chosen is None and settled_at_index is not None:
            candidates = [
                (record, action)
                for index, (record, action) in enumerate(pairs)
                if record.result is ResolutionResult.ACCEPTED
                and (
                    index == settled_at_index
                    or (index > settled_at_index and settlement_admits(settlement["action"], record.action.value))
                )
            ]
            fresh = [pair for pair in candidates if pair[1]["fresh"]]
            if candidates:  # the settlement's own resolution is accepted; else fall back below
                record, action = fresh[-1] if fresh else candidates[-1]
                if action["fresh"]:
                    return {"resolution_id": record.resolution_id, "next_safe_action": record.next_safe_action}
                return cls._stale_advice(record, action["freshness_code"])
        if chosen is None:
            accepted = [
                record
                for record, action in pairs
                if record.result is ResolutionResult.ACCEPTED and action["fresh"]
            ]
            if accepted:
                chosen = accepted[-1]
        if chosen is None:
            record, action = pairs[-1]
            if record.result is ResolutionResult.REJECTED and action["fresh"]:
                chosen = record
            else:
                code = (
                    record.result_code
                    if record.result is ResolutionResult.STALE
                    else action["freshness_code"]
                )
                return cls._stale_advice(record, code)
        return {
            "resolution_id": chosen.resolution_id,
            "next_safe_action": chosen.next_safe_action,
        }
