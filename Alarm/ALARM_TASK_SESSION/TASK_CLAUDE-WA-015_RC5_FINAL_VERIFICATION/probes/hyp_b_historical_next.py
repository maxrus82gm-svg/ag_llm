"""CLAUDE-WA-015 hypothesis B: NEXT of a historical (COMPLETED) TASK that still carries open recovery.

Temp storage only. Run from the repository root: python -B <this file>
Legacy state (documented isolated fixture): the recovery facts are produced through the public
HTTP control plane on an ACTIVE TASK; the TASK is then moved to completed/ through the old ungated
storage primitive ``TaskStore.complete_task`` (the pre-RC-5 completion path, still a public library
method). After that, only the HTTP control plane is used: what GET task / projection / context /
ui / closeout / recover say, and what happens when each suggested action is actually called.
Bytes of the Workspace, of the completed TASK directory and of the RC-3 claim store are hashed
before and after every call.

Fixtures (all on microtask m1 = current, ACTIVE / RECOVERY_REQUIRED stage)
  B1 op_2 STARTED, no resolution                        -> reconciliation NEXT
  B2 op_2 STARTED, fresh accepted ROLLBACK              -> Resolver NEXT
  B3 B2 + RC-4 session PRESERVED                        -> rollback NEXT (no claims yet)
  B4 B2 + RC-4 apply interrupted after the write landed -> APPLYING, target in flight
  B5 B2 + RC-4 apply ended PARTIAL (claims kept)        -> rollback NEXT "close ... release"
"""
import hashlib
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

import web_alarm.rollback_service as rollback_module  # noqa: E402
from web_alarm.server import ApiError, WebAlarmApi  # noqa: E402
from web_alarm.task_store import TaskStore  # noqa: E402
from web_alarm.workspace_registry import WorkspaceRegistry  # noqa: E402

TASK = "task_b"
BEFORE, AFTER, KEEP = b"before\n", b"after-content\n", b"keep\n"


def digest(root: Path, skip=()) -> str:
    items = []
    if root.is_dir():
        for path in sorted(root.rglob("*")):
            rel = path.relative_to(root).as_posix()
            if path.is_file() and not any(rel.startswith(s) for s in skip):
                items.append(f"{rel} {hashlib.sha256(path.read_bytes()).hexdigest()}")
    return hashlib.sha256("\n".join(items).encode()).hexdigest()[:10]


class Crash(BaseException):
    """Simulated process death inside RC-4 apply (escapes every except clause)."""


