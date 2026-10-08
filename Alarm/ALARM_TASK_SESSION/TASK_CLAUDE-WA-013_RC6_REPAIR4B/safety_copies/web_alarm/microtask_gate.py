"""RC-6 Repair #3: one authoritative microtask lifecycle/recovery gate.

Pure settlement-disposition rules (moved here from ``projection`` unchanged, so
RC-3 can share them without importing the projection) plus the two gates every
lifecycle-sensitive decision uses:

- ``execution_refusal``: may an operation of this microtask hold mutation
  authority now? Shared by RC-3 ``mutation_boundary`` and the RC-6 READY
  proofs, so "READY_FOR_EXECUTION" and "AUTHORIZED" follow one rule.
- ``verification_refusal``: may this microtask become VERIFIED now? Used by
  the server state machine under the operation TASK lock + mutation lock, so
  verification and recovery decisions of the same microtask are serialized.

Semantics (F-B): VERIFIED is the terminal disposition of a microtask. A
verification is admitted only while none of its operations has an open
recovery; a non-destructive recovery settlement (ADOPT, ABORT) decided after
it is administrative and leaves the microtask VERIFIED, while a ROLLBACK of a
VERIFIED stage is never absorbed (R1 keeps it at an explicit decision).
"""

from __future__ import annotations

from typing import Any, Iterable

from .models import MicrotaskStatus, OperationStatus
from .operation_store import OperationStore, OperationStoreError
from .resolution_store import ResolutionStoreError
from .resolver_service import ResolverError, ResolverService
from .rollback_store import CLOSED, PRESERVATION_FAILED, VERIFIED, RollbackStore, RollbackStoreError
from .task_store import TaskStore, TaskStoreError

# normal physical mutation is allowed only for an operation of an ACTIVE microtask
EXECUTION_STATUS = MicrotaskStatus.ACTIVE

_OPEN_FATE = {OperationStatus.STARTED.value, OperationStatus.UNKNOWN_AFTER_DISCONNECT.value}
_DESTRUCTIVE = ("ABORT", "ROLLBACK")
# projection blockers / diagnostics that make the recovery facts unprovable
_FACTS_UNREADABLE = {
    "MICROTASKS_UNREADABLE",
    "OPERATIONS_UNREADABLE",
    "RESOLUTIONS_UNREADABLE",
    "ROLLBACKS_UNREADABLE",
    "RESOLVER_FACTS_UNAVAILABLE",
    "CLAIMS_UNREADABLE",
}


# Repair #4A: lifecycle statuses of a microtask that has never been ACTIVE (the
# state machine reaches them only before the first ACTIVE): none of its
# operations can have had mutation authority (execution_refusal)
PRE_EXECUTION_STATUSES = frozenset({
    MicrotaskStatus.PLANNED.value,
    MicrotaskStatus.PREPARING.value,
    MicrotaskStatus.BACKUP_VERIFIED.value,
    MicrotaskStatus.READY.value,
    MicrotaskStatus.BLOCKED_PREPARE.value,
})


def pre_execution_next_action(operation_id: str, microtask_id: str, microtask_status: str, action: str) -> str:
    """Manual boundary of an accepted ADOPT / ROLLBACK / RETRY whose microtask never executed.

    It cannot be completed now (no DONE without execution, no rollback of a
    stage that never ran, no re-arm before activation) but stays completable:
    activate the microtask normally, or close the operation with ABORT (which
    RC-6 settles to RECOVERY_REQUIRED).
    """
    return (
        f"accepted {action} of operation {operation_id} cannot be completed while its microtask "
        f"{microtask_id} is {microtask_status}: the microtask has never been ACTIVE, so no operation of it "
        "can have had a server-authorized effect. Either activate the microtask through the state machine "
        f"(then recover completes the accepted {action}) or record ABORT for the operation (settled to the "
        "RECOVERY_REQUIRED boundary)"
    )


def settlement_lifecycle_target(actions: Iterable[str]) -> MicrotaskStatus | None:
    """RC-6 Repair #2 (R2): one recovery disposition per microtask.

    The recovery settlements of *all* operations of a microtask are aggregated
    instead of each one steering the shared microtask status on its own. An
    ABORT or ROLLBACK settlement means part of the microtask's work was not (or
    no longer is) carried out as planned: the microtask belongs at the manual
    RECOVERY_REQUIRED boundary. ADOPT alone means the effect is accepted: DONE
    (VERIFIED once normally verified). The conservative disposition wins
    regardless of order, so two settlements never ask for opposite statuses
    and an ADOPT never lifts a microtask out of the RECOVERY_REQUIRED boundary
    that another operation's ABORT/ROLLBACK put it at.
    """
    actions = list(actions)
    if any(action in _DESTRUCTIVE for action in actions):
        return MicrotaskStatus.RECOVERY_REQUIRED
    if actions:
        return MicrotaskStatus.DONE
    return None


