"""CLAUDE-WA-015 hypothesis A: can a TASK be COMPLETED through the public closeout gate while an
accepted ABORT (or fresh ADOPT) is not yet settled by RC-6?

Temp storage only. Run from the repository root: python -B <this file>
Workspace / TASK registration use the public services; every lifecycle step of the scenario goes
through the HTTP control plane (WebAlarmApi.dispatch): microtasks create/prepare/transition,
operations begin/transition, reconcile, resolutions, claim acquire/release, closeout, complete,
recover, GET task/projection/context/ui. No storage file is written directly. File changes in
A5 are made "outside the server" on purpose (an ADOPT needs the exact post-state).

Scenarios
  A1  m1,m2 VERIFIED; op_1 on m2 begun + STARTED; ABORT accepted; NOT settled -> complete?
  A1u same with UNKNOWN_AFTER_DISCONNECT, A1i with INTENT
  A2  positive control: same, RC-6 recover settles the ABORT first, then complete
  A3  negative control: op_1 STARTED without any resolution -> complete refused
  A4  clean control: no operation -> complete
  A5  ADOPT variant: fresh accepted ADOPT, not settled -> complete?
  A6  ownership control: op_1 holds an RC-3 claim -> ACTIVE_CLAIM refuses, release, then complete
"""
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from web_alarm.server import ApiError, WebAlarmApi  # noqa: E402
from web_alarm.task_store import TaskStore  # noqa: E402
from web_alarm.workspace_registry import WorkspaceRegistry  # noqa: E402

TASK = "task_a"
FILES = {"one.txt": b"one\n", "two.txt": b"two\n"}


def tree_digest(root: Path, skip=("locks",)) -> str:
    items = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_file() and not any(rel.startswith(s + "/") for s in skip):
            items.append(f"{rel} {hashlib.sha256(path.read_bytes()).hexdigest()}")
    return hashlib.sha256("\n".join(items).encode()).hexdigest()[:12]


class World:
    def __init__(self, tmp: Path):
        self.storage, self.project = tmp / "state", tmp / "project"
        self.project.mkdir()
        for name, data in FILES.items():
            (self.project / name).write_bytes(data)
        WorkspaceRegistry(self.storage).register("A", self.project, workspace_id="ws_a")
        TaskStore(self.storage).create_task("ws_a", "A", "RAW", "WA-015 A", task_id=TASK)
        self.api = WebAlarmApi(self.storage)

    def call(self, method, path, body=None):
        try:
            return self.api.dispatch(method, path, body)
        except ApiError as exc:
            return exc.status, {"error": exc.code, "message": exc.message[:200], "details": exc.details}

    def ok(self, method, path, body=None):
        code, out = self.call(method, path, body)
        assert code in (200, 201), (path, code, out)
        return out

    def verified_microtask(self, mid, target):
        self.ok("POST", f"/tasks/{TASK}/microtasks", {"title": mid.upper(), "goal": mid, "microtask_id": mid})
        self.ok("POST", f"/microtasks/{mid}/prepare", {"task_id": TASK, "targets": [{"path": target, "expected_change": "edit"}]})
        for status in ("READY", "ACTIVE", "DONE"):
            self.ok("POST", f"/microtasks/{mid}/transition", {"task_id": TASK, "target_status": status})
        self.ok("POST", f"/microtasks/{mid}/transition",
                {"task_id": TASK, "target_status": "VERIFIED", "verification_evidence": f"{mid} checked"})

    def begin(self, op, mid="m2", target="two.txt", data="after\n"):
        return self.ok("POST", f"/tasks/{TASK}/operations", {
            "microtask_id": mid, "action": "write", "target": target, "operation_id": op,
            "payload": {"encoding": "utf-8", "data": data}})

    def op_transition(self, op, status):
        return self.call("POST", f"/tasks/{TASK}/operations/{op}/transition", {"target_status": status})

    def op(self, op):
        return self.ok("GET", f"/tasks/{TASK}/operations/{op}")["operation"]

    def resolve(self, op, action, mid="m2"):
        rec = self.ok("POST", f"/tasks/{TASK}/reconcile", {"microtask_id": mid, "operation_id": op})
        code, out = self.call("POST", f"/tasks/{TASK}/resolutions", {
            "microtask_id": mid, "operation_id": op, "action": action,
            "evidence_fingerprint": rec["DECISION"]["evidence_fingerprint"],
            "operation_revision": self.op(op)["revision"]})
        res = out.get("resolution") or ((out.get("details") or {}).get("resolution")) or {}
        return f"{action}:{code}/{res.get('result')} (decision {rec['DECISION']['decision']})"

    def closeout(self):
        out = self.ok("GET", f"/tasks/{TASK}/closeout")
        return out["eligible"], [b["code"] for b in out["blockers"]]

    def projection(self):
        p = self.ok("GET", f"/tasks/{TASK}/projection")["projection"]
        return p

    def summary(self):
        p = self.projection()
        ctx = self.ok("GET", f"/tasks/{TASK}/context")
        ui = self.ok("GET", f"/tasks/{TASK}/ui")
        return {
            "task": f"{p['task']['status']}/{p['task']['location']}",
            "recovery.state": p["recovery"]["state"],
            "authority_source": p["authority_source"],
            "NEXT": p["next_safe_action"][:150],
            "context.AUTHORITY/RECOVERY": f"{ctx['AUTHORITY_SOURCE']}/{ctx['RECOVERY']['state']}",
            "context.NEXT==projection": ctx["NEXT_SAFE_ACTION"] == p["next_safe_action"],
            "ui.recovery_state": ui["recovery_state"],
            "ui.NEXT==projection": ui["next_safe_action"] == p["next_safe_action"],
        }

    def recover(self):
        code, out = self.call("POST", f"/tasks/{TASK}/recover", {})
        return code, out.get("state"), [s.get("action") for s in out.get("performed_steps", [])], (out.get("reason") or "")[:150]

    def complete(self):
        code, out = self.call("POST", f"/tasks/{TASK}/complete", {})
        return code, out.get("result") or out.get("error")

    def claims(self):
        root = self.storage / "target_claims"
        active = 0
        if root.is_dir():
            for path in root.glob("*.json"):
                if json.loads(path.read_text(encoding="utf-8")).get("active"):
                    active += 1
        return active


