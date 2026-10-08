"""CLAUDE-WA-014 Gate A: is "accepted ABORT before ACTIVE -> sibling ROLLBACK" reachable through
supported APIs, and does it physically restore files?

Temp storage only. Run from the repository root: python -B <this file> [code_root]
Every lifecycle step that matters goes through the HTTP control plane (WebAlarmApi.dispatch):
reconcile, resolutions, microtask transition, operation transition, recover, rollbacks. Setup
(workspace, task, microtask, restore point, operation intents) uses the public services.
No storage file is written directly. File changes are made by the probe "outside the server"
(no RC-3 mutation_boundary ever runs): the authority each operation had is printed.

Scenarios
  A1 RC-6 recover   : m1 READY, op1 ABORT accepted, m1 -> ACTIVE (API), op2 ROLLBACK accepted, recover
  A2 direct RC-4    : same, then POST /tasks/{t}/rollbacks + /apply
  A3 order          : ABORT accepted, then the ACTIVE attempt itself (is it refused?)
  A4 reverse order  : m1 ACTIVE first (legit), op2's change, THEN op1 ABORT, op2 ROLLBACK -> must stay allowed
  A5 ROLLBACK first : m1 READY, op2 ROLLBACK accepted (no ABORT), m1 -> ACTIVE, recover (Repair #4A's exit)
Target kinds: write (existing file), delete (deleted file re-created), create (created file deleted).
"""
import hashlib
import json
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

CODE_ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
sys.path.insert(0, str(CODE_ROOT))

from web_alarm.operation_store import OperationStore  # noqa: E402
from web_alarm.server import ApiError, WebAlarmApi  # noqa: E402
from web_alarm.state_machine import ServerStateMachine  # noqa: E402
from web_alarm.task_store import TaskStore  # noqa: E402
from web_alarm.workspace_registry import WorkspaceRegistry  # noqa: E402

TASK = "task_014"
BEFORE, AFTER, KEEP, GONE, NEW = b"before\n", b"after-content\n", b"keep\n", b"gone\n", b"new file\n"
FILES = {
    "write": {"a.txt": BEFORE, "keep.txt": KEEP},
    "delete": {"a.txt": BEFORE, "gone.txt": GONE, "keep.txt": KEEP},
    "create": {"keep.txt": KEEP},
}
SPECS = {
    "write": [("a.txt", "edit"), ("keep.txt", "delete")],
    "delete": [("a.txt", "edit"), ("gone.txt", "delete"), ("keep.txt", "delete")],
    "create": [("new.txt", "create"), ("keep.txt", "delete")],
}
FRESH = """
    import json, sys
    sys.path.insert(0, {code!r})
    from web_alarm.server import WebAlarmApi
    code, r = WebAlarmApi({storage!r}).dispatch("POST", "/tasks/{task}/recover", {{}})
    print(json.dumps([r["state"], [s["action"] for s in r["performed_steps"]]]))
"""


def digest(project):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()[:10] for p in sorted(project.iterdir()) if p.is_file()}


class World:
    def __init__(self, tmp, kind):
        self.kind = kind
        self.storage, self.project = Path(tmp) / "state", Path(tmp) / "project"
        self.project.mkdir()
        for name, data in FILES[kind].items():
            (self.project / name).write_bytes(data)
        WorkspaceRegistry(self.storage).register("014", self.project, workspace_id="ws_014")
        self.tasks = TaskStore(self.storage)
        self.tasks.create_task("ws_014", "014", "RAW", "WA-014", task_id=TASK)
        self.tasks.create_microtask(TASK, "M1", "m1", microtask_id="m1")
        ServerStateMachine(self.storage).prepare_microtask(TASK, "m1", SPECS[kind])
        self.api = WebAlarmApi(self.storage)
        self.ops = OperationStore(self.storage)
        self.ops.begin(TASK, "m1", "write", "keep.txt", operation_id="op_1", payload=b"keep-v2\n")
        if kind == "create":
            self.ops.begin(TASK, "m1", "create_file", "new.txt", operation_id="op_2", payload=NEW)
        else:
            self.ops.begin(TASK, "m1", "write", "a.txt", operation_id="op_2", payload=AFTER)

    def call(self, path, body):
        try:
            return self.api.dispatch("POST", path, body)
        except ApiError as exc:
            return exc.status, {"error": exc.code, "message": exc.message[:160]}

    def transition(self, status):
        code, out = self.call("/microtasks/m1/transition", {"task_id": TASK, "target_status": status})
        return f"{status}:{code}" + ("" if code == 200 else f" {out.get('error')} ({out.get('message', '')[:90]})")

    def resolve(self, op, action):
        _, rec = self.call(f"/tasks/{TASK}/reconcile", {"microtask_id": "m1", "operation_id": op})
        code, out = self.call(f"/tasks/{TASK}/resolutions", {
            "microtask_id": "m1", "operation_id": op, "action": action,
            "evidence_fingerprint": rec["DECISION"]["evidence_fingerprint"],
            "operation_revision": self.ops.get(TASK, op).revision})
        res = out.get("resolution") or (out.get("details") or {}).get("resolution") or {}
        return code, res.get("resolution_id"), f"{action} {code} {res.get('result')}/{res.get('result_code')}"

    def external_partial(self):
        code, _ = self.call(f"/tasks/{TASK}/operations/op_2/transition", {"target_status": "STARTED"})
        assert code == 200
        if self.kind == "create":
            (self.project / "new.txt").write_bytes(NEW)
        else:
            (self.project / "a.txt").write_bytes(AFTER)
        if self.kind == "delete":
            (self.project / "gone.txt").unlink()

    def authority(self, op):
        """The F-C rule RC-3 mutation_boundary applies before any normal write (microtask_gate)."""
        from web_alarm.microtask_gate import execution_refusal
        from web_alarm.resolver_service import ResolverService
        from web_alarm.rollback_store import RollbackStore
        refusal = execution_refusal(TASK, "m1", tasks=self.tasks, operations=self.ops,
                                    resolver=ResolverService(self.storage), rollbacks=RollbackStore(self.storage))
        return refusal[0] if refusal else "AUTHORITY_POSSIBLE"

    def micro(self):
        return self.tasks.open_microtask(TASK, "m1").status.value

    def recover(self):
        code, out = self.call(f"/tasks/{TASK}/recover", {})
        return f"{out.get('state')} {[s['action'] for s in out.get('performed_steps', [])]}"

    def direct_rc4(self, resolution_id):
        code, prep = self.call(f"/tasks/{TASK}/rollbacks", {
            "microtask_id": "m1", "operation_id": "op_2", "resolution_id": resolution_id})
        if code not in (200, 201):
            return f"prepare {code} {prep.get('error')}"
        rid = prep["rollback"]["rollback_id"]
        code2, app = self.call(f"/tasks/{TASK}/rollbacks/{rid}/apply", {})
        return f"prepare {code}/{prep['result']} apply {code2}/{app.get('result', app.get('error'))}"

    def fresh(self):
        out = subprocess.run([sys.executable, "-B", "-c", textwrap.dedent(FRESH.format(
            code=str(CODE_ROOT), storage=str(self.storage), task=TASK))], capture_output=True, text=True)
        return out.stdout.strip() or out.stderr[-200:]