def authoritative_action(facts: dict[str, Any] | None) -> dict[str, Any] | None:
    """The Resolver's authoritative entry of ``report_facts`` plus its action and authority."""
    if facts is None or facts.get("next_safe_action") is None:
        return None
    authoritative = facts["next_safe_action"]
    entry = next(
        (a for a in facts["resolver_actions"] if a["resolution_id"] == authoritative["resolution_id"]),
        None,
    )
    return dict(
        authoritative,
        action=entry["action"] if entry is not None else None,
        authority=bool(entry is not None and entry["authority"]),
    )


def late_abort(settlement: dict[str, Any] | None, authoritative: dict[str, Any] | None) -> bool:
    """Repair #3 (F-B): an accepted ABORT decided after the operation was already settled.

    The settlement stays the operation's immutable record; the ABORT is the
    operation's current authority and counts for the microtask disposition.
    """
    return bool(
        settlement
        and authoritative is not None
        and authoritative["resolution_id"] != settlement["resolution_id"]
        and authoritative.get("action") == "ABORT"
        and authoritative.get("authority")
    )


def current_settlements_by_microtask(pairs) -> dict[str, list[str]]:
    """Settlement actions per microtask that still speak for their operation.

    ``pairs`` yields (operation record, Resolver authoritative action or None).
    A settlement counts while its own resolution is still the operation's
    authority; a newer authoritative action of that operation (e.g. a fresh
    RETRY after a verified rollback) supersedes it for the disposition, except
    that a later accepted ABORT (``late_abort``; the authoritative entry must
    come from ``authoritative_action``) counts as an ABORT disposition.
    """
    result: dict[str, list[str]] = {}
    for op, authoritative in pairs:
        settlement = op.recovery_settlement
        if not settlement:
            continue
        if authoritative is not None and authoritative["resolution_id"] != settlement["resolution_id"]:
            if late_abort(settlement, authoritative):
                result.setdefault(op.microtask_id, []).append("ABORT")
            continue
        result.setdefault(op.microtask_id, []).append(settlement["action"])
    return result


def settlement_lifecycle_satisfied(target: MicrotaskStatus, status: str) -> bool:
    """Is the microtask already at the disposition its settlements require?"""
    if target is MicrotaskStatus.DONE:
        return status in (MicrotaskStatus.DONE.value, MicrotaskStatus.VERIFIED.value)
    return status == target.value


def verified_absorbs(actions: Iterable[str]) -> bool:
    """Repair #3 (F-B): VERIFIED is the terminal disposition of non-destructive settlements.

    ADOPT and ABORT change nothing physically; with ``execution_refusal`` no
    operation of a non-ACTIVE microtask can get mutation authority, so nothing
    an operation of a VERIFIED microtask does can change the verified stage
    any more. A ROLLBACK physically undid work: never absorbed.
    """
    return not any(action == "ROLLBACK" for action in actions)


def effective_settlement_target(actions: Iterable[str], microtask_status: MicrotaskStatus | str) -> MicrotaskStatus | None:
    """The lifecycle a microtask's settlements require, given its current status."""
    actions = list(actions)
    target = settlement_lifecycle_target(actions)
    status = MicrotaskStatus(microtask_status)
    if target is not None and status is MicrotaskStatus.VERIFIED and verified_absorbs(actions):
        return MicrotaskStatus.VERIFIED
    return target


def _rollback_settled(session: dict[str, Any]) -> bool:
    return session["status"] in (CLOSED, PRESERVATION_FAILED) or (
        session["status"] == VERIFIED and session["claims_released"]
    )


def disposition_actions(
    task_id: str,
    microtask_id: str,
    *,
    operations: OperationStore,
    resolver: ResolverService,
    rollbacks: RollbackStore,
) -> list[str]:
    """Every recovery action that speaks for this microtask's operations now.

    Settled or not: a current settlement (same rule as the projection), an
    authoritative accepted ABORT/ROLLBACK that RC-6 has not settled yet, and an
    open tracked RC-4 rollback session (it can still restore the stage).
    """
    actions: list[str] = []
    for op in operations.list(task_id):
        if op.microtask_id != microtask_id:
            continue
        facts = None
        if resolver.store.list(task_id, operation_id=op.operation_id):
            facts = resolver.report_facts(task_id, microtask_id, op.operation_id)
        authoritative = facts["next_safe_action"] if facts is not None else None
        settlement = op.recovery_settlement
        if settlement and (authoritative is None or authoritative["resolution_id"] == settlement["resolution_id"]):
            actions.append(settlement["action"])
        elif authoritative is not None:
            entry = next(
                (a for a in facts["resolver_actions"] if a["resolution_id"] == authoritative["resolution_id"]),
                None,
            )
            if entry is not None and entry["authority"] and entry["action"] in _DESTRUCTIVE:
                actions.append(entry["action"])
        if any(not _rollback_settled(s) for s in rollbacks.list(task_id, operation_id=op.operation_id)):
            actions.append("ROLLBACK")
    return actions


