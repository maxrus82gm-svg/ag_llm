"""Repair #4 adversarial pass (temp storage only, real processes).

Run from the repository root: python -B <this file> [rounds]
  Y1  RC-6 ADOPT settlement vs a concurrent late ROLLBACK request, N rounds with
      jitter: never an endless FAIL_CLOSED, never a second physical restore, one
      immutable settlement, a second recover does nothing.
  Y2  two concurrent recovers over the same W2 / W1 crash state: the reconcile
      happens exactly once, both end consistent.
  Y3  legacy ACCEPTED ROLLBACK written over a ROLLBACK settlement (pre-Repair-#4
      data): RC-4 cannot start a second rollback from it, recover restores nothing.
  Y4  recover in a loop while a live preparation runs: it never touches it.
"""
import json
import random
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from web_alarm.manifest_store import ManifestSnapshotStore  # noqa: E402
from web_alarm.models import MicrotaskStatus, OperationStatus  # noqa: E402
from web_alarm.operation_store import OperationStore  # noqa: E402
from web_alarm.reconciliation_service import ReconciliationService  # noqa: E402
from web_alarm.recovery_coordinator import RecoveryCoordinator  # noqa: E402
from web_alarm.resolution_store import ResolutionRecord, ResolutionResult, ResolutionStore  # noqa: E402
from web_alarm.resolver_service import ResolverService  # noqa: E402
from web_alarm.rollback_service import RollbackService  # noqa: E402
from web_alarm.state_machine import ServerStateMachine  # noqa: E402
from web_alarm.target_claim_service import TargetClaimService  # noqa: E402
from web_alarm.task_store import TaskStore  # noqa: E402
from web_alarm.workspace_registry import WorkspaceRegistry  # noqa: E402

TASK = "task_y"
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
    WorkspaceRegistry(storage).register("Y", project, workspace_id="ws_y")
    tasks = TaskStore(storage)
    tasks.create_task("ws_y", "Y", "RAW", "Y", task_id=TASK)
    tasks.create_microtask(TASK, "M1", "m1", microtask_id="m1")
    return storage, project, tasks