def verdict(before, after):
    return "DESTRUCTIVE" if after != before else "NO BYTE CHANGED"


def scenario_exploit(kind, path):
    with tempfile.TemporaryDirectory() as tmp:
        w = World(tmp, kind)
        w.transition("READY")
        _, _, abort = w.resolve("op_1", "ABORT")
        auth_ready = w.authority("op_2")
        activation = w.transition("ACTIVE")
        auth_active = w.authority("op_2")
        w.external_partial()
        _, rid, rollback = w.resolve("op_2", "ROLLBACK")
        before = digest(w.project)
        action = w.recover() if path == "RC-6" else w.direct_rc4(rid)
        fresh = w.fresh()
        after = digest(w.project)
        settlement = (w.ops.get(TASK, "op_1").recovery_settlement or {})
        print(f"A{'1' if path == 'RC-6' else '2'} {path} [{kind}] | op1 {abort} | op2 authority READY={auth_ready} | "
              f"{activation} | op2 authority ACTIVE={auth_active} | op2 {rollback} | {action} | fresh={fresh} | "
              f"micro={w.micro()} op1 settlement fact={settlement.get('microtask_status')} | "
              f"bytes {before} -> {after} | {verdict(before, after)}", flush=True)


def scenario_order():
    with tempfile.TemporaryDirectory() as tmp:
        w = World(tmp, "write")
        w.transition("READY")
        _, _, abort = w.resolve("op_1", "ABORT")
        attempt = w.transition("ACTIVE")
        print(f"A3 order | op1 {abort} | then ACTIVE attempt: {attempt} | micro={w.micro()}", flush=True)


def scenario_reverse(kind):
    with tempfile.TemporaryDirectory() as tmp:
        w = World(tmp, kind)
        w.transition("READY")
        activation = w.transition("ACTIVE")  # legitimately, before any recovery decision
        auth = w.authority("op_2")
        w.external_partial()
        _, _, abort = w.resolve("op_1", "ABORT")
        _, rid, rollback = w.resolve("op_2", "ROLLBACK")
        before = digest(w.project)
        action = w.recover()
        after = digest(w.project)
        print(f"A4 reverse [{kind}] | {activation} | op2 authority ACTIVE (before ABORT)={auth} | op1 {abort} | "
              f"op2 {rollback} | {action} | bytes {before} -> {after} | {verdict(before, after)} (expected: restored)",
              flush=True)


def scenario_rollback_first(path):
    with tempfile.TemporaryDirectory() as tmp:
        w = World(tmp, "write")
        w.transition("READY")
        w.external_partial()
        _, rid, rollback = w.resolve("op_2", "ROLLBACK")
        first = w.recover()
        activation = w.transition("ACTIVE")
        auth = w.authority("op_2")
        before = digest(w.project)
        action = w.recover() if path == "RC-6" else w.direct_rc4(rid)
        after = digest(w.project)
        print(f"A5 ROLLBACK before ACTIVE, {path} | op2 {rollback} | recover at READY: {first} | {activation} | "
              f"op2 authority ACTIVE={auth} | {action} | bytes {before} -> {after} | {verdict(before, after)}", flush=True)


if __name__ == "__main__":
    print(f"code root: {CODE_ROOT}")
    for path in ("RC-6", "RC-4"):
        for kind in ("write", "delete", "create"):
            scenario_exploit(kind, path)
    scenario_order()
    for kind in ("write", "create"):
        scenario_reverse(kind)
    for path in ("RC-6", "RC-4"):
        scenario_rollback_first(path)