def rc6_would(world: World):
    """What RC-6 recover would do now: run it on a byte copy of the storage (the original is untouched)."""
    copy = world.storage.parent / "rc6_copy"
    shutil.copytree(world.storage, copy)
    before = tree_digest(world.project)
    out = WebAlarmApi(copy).dispatch("POST", f"/tasks/{TASK}/recover", {})[1]
    after = tree_digest(world.project)
    shutil.rmtree(copy)
    return f"{out['state']} steps={[s.get('action') for s in out['performed_steps']]} workspace_changed={before != after}"


def base(tmp):
    w = World(Path(tmp))
    w.verified_microtask("m1", "one.txt")
    w.verified_microtask("m2", "two.txt")
    return w


def show(label, data):
    print(f"  {label}: " + json.dumps(data, ensure_ascii=False))


def scenario_a1(status_path, label):
    with tempfile.TemporaryDirectory() as tmp:
        w = base(tmp)
        w.begin("op_1")
        for status in status_path:
            code, out = w.op_transition("op_1", status)
            assert code == 200, out
        print(f"{label}: op_1 path {['INTENT'] + list(status_path)} on VERIFIED m2")
        show("closeout before ABORT", w.closeout())
        show("resolution", w.resolve("op_1", "ABORT"))
        show("closeout after ABORT (not settled)", w.closeout())
        show("projection (active)", w.summary())
        show("RC-6 recover would (on a copy)", rc6_would(w))
        ws_before = tree_digest(w.project)
        show("POST complete", w.complete())
        op = w.op("op_1")
        show("persisted after completion", {
            "op.status": op["status"], "op.recovery_settlement": op["recovery_settlement"],
            "claims_active": w.claims(), "workspace_changed": tree_digest(w.project) != ws_before})
        show("projection (completed)", w.summary())
        show("POST recover (completed)", w.recover())
        show("settlement after recover", w.op("op_1")["recovery_settlement"])
        code, out = w.call("POST", f"/tasks/{TASK}/reconcile", {"microtask_id": "m2", "operation_id": "op_1"})
        show("POST reconcile on completed", [code, out.get("error"), (out.get("message") or "")[:100]])


