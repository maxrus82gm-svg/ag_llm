"""Repair #4A adversarial pass (temp storage only, real processes).

Run from the repository root: python -B <this file> [rounds]
  Z1  prepare (state machine) / Resolver ABORT / recover started together on a
      PLANNED microtask with an INTENT operation, N rounds with jitter: after two
      more recovers the microtask is at RECOVERY_REQUIRED with one ABORT settlement,
      never FAIL_CLOSED, no mutation authority, and any restore point is intact.
  Z2  W2 crash + a RETRY whose basis goes stale: reconcile first, then an honest
      manual state (no trap); a later ABORT completes.
  Z3  W2 crash with a corrupt published restore point + ABORT: fail-closed
      preparation (evidence kept), the ABORT still reaches its manual boundary.
"""
import json
import random
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from web_alarm.manifest_store import ManifestSnapshotStore  # noqa: E402
from web_alarm.models import MicrotaskStatus, OperationStatus  # noqa: E402
from web_alarm.operation_store import OperationStore  # noqa: E402
from web_alarm.reconciliation_service import ReconciliationService  # noqa: E402
from web_alarm.recovery_coordinator import RecoveryCoordinator  # noqa: E402
from web_alarm.resolver_service import ResolverService  # noqa: E402
from web_alarm.target_claim_service import TargetClaimService  # noqa: E402
from web_alarm.task_store import TaskStore  # noqa: E402
from web_alarm.workspace_registry import WorkspaceRegistry  # noqa: E402

TASK = "task_z"
BEFORE, AFTER = b"before\n", b"after\n"
REPO = Path.cwd()
failures = []


def check(case, ok, detail):
    print(f"{case} | {'OK' if ok else 'FAIL'} | {detail}", flush=True)
    if not ok:
        failures.append(case)


def world(tmp):
    storage, project = Path(tmp) / "state", Path(tmp) / "project"
    project.mkdir()
    (project / "a.txt").write_bytes(BEFORE)
    WorkspaceRegistry(storage).register("Z", project, workspace_id="ws_z")
    tasks = TaskStore(storage)
    tasks.create_task("ws_z", "Z", "RAW", "Z", task_id=TASK)
    tasks.create_microtask(TASK, "M1", "m1", microtask_id="m1")
    OperationStore(storage).begin(TASK, "m1", "write", "a.txt", operation_id="op_1", payload=AFTER)
    TargetClaimService(storage).acquire(TASK, "op_1", operation_revision=1)
    return storage, project, tasks


