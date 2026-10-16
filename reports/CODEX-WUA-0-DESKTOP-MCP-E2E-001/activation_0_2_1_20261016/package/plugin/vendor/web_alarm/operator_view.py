"""Read-only operator DTOs. Presentation facts confer no execution authority.

RC-5 remains the only source of NEXT/recovery decisions. There is no new UI
state machine, store, implicit repair, retry or checkpoint writer here.
"""
from __future__ import annotations

from typing import Any

from .models import record_to_dict
from .operation_store import OperationStoreError
from .recovery_report_store import RecoveryReportStoreError
from .task_store import TaskStoreError


def navigation(api) -> dict[str, Any]:
    """Keep damaged TASKs visible without making all other workspaces unusable."""
    result: dict[str, Any] = {"active": [], "completed": [], "errors": []}
    for location, directory in (("active", api.tasks.active_dir), ("completed", api.tasks.completed_dir)):
        for path in sorted(directory.iterdir()):
            if not path.is_dir():
                continue
            try:
                task = api.tasks.open_task(path.name)
                projection = api.projection.build(task.task_id)
                row = record_to_dict(task)
                row.update(current_microtask_id=projection["position"]["current_microtask_id"],
                           current_status=projection["position"]["current_status"],
                           blockers=projection["blockers"], recovery_state=projection["recovery"]["state"],
                           location=location)
                result[location].append(row)
            except (TaskStoreError, RuntimeError, ValueError, OSError) as exc:
                result["errors"].append({"task_id": path.name, "location": location, "reason": str(exc)})
    return result


def operator_details(api, task_id: str, bundle: dict, events: list, event_error: str | None) -> dict:
    """Bounded consistency check; a GET never retries indefinitely or writes.

    Projection is lock-free. Comparing its semantic/source fingerprints across
    this read catches concurrent changes, but is not a transactional snapshot or
    a future byte-proof. Detailed records must also match that projection basis.
    """
    projection = bundle["projection"]
    errors = ([{"source": "events", "reason": event_error}] if event_error else [])
    try:
        records = [record_to_dict(op) for op in api.operations.list(task_id)]
    except (OperationStoreError, TaskStoreError) as exc:
        records = []
        errors.append({"source": "operations", "reason": str(exc)})
    try:
        recovery_reports = [item.to_dict() for item in api.recovery_reports.list_reports(task_id)]
    except (RecoveryReportStoreError, TaskStoreError) as exc:
        recovery_reports = []
        errors.append({"source": "recovery_reports", "reason": str(exc)})
    later = api.projection.build(task_id)
    basis = projection["source_basis"]
    micro_basis = [[m["microtask_id"], m["sequence"], m["status"], m["updated_at"]]
                   for m in bundle["microtasks"]]
    operation_basis = [[op["operation_id"], op["microtask_id"], op["status"], op["revision"],
                        op["contract_version"], op["request_fingerprint"], op["recovery_settlement"],
                        op["updated_at"]] for op in records]
    task = bundle["task"]
    plan = bundle["plan"]
    coherent = (
        projection["source_fingerprint"] == later["source_fingerprint"]
        and projection["projection_fingerprint"] == later["projection_fingerprint"]
        and micro_basis == basis["microtasks"]
        and operation_basis == basis["operations"]
        and [task["task_id"], task["workspace_id"], task["status"], task["plan_revision"],
             task["updated_at"]] == basis["task"][:5]
        and [plan["revision"], plan["microtask_ids"], plan["current_microtask_id"],
             plan["updated_at"]] == basis["plan"]
    )
    blocked = bool(projection["blockers"])
    position = projection["position"]
    views = {op["operation_id"]: op for op in projection["operations"]}
    operations = []
    for record in records:
        view = views.get(record["operation_id"], {})
        operations.append({"record": record, "projection": view,
                           "receipt_scope": "HISTORICAL_ONLY" if record["receipt"] else None,
                           # A read of history cannot prove receipt delivery/replay or current bytes.
                           "replay_confirmed": True if any(e.event_type == "OPERATION_REPLAY"
                                                            and e.operation_id == record["operation_id"]
                                                            for e in events) else None,
                           "current_post_state_matches": None,
                           "history": [record_to_dict(e) for e in events
                                       if e.operation_id == record["operation_id"]]})
    stages = []
    for index, micro in enumerate(bundle["microtasks"]):
        mid = micro["microtask_id"]
        stages.append({**micro, "position": index + 1,
                       "is_current": mid == position["current_microtask_id"],
                       "prerequisites": plan["microtask_ids"][:index],
                       "operations": [op for op in operations if op["record"]["microtask_id"] == mid],
                       "blockers": [b for b in projection["blockers"]
                                    if b.get("microtask_id") in (None, mid)],
                       "events": [record_to_dict(e) for e in events if e.microtask_id == mid],
                       "recovery_reports": [r for r in recovery_reports if r["microtask_id"] == mid]})
    unfinished = [op for op in operations
                  if op["record"]["microtask_id"] == position["current_microtask_id"]
                  and op["record"]["status"] in ("INTENT", "STARTED", "UNKNOWN_AFTER_DISCONNECT")]
    closed = projection["task"]["location"] != "active" or task["status"] in ("COMPLETED", "ARCHIVED")
    current = unfinished[0] if len(unfinished) == 1 and coherent and not blocked and not closed else None
    reason = ("Закрытая TASK: операции являются историей." if closed else
              "Данные противоречивы или изменились во время чтения." if blocked or not coherent else
              "Несколько незавершённых операций текущего этапа; текущая не определена." if len(unfinished) > 1 else
              "Нет единственной незавершённой операции текущего этапа." if not unfinished else
              "Единственная незавершённая операция текущего этапа; это не доказательство исполнения сейчас.")
    persisted_verified = sum(m["status"] == "VERIFIED" for m in bundle["microtasks"])
    return {"version": 1, "coherent": coherent, "read_at": later["generated_at"],
            "consistency_note": "Снимок чтения, не транзакция и не разрешение на mutation.",
            "progress": {"verified": persisted_verified if coherent and not blocked else None,
                         "persisted_verified": persisted_verified, "total": len(plan["microtask_ids"]),
                         "done": sum(m["status"] == "DONE" for m in bundle["microtasks"])},
            "stages": stages, "operations": operations, "current_operation": current,
            "current_operation_reason": reason, "recovery_reports": recovery_reports,
            "evidence_errors": errors}