def scenario_a2():
    with tempfile.TemporaryDirectory() as tmp:
        w = base(tmp)
        w.begin("op_1")
        w.op_transition("op_1", "STARTED")
        print("A2 positive control: ABORT settled by RC-6 before completion")
        show("resolution", w.resolve("op_1", "ABORT"))
        show("POST recover (active)", w.recover())
        show("settlement", w.op("op_1")["recovery_settlement"])
        show("closeout after settlement", w.closeout())
        show("POST complete", w.complete())
        show("projection (completed)", w.summary())


def scenario_a3():
    with tempfile.TemporaryDirectory() as tmp:
        w = base(tmp)
        w.begin("op_1")
        w.op_transition("op_1", "STARTED")
        print("A3 negative control: STARTED without any resolution")
        show("closeout", w.closeout())
        show("POST complete", w.complete())
        show("task", w.projection()["task"])


def scenario_a4():
    with tempfile.TemporaryDirectory() as tmp:
        w = base(tmp)
        print("A4 clean control: no operation")
        show("closeout", w.closeout())
        show("POST recover (active)", w.recover())
        show("POST complete", w.complete())
        show("projection (completed)", w.summary())


def scenario_a5():
    with tempfile.TemporaryDirectory() as tmp:
        w = base(tmp)
        w.begin("op_1", data="adopted\n")
        w.op_transition("op_1", "STARTED")
        (w.project / "two.txt").write_bytes(b"adopted\n")  # exact post-state, outside the server
        print("A5 ADOPT variant: fresh accepted ADOPT, not settled")
        show("resolution", w.resolve("op_1", "ADOPT"))
        show("closeout after ADOPT (not settled)", w.closeout())
        show("RC-6 recover would (on a copy)", rc6_would(w))
        show("POST complete", w.complete())
        op = w.op("op_1")
        show("persisted after completion", {"op.status": op["status"], "op.recovery_settlement": op["recovery_settlement"]})
        show("projection (completed)", w.summary())
        (w.project / "two.txt").write_bytes(b"later edit\n")  # the history TASK's ADOPT basis ages
        show("projection (completed, after a later edit)", w.summary())
        show("POST recover (completed)", w.recover())


def scenario_a6():
    with tempfile.TemporaryDirectory() as tmp:
        w = base(tmp)
        w.begin("op_1")
        code, out = w.call("POST", f"/tasks/{TASK}/operations/op_1/claim", {"operation_revision": w.op("op_1")["revision"]})
        w.op_transition("op_1", "STARTED")
        print("A6 ownership control: op_1 holds an RC-3 claim")
        show("claim acquire", [code, out.get("result")])
        show("resolution", w.resolve("op_1", "ABORT"))
        show("closeout (claim held)", w.closeout())
        show("POST complete", w.complete())
        code, out = w.call("POST", f"/tasks/{TASK}/operations/op_1/claim/release", {"reason": "probe"})
        show("claim release (public, after ABORT)", [code, out.get("result")])
        show("closeout after release (ABORT still not settled)", w.closeout())
        show("POST complete", w.complete())
        show("settlement", w.op("op_1")["recovery_settlement"])


def scenario_a7():
    """RC-6 R1 renamed ROLLBACK_ACCEPTED of a VERIFIED stage to ROLLBACK_STAGE_PROTECTED: does closeout see it?"""
    with tempfile.TemporaryDirectory() as tmp:
        w = World(Path(tmp))
        (w.project / "keep.txt").write_bytes(b"keep\n")
        w.verified_microtask("m1", "one.txt")
        w.ok("POST", f"/tasks/{TASK}/microtasks", {"title": "M2", "goal": "m2", "microtask_id": "m2"})
        w.ok("POST", "/microtasks/m2/prepare", {"task_id": TASK, "targets": [
            {"path": "two.txt", "expected_change": "edit"}, {"path": "keep.txt", "expected_change": "edit"}]})
        for status in ("READY", "ACTIVE", "DONE"):
            w.ok("POST", "/microtasks/m2/transition", {"task_id": TASK, "target_status": status})
        w.ok("POST", "/microtasks/m2/transition", {"task_id": TASK, "target_status": "VERIFIED", "verification_evidence": "m2 checked"})
        w.begin("op_1", data="after\n")
        w.op_transition("op_1", "FAILED")  # terminal operation outcome
        (w.project / "two.txt").write_bytes(b"after\n")  # its effect is present anyway (outside the server)
        print("A7 FAILED op_1 on VERIFIED m2, Workspace mixes pre/post -> ROLLBACK")
        show("closeout before", w.closeout())
        show("resolution", w.resolve("op_1", "ROLLBACK"))
        p = w.projection()
        show("projection op recovery", [v["recovery"]["state"] for v in p["operations"] if v["recovery"]])
        show("closeout after ROLLBACK accepted", w.closeout())
        show("RC-6 recover would (on a copy)", rc6_would(w))
        show("POST complete", w.complete())
        show("projection (completed)", w.summary())