class World:
    def __init__(self, tmp: Path):
        self.storage, self.project = tmp / "state", tmp / "project"
        self.project.mkdir()
        (self.project / "a.txt").write_bytes(BEFORE)
        (self.project / "keep.txt").write_bytes(KEEP)
        WorkspaceRegistry(self.storage).register("B", self.project, workspace_id="ws_b")
        self.tasks = TaskStore(self.storage)
        self.tasks.create_task("ws_b", "B", "RAW", "WA-015 B", task_id=TASK)
        self.api = WebAlarmApi(self.storage)
        self.ok("POST", f"/tasks/{TASK}/microtasks", {"title": "M1", "goal": "m1", "microtask_id": "m1"})
        self.ok("POST", "/microtasks/m1/prepare", {"task_id": TASK, "targets": [
            {"path": "a.txt", "expected_change": "edit"}, {"path": "keep.txt", "expected_change": "edit"}]})
        for status in ("READY", "ACTIVE"):
            self.ok("POST", "/microtasks/m1/transition", {"task_id": TASK, "target_status": status})
        self.ok("POST", f"/tasks/{TASK}/operations", {"microtask_id": "m1", "action": "write", "target": "a.txt",
                                                       "operation_id": "op_2",
                                                       "payload": {"encoding": "utf-8", "data": AFTER.decode()}})
        self.ok("POST", f"/tasks/{TASK}/operations/op_2/transition", {"target_status": "STARTED"})
        (self.project / "a.txt").write_bytes(AFTER)  # the operation's effect (no executor exists yet)

    def call(self, method, path, body=None):
        try:
            return self.api.dispatch(method, path, body)
        except ApiError as exc:
            return exc.status, {"error": exc.code, "message": exc.message[:160], "details": exc.details}
        except Exception as exc:  # an unexpected server-side exception is evidence too
            return 500, {"error": type(exc).__name__, "message": str(exc)[:160]}

    def ok(self, method, path, body=None):
        code, out = self.call(method, path, body)
        assert code in (200, 201), (path, code, out)
        return out

    def rollback_resolution(self):
        rec = self.ok("POST", f"/tasks/{TASK}/reconcile", {"microtask_id": "m1", "operation_id": "op_2"})
        rev = self.ok("GET", f"/tasks/{TASK}/operations/op_2")["operation"]["revision"]
        out = self.ok("POST", f"/tasks/{TASK}/resolutions", {
            "microtask_id": "m1", "operation_id": "op_2", "action": "ROLLBACK",
            "evidence_fingerprint": rec["DECISION"]["evidence_fingerprint"], "operation_revision": rev})
        self.resolution_id = out["resolution"]["resolution_id"]
        return out["resolution"]["result"]

    def prepare(self):
        out = self.ok("POST", f"/tasks/{TASK}/rollbacks", {
            "microtask_id": "m1", "operation_id": "op_2", "resolution_id": self.resolution_id})
        self.rollback_id = out["rollback"]["rollback_id"]
        return out["result"]

    def apply_patched(self, patched):
        real = rollback_module._write_restored_bytes
        rollback_module._write_restored_bytes = patched
        try:
            return self.call("POST", f"/tasks/{TASK}/rollbacks/{self.rollback_id}/apply", {})
        except Crash:
            return "CRASH", {}
        finally:
            rollback_module._write_restored_bytes = real

    def legacy_complete(self):
        self.tasks.complete_task(TASK)  # the old ungated primitive (pre-RC-5 completion path)

    def hashes(self):
        return (digest(self.project), digest(self.storage / "tasks", skip=()), digest(self.storage / "target_claims"))

    def views(self):
        p = self.ok("GET", f"/tasks/{TASK}/projection")["projection"]
        bundle = self.ok("GET", f"/tasks/{TASK}")
        ctx = self.ok("GET", f"/tasks/{TASK}/context")
        ui = self.ok("GET", f"/tasks/{TASK}/ui")
        close = self.ok("GET", f"/tasks/{TASK}/closeout")
        code, rec = self.call("POST", f"/tasks/{TASK}/recover", {})
        return {
            "task": f"{p['task']['status']}/{p['task']['location']}",
            "recovery.state": p["recovery"]["state"],
            "authority_source": p["authority_source"],
            "NEXT": p["next_safe_action"][:230],
            "same NEXT in GET task/context/ui": (
                bundle["projection"]["next_safe_action"] == ctx["NEXT_SAFE_ACTION"] == ui["next_safe_action"]
                == p["next_safe_action"]),
            "ui.recovery_state": ui["recovery_state"],
            "closeout": [b["code"] for b in close["blockers"]],
            "recover": [code, rec.get("state"), [s.get("action") for s in rec.get("performed_steps", [])]],
        }

    def attempt(self, label, method, path, body=None):
        before = self.hashes()
        code, out = self.call(method, path, body)
        after = self.hashes()
        changed = [name for name, x, y in zip(("workspace", "tasks", "claims"), before, after) if x != y]
        result = out.get("result") or out.get("state") or out.get("error")
        print(f"    {label}: {code} {result} | {(out.get('message') or out.get('reason') or '')[:110]} | "
              f"bytes changed: {changed or 'none'}", flush=True)
        return changed


def remote_entry(world):
    from web_alarm.remote_entry import RemoteEntry, RemoteEntryError
    from web_alarm.task_store import TaskStoreError
    try:
        RemoteEntry(world.storage).enter(TASK)
        return "ENTERED"
    except (RemoteEntryError, TaskStoreError) as exc:
        return f"refused: {str(exc)[:80]}"