def child(code):
    return subprocess.Popen([sys.executable, "-B", "-c", textwrap.dedent(code)], cwd=REPO,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def restored(storage):
    return sum(1 for s in RollbackService(storage).store.list(TASK) for t in s["targets"] if t["status"] == "RESTORED")


def three_target_partial(storage, project):
    sm = ServerStateMachine(storage)
    for name, data in (("a.txt", BEFORE), ("b.txt", b"b-before\n"), ("c.txt", b"c-keep\n")):
        (project / name).write_bytes(data)
    sm.prepare_microtask(TASK, "m1", [("a.txt", "edit"), ("b.txt", "delete"), ("c.txt", "delete")])
    sm.transition(TASK, "m1", MicrotaskStatus.READY)
    sm.transition(TASK, "m1", MicrotaskStatus.ACTIVE)
    ops = OperationStore(storage)
    ops.begin(TASK, "m1", "write", "a.txt", operation_id="op_1", payload=AFTER)
    TargetClaimService(storage).acquire(TASK, "op_1", operation_revision=1)
    ops.transition(TASK, "op_1", OperationStatus.STARTED)
    (project / "a.txt").write_bytes(AFTER)
    (project / "b.txt").unlink()
    sm.transition(TASK, "m1", MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT)


def resolve(storage, action):
    decision = ReconciliationService(storage).reconcile(TASK, "m1", "op_1")["DECISION"]
    return ResolverService(storage).apply(TASK, "m1", "op_1", action,
                                          evidence_fingerprint=decision["evidence_fingerprint"],
                                          operation_revision=OperationStore(storage).get(TASK, "op_1").revision)


def y1(rounds):
    shapes = {}
    for index in range(rounds):
        with tempfile.TemporaryDirectory() as tmp:
            storage, project, tasks = world(tmp)
            sm = ServerStateMachine(storage)
            (project / "a.txt").write_bytes(BEFORE)
            sm.prepare_microtask(TASK, "m1", [("a.txt", "edit")])
            sm.transition(TASK, "m1", MicrotaskStatus.READY)
            sm.transition(TASK, "m1", MicrotaskStatus.ACTIVE)
            ops = OperationStore(storage)
            ops.begin(TASK, "m1", "write", "a.txt", operation_id="op_1", payload=AFTER)
            ops.transition(TASK, "op_1", OperationStatus.STARTED)
            (project / "a.txt").write_bytes(AFTER)
            sm.transition(TASK, "m1", MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT)
            resolve(storage, "ADOPT")
            d1, d2 = random.random() * 0.05, random.random() * 0.05
            settler = child(f"""
                import json, time
                from web_alarm.recovery_coordinator import RecoveryCoordinator
                time.sleep({d1})
                r = RecoveryCoordinator({str(storage)!r}).recover({TASK!r})
                print(json.dumps(r["state"]))
            """)
            asker = child(f"""
                import json, time
                from web_alarm.operation_store import OperationStore
                from web_alarm.reconciliation_service import ReconciliationService
                from web_alarm.resolver_service import ResolverService
                time.sleep({d2})
                decision = ReconciliationService({str(storage)!r}).reconcile({TASK!r}, "m1", "op_1")["DECISION"]
                out = ResolverService({str(storage)!r}).apply({TASK!r}, "m1", "op_1", "ROLLBACK",
                    evidence_fingerprint=decision["evidence_fingerprint"],
                    operation_revision=OperationStore({str(storage)!r}).get({TASK!r}, "op_1").revision)
                print(json.dumps(out["resolution"].result_code))
            """)
            s_state = json.loads(settler.communicate(timeout=120)[0].strip().splitlines()[-1])
            a_code = json.loads(asker.communicate(timeout=120)[0].strip().splitlines()[-1])
            runs = [RecoveryCoordinator(storage).recover(TASK) for _ in range(2)]
            settlement = (OperationStore(storage).get(TASK, "op_1").recovery_settlement or {}).get("action")
            shape = (a_code, settlement, runs[1]["state"])
            shapes[shape] = shapes.get(shape, 0) + 1
            ok = (
                "FAIL_CLOSED" not in (s_state, runs[0]["state"], runs[1]["state"])
                and restored(storage) == 0
                and runs[1]["performed_steps"] == []
            )
            if not ok:
                check(f"Y1 round {index}", False, f"{shape} settler={s_state} first={runs[0]['state']}")
    check("Y1 ADOPT settlement vs concurrent late ROLLBACK", not any(f.startswith("Y1 round") for f in failures),
          f"{rounds} rounds, outcomes {shapes}")


CRASH = """
    import os
    from web_alarm.manifest_store import ManifestSnapshotStore
    from web_alarm.state_machine import ServerStateMachine
    from web_alarm.task_store import TaskStore
    if {window!r} == "W1":
        def die(self, *a, **k):
            os._exit(23)
        ManifestSnapshotStore._resolve_target = die
    else:
        real = TaskStore.compare_and_set_microtask_status
        def die(self, t, m, *, expected, status, activate=False):
            if getattr(status, "value", status) == "BACKUP_VERIFIED":
                os._exit(29)
            return real(self, t, m, expected=expected, status=status, activate=activate)
        TaskStore.compare_and_set_microtask_status = die
    ServerStateMachine({storage!r}).prepare_microtask({task!r}, "m1", [("a.txt", "edit")])
"""


def y2():
    for window, expected in (("W2", "BACKUP_VERIFIED"), ("W1", "BLOCKED_PREPARE")):
        with tempfile.TemporaryDirectory() as tmp:
            storage, project, tasks = world(tmp)
            (project / "a.txt").write_bytes(BEFORE)
            child(CRASH.format(window=window, storage=str(storage), task=TASK)).communicate(timeout=120)
            recovers = [child(f"""
                import json
                from web_alarm.recovery_coordinator import RecoveryCoordinator
                r = RecoveryCoordinator({str(storage)!r}).recover({TASK!r})
                print(json.dumps([r["state"], [s["outcome"].get("result") for s in r["performed_steps"]]]))
            """) for _ in range(2)]
            outs = [json.loads(p.communicate(timeout=120)[0].strip().splitlines()[-1]) for p in recovers]
            reconciled = [o for o in outs if any(r and r.startswith("PREPARATION_") and r != "PREPARATION_IN_PROGRESS" for r in o[1])]
            events = [e for e in __import__("web_alarm.event_checkpoint_store", fromlist=["x"]).EventCheckpointStore(storage).read_events(TASK)
                      if e.event_type == "RESTORE_POINT_PREPARATION_RECONCILED"]
            status = tasks.open_microtask(TASK, "m1").status.value
            check(f"Y2 two concurrent recovers after a {window} crash",
                  status == expected and len(events) == 1 and len(reconciled) == 1,
                  f"outs={outs} status={status} reconcile_events={len(events)}")


def y3():
    with tempfile.TemporaryDirectory() as tmp:
        storage, project, tasks = world(tmp)
        three_target_partial(storage, project)
        resolve(storage, "ROLLBACK")
        RecoveryCoordinator(storage).recover(TASK)
        before = restored(storage)
        (project / "a.txt").write_bytes(AFTER)
        (project / "b.txt").unlink()
        decision = ReconciliationService(storage).reconcile(TASK, "m1", "op_1")["DECISION"]
        store = ResolutionStore(storage)
        settled = store.get(TASK, OperationStore(storage).get(TASK, "op_1").recovery_settlement["resolution_id"])
        revision = OperationStore(storage).get(TASK, "op_1").revision
        store.write_new(ResolutionRecord(
            resolution_id="res_legacy_rollback", task_id=TASK, microtask_id="m1", operation_id="op_1",
            action=settled.action, requested_basis=dict(settled.requested_basis, evidence_fingerprint=decision["evidence_fingerprint"], operation_revision=revision),
            basis=dict(settled.basis, evidence_fingerprint=decision["evidence_fingerprint"], operation_revision=revision,
                       decision=decision["decision"]),
            result=ResolutionResult.ACCEPTED, result_code="BASIS_FRESH_ACTION_ALLOWED", result_reason="legacy",
            effect=settled.effect, next_safe_action="legacy", provenance=settled.provenance, payload_verified=None,
        ))
        try:
            out = RollbackService(storage).prepare(TASK, "m1", "op_1", "res_legacy_rollback", channel="adversarial")
            rc4 = f"RC-4 prepare {out['result']}/{out.get('result_code')}"
        except Exception as exc:  # noqa: BLE001
            rc4 = f"RC-4 prepare raised {type(exc).__name__}: {exc}"
        runs = [RecoveryCoordinator(storage).recover(TASK) for _ in range(2)]
        check("Y3 legacy accepted ROLLBACK over a ROLLBACK settlement",
              restored(storage) == before and "FAIL_CLOSED" not in [r["state"] for r in runs]
              and "RECOVERY_ALREADY_SETTLED" in rc4,
              f"{rc4}; recover={[r['state'] for r in runs]} restored {before}->{restored(storage)} a={(project / 'a.txt').read_bytes()!r}")


def y4(rounds):
    with tempfile.TemporaryDirectory() as tmp:
        storage, project, tasks = world(tmp)
        (project / "a.txt").write_bytes(BEFORE)
        flags = Path(tmp) / "flags"
        flags.mkdir()
        preparer = child(f"""
            import pathlib, time
            from web_alarm.manifest_store import ManifestSnapshotStore
            from web_alarm.state_machine import ServerStateMachine
            flags = pathlib.Path({str(flags)!r})
            real = ManifestSnapshotStore._resolve_target
            def hold(self, *a, **k):
                (flags / "capturing").write_text("1")
                while not (flags / "release").exists():
                    time.sleep(0.01)
                return real(self, *a, **k)
            ManifestSnapshotStore._resolve_target = hold
            ServerStateMachine({str(storage)!r}).prepare_microtask({TASK!r}, "m1", [("a.txt", "edit")])
        """)
        try:
            deadline = time.time() + 60
            while not (flags / "capturing").exists() and time.time() < deadline:
                time.sleep(0.01)
            states = [RecoveryCoordinator(storage).recover(TASK)["state"] for _ in range(rounds)]
            untouched = tasks.open_microtask(TASK, "m1").status is MicrotaskStatus.PREPARING
        finally:
            (flags / "release").write_text("1")
            preparer.communicate(timeout=120)
        final = tasks.open_microtask(TASK, "m1").status.value
        check("Y4 recover never touches a live preparation",
              untouched and set(states) == {"RECOVERY_IN_PROGRESS"} and final == "BACKUP_VERIFIED"
              and ManifestSnapshotStore(storage).verify_restore_point(TASK, "m1") is not None,
              f"{rounds} recovers -> {set(states)}; after release: {final}")


if __name__ == "__main__":
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    random.seed(20261008)
    y1(rounds)
    y2()
    y3()
    y4(rounds)
    print("ALL OK" if not failures else f"FAILURES: {failures}")
