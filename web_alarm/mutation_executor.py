"""WA4-E: authoritative mutation executor / gateway (CLAUDE-WA-018).

The server, never the caller, performs one tracked file mutation as a transaction over
the existing Recovery Closure components; there is no second store, authority, Resolver
or recovery path:

  INTENT            RC-1 durable Operation Contract v2, idempotent ``OperationStore.begin``
                    (canonical target, server-observed pre-state, payload by hash, fingerprint)
  admission         contract complete, payload intact, target in the microtask's manifest,
                    restore point VERIFIED (``ManifestSnapshotStore.restore_plan``, pure)
  ownership         RC-3 claim on the canonical physical target (not authority by itself)
  boundary          RC-3 ``mutation_boundary``: TASK lock + mutation lock + target lock;
                    CAS of claim, revision, contract and current pre-state bytes; the F-C
                    execution gate (``microtask_gate.execution_refusal``: TASK not closed,
                    ACTIVE lifecycle-current microtask, no ABORT/ROLLBACK disposition)
  STARTED           persisted through the lock-held transition path while the TASK lock is
                    held, *before* the first physical write; if it cannot be persisted,
                    nothing is written
  mutation          WRITE/edit: temp + fsync + atomic replace; CREATE: temp + atomic
                    create-if-absent (never overwrites); DELETE: unlink
  post-proof        RC-1 DONE transition under the same locks: the server re-reads the
                    target and persists the receipt only when its bytes exactly equal the
                    contracted post-state; otherwise the operation stays STARTED
  release           the RC-3 claim is released after DONE

Replay of the same durable contract (same ``operation_id`` and request fingerprint) never
repeats a side effect: DONE/VERIFIED returns the persisted receipt; STARTED or
UNKNOWN_AFTER_DISCONNECT (fate unknown) is never re-executed blindly — RC-2 reconciliation
and the Resolver decide, RC-6 ``recover`` carries the decision out; only an authoritative
fresh RETRY of a STARTED operation is executed again, through the same boundary and CAS.
A changed request under the same ``operation_id`` is refused (fingerprint conflict).

move / rename are a tracked sequence of two single-target operations (24, WA-4.2): CREATE
the destination with the exact source bytes, then DELETE the source. Both operations are
declared and both targets are owned (RC-3 claims) before the first write; each step has its
own durable identity, STARTED-before-write, post-proof and receipt. The pair is not one
atomic transaction: an interruption between the steps is a reported PARTIAL state.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .file_state import FileStateError, authority_of, observe_bytes, observe_path, same_authority
from .manifest_store import ManifestSnapshotStore, ManifestStoreError, _atomic_write_bytes
from .models import OperationStatus, new_id
from .operation_contract import LEGACY_CONTRACT_VERSION, MutationKind, mutation_kind_for
from .operation_store import (
    OperationConflictError,
    OperationContractRejected,
    OperationPayloadIntegrityError,
    OperationReceiptMismatch,
    OperationStoreError,
)
from .reconciliation import ReconciliationEvidenceError
from .reconciliation_service import ReconciliationService
from .resolution_store import ResolutionAction, ResolutionResult, ResolutionStoreError
from .resolver_service import ResolverError
from .store_lock import DEFAULT_LOCK_TIMEOUT_SECONDS
from .target_claim_service import (
    ACQUIRED,
    REBASED,
    REPLAYED as CLAIM_REPLAYED,
    TargetClaimError,
    TargetClaimService,
)
from .target_claim_store import physical_target_key
from .target_identity import TargetIdentityError, canonical_target
from .task_store import COMPLETION_ACTIVE, TaskStoreError
from .workspace_registry import WorkspaceRegistryError

EXECUTED = "EXECUTED"
REPLAYED = "REPLAYED"
REFUSED = "REFUSED"
RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"
PARTIAL = "PARTIAL"

COMPOSITE_ACTIONS = frozenset({"move", "rename"})
CREATE_STEP_SUFFIX = ".create-destination"
DELETE_STEP_SUFFIX = ".delete-source"

_RECONCILE_NEXT = (
    "its physical result is not proved, so it is never repeated blindly: reconcile it "
    "(POST /tasks/{task}/reconcile), record the Resolver decision on that evidence (ADOPT an "
    "applied effect, RETRY a proven-unapplied one, ROLLBACK, or ABORT) and run recover (RC-6); a "
    "fresh RETRY of a STARTED operation is executed again by this executor"
)


class MutationExecutorError(RuntimeError):
    """The executor could not run safely (unreadable authority facts)."""


class MutationRequestError(MutationExecutorError):
    """The mutation request itself is malformed."""


class _WriteRefused(Exception):
    """The physical write raised; whether bytes changed is proved by re-observation."""


def _require_text(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MutationRequestError(f"{name} must be a non-empty string")
    return value.strip()


def _create_exclusive(path: Path, data: bytes) -> None:
    """Create ``path`` with ``data`` atomically, never replacing an existing file.

    The bytes go to a temporary sibling first; ``os.link`` then publishes them only if the
    name is still free (FileExistsError otherwise). Where hard links are unavailable on
    Windows, ``os.rename`` is used: it never replaces an existing file there.
    """
    temp = path.parent / f".{path.name}.{new_id('wa4e')}.tmp"
    try:
        with temp.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temp, path)
        except FileExistsError:
            raise
        except (OSError, NotImplementedError, AttributeError):
            if os.name != "nt":
                raise
            os.rename(temp, path)  # Windows: FileExistsError if the name was taken meanwhile
    finally:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass


class MutationExecutor:
    def __init__(
        self,
        storage_root: str | Path | None = None,
        *,
        lock_timeout: float = DEFAULT_LOCK_TIMEOUT_SECONDS,
    ) -> None:
        self.claims = TargetClaimService(storage_root, lock_timeout=lock_timeout)
        self.operations = self.claims.operations
        self.tasks = self.operations.tasks
        root = self.tasks.storage_root
        self.manifests = ManifestSnapshotStore(root)
        self.resolver = self.claims.resolver
        self.reconciliation = ReconciliationService(root)
        self.events = self.operations.events

    # --- results ----------------------------------------------------------------------

    @staticmethod
    def _result(
        result: str,
        code: str,
        reason: str,
        *,
        task_id: str,
        operation_id: str,
        record=None,
        next_safe_action: str | None = None,
        physical_mutation_performed: bool = False,
        **extra: Any,
    ) -> dict[str, Any]:
        contract = (record.contract or {}) if record is not None else {}
        outcome = {
            "result": result,
            "result_code": code,
            "reason": reason,
            "task_id": task_id,
            "operation_id": operation_id,
            "operation_status": record.status.value if record is not None else None,
            "operation_revision": record.revision if record is not None else None,
            "mutation_kind": contract.get("mutation_kind"),
            "target": record.target if record is not None else None,
            "receipt": record.receipt if record is not None else None,
            "physical_mutation_performed": physical_mutation_performed,
            "next_safe_action": next_safe_action,
        }
        outcome.update(extra)
        return outcome

    # --- public entry ---------------------------------------------------------------------

    def execute(
        self,
        task_id: str,
        microtask_id: str,
        operation_id: str,
        action: str,
        target: str,
        *,
        destination: str | None = None,
        payload: bytes | None = None,
        expected_pre_state: Any = None,
        expected_post_state: Any = None,
        expected_precondition_sha256: str | None = None,
        request_payload: Any = None,
        agent: str | None = None,
        channel: str | None = None,
        allow_secret_target: bool = False,
    ) -> dict[str, Any]:
        """Execute one tracked mutation (or a move/rename pair); replay-safe by ``operation_id``."""
        task_id = _require_text("task_id", task_id)
        microtask_id = _require_text("microtask_id", microtask_id)
        # The idempotency key of the durable contract: without it a replay would be a new operation.
        operation_id = _require_text("operation_id", operation_id)
        action = _require_text("action", action)
        target = _require_text("target", target)
        if action.lower() in COMPOSITE_ACTIONS:
            if destination is None:
                raise MutationRequestError(f"{action} requires a destination")
            if any(value is not None for value in (payload, expected_pre_state, expected_post_state,
                                                    expected_precondition_sha256, request_payload)):
                raise MutationRequestError(f"{action} takes no payload or declared states: the server reads the source")
            return self._execute_composite(
                task_id, microtask_id, operation_id, action.lower(), target,
                _require_text("destination", destination), agent=agent, channel=channel,
            )
        if destination is not None:
            raise MutationRequestError("destination is only valid for move/rename")
        kind = mutation_kind_for(action)
        if kind is None:
            raise MutationRequestError(f"unsupported mutation action: {action}")
        if kind is MutationKind.DELETE and expected_pre_state is None and expected_post_state is None:
            # an executable DELETE contract is explicit: its post-state is the absent file
            expected_post_state = {"exists": False}
        begin = dict(
            payload=payload,
            expected_pre_state=expected_pre_state,
            expected_post_state=expected_post_state,
            expected_precondition_sha256=expected_precondition_sha256,
            request_payload=request_payload,
            allow_secret_target=allow_secret_target,
        )
        record = self._intent(task_id, microtask_id, operation_id, action, target, begin, agent, channel)
        if isinstance(record, dict):
            return record
        return self._drive(task_id, record, agent=agent, channel=channel)

    # --- INTENT ----------------------------------------------------------------------------

    def _intent(self, task_id, microtask_id, operation_id, action, target, begin, agent, channel):
        """The durable contract (new, or the same one replayed); a refusal result otherwise."""
        try:
            return self.operations.begin(
                task_id, microtask_id, action, target, operation_id=operation_id,
                agent=agent, channel=channel, **begin,
            )["operation"]
        except OperationConflictError as exc:
            return self._result(REFUSED, "OPERATION_ID_CONFLICT", str(exc), task_id=task_id,
                                operation_id=operation_id,
                                next_safe_action="a changed request needs a new operation_id")
        except OperationContractRejected as exc:
            return self._result(REFUSED, "CONTRACT_REJECTED", str(exc), task_id=task_id,
                                operation_id=operation_id,
                                next_safe_action="fix the request; nothing was recorded or written")
        except (TaskStoreError, OperationStoreError) as exc:
            try:
                active = self.tasks.completion_state(task_id) == COMPLETION_ACTIVE
            except TaskStoreError:
                return self._result(REFUSED, "UNKNOWN_TASK", str(exc), task_id=task_id,
                                    operation_id=operation_id)
            if active:
                return self._result(REFUSED, "REQUEST_REJECTED", str(exc), task_id=task_id,
                                    operation_id=operation_id,
                                    next_safe_action="fix the request; nothing was recorded or written")
            return self._closed_replay(task_id, microtask_id, operation_id, action, target, begin, exc)

    def _closed_replay(self, task_id, microtask_id, operation_id, action, target, begin, error):
        """A lost response of an operation whose TASK has been closed since: read-only replay."""
        try:
            record = self.operations.get(task_id, operation_id)
            _, _, request = self.operations._prepare(
                task_id, microtask_id, action, target,
                expected_precondition_sha256=begin["expected_precondition_sha256"],
                request_payload=begin["request_payload"],
                expected_pre_state=begin["expected_pre_state"],
                expected_post_state=begin["expected_post_state"],
                payload=begin["payload"], agent=None, channel=None,
                allow_secret_target=begin["allow_secret_target"],
            )
        except (TaskStoreError, OperationStoreError):
            return self._result(REFUSED, "TASK_NOT_ACTIVE", str(error), task_id=task_id,
                                operation_id=operation_id,
                                next_safe_action="no mutation is admitted outside an active TASK")
        if record.request_fingerprint != request.fingerprint:
            return self._result(REFUSED, "OPERATION_ID_CONFLICT",
                                "operation_id exists with a different request fingerprint",
                                task_id=task_id, operation_id=operation_id, record=record)
        if record.status in (OperationStatus.DONE, OperationStatus.VERIFIED):
            return self._result(REPLAYED, "KNOWN_RECEIPT", "persisted receipt of a closed TASK",
                                task_id=task_id, operation_id=operation_id, record=record,
                                next_safe_action="the TASK is closed: read-only history")
        return self._result(REFUSED, "TASK_CLOSED", str(error), task_id=task_id,
                            operation_id=operation_id, record=record,
                            next_safe_action="the TASK is closed: no mutation is admitted")

    # --- lifecycle dispatch --------------------------------------------------------------------

    def _drive(self, task_id: str, record, *, agent=None, channel=None) -> dict[str, Any]:
        op = record.operation_id
        if record.contract_version == LEGACY_CONTRACT_VERSION:
            return self._result(REFUSED, "LEGACY_CONTRACT", "legacy contract v1 cannot be executed",
                                task_id=task_id, operation_id=op, record=record)
        if record.status in (OperationStatus.DONE, OperationStatus.VERIFIED):
            return self._replayed(task_id, record)
        if record.status is OperationStatus.FAILED:
            return self._result(REFUSED, "OPERATION_FAILED", "the operation is FAILED (terminal)",
                                task_id=task_id, operation_id=op, record=record,
                                next_safe_action="a new attempt needs a new operation_id")
        retry = None
        if record.status in (OperationStatus.STARTED, OperationStatus.UNKNOWN_AFTER_DISCONNECT):
            retry = self._authoritative_retry(task_id, record)
            if retry is None:
                return self._reconciliation_required(task_id, record, "FATE_UNKNOWN",
                                                     f"the operation is {record.status.value}")
            if record.status is OperationStatus.UNKNOWN_AFTER_DISCONNECT:
                return self._result(
                    REFUSED, "RETRY_LIFECYCLE_UNSUPPORTED",
                    "a RETRY of an UNKNOWN_AFTER_DISCONNECT operation cannot record its outcome: the RC-1 "
                    "lifecycle has no transition out of UNKNOWN_AFTER_DISCONNECT",
                    task_id=task_id, operation_id=op, record=record,
                    next_safe_action="ABORT it and execute the change as a new operation (PROPOSAL: a "
                    "re-arm transition UNKNOWN_AFTER_DISCONNECT -> STARTED needs a lifecycle decision)")
        return self._execute(task_id, record, retry, agent=agent, channel=channel)

    def _authoritative_retry(self, task_id: str, record):
        """The fresh accepted RETRY that is this operation's authority (RC-3 eligibility rule)."""
        try:
            accepted = [
                item for item in self.resolver.store.list(task_id, operation_id=record.operation_id)
                if item.result is ResolutionResult.ACCEPTED
            ]
            if any(item.action is ResolutionAction.ABORT for item in accepted):
                return None
            fresh = [item for item in accepted if self.resolver.freshness(item)["fresh"]]
        except (ResolutionStoreError, ResolverError) as exc:
            raise MutationExecutorError(f"recovery facts are unreadable: {exc}") from exc
        if fresh and fresh[-1].action is ResolutionAction.RETRY:
            return fresh[-1]
        return None

    def _reconciliation_required(self, task_id: str, record, code: str, reason: str) -> dict[str, Any]:
        decision = None
        try:
            advice = self.reconciliation.reconcile(task_id, record.microtask_id, record.operation_id)
            decision = {key: advice["DECISION"][key] for key in ("decision", "reason_code", "evidence_fingerprint")}
        except (ReconciliationEvidenceError, OperationStoreError, ManifestStoreError, TaskStoreError) as exc:
            decision = {"decision": None, "reason_code": "EVIDENCE_UNAVAILABLE", "reason": str(exc)}
        return self._result(
            RECONCILIATION_REQUIRED, code, reason, task_id=task_id, operation_id=record.operation_id,
            record=record, reconciliation=decision,
            next_safe_action=f"operation {record.operation_id}: {_RECONCILE_NEXT.format(task=task_id)}",
        )

    def _replayed(self, task_id: str, record) -> dict[str, Any]:
        release = self._release(task_id, record.operation_id, "WA4E_REPLAY_FINISHES_RELEASE")
        return self._result(
            REPLAYED, "KNOWN_RECEIPT",
            f"the operation is already {record.status.value}: its persisted receipt is returned, nothing "
            "is executed again",
            task_id=task_id, operation_id=record.operation_id, record=record, claim_release=release,
            next_safe_action=(
                "verify the change and transition the operation DONE -> VERIFIED"
                if record.status is OperationStatus.DONE else "nothing to do"
            ),
        )

    # --- admission + boundary ---------------------------------------------------------------

    def _manifest_refusal(self, task_id: str, record) -> tuple[str, str] | None:
        """The target must be a target of the microtask's VERIFIED restore point."""
        try:
            plan = self.manifests.restore_plan(task_id, record.microtask_id)
            root = self.operations.registry.get(record.contract["workspace_id"]).workspace_root
            keys = {canonical_target(root, item["source_path"]).key for item in plan["items"]}
        except (ManifestStoreError, TaskStoreError) as exc:
            return "RESTORE_POINT_NOT_VERIFIED", f"no verified restore point for {record.microtask_id}: {exc}"
        except (WorkspaceRegistryError, TargetIdentityError, KeyError) as exc:
            return "RESTORE_POINT_NOT_VERIFIED", f"restore point targets are unresolvable: {exc}"
        if record.contract["target_key"] not in keys:
            return (
                "TARGET_NOT_IN_MANIFEST",
                f"{record.target} is not a target of the restore point of {record.microtask_id}; a tracked "
                "mutation is admitted only for a target RC-4 can restore",
            )
        return None

    def _execute(self, task_id: str, record, retry, *, agent=None, channel=None) -> dict[str, Any]:
        op = record.operation_id
        contract = record.contract or {}
        if not contract.get("mutation_kind"):
            return self._result(REFUSED, "UNKNOWN_MUTATION_KIND", "the contract names no mutation kind",
                                task_id=task_id, operation_id=op, record=record)
        kind = MutationKind(contract["mutation_kind"])
        if not contract.get("complete"):
            return self._result(REFUSED, "CONTRACT_INCOMPLETE",
                                "the contract is incomplete: " + ", ".join(contract.get("issues", [])),
                                task_id=task_id, operation_id=op, record=record,
                                next_safe_action="declare a complete contract under a new operation_id")
        data = None
        if kind in (MutationKind.CREATE, MutationKind.WRITE):
            try:
                data = self.operations.read_payload(task_id, op)  # hash+size verified, before STARTED
            except OperationPayloadIntegrityError as exc:
                return self._result(REFUSED, "PAYLOAD_INTEGRITY_FAILURE", str(exc),
                                    task_id=task_id, operation_id=op, record=record)
        refusal = self._manifest_refusal(task_id, record)
        if refusal is not None:
            return self._result(REFUSED, *refusal, task_id=task_id, operation_id=op, record=record,
                                next_safe_action="nothing was written")
        try:
            claim = self.claims.acquire(task_id, op, operation_revision=record.revision, agent=agent,
                                        channel=channel)
        except TargetClaimError as exc:
            return self._result(REFUSED, "OWNERSHIP_UNAVAILABLE", str(exc), task_id=task_id,
                                operation_id=op, record=record)
        refused = claim["result"] not in (ACQUIRED, REBASED, CLAIM_REPLAYED) or (
            claim["result"] == CLAIM_REPLAYED and claim["result_code"] != "SAME_BASIS"
        )
        if refused:
            settled = self.operations.get(task_id, op)
            if settled.status in (OperationStatus.DONE, OperationStatus.VERIFIED):
                return self._replayed(task_id, settled)  # another delivery of this contract executed it
        if claim["result"] == CLAIM_REPLAYED and claim["result_code"] != "SAME_BASIS":
            # RC-3: a basis whose claim was released is never owned again
            return self._result(REFUSED, "CLAIM_ALREADY_RELEASED", claim["reason"], task_id=task_id,
                                operation_id=op, record=record,
                                next_safe_action="nothing was written; execute the change as a new operation_id")
        if claim["result"] not in (ACQUIRED, REBASED, CLAIM_REPLAYED):
            code = "PRECONDITION_FAILED" if claim["result_code"] == "STATE_DRIFT" else claim["result_code"]
            return self._result(REFUSED, code, claim["reason"], task_id=task_id, operation_id=op,
                                record=record, blocking_owner=claim.get("blocking_owner"),
                                next_safe_action="nothing was written")
        claim_id = claim["claim"]["claim_id"]
        outcome = None
        refusal = None
        try:
            with self.claims.mutation_boundary(task_id, op, operation_revision=record.revision,
                                               claim_id=claim_id) as gate:
                if not gate["mutation_authority"]:
                    refusal = (gate["result_code"], gate["reason"])
                else:
                    outcome = self._mutate_locked(task_id, record, kind, data, retry)
        except TargetClaimError as exc:
            refusal = ("BOUNDARY_UNAVAILABLE", str(exc))
        if outcome is None:
            settled = self.operations.get(task_id, op)
            if settled.status in (OperationStatus.DONE, OperationStatus.VERIFIED):
                # the same contract delivered twice at once: the other delivery executed it
                return self._replayed(task_id, settled)
            code, reason = refusal
            if code == "STATE_DRIFT":
                code = "PRECONDITION_FAILED"
            outcome = self._result(
                REFUSED, code, reason, task_id=task_id, operation_id=op, record=self.operations.get(task_id, op),
                next_safe_action=(
                    "nothing was written; the operation keeps its target ownership (RC-3: it belongs to the "
                    "logical operation) and a replay continues once the blocker is gone; to abandon it, "
                    "transition it to FAILED or record ABORT, then release its claim"
                ),
            )
        if outcome["result"] == EXECUTED:
            outcome["claim_release"] = self._release(task_id, op, "WA4E_EXECUTED")
        return outcome

    def _mutate_locked(self, task_id: str, record, kind: MutationKind, data: bytes | None, retry) -> dict[str, Any]:
        """Inside the RC-3 boundary: TASK lock + mutation lock + target lock are held."""
        op = record.operation_id
        current = self.operations.get(task_id, op)
        if current.revision != record.revision or current.status is not record.status:
            return self._result(REFUSED, "OPERATION_CHANGED", "the operation changed before the boundary",
                                task_id=task_id, operation_id=op, record=current)
        refusal = self._manifest_refusal(task_id, current)  # re-proved under the lifecycle lock
        if refusal is not None:
            return self._result(REFUSED, *refusal, task_id=task_id, operation_id=op, record=current)
        canonical, _ = self.claims._target(current)
        path = canonical.path
        if retry is None:
            try:
                current = self.operations._transition_locked(
                    task_id, op, OperationStatus.STARTED,
                    result_summary="WA4-E: authoritative execution started",
                )["operation"]
            except OperationStoreError as exc:
                return self._result(REFUSED, "STARTED_NOT_PERSISTED",
                                    f"STARTED could not be persisted, nothing was written: {exc}",
                                    task_id=task_id, operation_id=op, record=self.operations.get(task_id, op),
                                    next_safe_action="replay the same request once storage is writable")
        else:
            self.events.append_event(task_id, "MUTATION_RETRY_EXECUTING", microtask_id=current.microtask_id,
                                     operation_id=op, payload={"resolution_id": retry.resolution_id})
        # STARTED is durable (or already was, for an authoritative RETRY): only now the first write.
        if kind is MutationKind.WRITE and not current.contract["pre_state"]["exists"]:
            kind = MutationKind.CREATE  # a write of an absent file never replaces one that appeared meanwhile
        try:
            self._apply(kind, path, data)
        except _WriteRefused as exc:
            return self._write_failed(task_id, current, path, exc)
        try:
            done = self.operations._transition_locked(
                task_id, op, OperationStatus.DONE,
                result_summary="WA4-E: executed; exact post-state proved by the server",
            )["operation"]
        except OperationReceiptMismatch as exc:
            return self._reconciliation_required(task_id, self.operations.get(task_id, op), "POST_PROOF_FAILED",
                                                 f"the target does not hold the contracted post-state: {exc}")
        except OperationStoreError as exc:
            return self._reconciliation_required(task_id, self.operations.get(task_id, op), "RECEIPT_NOT_PERSISTED",
                                                 f"the receipt could not be persisted: {exc}")
        self.events.append_event(
            task_id, "MUTATION_EXECUTED", microtask_id=done.microtask_id, operation_id=op,
            payload={"mutation_kind": done.contract["mutation_kind"], "receipt": authority_of(done.receipt),
                     "retry_resolution_id": retry.resolution_id if retry is not None else None},
        )
        return self._result(EXECUTED, "EXACT_POST_STATE_PROVED",
                            "executed once; the receipt is the server-observed post-state",
                            task_id=task_id, operation_id=op, record=done, physical_mutation_performed=True,
                            next_safe_action="verify the change and transition the operation DONE -> VERIFIED")

    @staticmethod
    def _apply(kind: MutationKind, path: Path, data: bytes | None) -> None:
        try:
            if kind is MutationKind.WRITE:
                _atomic_write_bytes(path, data)
            elif kind is MutationKind.CREATE:
                _create_exclusive(path, data)
            else:
                path.unlink()
        except (OSError, ManifestStoreError) as exc:
            raise _WriteRefused(f"{type(exc).__name__}: {exc}") from exc

    def _write_failed(self, task_id: str, record, path: Path, exc: _WriteRefused) -> dict[str, Any]:
        try:
            observed = observe_path(path)
            unchanged = same_authority(observed, authority_of(record.contract["pre_state"]))
        except FileStateError:
            unchanged = False
        return self._reconciliation_required(
            task_id, self.operations.get(task_id, record.operation_id),
            "WRITE_REFUSED_TARGET_UNCHANGED" if unchanged else "WRITE_OUTCOME_UNKNOWN",
            f"the physical write failed ({exc}); the target is "
            + ("proven unchanged (pre-state)" if unchanged else "not proven unchanged"),
        )

    def _release(self, task_id: str, operation_id: str, reason: str) -> dict[str, Any] | None:
        try:
            outcome = self.claims.release(task_id, operation_id, reason=reason, channel="wa4e_executor")
        except (TargetClaimError, OperationStoreError, TaskStoreError) as exc:
            return {"result": "PENDING", "reason": str(exc)}
        return {"result": outcome["result"], "result_code": outcome["result_code"]}

    # --- move / rename -------------------------------------------------------------------------

    def _execute_composite(self, task_id, microtask_id, operation_id, action, source, destination, *,
                           agent=None, channel=None) -> dict[str, Any]:
        try:
            task = self.tasks.open_task(task_id)
            root = self.operations.registry.get(task.workspace_id).workspace_root
            src = canonical_target(root, source)
            dst = canonical_target(root, destination)
        except (TaskStoreError, WorkspaceRegistryError, TargetIdentityError) as exc:
            return self._result(REFUSED, "TARGET_REJECTED", str(exc), task_id=task_id, operation_id=operation_id)
        if physical_target_key(src.path) == physical_target_key(dst.path):
            return self._result(REFUSED, "SAME_PHYSICAL_TARGET",
                                "source and destination name the same physical file (a case-only rename on "
                                "a case-insensitive file system is not a tracked move)",
                                task_id=task_id, operation_id=operation_id)
        if action == "rename" and src.path.parent != dst.path.parent:
            return self._result(REFUSED, "RENAME_ACROSS_DIRECTORIES",
                                "rename keeps the directory; use move", task_id=task_id, operation_id=operation_id)
        create_id, delete_id = operation_id + CREATE_STEP_SUFFIX, operation_id + DELETE_STEP_SUFFIX
        marker = {"kind": action, "operation_id": operation_id, "source": src.key, "destination": dst.key}
        delete_request = {"composite": dict(marker, step="delete-source")}
        create_request = {"composite": dict(marker, step="create-destination")}
        steps: list[dict[str, Any]] = []

        # 1. the DELETE of the source is declared first: its contract pins the bytes being moved
        removal = self._intent(task_id, microtask_id, delete_id, "delete", source,
                               self._begin_args(delete_request, expected_post_state={"exists": False}),
                               agent, channel)
        if isinstance(removal, dict):
            if removal["result"] != REPLAYED:
                return self._composite(task_id, operation_id, action, [removal])
            # a closed TASK: a read-only replay of both persisted receipts
            payload = self._stored_payload(task_id, create_id)
            creation = (
                self._intent(task_id, microtask_id, create_id, "create", destination,
                             self._begin_args(create_request, payload=payload), agent, channel)
                if payload is not None
                else self._result(REFUSED, "TASK_CLOSED", "the TASK is closed", task_id=task_id,
                                  operation_id=create_id)
            )
            return self._composite(task_id, operation_id, action, [creation, removal])
        source_pre = authority_of(removal.contract["pre_state"])
        # 2. the CREATE of the destination carries exactly those bytes
        if self._existing(task_id, create_id) is None:
            try:
                payload = src.path.read_bytes()
            except OSError as exc:
                return self._composite(task_id, operation_id, action, [self._result(
                    REFUSED, "SOURCE_UNREADABLE", str(exc), task_id=task_id, operation_id=create_id)])
        else:
            payload = self._stored_payload(task_id, create_id)
            if payload is None:
                return self._composite(task_id, operation_id, action, [self._result(
                    REFUSED, "PAYLOAD_INTEGRITY_FAILURE", "the stored destination payload is unreadable",
                    task_id=task_id, operation_id=create_id)])
        if not same_authority(observe_bytes(payload), source_pre):
            return self._composite(task_id, operation_id, action, [self._result(
                REFUSED, "SOURCE_CHANGED",
                "the source bytes differ from the declared source pre-state; nothing was written",
                task_id=task_id, operation_id=create_id, record=removal,
                next_safe_action=f"transition {delete_id} to FAILED (or record ABORT) and declare the move anew "
                "under a new operation_id")])
        creation = self._intent(task_id, microtask_id, create_id, "create", destination,
                                self._begin_args(create_request, payload=payload), agent, channel)
        if isinstance(creation, dict):
            return self._composite(task_id, operation_id, action, [creation])
        # 3. own the source before the first write (protects it for the whole pair)
        if removal.status is OperationStatus.INTENT:
            try:
                owned = self.claims.acquire(task_id, delete_id, operation_revision=removal.revision,
                                            agent=agent, channel=channel)
            except TargetClaimError as exc:
                owned = {"result": "ERROR", "result_code": "OWNERSHIP_UNAVAILABLE", "reason": str(exc)}
            if owned["result"] not in (ACQUIRED, REBASED, CLAIM_REPLAYED):
                code = "PRECONDITION_FAILED" if owned["result_code"] == "STATE_DRIFT" else owned["result_code"]
                return self._composite(task_id, operation_id, action, [self._result(
                    REFUSED, code, owned["reason"], task_id=task_id, operation_id=delete_id, record=removal,
                    blocking_owner=owned.get("blocking_owner"), next_safe_action="nothing was written")])
        # 4. step 1: CREATE destination, then 5. step 2: DELETE source
        first = self._drive(task_id, self.operations.get(task_id, create_id), agent=agent, channel=channel)
        steps.append(first)
        if first["result"] not in (EXECUTED, REPLAYED):
            return self._composite(task_id, operation_id, action, steps)  # both claims stay for a replay
        second = self._drive(task_id, self.operations.get(task_id, delete_id), agent=agent, channel=channel)
        steps.append(second)
        return self._composite(task_id, operation_id, action, steps)

    @staticmethod
    def _begin_args(request_payload, *, payload=None, expected_post_state=None):
        return dict(payload=payload, expected_pre_state=None, expected_post_state=expected_post_state,
                    expected_precondition_sha256=None, request_payload=request_payload,
                    allow_secret_target=False)

    def _existing(self, task_id: str, operation_id: str):
        try:
            return self.operations.get(task_id, operation_id)
        except (OperationStoreError, TaskStoreError):
            return None

    def _stored_payload(self, task_id: str, operation_id: str) -> bytes | None:
        try:
            return self.operations.read_payload(task_id, operation_id)
        except (OperationStoreError, TaskStoreError):
            return None

    def _composite(self, task_id, operation_id, action, steps) -> dict[str, Any]:
        done = [s for s in steps if s["result"] in (EXECUTED, REPLAYED)]
        performed = any(s["physical_mutation_performed"] for s in steps)
        if len(done) == 2:
            result = REPLAYED if all(s["result"] == REPLAYED for s in steps) else EXECUTED
            code, next_action = "MOVE_COMPLETED", "verify both steps and transition them DONE -> VERIFIED"
        elif done:
            result, code = PARTIAL, "MOVE_INTERRUPTED"
            next_action = (
                f"the destination exists ({operation_id}{CREATE_STEP_SUFFIX} has its receipt) but the source "
                f"was not deleted ({steps[-1]['result_code']}): the pair is not atomic. Replay the same "
                f"{action} once the blocker is resolved (it continues with the delete), or roll the microtask "
                "back through RC-2/RC-4"
            )
        else:
            result = steps[-1]["result"] if steps else REFUSED
            code = steps[-1]["result_code"] if steps else "MOVE_NOT_STARTED"
            next_action = steps[-1]["next_safe_action"] if steps else None
        return {
            "result": result,
            "result_code": code,
            "reason": f"{action} as two tracked operations (create destination, delete source)",
            "task_id": task_id,
            "operation_id": operation_id,
            "composite": action,
            "steps": steps,
            "physical_mutation_performed": performed,
            "next_safe_action": next_action,
        }
