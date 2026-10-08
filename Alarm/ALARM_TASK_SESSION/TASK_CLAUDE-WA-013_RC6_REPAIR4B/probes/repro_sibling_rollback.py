"""Repair #4B: pre-execution ABORT (op1) x sibling ROLLBACK (op2) of one microtask.

Reproduction in temp storage only. Run from the repository root:
    python -B <this file> [code_root]
``code_root`` (optional) is a directory whose ``web_alarm`` package is imported
instead of the working tree (e.g. a safety copy of an older commit).

Facts per scenario:
- who changed the files: only this probe, "externally" (no ACTIVE microtask,
  no RC-3 mutation_boundary, so no server-authorized executor ever ran);
- op2 STARTED is a persisted lifecycle fact only (public operation transition);
- RESULT: DESTRUCTIVE = RC-4 physically restored project bytes of a microtask
  that has never been ACTIVE; REFUSED = no project byte changed.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

CODE_ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
sys.path.insert(0, str(CODE_ROOT))

from web_alarm.models import MicrotaskStatus  # noqa: E402
from web_alarm.operation_store import OperationStore  # noqa: E402
from web_alarm.reconciliation_service import ReconciliationService  # noqa: E402
try:  # RC-6 exists only from commit 159 on; older code runs the direct RC-4 scenarios only
    from web_alarm.recovery_coordinator import RecoveryCoordinator  # noqa: E402
except ModuleNotFoundError:
    RecoveryCoordinator = None
from web_alarm.resolver_service import ResolverService  # noqa: E402
from web_alarm.rollback_service import RollbackService  # noqa: E402
from web_alarm.server import ApiError, WebAlarmApi  # noqa: E402
from web_alarm.state_machine import ServerStateMachine  # noqa: E402
from web_alarm.task_store import TaskStore  # noqa: E402
from web_alarm.workspace_registry import WorkspaceRegistry  # noqa: E402

TASK = "task_4b"
BEFORE, AFTER, KEEP, GONE, NEW = b"before\n", b"after-content\n", b"keep\n", b"gone\n", b"new file\n"

FRESH = """
    import json, sys
    sys.path.insert(0, {code!r})
    from web_alarm.recovery_coordinator import RecoveryCoordinator
    r = RecoveryCoordinator({storage!r}).recover({task!r})
    print(json.dumps([r["state"], r["recovery_state"], [s["action"] for s in r["performed_steps"]], r["reason"][:200]]))
"""

CRASH_W2 = """
    import os, sys
    sys.path.insert(0, {code!r})
    from web_alarm.state_machine import ServerStateMachine
    from web_alarm.task_store import TaskStore
    real = TaskStore.compare_and_set_microtask_status
    def die(self, t, m, *, expected, status, activate=False):
        if getattr(status, "value", status) == "BACKUP_VERIFIED":
            os._exit(29)
        return real(self, t, m, expected=expected, status=status, activate=activate)
    TaskStore.compare_and_set_microtask_status = die
    ServerStateMachine({storage!r}).prepare_microtask({task!r}, "m1", {specs!r})
