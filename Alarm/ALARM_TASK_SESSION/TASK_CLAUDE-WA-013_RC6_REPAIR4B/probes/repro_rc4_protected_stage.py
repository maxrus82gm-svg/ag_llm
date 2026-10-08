"""Direct RC-4 (service + HTTP API) on a protected stage: VERIFIED m1 and a non-current m1.

Temp storage only. Run from the repository root: python -B <this file> [code_root]
m1 goes PLANNED -> ... -> ACTIVE -> DONE -> VERIFIED through the state machine (no
operation), then a new operation of m1 is begun and marked STARTED (lifecycle only)
and its target changed outside the server.
"""
import hashlib
import sys
import tempfile
from pathlib import Path

CODE_ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
sys.path.insert(0, str(CODE_ROOT))

from web_alarm.models import MicrotaskStatus  # noqa: E402
from web_alarm.operation_store import OperationStore  # noqa: E402
from web_alarm.reconciliation_service import ReconciliationService  # noqa: E402
from web_alarm.resolver_service import ResolverService  # noqa: E402
from web_alarm.rollback_service import RollbackService  # noqa: E402
from web_alarm.server import ApiError, WebAlarmApi  # noqa: E402
from web_alarm.state_machine import ServerStateMachine  # noqa: E402
from web_alarm.task_store import TaskStore  # noqa: E402
from web_alarm.workspace_registry import WorkspaceRegistry  # noqa: E402

TASK = "task_4b_r1"


def digest(project):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()[:12] for p in sorted(project.iterdir()) if p.is_file()}


def run(second_microtask, via_api):
    with tempfile.TemporaryDirectory() as tmp:
        storage, project = Path(tmp) / "state", Path(tmp) / "project"
        project.mkdir()
        (project / "a.txt").write_bytes(b"before\n")
        (project / "keep.txt").write_bytes(b"keep\n")
        WorkspaceRegistry(storage).register("R1", project, workspace_id="ws_r1")
        tasks = TaskStore(storage)
        tasks.create_task("ws_r1", "R1", "RAW", "R1", task_id=TASK)
        tasks.create_microtask(TASK, "M1", "m1", microtask_id="m1")
        if second_microtask:
            tasks.create_microtask(TASK, "M2", "m2", microtask_id="m2")
        sm = ServerStateMachine(storage)
        sm.prepare_microtask(TASK, "m1", [("a.txt", "edit"), ("keep.txt", "delete")])
        for status in ("READY", "ACTIVE", "DONE"):
            sm.transition(TASK, "m1", MicrotaskStatus(status))
        sm.transition(TASK, "m1", MicrotaskStatus.VERIFIED, verification_evidence="checked")
        ops = OperationStore(storage)
        ops.begin(TASK, "m1", "write", "a.txt", operation_id="op_late", payload=b"after\n")
        ops.transition(TASK, "op_late", "STARTED")
        (project / "a.txt").write_bytes(b"after\n")
        decision = ReconciliationService(storage).reconcile(TASK, "m1", "op_late")["DECISION"]
        res = ResolverService(storage).apply(TASK, "m1", "op_late", "ROLLBACK",
                                             evidence_fingerprint=decision["evidence_fingerprint"],
                                             operation_revision=ops.get(TASK, "op_late").revision)["resolution"]
        before = digest(project)
        try:
            if via_api:
                api = WebAlarmApi(storage)
                code, prep = api.dispatch("POST", f"/tasks/{TASK}/rollbacks", {
                    "microtask_id": "m1", "operation_id": "op_late", "resolution_id": res.resolution_id})
                code2, applied = api.dispatch("POST", f"/tasks/{TASK}/rollbacks/{prep['rollback']['rollback_id']}/apply", {})
                outcome = f"API prepare {code}/{prep['result']} apply {code2}/{applied['result']}"
            else:
                rb = RollbackService(storage)
                prep = rb.prepare(TASK, "m1", "op_late", res.resolution_id)
                if prep["rollback"] is None:
                    outcome = f"prepare {prep['result']}/{prep['result_code']}: {prep['reason'][:110]}"
                else:
                    applied = rb.apply(TASK, prep["rollback"]["rollback_id"])
                    outcome = f"prepare {prep['result']} apply {applied['result']}/{applied['result_code']}"
        except ApiError as exc:
            outcome = f"ApiError {exc}"
        except Exception as exc:  # noqa: BLE001
            outcome = f"{type(exc).__name__}: {str(exc)[:140]}"
        after = digest(project)
        label = "m1 VERIFIED, m2 current" if second_microtask else "m1 VERIFIED (last stage)"
        print(f"R1 direct RC-4 ({'API' if via_api else 'RollbackService'}) | {label} | ROLLBACK "
              f"{res.result.value}/{res.result_code} | {outcome} | m1={tasks.open_microtask(TASK, 'm1').status.value} "
              f"| bytes {before} -> {after} | {'DESTRUCTIVE (VERIFIED stage rolled back)' if after != before else 'REFUSED'}",
              flush=True)


if __name__ == "__main__":
    print(f"code root: {CODE_ROOT}")
    run(False, False)
    run(True, False)
    run(True, True)