def attempts(w, kinds):
    if "reconcile" in kinds:
        w.attempt("POST reconcile", "POST", f"/tasks/{TASK}/reconcile", {"microtask_id": "m1", "operation_id": "op_2"})
    if "resolve" in kinds:
        w.attempt("POST resolutions ABORT", "POST", f"/tasks/{TASK}/resolutions", {
            "microtask_id": "m1", "operation_id": "op_2", "action": "ABORT",
            "evidence_fingerprint": "0" * 64, "operation_revision": 2})
    if "prepare" in kinds:
        w.attempt("POST rollbacks (prepare)", "POST", f"/tasks/{TASK}/rollbacks", {
            "microtask_id": "m1", "operation_id": "op_2", "resolution_id": w.resolution_id})
    if "apply" in kinds:
        w.attempt("POST rollback apply", "POST", f"/tasks/{TASK}/rollbacks/{w.rollback_id}/apply", {})
    if "close" in kinds:
        w.attempt("POST rollback close", "POST", f"/tasks/{TASK}/rollbacks/{w.rollback_id}/close", {})
    w.attempt("POST microtask transition", "POST", "/microtasks/m1/transition", {"task_id": TASK, "target_status": "DONE"})
    w.attempt("POST operation transition", "POST", f"/tasks/{TASK}/operations/op_2/transition", {"target_status": "DONE"})
    w.attempt("POST checkpoint rebuild", "POST", f"/tasks/{TASK}/checkpoint/rebuild", {})
    w.attempt("POST recover", "POST", f"/tasks/{TASK}/recover", {})


def run(label, build, kinds):
    with tempfile.TemporaryDirectory() as tmp:
        w = World(Path(tmp))
        detail = build(w)
        print(f"{label}: {detail}", flush=True)
        w.legacy_complete()
        print("  views: " + json.dumps(w.views(), ensure_ascii=False), flush=True)
        print(f"  RemoteEntry.enter: {remote_entry(w)}", flush=True)
        if hasattr(w, "rollback_id"):
            print(f"  session before attempts: {json.dumps(session_brief(w), ensure_ascii=False)}", flush=True)
        attempts(w, kinds)
        if hasattr(w, "rollback_id"):
            print(f"  session after attempts: {json.dumps(session_brief(w), ensure_ascii=False)}", flush=True)
            print(f"  claim store active claims after attempts: {active_claims(w)}", flush=True)


def session_brief(w):
    s = w.ok("GET", f"/tasks/{TASK}/rollbacks/{w.rollback_id}")["rollback"]
    return {"status": s["status"], "claims_released": s["claims_released"], "revision": s["revision"],
            "targets": {t["source_path"]: t["status"] for t in s["targets"]},
            "claim_ids": [t["claim_id"] for t in s["targets"] if t["claim_id"]]}


def active_claims(w):
    root = w.storage / "target_claims"
    return sorted(json.loads(p.read_text(encoding="utf-8"))["active"]["claim_id"]
                  for p in root.glob("*.json") if json.loads(p.read_text(encoding="utf-8"))["active"]) if root.is_dir() else []


def b1(w):
    return "op_2 STARTED, no resolution"


def b2(w):
    return f"op_2 STARTED, ROLLBACK {w.rollback_resolution()}"


def b3(w):
    return f"op_2 STARTED, ROLLBACK {w.rollback_resolution()}, prepare {w.prepare()}"


def b4(w):
    w.rollback_resolution()
    w.prepare()

    def crash_after_write(path, data):
        rollback_module._atomic_write_bytes(path, data)
        raise Crash()

    code, _ = w.apply_patched(crash_after_write)
    return f"ROLLBACK accepted, PRESERVED, apply -> {code} (write landed, then process death)"


def b5(w):
    w.rollback_resolution()
    w.prepare()

    def write_then_external_drift(path, data):
        rollback_module._atomic_write_bytes(path, data)
        (w.project / "keep.txt").write_bytes(b"external drift\n")  # another writer, outside the server

    code, out = w.apply_patched(write_then_external_drift)
    return f"ROLLBACK accepted, PRESERVED, apply -> {code} {out.get('result') or out.get('error')}"


if __name__ == "__main__":
    run("B1", b1, {"reconcile", "resolve"})
    run("B2", b2, {"reconcile", "resolve", "prepare"})
    run("B3", b3, {"apply", "close"})
    run("B4", b4, {"apply", "close"})
    run("B5", b5, {"apply", "close"})
