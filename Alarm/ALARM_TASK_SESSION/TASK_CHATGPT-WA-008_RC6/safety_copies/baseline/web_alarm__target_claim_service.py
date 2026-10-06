"""RC-3 canonical-target conflict gate + mutation-boundary CAS.

A claim gives one logical operation exclusive ownership of one physical target.
It is not mutation authority by itself: authority exists only inside
``mutation_boundary``, which re-proves the CAS basis while holding the TASK
lock and the target lock. The future WA4-E executor writes inside that
boundary; RC-3 itself never writes, edits or deletes a project file.

Lock order is always TASK lock (OperationStore.task_lock) -> target lock, and no
code path waits for a TASK lock while holding a target lock, so independent
TASKs cannot deadlock. Different physical targets use different target locks.

Ownership belongs to the logical operation, not to a process: a crash, restart
or lost Remote/Chat neither releases a claim nor transfers it (no lease/TTL,
RT-001 V17). A claim ends only by owner release or owner rebase.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .file_state import FileStateError, authority_of, eol_only_drift, observe_path, same_authority
from .models import OperationRecord, OperationStatus, utc_now_iso
from .operation_contract import LEGACY_CONTRACT_VERSION
from .operation_store import OperationStore, OperationStoreError
from .resolution_store import ResolutionAction, ResolutionResult, ResolutionStoreError
from .resolver_service import ResolverService
from .store_lock import DEFAULT_LOCK_TIMEOUT_SECONDS, InterProcessLock, StoreLockTimeout
from .target_claim_store import (
    ACTIVE,
    AUTHORIZED,
    DENIED,
    RELEASED,
    SUPERSEDED,
    TargetClaimStore,
    authorization_identity,
    claim_identity,
    physical_target_key,
)
from .target_identity import CanonicalTarget, TargetIdentityError, canonical_target
from .workspace_registry import WorkspaceRegistryError

ACQUIRED = "ACQUIRED"
REBASED = "REBASED"
REPLAYED = "REPLAYED"
CONFLICT = "CONFLICT"
STALE = "STALE"
REJECTED = "REJECTED"

_MUTATION_WINDOW_OPEN = {OperationStatus.STARTED, OperationStatus.UNKNOWN_AFTER_DISCONNECT}
_COMPLETED = {OperationStatus.DONE, OperationStatus.VERIFIED}


class TargetClaimError(RuntimeError):
    """Authoritative operation/claim state cannot be read safely."""


class TargetClaimInputError(TargetClaimError):
    """The claim request itself is malformed."""


def _provenance(agent: str | None, channel: str | None) -> dict[str, Any]:
    for name, value in (("agent", agent), ("channel", channel)):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise TargetClaimInputError(f"{name} must be a non-empty string when provided")
    return {
        "agent": agent.strip() if agent else None,
        "channel": channel.strip() if channel else None,
        "authority": "claimed",
    }


def _owner(claim: dict[str, Any] | None) -> dict[str, Any] | None:
    if claim is None:
        return None
    summary = {
        key: claim[key]
        for key in (
            "claim_id",
            "generation",
            "task_id",
            "microtask_id",
            "operation_id",
            "operation_revision",
            "created_at",
        )
    }
    summary["owner"] = claim.get("owner")
    return summary


def _same_operation(claim: dict[str, Any] | None, task_id: str, operation_id: str) -> bool:
    # A claim held by a tracked rollback (``owner``) is never the operation's own.
    return (
        claim is not None
        and claim.get("owner") is None
        and claim["task_id"] == task_id
        and claim["operation_id"] == operation_id
    )


class TargetClaimService:
    def __init__(
        self,
        storage_root: str | Path | None = None,
        *,
        lock_timeout: float = DEFAULT_LOCK_TIMEOUT_SECONDS,
    ) -> None:
        self.operations = OperationStore(storage_root, lock_timeout=lock_timeout)
        root = self.operations.tasks.storage_root
        self.resolver = ResolverService(root)
        self.claims = TargetClaimStore(root)
        self.events = self.operations.events
        self.lock_timeout = lock_timeout

    # --- authoritative inputs ----------------------------------------------------

    @contextmanager
    def _target_lock(self, physical_key: str) -> Iterator[None]:
        lock = InterProcessLock(self.claims.lock_path(physical_key), timeout=self.lock_timeout)
        try:
            lock.acquire()
        except StoreLockTimeout as exc:
            raise TargetClaimError(str(exc)) from exc
        try:
            yield
        finally:
            lock.release()

    def _record(self, task_id: str, operation_id: str) -> OperationRecord:
        for name, value in (("task_id", task_id), ("operation_id", operation_id)):
            if not isinstance(value, str) or not value.strip():
                raise TargetClaimInputError(f"{name} must be a non-empty string")
        try:
            return self.operations.get(task_id, operation_id)
        except OperationStoreError as exc:
            raise TargetClaimError(f"operation state unavailable: {exc}") from exc

    def _target(self, record: OperationRecord) -> tuple[CanonicalTarget, str]:
        """Server-side canonical identity from the verified contract, never the caller."""
        contract = record.contract or {}
        try:
            root = self.operations.registry.get(contract["workspace_id"]).workspace_root
            canonical = canonical_target(root, record.target)
        except (WorkspaceRegistryError, TargetIdentityError, KeyError) as exc:
            raise TargetClaimError(f"target identity unavailable: {exc}") from exc
        if canonical.key != contract.get("target_key"):
            raise TargetClaimError("canonical target no longer matches the operation contract")
        return canonical, physical_target_key(canonical.path)

    @staticmethod
    def _revision(value: Any, record: OperationRecord) -> int | None:
        if value is None and record.contract_version == LEGACY_CONTRACT_VERSION:
            return None
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise TargetClaimInputError("operation_revision must be a positive integer")
        return value

    def _eligibility(self, task_id: str, record: OperationRecord) -> tuple[str, str] | None:
        """Why this operation may not hold or use mutation ownership, or None."""
        if record.contract_version == LEGACY_CONTRACT_VERSION:
            return "LEGACY_CONTRACT", "legacy contract v1 cannot prove canonical target + CAS basis"
        if record.status in _COMPLETED:
            return "OPERATION_ALREADY_COMPLETED", f"operation is {record.status.value}"
        status = self.operations.contract_status(task_id, record.operation_id)
        if status["payload_verified"] is False:
            return "PAYLOAD_INTEGRITY_FAILURE", "durable payload does not match its reference"
        if not status["rearm_contract_sufficient"]:
            return "CONTRACT_INSUFFICIENT", "contract is incomplete: " + ", ".join(status["issues"])
        try:
            accepted = [
                item
                for item in self.resolver.store.list(task_id, operation_id=record.operation_id)
                if item.result is ResolutionResult.ACCEPTED
            ]
        except ResolutionStoreError as exc:
            raise TargetClaimError(str(exc)) from exc
        aborted = next((item for item in accepted if item.action is ResolutionAction.ABORT), None)
        if aborted is not None:
            return "RECOVERY_ABORTED", f"recovery was aborted by {aborted.resolution_id}"
        if record.status is OperationStatus.INTENT:
            return None
        fresh = [item for item in accepted if self.resolver.freshness(item)["fresh"]]
        if not fresh or fresh[-1].action is not ResolutionAction.RETRY:
            found = fresh[-1].action.value if fresh else "none"
            return (
                "RECOVERY_RESOLUTION_REQUIRED",
                f"operation is {record.status.value}; a fresh accepted RETRY re-arm is "
                f"required before new ownership (latest fresh accepted: {found})",
            )
        return None

    def _event(self, task_id: str, record: OperationRecord, event_type: str, payload: dict[str, Any]) -> None:
        self.events.append_event(
            task_id,
            event_type,
            microtask_id=record.microtask_id,
            operation_id=record.operation_id,
            payload=dict(payload, physical_mutation_performed=False),
        )

    @staticmethod
    def _outcome(result: str, code: str, reason: str, **extra: Any) -> dict[str, Any]:
        outcome = {
            "result": result,
            "result_code": code,
            "reason": reason,
            "claim": None,
            "blocking_owner": None,
            "mutation_authority": False,
            "physical_mutation_performed": False,
        }
        outcome.update(extra)
        return outcome

    # --- acquire ----------------------------------------------------------------------

    def acquire(
        self,
        task_id: str,
        operation_id: str,
        *,
        operation_revision: int | None,
        agent: str | None = None,
        channel: str | None = None,
    ) -> dict[str, Any]:
        provenance = _provenance(agent, channel)
        with self.operations.task_lock(task_id):
            record = self._record(task_id, operation_id)
            revision = self._revision(operation_revision, record)
            if record.contract_version == LEGACY_CONTRACT_VERSION:
                outcome = self._outcome(REJECTED, "LEGACY_CONTRACT", "legacy contract v1 cannot own a target")
                self._event(task_id, record, "TARGET_CLAIM_REJECTED", {"result_code": "LEGACY_CONTRACT"})
                return outcome
            canonical, physical_key = self._target(record)
            with self._target_lock(physical_key):
                data = self.claims.load(physical_key)
                active = data["active"]
                own = active if _same_operation(active, task_id, operation_id) else None
                if own is not None and own["operation_revision"] == revision:
                    return self._outcome(REPLAYED, "SAME_BASIS", "known active claim", claim=own)
                ended = [
                    claim
                    for claim in data["history"]
                    if _same_operation(claim, task_id, operation_id)
                    and claim["operation_revision"] == revision
                    and claim["status"] == RELEASED
                ]
                if own is None and ended:
                    return self._outcome(
                        REPLAYED,
                        "SAME_BASIS_ALREADY_RELEASED",
                        "this basis was already claimed and released; a new basis is required",
                        claim=ended[-1],
                    )
                if revision != record.revision:
                    outcome = self._outcome(
                        STALE,
                        "OPERATION_REVISION_CHANGED",
                        f"requested revision {revision} but operation is at {record.revision}",
                    )
                elif active is not None and own is None:
                    outcome = self._outcome(
                        CONFLICT,
                        "TARGET_OWNED",
                        "another operation owns this canonical physical target",
                        blocking_owner=_owner(active),
                    )
                else:
                    outcome = None
                    refusal = self._eligibility(task_id, record)
                    if refusal is not None:
                        outcome = self._outcome(REJECTED, *refusal)
                if outcome is None:
                    basis = authority_of(record.contract["pre_state"])
                    try:
                        observed = observe_path(canonical.path)
                    except FileStateError as exc:
                        outcome = self._outcome(REJECTED, "TARGET_UNOBSERVABLE", str(exc))
                    else:
                        if not same_authority(observed, basis):
                            outcome = self._outcome(
                                STALE,
                                "STATE_DRIFT",
                                "target bytes no longer match the contract pre-state CAS basis",
                                eol_only_drift=eol_only_drift(record.contract["pre_state"], observed),
                            )
                if outcome is not None:
                    self._event(
                        task_id,
                        record,
                        f"TARGET_CLAIM_{outcome['result']}",
                        {
                            "result_code": outcome["result_code"],
                            "target": record.target,
                            "target_hash": data["target_hash"],
                            "blocking_claim_id": (outcome["blocking_owner"] or {}).get("claim_id"),
                        },
                    )
                    return outcome

                now = utc_now_iso()
                generation = data["next_generation"]
                claim = {
                    "claim_id": claim_identity(data["target_hash"], generation, task_id, operation_id, revision),
                    "generation": generation,
                    "task_id": task_id,
                    "microtask_id": record.microtask_id,
                    "operation_id": operation_id,
                    "workspace_id": record.contract["workspace_id"],
                    "target": record.target,
                    "target_key": record.contract["target_key"],
                    "operation_revision": revision,
                    "operation_request_fingerprint": record.request_fingerprint,
                    "contract_version": record.contract_version,
                    "cas_basis": basis,
                    "status": ACTIVE,
                    "created_at": now,
                    "provenance": provenance,
                    "ended_at": None,
                    "end_reason": None,
                    "ended_by": None,
                    "superseded_by": None,
                    "authorizations": [],
                }
                result = ACQUIRED
                if own is not None:
                    own.update(
                        status=SUPERSEDED,
                        ended_at=now,
                        end_reason="REBASED_BY_OWNER",
                        ended_by=provenance,
                        superseded_by=claim["claim_id"],
                    )
                    data["history"].append(own)
                    result = REBASED
                data["active"] = claim
                data["next_generation"] = generation + 1
                self.claims.write(data)
                self._event(
                    task_id,
                    record,
                    f"TARGET_CLAIM_{result}",
                    {
                        "claim_id": claim["claim_id"],
                        "target": record.target,
                        "target_hash": data["target_hash"],
                        "operation_revision": revision,
                        "cas_basis": basis,
                    },
                )
                return self._outcome(result, "TARGET_FREE_BASIS_VALID", "claim is persistent", claim=claim)

    # --- mutation-boundary CAS -----------------------------------------------------------

    def _cas(
        self,
        task_id: str,
        record: OperationRecord,
        canonical: CanonicalTarget,
        data: dict[str, Any],
        revision: int,
        claim_id: str | None,
    ) -> tuple[dict[str, Any] | None, str, str, dict[str, Any] | None, bool]:
        """(own claim, result_code, reason, observed, authorized); read-only."""
        active = data["active"]
        own = active if _same_operation(active, record.task_id, record.operation_id) else None
        if own is None:
            if active is not None:
                return None, "NOT_OWNER", "another operation owns this target", None, False
            ended = [c for c in data["history"] if _same_operation(c, record.task_id, record.operation_id)]
            code = f"CLAIM_{ended[-1]['status']}" if ended else "NO_ACTIVE_CLAIM"
            return None, code, "this operation holds no active claim on the target", None, False
        if claim_id is not None and claim_id != own["claim_id"]:
            return own, "CLAIM_MISMATCH", "requested claim_id is not the active claim", None, False
        if revision != record.revision:
            return own, "OPERATION_REVISION_CHANGED", f"operation is at revision {record.revision}", None, False
        if own["operation_revision"] != record.revision:
            return own, "CLAIM_BASIS_STALE", "claim was created at an older operation revision", None, False
        if own["target_key"] != record.contract["target_key"] or own["cas_basis"] != authority_of(
            record.contract["pre_state"]
        ):
            return own, "CLAIM_CONTRACT_MISMATCH", "claim basis differs from the operation contract", None, False
        refusal = self._eligibility(task_id, record)
        if refusal is not None:
            return own, refusal[0], refusal[1], None, False
        try:
            observed = observe_path(canonical.path).authority()
        except FileStateError as exc:
            return own, "TARGET_UNOBSERVABLE", str(exc), None, False
        if not same_authority(observed, own["cas_basis"]):
            return own, "STATE_DRIFT", "target bytes changed since the CAS basis", observed, False
        return own, "CAS_BASIS_HOLDS", "claim, revision, contract and target bytes match", observed, True

    @contextmanager
    def mutation_boundary(
        self,
        task_id: str,
        operation_id: str,
        *,
        operation_revision: int | None,
        claim_id: str | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Hold TASK + target locks and yield the CAS outcome.

        Mutation authority exists only inside this block and only when
        ``outcome["mutation_authority"]`` is true. RC-3 callers do nothing inside;
        WA4-E performs its single write here.
        """
        with self.operations.task_lock(task_id):
            record = self._record(task_id, operation_id)
            revision = self._revision(operation_revision, record)
            if record.contract_version == LEGACY_CONTRACT_VERSION:
                self._event(task_id, record, "MUTATION_DENIED", {"result_code": "LEGACY_CONTRACT"})
                yield self._outcome(DENIED, "LEGACY_CONTRACT", "legacy contract v1 has no CAS basis")
                return
            canonical, physical_key = self._target(record)
            with self._target_lock(physical_key):
                data = self.claims.load(physical_key)
                own, code, reason, observed, authorized = self._cas(
                    task_id, record, canonical, data, revision, claim_id
                )
                result = AUTHORIZED if authorized else DENIED
                entry = None
                if own is not None and data["active"] is own:
                    auth_id = authorization_identity(own["claim_id"], revision, observed, code)
                    entry = next(
                        (item for item in own["authorizations"] if item["authorization_id"] == auth_id),
                        None,
                    )
                    if entry is None:
                        entry = {
                            "authorization_id": auth_id,
                            "result": result,
                            "result_code": code,
                            "operation_revision": revision,
                            "observed": observed,
                            "at": utc_now_iso(),
                        }
                        own["authorizations"].append(entry)
                        self.claims.write(data)
                        self._event(
                            task_id,
                            record,
                            "MUTATION_AUTHORIZED" if authorized else "MUTATION_DENIED",
                            {"claim_id": own["claim_id"], "authorization_id": auth_id, "result_code": code},
                        )
                else:
                    self._event(task_id, record, "MUTATION_DENIED", {"result_code": code})
                yield self._outcome(
                    result,
                    code,
                    reason,
                    claim=own,
                    authorization=entry,
                    blocking_owner=None if own is not None else _owner(data["active"]),
                    mutation_authority=authorized,
                )

    def authorize(
        self,
        task_id: str,
        operation_id: str,
        *,
        operation_revision: int | None,
        claim_id: str | None = None,
    ) -> dict[str, Any]:
        """Run the mutation-boundary CAS and record its result; perform nothing."""
        with self.mutation_boundary(
            task_id, operation_id, operation_revision=operation_revision, claim_id=claim_id
        ) as outcome:
            # Authority does not survive the boundary: report it as evidence only.
            return dict(outcome, mutation_authority=False, authorized=outcome["result"] == AUTHORIZED)

    # --- release ------------------------------------------------------------------------------

    def _release_refusal(self, task_id: str, record: OperationRecord) -> tuple[str, str] | None:
        """A STARTED/UNKNOWN operation's mutation fate is open: keep the claim until
        an accepted Resolver outcome closes the window (fresh ADOPT or ABORT)."""
        if record.status not in _MUTATION_WINDOW_OPEN:
            return None
        try:
            accepted = [
                item
                for item in self.resolver.store.list(task_id, operation_id=record.operation_id)
                if item.result is ResolutionResult.ACCEPTED
            ]
        except ResolutionStoreError as exc:
            raise TargetClaimError(str(exc)) from exc
        if any(item.action is ResolutionAction.ABORT for item in accepted):
            return None
        if any(
            item.action is ResolutionAction.ADOPT and self.resolver.freshness(item)["fresh"]
            for item in accepted
        ):
            return None
        return (
            "RELEASE_REQUIRES_RECOVERY_OUTCOME",
            f"operation is {record.status.value}; its mutation fate is unknown until a fresh "
            "accepted ADOPT or an accepted ABORT",
        )

    def release(
        self,
        task_id: str,
        operation_id: str,
        *,
        claim_id: str | None = None,
        reason: str | None = None,
        agent: str | None = None,
        channel: str | None = None,
    ) -> dict[str, Any]:
        provenance = _provenance(agent, channel)
        if reason is not None and (not isinstance(reason, str) or not reason.strip()):
            raise TargetClaimInputError("reason must be a non-empty string when provided")
        with self.operations.task_lock(task_id):
            record = self._record(task_id, operation_id)
            if record.contract_version == LEGACY_CONTRACT_VERSION:
                return self._outcome(REJECTED, "NO_CLAIM", "legacy operations never hold claims")
            canonical, physical_key = self._target(record)
            with self._target_lock(physical_key):
                data = self.claims.load(physical_key)
                active = data["active"]
                if _same_operation(active, task_id, operation_id) and claim_id in (None, active["claim_id"]):
                    refusal = self._release_refusal(task_id, record)
                    if refusal is not None:
                        self._event(task_id, record, "TARGET_CLAIM_RELEASE_REJECTED", {"result_code": refusal[0]})
                        return self._outcome(REJECTED, *refusal, claim=active)
                    active.update(
                        status=RELEASED,
                        ended_at=utc_now_iso(),
                        end_reason=(reason or "OWNER_RELEASE").strip(),
                        ended_by=provenance,
                    )
                    data["history"].append(active)
                    data["active"] = None
                    self.claims.write(data)
                    self._event(
                        task_id,
                        record,
                        "TARGET_CLAIM_RELEASED",
                        {"claim_id": active["claim_id"], "target_hash": data["target_hash"]},
                    )
                    return self._outcome(RELEASED, "OWNER_RELEASED", "claim released", claim=active)
                ended = [
                    claim
                    for claim in data["history"]
                    if _same_operation(claim, task_id, operation_id)
                    and claim["status"] == RELEASED
                    and claim_id in (None, claim["claim_id"])
                ]
                if ended:
                    return self._outcome(REPLAYED, "ALREADY_RELEASED", "claim was already released", claim=ended[-1])
                code = "NOT_OWNER" if active is not None else "NO_CLAIM"
                self._event(task_id, record, "TARGET_CLAIM_RELEASE_REJECTED", {"result_code": code})
                return self._outcome(
                    REJECTED,
                    code,
                    "only the owning operation can release this claim",
                    blocking_owner=_owner(active),
                )

    # --- inspect ---------------------------------------------------------------------------------

    def inspect(self, task_id: str, operation_id: str) -> dict[str, Any]:
        """Read-only ownership picture for a new process; nothing is written."""
        record = self._record(task_id, operation_id)
        if record.contract_version == LEGACY_CONTRACT_VERSION:
            return {
                "operation_id": operation_id,
                "contract_version": record.contract_version,
                "owned_by_operation": False,
                "active_claim": None,
                "operation_claims": [],
                "blocking_owner": None,
                "cas_preview": {"result": DENIED, "result_code": "LEGACY_CONTRACT"},
                "physical_mutation_performed": False,
            }
        canonical, physical_key = self._target(record)
        data = self.claims.load(physical_key)
        active = data["active"]
        own_claims = [
            claim
            for claim in data["history"] + ([active] if active else [])
            if _same_operation(claim, task_id, operation_id)
        ]
        _, code, reason, _, authorized = self._cas(
            task_id, record, canonical, data, record.revision, None
        )
        return {
            "operation_id": operation_id,
            "operation_revision": record.revision,
            "operation_status": record.status.value,
            "target": record.target,
            "target_hash": data["target_hash"],
            "physical_key": physical_key,
            "owned_by_operation": _same_operation(active, task_id, operation_id),
            "active_claim": active,
            "operation_claims": own_claims,
            "blocking_owner": None if _same_operation(active, task_id, operation_id) else _owner(active),
            "cas_preview": {
                "result": AUTHORIZED if authorized else DENIED,
                "result_code": code,
                "reason": reason,
            },
            "physical_mutation_performed": False,
        }