def child(code):
    return subprocess.Popen([sys.executable, "-B", "-c", textwrap.dedent(code)], cwd=REPO,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def resolve(storage, action):
    decision = ReconciliationService(storage).reconcile(TASK, "m1", "op_1")["DECISION"]
    return ResolverService(storage).apply(TASK, "m1", "op_1", action,
                                          evidence_fingerprint=decision["evidence_fingerprint"],
                                          operation_revision=OperationStore(storage).get(TASK, "op_1").revision)


CRASH_W2 = """
    import os
    from web_alarm.state_machine import ServerStateMachine
    from web_alarm.task_store import TaskStore
    real = TaskStore.compare_and_set_microtask_status
    def die(self, t, m, *, expected, status, activate=False):
        if getattr(status, "value", status) == "BACKUP_VERIFIED":
            os._exit(29)
        return real(self, t, m, expected=expected, status=status, activate=activate)
    TaskStore.compare_and_set_microtask_status = die
    ServerStateMachine({storage!r}).prepare_microtask({task!r}, "m1", [("a.txt", "edit")])
"""


def z1(rounds):
    shapes = {}
    for index in range(rounds):
        with tempfile.TemporaryDirectory() as tmp:
            storage, project, tasks = world(tmp)
            delays = [random.random() * 0.08 for _ in range(3)]
            procs = [
                child(f"""
                    import json, time
                    time.sleep({delays[0]})
                    from web_alarm.state_machine import ServerStateMachine
                    try:
                        ServerStateMachine({str(storage)!r}).prepare_microtask({TASK!r}, "m1", [("a.txt", "edit")])
                        print(json.dumps("PREPARED"))
                    except Exception as exc:
                        print(json.dumps("PREPARE " + type(exc).__name__))
                """),
                child(f"""
                    import json, time
                    time.sleep({delays[1]})
                    from web_alarm.operation_store import OperationStore
                    from web_alarm.reconciliation_service import ReconciliationService
                    from web_alarm.resolver_service import ResolverService
                    d = ReconciliationService({str(storage)!r}).reconcile({TASK!r}, "m1", "op_1")["DECISION"]
                    out = ResolverService({str(storage)!r}).apply({TASK!r}, "m1", "op_1", "ABORT",
                        evidence_fingerprint=d["evidence_fingerprint"],
                        operation_revision=OperationStore({str(storage)!r}).get({TASK!r}, "op_1").revision)
                    print(json.dumps(out["resolution"].result_code))
                """),
                child(f"""
                    import json, time
                    time.sleep({delays[2]})
                    from web_alarm.recovery_coordinator import RecoveryCoordinator
                    print(json.dumps(RecoveryCoordinator({str(storage)!r}).recover({TASK!r})["state"]))
                """),
            ]
            outs = []
            for p in procs:
                out, err = p.communicate(timeout=120)
                outs.append(json.loads(out.strip().splitlines()[-1]) if out.strip() else f"ERR {err[-200:]}")
            finals = [RecoveryCoordinator(storage).recover(TASK) for _ in range(2)]
            micro = tasks.open_microtask(TASK, "m1").status.value
            settlement = (OperationStore(storage).get(TASK, "op_1").recovery_settlement or {}).get("action")
            published = (tasks.microtask_directory(TASK, "m1") / "restore_point" / "manifest.json").is_file()
            intact = (not published) or ManifestSnapshotStore(storage).verify_restore_point(TASK, "m1") is not None
            authority = TargetClaimService(storage).authorize(TASK, "op_1", operation_revision=OperationStore(storage).get(TASK, "op_1").revision)["result"]
            shape = (outs[0], outs[1], outs[2], micro, published)
            shapes[shape] = shapes.get(shape, 0) + 1
            accepted = outs[1] == "BASIS_FRESH_ACTION_ALLOWED"
            ok = (
                "FAIL_CLOSED" not in [f["state"] for f in finals] and outs[2] != "FAIL_CLOSED"
                and intact and authority == "DENIED" and finals[1]["performed_steps"] == []
                and (
                    (accepted and micro == "RECOVERY_REQUIRED" and settlement == "ABORT")
                    # the preparation changed the evidence first: the ABORT is honestly
                    # refused as STALE, nothing settles, the microtask stays prepared
                    or (not accepted and settlement is None and micro == "BACKUP_VERIFIED")
                )
            )
            if not ok:
                check(f"Z1 round {index}", False, f"{shape} finals={[f['state'] for f in finals]} settlement={settlement}")
    check("Z1 prepare / ABORT / recover together", not any(f.startswith("Z1 round") for f in failures),
          f"{rounds} rounds, outcomes {shapes}")


def z2():
    with tempfile.TemporaryDirectory() as tmp:
        storage, project, tasks = world(tmp)
        OperationStore(storage).transition(TASK, "op_1", OperationStatus.STARTED)
        child(CRASH_W2.format(storage=str(storage), task=TASK)).communicate(timeout=120)
        retry = resolve(storage, "RETRY")["resolution"].result_code
        (project / "a.txt").write_bytes(b"moved on\n")  # the RETRY basis goes stale
        runs = [RecoveryCoordinator(storage).recover(TASK) for _ in range(2)]
        resolve(storage, "ABORT")
        closed = RecoveryCoordinator(storage).recover(TASK)
        micro = tasks.open_microtask(TASK, "m1").status.value
        check("Z2 W2 + stale RETRY, then ABORT",
              "FAIL_CLOSED" not in [r["state"] for r in runs] and micro == "RECOVERY_REQUIRED"
              and closed["state"] != "FAIL_CLOSED",
              f"RETRY {retry}; recover={[(r['state'], r['recovery_state']) for r in runs]} "
              f"steps1={[s['action'] for s in runs[0]['performed_steps']]}; after ABORT {closed['state']} micro={micro}")


def z3():
    with tempfile.TemporaryDirectory() as tmp:
        storage, project, tasks = world(tmp)
        child(CRASH_W2.format(storage=str(storage), task=TASK)).communicate(timeout=120)
        snap = next((tasks.microtask_directory(TASK, "m1") / "restore_point").glob("snapshots/*.bin"))
        snap.write_bytes(b"tampered")
        resolve(storage, "ABORT")
        runs = [RecoveryCoordinator(storage).recover(TASK) for _ in range(2)]
        micro = tasks.open_microtask(TASK, "m1").status.value
        manifest = ManifestSnapshotStore(storage).open_manifest(TASK, "m1").status.value
        results = [s["outcome"].get("result") for s in runs[0]["performed_steps"]]
        check("Z3 corrupt published restore point + ABORT",
              "FAIL_CLOSED" not in [r["state"] for r in runs] and micro == "RECOVERY_REQUIRED"
              and manifest == "BLOCKED_PREPARE" and results[:1] == ["PREPARATION_BLOCKED"] and snap.exists(),
              f"steps={[s['action'] for s in runs[0]['performed_steps']]} results={results} micro={micro} "
              f"manifest={manifest} second={runs[1]['performed_steps']}")


if __name__ == "__main__":
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    random.seed(20261008)
    z1(rounds)
    z2()
    z3()
    print("ALL OK" if not failures else f"FAILURES: {failures}")