def execution_refusal(
    task_id: str,
    microtask_id: str,
    *,
    tasks: TaskStore,
    operations: OperationStore,
    resolver: ResolverService,
    rollbacks: RollbackStore,
) -> tuple[str, str] | None:
    """F-C: why no operation of this microtask may hold mutation authority now, or None.

    Normal physical mutation needs an ACTIVE, lifecycle-current microtask (every
    earlier microtask VERIFIED) whose operations carry no ABORT/ROLLBACK
    recovery disposition (settled, accepted or in an open RC-4 session).
    Unreadable facts refuse (fail-closed). The caller holds the
    operation TASK lock and the mutation lock, so the answer stays true for as
    long as it keeps them.
    """
    try:
        micro = tasks.open_microtask(task_id, microtask_id)
        if micro.status is not EXECUTION_STATUS:
            return (
                "MICROTASK_NOT_ACTIVE",
                f"microtask {microtask_id} is {micro.status.value}; normal physical mutation is allowed "
                "only while the microtask is ACTIVE",
            )
        plan = tasks.list_microtasks(task_id)
        if microtask_id not in [m.microtask_id for m in plan]:
            return "MICROTASK_NOT_CURRENT", f"microtask {microtask_id} is not part of the TASK plan"
        for earlier in plan:
            if earlier.microtask_id == microtask_id:
                break
            if earlier.status is not MicrotaskStatus.VERIFIED:
                return (
                    "MICROTASK_NOT_CURRENT",
                    f"microtask {microtask_id} is ACTIVE, but the earlier microtask {earlier.microtask_id} "
                    f"is {earlier.status.value}: only the lifecycle-current stage may be mutated",
                )
        actions = disposition_actions(
            task_id, microtask_id, operations=operations, resolver=resolver, rollbacks=rollbacks
        )
    except (TaskStoreError, OperationStoreError, ResolverError, ResolutionStoreError, RollbackStoreError) as exc:
        return "LIFECYCLE_STATE_UNAVAILABLE", f"microtask lifecycle/recovery facts are unreadable: {exc}"
    if settlement_lifecycle_target(actions) is MicrotaskStatus.RECOVERY_REQUIRED:
        found = ", ".join(sorted(set(a for a in actions if a in _DESTRUCTIVE)))
        return (
            "MICROTASK_RECOVERY_REQUIRED",
            f"microtask {microtask_id} carries an {found} recovery disposition: normal mutation is "
            "forbidden until an explicit lifecycle/recovery decision",
        )
    return None


def verification_refusal(projection: dict[str, Any], microtask_id: str) -> tuple[str, str] | None:
    """F-B: why this microtask may not become VERIFIED now, or None.

    ``projection`` must be built while the caller holds the operation TASK lock
    and the mutation lock. Refused while any operation of the microtask has an
    open mutation fate or a recovery that still has a lifecycle consequence;
    advisory-only Resolver states of a closed operation and the administrative
    rest of an ADOPT settlement (ownership release) do not block.
    """
    unreadable = [
        item for item in projection["blockers"] + projection["diagnostics"]
        if item["code"] in _FACTS_UNREADABLE
    ]
    if unreadable:
        first = unreadable[0]
        return "RECOVERY_FACTS_UNAVAILABLE", f"{first['code']}: {first['reason']}"
    for view in projection["operations"]:
        if view["microtask_id"] != microtask_id:
            continue
        op_id = view["operation_id"]
        if view["status"] in _OPEN_FATE and view["recovery_settlement"] is None:
            return (
                "OPERATION_FATE_OPEN",
                f"operation {op_id} is {view['status']}: its mutation fate is open; reconcile it and "
                "settle its recovery before the microtask is verified",
            )
        recovery = view["recovery"]
        if recovery is None:
            continue
        state = recovery["state"]
        if state.endswith("_REJECTED") or state == "RESOLUTION_STALE":
            continue  # advice only; this operation's mutation fate is closed
        if state.endswith("_SETTLED") and recovery.get("lifecycle_target") in (
            MicrotaskStatus.DONE.value,
            MicrotaskStatus.VERIFIED.value,
        ):
            continue  # only the ownership release of an accepted effect is left
        return (
            "RECOVERY_OPEN",
            f"operation {op_id} has an open recovery ({state}); finish it through recover before "
            "the microtask is verified",
        )
    return None
