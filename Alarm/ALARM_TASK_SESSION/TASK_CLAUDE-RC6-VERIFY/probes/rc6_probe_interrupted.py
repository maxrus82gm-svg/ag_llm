"""Does RC-6 resume an RC-4 rollback interrupted by a crash, or abandon it?"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, r"M:\GitHub\ag_llm")
import rc6_probes as p  # noqa: E402  (scratchpad module)

from web_alarm.event_checkpoint_store import EventCheckpointStore  # noqa: E402
from web_alarm.projection import ProjectionService  # noqa: E402
from web_alarm.rollback_service import RollbackService  # noqa: E402

CRASH = r"""
import os, sys
import web_alarm.rollback_service as rs
storage, task_id, rollback_id, mode = sys.argv[1:5]
real = rs._write_restored_bytes
calls = []
def crash(path, data):
    calls.append(1)
    if len(calls) == 1:
        return real(path, data)
    if mode == "after_write":
        real(path, data)
    os._exit(17)
rs._write_restored_bytes = crash
rs.RollbackService(storage).apply(task_id, rollback_id)
"""

CRASH_BETWEEN = r"""
import os, sys
import web_alarm.rollback_service as rs
storage, task_id, rollback_id = sys.argv[1:4]
real_event = rs.RollbackService._event
def event(self, record, event_type, payload):
    real_event(self, record, event_type, payload)
    if event_type == "ROLLBACK_TARGET_RESTORED":
        os._exit(18)   # first target restored + receipt persisted; second not started
rs.RollbackService._event = event
rs.RollbackService(storage).apply(task_id, rollback_id)
"""


def setup(w):
    for name, data in (("a.txt", b"a-before\n"), ("b.txt", b"b-before\n"), ("c.txt", b"c-keep\n")):
        w.write(name, data)
    w.machine.prepare_microtask(p.TASK, "m1", [("a.txt", "edit"), ("b.txt", "delete"), ("c.txt", "delete")])
    w.machine.transition(p.TASK, "m1", "READY")
    w.machine.transition(p.TASK, "m1", "ACTIVE")
    w.ops.begin(p.TASK, "m1", "write", "a.txt", operation_id="op_1", payload=b"a-after\n")
    w.ops.transition(p.TASK, "op_1", "STARTED")
    w.write("a.txt", b"a-after\n")
    (w.project / "b.txt").unlink()  # second declared change landed; c.txt untouched -> mixed
    w.machine.transition(p.TASK, "m1", "UNKNOWN_AFTER_DISCONNECT")


def run(label, script, *extra):
    w = p.World()
    try:
        setup(w)
        from web_alarm.reconciliation_service import ReconciliationService
        decision = ReconciliationService(w.storage).reconcile(p.TASK, "m1", "op_1")["DECISION"]
        print(f"\n### {label}\n  decision before rollback: {decision['decision']} ({decision['reason_code']})")
        if decision["decision"] != "ROLLBACK_CURRENT_MICROTASK":
            return
        res = w.resolve("ROLLBACK")
        rb = RollbackService(w.storage)
        record = rb.prepare(p.TASK, "m1", "op_1", res.resolution_id)["rollback"]
        code = subprocess.run([sys.executable, "-B", "-c", script, str(w.storage), p.TASK, record["rollback_id"], *extra],
                              cwd=r"M:\GitHub\ag_llm").returncode
        session = rb.inspect(p.TASK, record["rollback_id"])
        print("  crash exit:", code, "| session:", session["status"], [t["status"] for t in session["targets"]])
        projection = ProjectionService(w.storage).build(p.TASK)
        print("  projection recovery:", projection["recovery"]["state"])
        print("  RC-4 itself could resume? ->", "yes (apply re-proves modulo own receipts)")
        result = w.recover()
        p.show("recover", result)
        session = rb.inspect(p.TASK, record["rollback_id"])
        restores = sum(1 for e in EventCheckpointStore(w.storage).read_events(p.TASK) if e.event_type == "ROLLBACK_TARGET_RESTORED")
        print("  session after recover:", session["status"], [t["status"] for t in session["targets"]],
              "| a.txt restored:", (w.project / "a.txt").read_bytes() == b"a-before\n",
              "| b.txt restored:", (w.project / "b.txt").exists() and (w.project / "b.txt").read_bytes() == b"b-before\n",
              "| restore events:", restores)
    finally:
        w.close()


if __name__ == "__main__":
    run("crash after first restore, before the second target started", CRASH_BETWEEN)
    run("crash inside the second write (T_APPLYING, write landed)", CRASH, "after_write")
    run("crash inside the second write (T_APPLYING, write not landed)", CRASH, "before_write")
