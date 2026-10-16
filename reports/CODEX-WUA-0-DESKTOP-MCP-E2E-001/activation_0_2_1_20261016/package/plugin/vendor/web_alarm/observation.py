"""WA4-R bounded OBSERVE: on-demand diagnostics, never mutation authority.

This is not a filesystem watcher or a strict-mode switch. A difference from a
restore point is an observed state, not an attributed external mutation event.
Missing executor telemetry does not establish that no write took place.
"""
from __future__ import annotations

from typing import Any

from .event_checkpoint_store import EventCheckpointStoreError
from .file_state import authority_of
from .operation_store import OperationStoreError
from .reconciliation import ReconciliationEvidenceError
from .task_store import TaskStoreError


def observe(api, task_id: str) -> dict[str, Any]:
    """Read existing stores once between two projections, with no retry/write.

    The consistency check covers canonical store facts, not an atomic snapshot
    of project bytes. RC-5 alone supplies NEXT. No result authorizes an action.
    """
    before = api.projection.build(task_id)
    errors: list[dict[str, str]] = []
    try:
        records = api.operations.list(task_id)
        operations_available = True
    except (OperationStoreError, TaskStoreError) as exc:
        records = []
        operations_available = False
        errors.append({"source": "operations", "reason": str(exc)})
    try:
        events = api.state.read_events(task_id)
        events_available = True
    except (EventCheckpointStoreError, TaskStoreError) as exc:
        events = []
        events_available = False
        errors.append({"source": "events", "reason": str(exc)})

    history = []
    for record in records:
        # DONE can also be recorded after an external write or Resolver ADOPT.
        # Even a correlated event is unauthenticated historical evidence only.
        correlated = [e.event_id for e in events
                      if e.task_id == task_id and e.microtask_id == record.microtask_id
                      and e.operation_id == record.operation_id
                      and e.event_type == "MUTATION_EXECUTED" and record.receipt is not None
                      and isinstance(e.payload, dict)
                      and e.payload.get("mutation_kind") == (record.contract or {}).get("mutation_kind")
                      and e.payload.get("receipt") == authority_of(record.receipt)]
        history.append({
            "operation_id": record.operation_id, "microtask_id": record.microtask_id,
            "status": record.status.value, "revision": record.revision,
            "contract_version": record.contract_version,
            "target": record.target, "action": record.action,
            "receipt": authority_of(record.receipt),
            "receipt_scope": "HISTORICAL_ONLY" if record.receipt else None,
            "gateway_execution_evidence": "CORRELATED_EXECUTOR_EVENT" if correlated else "NOT_ESTABLISHED",
            "executor_event_ids": correlated,
            "current_post_state_proved": False,
        })

    mid = before["position"]["current_microtask_id"]
    # Closed TASK inspection must remain history-only; never reopen it to scan.
    closed = (before["task"]["location"] != "active"
              or before["task"]["status"] in ("COMPLETED", "ARCHIVED"))
    state = {"scope": "CURRENT_MICROTASK_MANIFEST_ONLY", "microtask_id": mid,
             "availability": "NOT_PREPARED", "targets": [], "complete": False}
    if closed:
        state["availability"] = "CLOSED_TASK_HISTORY_ONLY"
    elif mid is not None and before["restore_point"]["status"] != "NOT_PREPARED":
        try:
            evidence = api.reconciliation.evidence.collect(task_id, mid)
            state.update(availability="AVAILABLE", complete=evidence.evidence_complete)
            errors.extend({"source": "manifest_observation", "reason": reason} for reason in evidence.errors)
            for item in evidence.targets:
                readable = item.path_error is None and item.current_exists is not None
                state["targets"].append({
                    "source_path": item.source_path,
                    "snapshot_valid": item.snapshot_valid,
                    "snapshot_error": item.snapshot_error,
                    "snapshot_pre_state": {"exists": item.exists_before, "size": item.size_before,
                                           "sha256": item.sha256_before},
                    "observed_state": {"exists": item.current_exists, "size": item.current_size,
                                       "sha256": item.current_sha256},
                    "read_error": item.path_error,
                    "differs_from_snapshot": (not item.matches_pre_state
                                              if readable and item.snapshot_valid else None),
                    "attribution": "NOT_ESTABLISHED",
                    "external_mutation_proved": None,
                })
        except (ReconciliationEvidenceError, TaskStoreError, OSError) as exc:
            state["availability"] = "UNAVAILABLE"
            errors.append({"source": "manifest_observation", "reason": str(exc)})

    after = api.projection.build(task_id)
    operation_basis = [[r.operation_id, r.microtask_id, r.status.value, r.revision,
                        r.contract_version, r.request_fingerprint, r.recovery_settlement, r.updated_at]
                       for r in records]
    coherent = (operations_available
                and operation_basis == before["source_basis"]["operations"]
                and before["source_fingerprint"] == after["source_fingerprint"]
                and before["projection_fingerprint"] == after["projection_fingerprint"])
    return {
        "observation_version": 1, "mode": "OBSERVE", "task_id": task_id,
        "read_only": True, "diagnostics_persisted": False,
        "mutation_authority": False, "workflow_mutation_performed": False,
        "enforcement_enabled": False,
        "canonical_state": {"task": after["task"], "position": after["position"],
                            "restore_point": after["restore_point"], "blockers": after["blockers"],
                            "recovery": after["recovery"], "authority_source": after["authority_source"],
                            "next_safe_action": after["next_safe_action"],
                            "source_fingerprint": after["source_fingerprint"],
                            "projection_fingerprint": after["projection_fingerprint"]},
        "storage_evidence_coherent": coherent,
        "consistency_scope": "BOUNDED_STORE_CHECK_NOT_ATOMIC_PROJECT_SNAPSHOT",
        "operations_available": operations_available, "events_available": events_available,
        "operation_history": history, "state_observation": state, "errors": errors,
        "coverage": {
            "continuous_monitoring": False,
            "external_event_feed": "UNAVAILABLE", "external_events": None,
            "external_operation_count": None, "unobserved_operation_count": None,
            "absence_of_telemetry_proves_no_mutation": False,
            "outside_manifest_scanned": False,
            "writer_attribution_available": False,
            "historical_events_authenticated": False,
            "transient_changes_may_be_missed": True,
        },
    }