def scenario_a10():
    """A fresh REJECTED resolution on a terminal operation: RC-6 manual boundary vs closeout."""
    with tempfile.TemporaryDirectory() as tmp:
        w = base(tmp)
        w.begin("op_1")
        w.op_transition("op_1", "FAILED")
        print("A10 FAILED op_1 on VERIFIED m2 + REJECTED ADOPT")
        show("resolution", w.resolve("op_1", "ADOPT"))
        show("closeout", w.closeout())
        show("RC-6 recover would (on a copy)", rc6_would(w))
        show("POST complete", w.complete())
        show("projection (completed)", w.summary())


def scenario_a7b():
    """A7 in the natural order: op_1 begun while m2 is ACTIVE, FAILED with its write landed, then m2 verified."""
    with tempfile.TemporaryDirectory() as tmp:
        w = World(Path(tmp))
        (w.project / "keep.txt").write_bytes(b"keep\n")
        w.verified_microtask("m1", "one.txt")
        w.ok("POST", f"/tasks/{TASK}/microtasks", {"title": "M2", "goal": "m2", "microtask_id": "m2"})
        w.ok("POST", "/microtasks/m2/prepare", {"task_id": TASK, "targets": [
            {"path": "two.txt", "expected_change": "edit"}, {"path": "keep.txt", "expected_change": "edit"}]})
        for status in ("READY", "ACTIVE"):
            w.ok("POST", "/microtasks/m2/transition", {"task_id": TASK, "target_status": status})
        w.begin("op_1", data="after\n")
        w.op_transition("op_1", "FAILED")  # executor reported failure ...
        (w.project / "two.txt").write_bytes(b"after\n")  # ... but its write landed
        w.ok("POST", "/microtasks/m2/transition", {"task_id": TASK, "target_status": "DONE"})
        code, out = w.call("POST", "/microtasks/m2/transition",
                           {"task_id": TASK, "target_status": "VERIFIED", "verification_evidence": "m2 checked"})
        print("A7b natural order: op_1 begun on ACTIVE m2, FAILED with its write landed, m2 DONE -> VERIFIED")
        show("VERIFIED transition", [code, out.get("error")])
        show("resolution", w.resolve("op_1", "ROLLBACK"))
        show("closeout after ROLLBACK accepted", w.closeout())
        show("RC-6 recover would (on a copy)", rc6_would(w))
        show("POST complete", w.complete())


def scenario_a8():
    """Control: an accepted RETRY of a terminal operation keeps blocking (RETRY_PENDING)."""
    with tempfile.TemporaryDirectory() as tmp:
        w = base(tmp)
        w.begin("op_1")
        w.op_transition("op_1", "FAILED")
        print("A8 control: FAILED op_1 on VERIFIED m2 + RETRY")
        show("resolution", w.resolve("op_1", "RETRY"))
        show("closeout", w.closeout())
        show("POST complete", w.complete())


if __name__ == "__main__" and sys.argv[1:] == ["extra"]:
    scenario_a7()
    scenario_a7b()
    scenario_a8()
    scenario_a10()
    sys.exit(0)

if __name__ == "__main__":
    scenario_a1(["STARTED"], "A1")
    scenario_a1(["UNKNOWN_AFTER_DISCONNECT"], "A1u")
    scenario_a1([], "A1i")
    scenario_a2()
    scenario_a3()
    scenario_a4()
    scenario_a5()
    scenario_a6()
