"""RC-4 tracked safe rollback.

Turns an accepted, fresh ROLLBACK resolution into a separate tracked recovery
operation:

1. ``prepare``: authority check (fresh accepted ROLLBACK for the same
   task/microtask/operation, contract v2, no ABORT), side-effect-free restore
   point verification, server-derived target set from the verified manifest,
   persistent PREPARED record, then preservation of every target's current
   physical state (bytes content-addressed outside the repository) -> PRESERVED.
   Any preservation failure ends the session in PRESERVATION_FAILED: nothing
   destructive ever happens in that session.
2. ``apply``: under the TASK lock and every mutated target's lock (sorted by
   target hash), re-prove the basis, acquire RC-3 ownership for all mutated
   targets atomically (owner = this rollback; a conflict anywhere blocks the
   whole destructive phase), then per target: CAS against the preserved state,
   persist APPLYING, restore exact snapshot bytes / delete a created file,
   post-read and persist a receipt. Drift stops the session; nothing is
   overwritten. VERIFIED only when every target is proven restored or already
   in pre-state; ownership is then released.

Freshness: the full Resolver fingerprint check is required before the first
destructive write. Once this session has restored a target, the evidence
fingerprint necessarily differs because of the session's own effect, so
continuation (and resume after interruption) re-proves the basis "modulo own
receipts": unchanged operation revision and request identity, unchanged restore
point, no ABORT, restored targets still at their restore state and every other
target still at its preserved state.

Interrupted writes are reconciled from bytes, never repeated blindly: an
APPLYING target equal to its restore state becomes RESTORED (recovered), one
still equal to its preserved state is safe to apply again, anything else drifts.
"""

from __future__ import annotations

import hashlib
from contextlib import ExitStack
from pathlib import Path
from typing import Any

from .file_state import FileStateError, authority_of, observe_path, same_authority
from .manifest_store import ManifestSnapshotStore, ManifestStoreError, _atomic_write_bytes
from .models import utc_now_iso
from .operation_contract import LEGACY_CONTRACT_VERSION
from .operation_store import OperationStore, OperationStoreError
from .payload_store import PayloadIntegrityError, PayloadScopeError, PayloadStoreError
from .resolution_store import ResolutionAction, ResolutionResult, ResolutionStoreError
from .resolver_service import ResolverService
from .rollback_store import (
    APPLYING,
    AUTHORIZED,
    CLOSED,
    DELETE_CREATED,
    FAILED,
    NOOP,
    PARTIAL,
    PREPARED,
    PRESERVATION_FAILED,
    PRESERVED,
    T_APPLYING,
    T_DRIFTED,
    T_FAILED,
    T_NOOP,
    T_PENDING,
    T_PRESERVED,
    T_RESTORED,
    VERIFIED,
    WRITE_RESTORE,
    PreservedStateStore,
    RollbackStore,
    RollbackStoreError,
    rollback_identity,
)
from .storage_policy import MAX_PAYLOAD_BYTES, secret_pattern_for
from .store_lock import DEFAULT_LOCK_TIMEOUT_SECONDS, InterProcessLock, StoreLockTimeout
from .target_claim_store import (
    ACTIVE,
    RELEASED,
    ROLLBACK_OWNER,
    SUPERSEDED,
    TargetClaimStore,
    TargetClaimStoreError,
    claim_identity,
    physical_target_key,
    target_hash,
)
from .target_identity import TargetIdentityError, canonical_target
from .workspace_registry import WorkspaceRegistryError

REJECTED = "REJECTED"
BLOCKED = "BLOCKED"
# Final for ``apply``: a PARTIAL/FAILED session never resumes (it only ends there
# after a drift/failure was recorded); it is closed and a new reconciliation
# decides. Interrupted sessions stay APPLYING and are reconciled by ``apply``.
_DONE = (VERIFIED, CLOSED, PRESERVATION_FAILED, PARTIAL, FAILED)


class RollbackError(RuntimeError):
    """Authoritative rollback state cannot be read or persisted safely."""


class RollbackInputError(RollbackError):
    """The rollback request itself is malformed."""


# The only two places where RC-4 changes project bytes (tests patch these).
def _write_restored_bytes(path: Path, data: bytes) -> None:
    _atomic_write_bytes(path, data)


def _delete_created(path: Path) -> None:
    path.unlink()


def _state(observed: Any) -> dict[str, Any]:
    return authority_of(observed)