"""


def sha(data):
    return hashlib.sha256(data).hexdigest()[:12]


def digest(project):
    return {p.name: sha(p.read_bytes()) for p in sorted(project.iterdir()) if p.is_file()}


def run(code):
    return subprocess.run([sys.executable, "-B", "-c", textwrap.dedent(code)], cwd=str(CODE_ROOT),
                          capture_output=True, text=True)


class World:
    def __init__(self, tmp, kind):
        self.kind = kind
        self.storage, self.project = Path(tmp) / "state", Path(tmp) / "project"
        self.project.mkdir()
        WorkspaceRegistry(self.storage).register("4B", self.project, workspace_id="ws_4b")
        self.tasks = TaskStore(self.storage)
        self.tasks.create_task("ws_4b", "4B", "RAW", "Repair4B", task_id=TASK)
        self.tasks.create_microtask(TASK, "M1", "m1", microtask_id="m1")
        self.sm = ServerStateMachine(self.storage)
        self.ops = OperationStore(self.storage)
        (self.project / "keep.txt").write_bytes(KEEP)
        if kind == "write":
            (self.project / "a.txt").write_bytes(BEFORE)
            self.specs = [("a.txt", "edit"), ("keep.txt", "delete")]
        elif kind == "delete":
            (self.project / "a.txt").write_bytes(BEFORE)
            (self.project / "gone.txt").write_bytes(GONE)
            self.specs = [("a.txt", "edit"), ("gone.txt", "delete"), ("keep.txt", "delete")]
        else:  # create
            self.specs = [("new.txt", "create"), ("keep.txt", "delete")]

    def prepare(self, status):
        if status == "W2":
            crash = run(CRASH_W2.format(code=str(CODE_ROOT), storage=str(self.storage), task=TASK, specs=self.specs))
            assert crash.returncode == 29, crash.stderr
            return
        self.sm.prepare_microtask(TASK, "m1", self.specs)
        if status in ("READY", "ACTIVE", "UNKNOWN"):
            self.sm.transition(TASK, "m1", MicrotaskStatus.READY)
        if status in ("ACTIVE", "UNKNOWN"):
            self.sm.transition(TASK, "m1", MicrotaskStatus.ACTIVE)
        if status == "UNKNOWN":
            self.sm.transition(TASK, "m1", MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT)

    def begin_ops(self):
        self.ops.begin(TASK, "m1", "write", "keep.txt", operation_id="op_1", payload=b"keep-v2\n")
        if self.kind == "create":
            self.ops.begin(TASK, "m1", "create_file", "new.txt", operation_id="op_2", payload=NEW)
        else:
            self.ops.begin(TASK, "m1", "write", "a.txt", operation_id="op_2", payload=AFTER)

    def external_partial_effect(self):
        """op2 STARTED (lifecycle only) + files changed outside the server."""
        self.ops.transition(TASK, "op_2", "STARTED")
        if self.kind == "create":
            (self.project / "new.txt").write_bytes(NEW)
        else:
            (self.project / "a.txt").write_bytes(AFTER)
        if self.kind == "delete":
            (self.project / "gone.txt").unlink()

    def resolve(self, action, op):
        decision = ReconciliationService(self.storage).reconcile(TASK, "m1", op)["DECISION"]
        out = ResolverService(self.storage).apply(
            TASK, "m1", op, action, evidence_fingerprint=decision["evidence_fingerprint"],
            operation_revision=self.ops.get(TASK, op).revision)
        r = out["resolution"]
        return r, f"{r.result.value}/{r.result_code} ({decision['decision']}/{decision['reason_code']})"

    def micro(self):
        return self.tasks.open_microtask(TASK, "m1").status.value

    def facts(self):
        sessions = RollbackService(self.storage).store.list(TASK)
        active = []
        root = self.storage / "target_claims"
        for path in sorted(root.rglob("*.json")) if root.exists() else []:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                continue
            if isinstance(data, dict) and data.get("active"):
                active.append(data["active"].get("operation_id"))
        op2 = self.ops.get(TASK, "op_2")
        return (f"micro={self.micro()} op2={op2.status.value} op2_settlement="
                f"{(getattr(op2, 'recovery_settlement', None) or {}).get('action')} rollbacks="
                f"{[(s['status'], s['claims_released']) for s in sessions]} active_claims={active}")


def recover_summary(world, label):
    r = RecoveryCoordinator(world.storage).recover(TASK)
    return f"{label}: {r['state']} steps={[s['action'] for s in r['performed_steps']]} reason={r['reason'][:150]!r}"


def scenario_rc6(kind, status):
    with tempfile.TemporaryDirectory() as tmp:
        w = World(tmp, kind)
        w.prepare(status)
        w.begin_ops()
        _, abort = w.resolve("ABORT", "op_1")
        first = recover_summary(w, "recover#1 (settle op1 ABORT)")
        after_abort = w.micro()
        w.external_partial_effect()
        _, rollback = w.resolve("ROLLBACK", "op_2")
        before = digest(w.project)
        second = recover_summary(w, "recover#2 (op2 ROLLBACK)")
        fresh = json.loads(run(FRESH.format(code=str(CODE_ROOT), storage=str(w.storage), task=TASK))
                           .stdout.strip().splitlines()[-1])
        after = digest(w.project)
        verdict = "DESTRUCTIVE" if after != before else "REFUSED (no byte changed)"
        print(f"B1 RC-6 [{kind}] m1 {status} | op1 ABORT {abort} | {first} | micro after ABORT={after_abort} "
              f"| op2 ROLLBACK {rollback} | {second} | fresh={fresh} | bytes {before} -> {after} | "
              f"{w.facts()} | {verdict}", flush=True)


def scenario_rc4_direct(kind, status, *, sibling_abort, via_api):
    with tempfile.TemporaryDirectory() as tmp:
        w = World(tmp, kind)
        w.prepare(status)
        w.begin_ops()
        note = "no sibling ABORT"
        if sibling_abort:
            _, abort = w.resolve("ABORT", "op_1")
            RecoveryCoordinator(w.storage).recover(TASK)
            note = f"op1 ABORT {abort} settled -> micro={w.micro()}"
        w.external_partial_effect()
        resolution, rollback = w.resolve("ROLLBACK", "op_2")
        before = digest(w.project)
        try:
            if via_api:
                api = WebAlarmApi(w.storage)
                code, prep = api.dispatch("POST", f"/tasks/{TASK}/rollbacks", {
                    "microtask_id": "m1", "operation_id": "op_2", "resolution_id": resolution.resolution_id})
                rid = prep["rollback"]["rollback_id"]
                code2, applied = api.dispatch("POST", f"/tasks/{TASK}/rollbacks/{rid}/apply", {})
                outcome = f"API prepare {code}/{prep['result']} apply {code2}/{applied['result']}"
            else:
                rb = RollbackService(w.storage)
                prep = rb.prepare(TASK, "m1", "op_2", resolution.resolution_id)
                applied = rb.apply(TASK, prep["rollback"]["rollback_id"]) if prep["rollback"] else None
                outcome = (f"prepare {prep['result']}/{prep['result_code']} apply "
                           f"{applied['result'] + '/' + applied['result_code'] if applied else '-'}")
        except ApiError as exc:
            outcome = f"ApiError {exc}"
        except Exception as exc:  # noqa: BLE001
            outcome = f"{type(exc).__name__}: {str(exc)[:140]}"
        after = digest(w.project)
        verdict = "DESTRUCTIVE" if after != before else "REFUSED (no byte changed)"
        entry = "API" if via_api else "RollbackService"
        print(f"B2 RC-4 direct ({entry}) [{kind}] m1 {status} | {note} | op2 ROLLBACK {rollback} | {outcome} "
              f"| bytes {before} -> {after} | {w.facts()} | {verdict}", flush=True)


if __name__ == "__main__":
    print(f"code root: {CODE_ROOT}")
    if RecoveryCoordinator is None:
        print("no RecoveryCoordinator in this code: direct RC-4 scenarios without a sibling ABORT only")
        for kind in ("write", "delete", "create"):
            scenario_rc4_direct(kind, "BACKUP_VERIFIED", sibling_abort=False, via_api=False)
        scenario_rc4_direct("write", "READY", sibling_abort=False, via_api=True)
        sys.exit(0)
    for kind in ("write", "delete", "create"):
        for status in ("BACKUP_VERIFIED", "READY"):
            scenario_rc6(kind, status)
    scenario_rc6("write", "W2")
    for status in ("ACTIVE", "UNKNOWN"):  # control: a stage that really executed
        scenario_rc6("write", status)
    for kind in ("write", "create"):
        scenario_rc4_direct(kind, "READY", sibling_abort=True, via_api=False)
    scenario_rc4_direct("write", "READY", sibling_abort=True, via_api=True)
    scenario_rc4_direct("write", "READY", sibling_abort=False, via_api=False)
    scenario_rc4_direct("write", "BACKUP_VERIFIED", sibling_abort=False, via_api=True)
    scenario_rc4_direct("write", "ACTIVE", sibling_abort=False, via_api=False)