class RollbackService:
    def __init__(
        self,
        storage_root: str | Path | None = None,
        *,
        lock_timeout: float = DEFAULT_LOCK_TIMEOUT_SECONDS,
        max_preserved_bytes: int = MAX_PAYLOAD_BYTES,
    ) -> None:
        self.operations = OperationStore(storage_root, lock_timeout=lock_timeout)
        root = self.operations.tasks.storage_root
        self.manifests = ManifestSnapshotStore(root)
        self.resolver = ResolverService(root)
        self.claims = TargetClaimStore(root)
        self.store = RollbackStore(root)
        self.preserved = PreservedStateStore(root, max_bytes=max_preserved_bytes)
        self.events = self.operations.events
        self.lock_timeout = lock_timeout

    # --- helpers ----------------------------------------------------------------------

    def _event(self, record: dict[str, Any], event_type: str, payload: dict[str, Any]) -> None:
        self.events.append_event(
            record["task_id"],
            event_type,
            microtask_id=record["microtask_id"],
            operation_id=record["operation_id"],
            payload=dict(payload, rollback_id=record["rollback_id"]),
        )

    def _persist(self, record: dict[str, Any]) -> None:
        record["revision"] += 1
        record["updated_at"] = utc_now_iso()
        record["next_safe_action"] = self._next_action(record)
        try:
            self.store.write(record)
        except RollbackStoreError as exc:
            raise RollbackError(str(exc)) from exc

    @staticmethod
    def _outcome(result: str, code: str, reason: str, record: dict[str, Any] | None, **extra: Any) -> dict[str, Any]:
        outcome = {
            "result": result,
            "result_code": code,
            "reason": reason,
            "rollback": record,
            "next_safe_action": record["next_safe_action"] if record else None,
        }
        outcome.update(extra)
        return outcome

    def _workspace_root(self, task_id: str) -> Path:
        try:
            task = self.operations.tasks.open_task(task_id)
            return Path(self.operations.registry.get(task.workspace_id).workspace_root)
        except WorkspaceRegistryError as exc:
            raise RollbackError(f"workspace unavailable: {exc}") from exc

    def _canonical(self, root: Path, target: dict[str, Any]):
        canonical = canonical_target(root, target["source_path"])
        if canonical.key != target["target_key"] or target_hash(physical_target_key(canonical.path)) != target["target_hash"]:
            raise TargetIdentityError("canonical target identity changed since the rollback basis")
        return canonical

    @staticmethod
    def _next_action(record: dict[str, Any]) -> str:
        status = record["status"]
        attempt = record["last_attempt"]
        if status == PREPARED:
            return "current-state preservation is incomplete; run prepare again (no destructive step has happened)"
        if status == PRESERVATION_FAILED:
            return (
                "current state could not be preserved for every target; nothing was restored; "
                "fix the blocker and start from a new reconciliation/ROLLBACK resolution"
            )
        if status in (PRESERVED, AUTHORIZED) and attempt is not None:
            return (
                f"rollback blocked before any destructive step ({attempt['code']}); nothing was "
                "restored; resolve the blocker and apply again, or start a new reconciliation"
            )
        if status == PRESERVED:
            return "current state of every target is preserved; apply the rollback (claims + per-target CAS)"
        if status == AUTHORIZED:
            return "rollback owns all mutated targets; apply continues with per-target CAS and restore"
        if status == APPLYING:
            return (
                "rollback was interrupted during a restore; apply again: it first proves each "
                "in-flight target's real bytes and never repeats a write blindly"
            )
        if status == VERIFIED:
            return (
                f"rollback of microtask {record['microtask_id']} restored and verified every target; "
                "receipts are persistent and target ownership is released; nothing further to roll back"
            )
        if status in (PARTIAL, FAILED):
            unresolved = [t["source_path"] for t in record["targets"] if t["status"] not in (T_RESTORED, T_NOOP)]
            return (
                f"rollback stopped ({status}); verified receipts exist only for restored targets; "
                f"unresolved: {unresolved}; inspect/reconcile them, then apply again or close the "
                "rollback to release its ownership"
            )
        return "rollback is closed; its ownership is released; start a new reconciliation if needed"

    # --- authority ------------------------------------------------------------------------

    def _authority(self, task_id: str, microtask_id: str, operation_id: str, resolution_id: str):
        try:
            resolution = self.resolver.store.find(task_id, resolution_id)
            accepted = [
                item
                for item in self.resolver.store.list(task_id, operation_id=operation_id)
                if item.result is ResolutionResult.ACCEPTED
            ]
        except ResolutionStoreError as exc:
            raise RollbackError(str(exc)) from exc
        if resolution is None:
            return None, None, ("NO_ROLLBACK_RESOLUTION", "no persistent resolution with this id")
        if (resolution.task_id, resolution.microtask_id, resolution.operation_id) != (
            task_id, microtask_id, operation_id,
        ):
            return None, None, ("RESOLUTION_MISMATCH", "resolution belongs to another task/microtask/operation")
        if resolution.action is not ResolutionAction.ROLLBACK:
            return None, None, ("NOT_A_ROLLBACK", f"resolution is {resolution.action.value}")
        if resolution.result is not ResolutionResult.ACCEPTED:
            return None, None, ("ROLLBACK_NOT_ACCEPTED", f"resolution is {resolution.result.value}")
        if any(item.action is ResolutionAction.ABORT for item in accepted):
            return None, None, ("RECOVERY_ABORTED", "recovery of this operation was aborted")
        try:
            record = self.operations.get(task_id, operation_id)
        except OperationStoreError as exc:
            raise RollbackError(f"operation state unavailable: {exc}") from exc
        if record.contract_version == LEGACY_CONTRACT_VERSION:
            return None, None, ("LEGACY_CONTRACT", "legacy contract v1 cannot own rollback targets")
        return resolution, record, None

    def _fresh(self, resolution) -> tuple[str, str] | None:
        freshness = self.resolver.freshness(resolution)
        if not freshness["fresh"]:
            return "STALE_RESOLUTION", f"ROLLBACK resolution is stale ({freshness['code']})"
        return None

    # --- prepare -------------------------------------------------------------------------------

    def prepare(
        self,
        task_id: str,
        microtask_id: str,
        operation_id: str,
        resolution_id: str,
        *,
        agent: str | None = None,
        channel: str | None = None,
    ) -> dict[str, Any]:
        for name, value in (("task_id", task_id), ("microtask_id", microtask_id),
                            ("operation_id", operation_id), ("resolution_id", resolution_id)):
            if not isinstance(value, str) or not value.strip():
                raise RollbackInputError(f"{name} must be a non-empty string")
        for name, value in (("agent", agent), ("channel", channel)):
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise RollbackInputError(f"{name} must be a non-empty string when provided")
        rollback_id = rollback_identity(task_id, resolution_id)
        with self.operations.task_lock(task_id):
            try:
                record = self.store.find(task_id, rollback_id)
            except RollbackStoreError as exc:
                raise RollbackError(str(exc)) from exc
            if record is not None:
                if (record["microtask_id"], record["operation_id"]) != (microtask_id, operation_id):
                    raise RollbackError("rollback_id already exists for another microtask/operation")
                if record["status"] != PREPARED:
                    return self._outcome("REPLAYED", "KNOWN_SESSION", "rollback session already exists", record)
                root = self._workspace_root(task_id)
                try:
                    op_record = self.operations.get(task_id, operation_id)
                except OperationStoreError as exc:
                    raise RollbackError(f"operation state unavailable: {exc}") from exc
            else:
                resolution, op_record, refusal = self._authority(task_id, microtask_id, operation_id, resolution_id)
                plan = None
                if refusal is None:  # restore point first: a corrupt snapshot also ages the evidence
                    try:
                        plan = self.manifests.restore_plan(task_id, microtask_id)
                    except ManifestStoreError as exc:
                        refusal = ("RESTORE_POINT_INVALID", str(exc))
                if refusal is None:
                    refusal = self._fresh(resolution)
                root = self._workspace_root(task_id)
                targets: list[dict[str, Any]] = []
                if refusal is None:
                    for item in plan["items"]:
                        try:
                            canonical = canonical_target(root, item["source_path"])
                        except TargetIdentityError as exc:
                            refusal = ("TARGET_IDENTITY_INVALID", str(exc))
                            break
                        targets.append(
                            {
                                "manifest_entry_id": item["manifest_entry_id"],
                                "snapshot_id": item["snapshot_id"],
                                "source_path": item["source_path"],
                                "target": canonical.relative,
                                "target_key": canonical.key,
                                "target_hash": target_hash(physical_target_key(canonical.path)),
                                "expected_restore": {
                                    "exists": item["exists_before"],
                                    "size": item["size_before"],
                                    "sha256": item["sha256_before"],
                                },
                                "preserved": None,
                                "planned_action": None,
                                "claim_id": None,
                                "status": T_PENDING,
                                "receipt": None,
                                "failure": None,
                            }
                        )
                    if refusal is None and len({t["target_hash"] for t in targets}) != len(targets):
                        refusal = ("TARGET_IDENTITY_INVALID", "two manifest entries name one physical target")
                if refusal is not None:
                    self.events.append_event(
                        task_id, "ROLLBACK_REJECTED", microtask_id=microtask_id, operation_id=operation_id,
                        payload={"resolution_id": resolution_id, "result_code": refusal[0]},
                    )
                    return self._outcome(REJECTED, refusal[0], refusal[1], None)
                now = utc_now_iso()
                record = {
                    "rollback_version": 1,
                    "schema_version": 1,
                    "rollback_id": rollback_id,
                    "task_id": task_id,
                    "microtask_id": microtask_id,
                    "operation_id": operation_id,
                    "resolution_id": resolution_id,
                    "basis": {
                        "evidence_fingerprint": resolution.basis["evidence_fingerprint"],
                        "operation_revision": op_record.revision,
                        "operation_request_fingerprint": op_record.request_fingerprint,
                        "manifest_id": plan["manifest_id"],
                        "restore_point_fingerprint": plan["restore_point_fingerprint"],
                    },
                    "status": PREPARED,
                    "revision": 0,
                    "created_at": now,
                    "updated_at": now,
                    "provenance": {
                        "agent": agent.strip() if agent else None,
                        "channel": channel.strip() if channel else None,
                        "authority": "claimed",
                    },
                    "targets": sorted(targets, key=lambda t: t["target_hash"]),
                    "last_attempt": None,
                    "result": None,
                    "claims_released": False,
                    "next_safe_action": "-",
                }
                self._persist(record)
                self._event(record, "ROLLBACK_PREPARED", {"resolution_id": resolution_id, "targets": len(targets)})

            # preserve every target's current physical state before anything destructive
            for target in record["targets"]:
                if target["status"] != T_PENDING:
                    continue
                failure = self._preserve(task_id, root, op_record, target)
                if failure is not None:
                    target["failure"] = {"code": failure[0], "reason": failure[1], "observed": None}
                    record["status"] = PRESERVATION_FAILED
                    record["result"] = {"overall": "NOT_STARTED", "code": failure[0], "at": utc_now_iso()}
                    self._persist(record)
                    self._event(record, "ROLLBACK_PRESERVATION_FAILED",
                                {"target": target["source_path"], "result_code": failure[0]})
                    return self._outcome(PRESERVATION_FAILED, failure[0], failure[1], record)
                self._persist(record)
            record["status"] = PRESERVED
            self._persist(record)
            self._event(record, "ROLLBACK_PRESERVED", {
                "targets": [{"target": t["source_path"], "preserved": _state(t["preserved"]),
                             "planned_action": t["planned_action"]} for t in record["targets"]],
            })
            return self._outcome(PRESERVED, "CURRENT_STATE_PRESERVED", "every target's current state is preserved", record)

    def _preserve(self, task_id: str, root: Path, op_record, target: dict[str, Any]) -> tuple[str, str] | None:
        try:
            canonical = self._canonical(root, target)
        except TargetIdentityError as exc:
            return "TARGET_IDENTITY_INVALID", str(exc)
        pattern = secret_pattern_for(canonical.relative)
        contract = op_record.contract or {}
        if pattern is not None and not (
            canonical.key == contract.get("target_key") and contract.get("policy", {}).get("secret_override")
        ):
            return "PRESERVATION_SECRET_SCOPE", f"target matches secret deny-list pattern {pattern!r}"
        try:
            observed = observe_path(canonical.path)
            blob = None
            if observed.exists:
                data = canonical.path.read_bytes()
                if len(data) != observed.size or hashlib.sha256(data).hexdigest() != observed.sha256:
                    return "PRESERVATION_UNSTABLE", "target changed while it was being preserved"
                blob = self.preserved.put(task_id, data, forbidden_roots=[root])
                if not same_authority(observe_path(canonical.path), observed):
                    return "PRESERVATION_UNSTABLE", "target changed while it was being preserved"
        except FileStateError as exc:
            return "PRESERVATION_UNOBSERVABLE", str(exc)
        except OSError as exc:
            return "PRESERVATION_UNREADABLE", str(exc)
        except PayloadScopeError as exc:
            return "PRESERVATION_SCOPE", str(exc)
        except (PayloadIntegrityError, PayloadStoreError) as exc:
            return "PRESERVATION_INTEGRITY", str(exc)
        preserved = _state(observed)
        target["preserved"] = dict(preserved, blob=blob, preserved_at=utc_now_iso())
        if same_authority(preserved, target["expected_restore"]):
            target["planned_action"] = NOOP
        elif target["expected_restore"]["exists"]:
            target["planned_action"] = WRITE_RESTORE
        else:
            target["planned_action"] = DELETE_CREATED
        target["status"] = T_PRESERVED
        return None

    # --- apply ------------------------------------------------------------------------------------

    def _session_basis(self, record: dict[str, Any], plan: dict[str, Any] | None) -> tuple[str, str] | None:
        """Re-prove the session basis; the full fingerprint only before own effects."""
        resolution, op_record, refusal = self._authority(
            record["task_id"], record["microtask_id"], record["operation_id"], record["resolution_id"]
        )
        if refusal is not None:
            return refusal
        basis = record["basis"]
        if op_record.revision != basis["operation_revision"]:
            return "OPERATION_REVISION_CHANGED", f"operation is at revision {op_record.revision}"
        if op_record.request_fingerprint != basis["operation_request_fingerprint"]:
            return "OPERATION_IDENTITY_CHANGED", "operation request fingerprint changed"
        if plan is None or plan["restore_point_fingerprint"] != basis["restore_point_fingerprint"]:
            return "RESTORE_POINT_CHANGED", "restore point differs from the rollback basis"
        touched = any(t["status"] in (T_RESTORED, T_APPLYING, T_FAILED) for t in record["targets"])
        if not touched:
            # name a physical drift precisely before the generic stale fingerprint
            for target in record["targets"]:
                try:
                    observed = observe_path(self._canonical(self._workspace_root(record["task_id"]), target).path)
                except (TargetIdentityError, FileStateError) as exc:
                    return "TARGET_UNOBSERVABLE", str(exc)
                if not same_authority(observed, target["preserved"]):
                    return "STATE_DRIFT", f"{target['source_path']} changed after preservation; nothing restored"
            return self._fresh(resolution)
        return None

    def _attempt(self, record: dict[str, Any], code: str, reason: str, **extra: Any) -> dict[str, Any]:
        record["last_attempt"] = dict({"code": code, "reason": reason, "at": utc_now_iso()}, **extra)
        self._persist(record)
        self._event(record, "ROLLBACK_BLOCKED", {"result_code": code})
        return self._outcome(BLOCKED, code, reason, record)

    def _new_claim(self, data: dict[str, Any], record: dict[str, Any], target: dict[str, Any], op_record, now: str) -> dict[str, Any]:
        generation = data["next_generation"]
        return {
            "claim_id": claim_identity(data["target_hash"], generation, record["task_id"],
                                       record["operation_id"], record["basis"]["operation_revision"]),
            "generation": generation,
            "task_id": record["task_id"],
            "microtask_id": record["microtask_id"],
            "operation_id": record["operation_id"],
            "workspace_id": op_record.contract["workspace_id"],
            "target": target["target"],
            "target_key": target["target_key"],
            "operation_revision": record["basis"]["operation_revision"],
            "operation_request_fingerprint": record["basis"]["operation_request_fingerprint"],
            "contract_version": op_record.contract_version,
            "cas_basis": _state(target["preserved"]),
            "status": ACTIVE,
            "created_at": now,
            "provenance": dict(record["provenance"]),
            "ended_at": None,
            "end_reason": None,
            "ended_by": None,
            "superseded_by": None,
            "authorizations": [],
            "owner": {"kind": ROLLBACK_OWNER, "rollback_id": record["rollback_id"]},
        }

    def _acquire_all(self, record: dict[str, Any], root: Path, mutating: list[dict[str, Any]]) -> dict[str, Any] | None:
        """All-or-nothing RC-3 ownership; caller holds every target lock."""
        op_record = self.operations.get(record["task_id"], record["operation_id"])
        files: dict[str, tuple[dict[str, Any], Any]] = {}
        blocking = []
        for target in mutating:
            canonical = self._canonical(root, target)
            physical_key = physical_target_key(canonical.path)
            data = self.claims.load(physical_key)
            active = data["active"]
            if active is not None:
                ours = (active.get("owner") or {}).get("rollback_id") == record["rollback_id"]
                source_owned = (
                    active.get("owner") is None
                    and active["task_id"] == record["task_id"]
                    and active["operation_id"] == record["operation_id"]
                )
                if not ours and not source_owned:
                    blocking.append(dict(target=target["source_path"], claim_id=active["claim_id"],
                                         task_id=active["task_id"], operation_id=active["operation_id"],
                                         owner=active.get("owner")))
            observed = observe_path(canonical.path)
            if not same_authority(observed, target["preserved"]):
                return self._attempt(record, "STATE_DRIFT",
                                     f"{target['source_path']} changed after preservation; nothing restored",
                                     observed=_state(observed))
            files[target["target_hash"]] = (data, canonical)
        if blocking:
            return self._attempt(record, "TARGET_CONFLICT", "another owner holds a rollback target; nothing restored",
                                 blocking_owners=blocking)
        now = utc_now_iso()
        for target in mutating:
            data, _ = files[target["target_hash"]]
            active = data["active"]
            if active is not None and (active.get("owner") or {}).get("rollback_id") == record["rollback_id"]:
                target["claim_id"] = active["claim_id"]
                continue
            claim = self._new_claim(data, record, target, op_record, now)
            if active is not None:  # the source operation's own claim is taken over, never left behind
                active.update(status=SUPERSEDED, ended_at=now, end_reason="SUPERSEDED_BY_ROLLBACK",
                              ended_by=dict(record["provenance"]), superseded_by=claim["claim_id"])
                data["history"].append(active)
            data["active"] = claim
            data["next_generation"] += 1
            self.claims.write(data)
            target["claim_id"] = claim["claim_id"]
        record["status"] = AUTHORIZED
        record["last_attempt"] = None
        self._persist(record)
        self._event(record, "ROLLBACK_AUTHORIZED", {"claims": [t["claim_id"] for t in mutating]})
        return None

    def _claim_held(self, root: Path, record: dict[str, Any], target: dict[str, Any]) -> bool:
        data = self.claims.load(physical_target_key(self._canonical(root, target).path))
        active = data["active"]
        return (
            active is not None
            and active["claim_id"] == target["claim_id"]
            and (active.get("owner") or {}).get("rollback_id") == record["rollback_id"]
        )

    def _release_claims(self, root: Path, record: dict[str, Any], reason: str) -> None:
        now = utc_now_iso()
        for target in record["targets"]:
            if target["claim_id"] is None:
                continue
            data = self.claims.load(physical_target_key(self._canonical(root, target).path))
            active = data["active"]
            if active is not None and active["claim_id"] == target["claim_id"]:
                active.update(status=RELEASED, ended_at=now, end_reason=reason, ended_by=dict(record["provenance"]))
                data["history"].append(active)
                data["active"] = None
                self.claims.write(data)
        record["claims_released"] = True

    def _receipt(self, record, target, action, observed, *, recovered: bool) -> dict[str, Any]:
        return {
            "rollback_id": record["rollback_id"],
            "target": target["source_path"],
            "target_key": target["target_key"],
            "target_hash": target["target_hash"],
            "action": action,
            "preserved": _state(target["preserved"]),
            "expected_restore": dict(target["expected_restore"]),
            "observed_post": _state(observed),
            "matches_expected_restore": same_authority(observed, target["expected_restore"]),
            "recovered_after_interruption": recovered,
            "operation_revision": record["basis"]["operation_revision"],
            "evidence_fingerprint": record["basis"]["evidence_fingerprint"],
            "restore_point_fingerprint": record["basis"]["restore_point_fingerprint"],
            "at": utc_now_iso(),
        }

    def _stop(self, record: dict[str, Any], target: dict[str, Any], status: str, code: str, reason: str, observed) -> None:
        target["status"] = status
        target["failure"] = {"code": code, "reason": reason, "observed": _state(observed) if observed is not None else None}
        self._persist(record)
        self._event(record, f"ROLLBACK_TARGET_{status}", {"target": target["source_path"], "result_code": code})

    def apply(self, task_id: str, rollback_id: str) -> dict[str, Any]:
        with self.operations.task_lock(task_id):
            try:
                record = self.store.get(task_id, rollback_id)
            except RollbackStoreError as exc:
                raise RollbackError(str(exc)) from exc
            if record["status"] in _DONE:
                return self._outcome("REPLAYED", f"ROLLBACK_{record['status']}", "known final rollback state", record)
            if record["status"] == PREPARED:
                return self._outcome(REJECTED, "PRESERVATION_INCOMPLETE", "run prepare first", record)
            root = self._workspace_root(task_id)
            try:
                plan = self.manifests.restore_plan(task_id, record["microtask_id"])
            except ManifestStoreError as exc:
                return self._attempt(record, "RESTORE_POINT_INVALID", str(exc))
            snapshots = {item["manifest_entry_id"]: item["snapshot_bytes"] for item in plan["items"]}
            mutating = [t for t in record["targets"] if t["planned_action"] != NOOP]
            with ExitStack() as stack:
                for digest in sorted(t["target_hash"] for t in mutating):
                    lock = InterProcessLock(self.claims.locks / f"{digest}.lock", timeout=self.lock_timeout)
                    try:
                        lock.acquire()
                    except StoreLockTimeout as exc:
                        raise RollbackError(str(exc)) from exc
                    stack.callback(lock.release)
                return self._apply_locked(record, root, plan, snapshots, mutating)

    def _apply_locked(self, record, root, plan, snapshots, mutating) -> dict[str, Any]:
        # 1. interrupted writes: prove the real bytes, never repeat blindly
        for target in record["targets"]:
            if target["status"] != T_APPLYING:
                continue
            try:
                observed = observe_path(self._canonical(root, target).path)
            except (TargetIdentityError, FileStateError) as exc:
                self._stop(record, target, T_DRIFTED, "UNKNOWN_AFTER_INTERRUPTION", str(exc), None)
                continue
            if same_authority(observed, target["expected_restore"]):
                target["status"] = T_RESTORED
                target["receipt"] = self._receipt(record, target, target["planned_action"], observed, recovered=True)
                self._persist(record)
                self._event(record, "ROLLBACK_TARGET_RESTORED", {"target": target["source_path"], "recovered": True})
            elif same_authority(observed, target["preserved"]):
                target["status"] = T_PRESERVED  # the write never landed: safe to apply under CAS
                self._persist(record)
            else:
                self._stop(record, target, T_DRIFTED, "UNKNOWN_AFTER_INTERRUPTION",
                           "bytes match neither the restore state nor the preserved state", observed)
        if any(t["status"] in (T_DRIFTED, T_FAILED) for t in record["targets"]):
            return self._finalize(record, root)

        # 2. re-prove the basis (full freshness before own effects)
        refusal = self._session_basis(record, plan)
        if refusal is not None:
            return self._attempt(record, *refusal)

        # 3. ownership: all-or-nothing before the first destructive step
        try:
            if record["status"] == PRESERVED:
                blocked = self._acquire_all(record, root, mutating)
                if blocked is not None:
                    return blocked
            else:
                lost = [t["source_path"] for t in mutating
                        if t["status"] not in (T_RESTORED,) and not self._claim_held(root, record, t)]
                if lost:
                    return self._attempt(record, "CLAIM_LOST", f"rollback no longer owns {lost}")
        except (TargetIdentityError, TargetClaimStoreError, FileStateError) as exc:
            return self._attempt(record, "OWNERSHIP_UNAVAILABLE", str(exc))

        # 4. per-target CAS -> restore -> post-verify -> receipt
        for target in record["targets"]:
            if target["status"] in (T_RESTORED, T_NOOP):
                continue
            try:
                canonical = self._canonical(root, target)
                observed = observe_path(canonical.path)
            except (TargetIdentityError, FileStateError) as exc:
                self._stop(record, target, T_DRIFTED, "TARGET_UNOBSERVABLE", str(exc), None)
                break
            if target["planned_action"] == NOOP:
                if not same_authority(observed, target["expected_restore"]):
                    self._stop(record, target, T_DRIFTED, "STATE_DRIFT", "pre-state target changed", observed)
                    break
                target["status"] = T_NOOP
                target["receipt"] = self._receipt(record, target, NOOP, observed, recovered=False)
                self._persist(record)
                continue
            if not self._claim_held(root, record, target):
                self._stop(record, target, T_DRIFTED, "CLAIM_LOST", "rollback no longer owns this target", observed)
                break
            if not same_authority(observed, target["preserved"]):
                self._stop(record, target, T_DRIFTED, "STATE_DRIFT",
                           "target changed after preservation; not overwritten", observed)
                break
            target["status"] = T_APPLYING
            record["status"] = APPLYING
            self._persist(record)
            try:
                if target["planned_action"] == WRITE_RESTORE:
                    _write_restored_bytes(canonical.path, snapshots[target["manifest_entry_id"]])
                else:
                    _delete_created(canonical.path)
                post = observe_path(canonical.path)
            except (OSError, ManifestStoreError, FileStateError) as exc:
                try:
                    post = observe_path(canonical.path)
                except FileStateError:
                    post = None
                self._stop(record, target, T_FAILED, "RESTORE_IO_ERROR", str(exc), post)
                break
            receipt = self._receipt(record, target, target["planned_action"], post, recovered=False)
            target["receipt"] = receipt
            if receipt["matches_expected_restore"]:
                target["status"] = T_RESTORED
                self._persist(record)
                self._event(record, "ROLLBACK_TARGET_RESTORED", {
                    "target": target["source_path"], "action": receipt["action"],
                    "observed_post": receipt["observed_post"],
                })
            else:
                self._stop(record, target, T_FAILED, "POST_VERIFY_MISMATCH",
                           "post-restore bytes differ from the restore state", post)
                break
        return self._finalize(record, root)

    def _finalize(self, record: dict[str, Any], root: Path) -> dict[str, Any]:
        targets = record["targets"]
        done = [t for t in targets if t["status"] in (T_RESTORED, T_NOOP)]
        restored = [t["source_path"] for t in targets if t["status"] == T_RESTORED]
        unresolved = [t["source_path"] for t in targets if t["status"] not in (T_RESTORED, T_NOOP)]
        if len(done) == len(targets):
            record["status"] = VERIFIED
            overall = "SUCCESS"
            self._release_claims(root, record, "ROLLBACK_VERIFIED")
        elif restored:
            record["status"] = PARTIAL
            overall = "PARTIAL"
        else:
            record["status"] = FAILED
            overall = "FAILED"
        record["result"] = {
            "overall": overall,
            "restored": restored,
            "noop": [t["source_path"] for t in targets if t["status"] == T_NOOP],
            "unresolved": unresolved,
            "at": utc_now_iso(),
        }
        self._persist(record)
        self._event(record, f"ROLLBACK_{record['status']}", {"restored": restored, "unresolved": unresolved})
        result = "VERIFIED" if overall == "SUCCESS" else overall
        return self._outcome(result, f"ROLLBACK_{overall}", "rollback result is persistent", record)

    # --- close / read ---------------------------------------------------------------------------------

    def close(self, task_id: str, rollback_id: str, *, reason: str | None = None) -> dict[str, Any]:
        """Release a non-verified session's ownership once no target fate is open."""
        with self.operations.task_lock(task_id):
            try:
                record = self.store.get(task_id, rollback_id)
            except RollbackStoreError as exc:
                raise RollbackError(str(exc)) from exc
            if record["status"] in (CLOSED, VERIFIED, PRESERVATION_FAILED):
                return self._outcome("REPLAYED", f"ROLLBACK_{record['status']}", "nothing to close", record)
            if record["status"] == APPLYING or any(t["status"] == T_APPLYING for t in record["targets"]):
                return self._outcome(REJECTED, "TARGET_FATE_UNKNOWN",
                                     "apply again first so in-flight targets are proven", record)
            root = self._workspace_root(task_id)
            digests = sorted(t["target_hash"] for t in record["targets"] if t["claim_id"])
            with ExitStack() as stack:
                for digest in digests:
                    lock = InterProcessLock(self.claims.locks / f"{digest}.lock", timeout=self.lock_timeout)
                    try:
                        lock.acquire()
                    except StoreLockTimeout as exc:
                        raise RollbackError(str(exc)) from exc
                    stack.callback(lock.release)
                try:
                    self._release_claims(root, record, (reason or "ROLLBACK_CLOSED").strip())
                except (TargetIdentityError, TargetClaimStoreError) as exc:
                    raise RollbackError(f"cannot release rollback ownership: {exc}") from exc
            record["status"] = CLOSED
            self._persist(record)
            self._event(record, "ROLLBACK_CLOSED", {"reason": reason})
            return self._outcome(CLOSED, "ROLLBACK_CLOSED", "rollback ownership released", record)

    def inspect(self, task_id: str, rollback_id: str) -> dict[str, Any]:
        try:
            return self.store.get(task_id, rollback_id)
        except RollbackStoreError as exc:
            raise RollbackError(str(exc)) from exc

    def report_facts(self, task_id: str, microtask_id: str, operation_id: str) -> dict[str, Any]:
        """Rollback facts for Recovery Report, only from persisted verified receipts."""
        try:
            sessions = [
                item for item in self.store.list(task_id, operation_id=operation_id)
                if item["microtask_id"] == microtask_id
            ]
        except RollbackStoreError as exc:
            raise RollbackError(str(exc)) from exc
        rolled_back: list[str] = []
        receipts = []
        by_resolution = {}
        for session in sessions:
            restored = [
                t["source_path"] for t in session["targets"]
                if t["status"] == T_RESTORED and t["receipt"] and t["receipt"]["matches_expected_restore"]
            ]
            rolled_back.extend(path for path in restored if path not in rolled_back)
            receipts.append({
                "rollback_id": session["rollback_id"],
                "resolution_id": session["resolution_id"],
                "status": session["status"],
                "overall": (session["result"] or {}).get("overall"),
                "restored": restored,
                "noop": [t["source_path"] for t in session["targets"] if t["status"] == T_NOOP],
                "unresolved": [t["source_path"] for t in session["targets"] if t["status"] not in (T_RESTORED, T_NOOP)],
                "claims_released": session["claims_released"],
                "physical_mutation_performed": bool(restored),
            })
            by_resolution[session["resolution_id"]] = session["next_safe_action"]
        return {
            "actually_rolled_back": rolled_back,
            "rollback_receipts": receipts,
            "next_safe_action_by_resolution": by_resolution,
        }
