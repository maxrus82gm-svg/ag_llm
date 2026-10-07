"""Repair #2 probe a10 re-run under the Repair #3 semantics (temp storage only).

a10 verified m1 through the state machine although op_1 was still STARTED. Since
Repair #3 (F-B) the state machine refuses exactly that; this probe shows (i) the
refusal and (ii) the same scenario on the legacy shape (VERIFIED written by the
blind storage primitive), followed by each newer recovery action:
- no write to project files, m1 stays VERIFIED, READY is never for op_1;
- RETRY / ROLLBACK stop for an explicit decision (no re-execution, no restore of a
  verified stage); ADOPT / ABORT are settled administratively, after which only the
  current stage m2 can be proved READY.
"""
import hashlib
import sys

sys.path.insert(0, r"M:\GitHub\ag_llm")
sys.path.insert(0, r"M:\GitHub\ag_llm\Alarm\ALARM_TASK_SESSION\TASK_CLAUDE-RC6-REVERIFY\probes")

from reverify_probes import TASK, World  # noqa: E402

from web_alarm.models import MicrotaskStatus  # noqa: E402
from web_alarm.state_machine import TransitionRejected  # noqa: E402


def project_digest(world):
    h = hashlib.sha256()
    for path in sorted(world.project.rglob("*")):
        if path.is_file():
            h.update(path.relative_to(world.project).as_posix().encode() + hashlib.sha256(path.read_bytes()).digest())
    return h.hexdigest()


ok = True
for action in ("RETRY", "ADOPT", "ABORT", "ROLLBACK"):
    world = World()
    try:
        for name, data in (("a.txt", b"a-before\n"), ("b.txt", b"b-before\n"), ("c.txt", b"c-keep\n")):
            world.write(name, data)
        world.machine.prepare_microtask(TASK, "m1", [("a.txt", "edit"), ("b.txt", "delete"), ("c.txt", "delete")])
        world.machine.transition(TASK, "m1", "READY")
        world.machine.transition(TASK, "m1", "ACTIVE")
        world.ops.begin(TASK, "m1", "write", "a.txt", operation_id="op_1", payload=b"a-after\n")
        world.ops.transition(TASK, "op_1", "STARTED")
        if action == "ADOPT":
            world.write("a.txt", b"a-after\n")
            (world.project / "b.txt").unlink()
            (world.project / "c.txt").unlink()
        elif action == "ROLLBACK":
            world.write("a.txt", b"a-after\n")
            (world.project / "b.txt").unlink()
        world.machine.transition(TASK, "m1", "DONE")
        try:
            world.machine.transition(TASK, "m1", "VERIFIED", verification_evidence="ok")
            admission = "VERIFIED ADMITTED (unexpected)"
            ok = False
        except TransitionRejected as exc:
            admission = "refused: " + exc.reason.split(":")[0]
        world.tasks.set_microtask_status(TASK, "m1", MicrotaskStatus.VERIFIED)  # legacy shape
        world.to_active("m2", "two.txt")
        out = world.resolve(action, must=False)
        if not out["accepted"]:
            print(f"{action}: admission {admission}; Resolver {out['resolution'].result.value}")
            continue
        before = project_digest(world)
        r = world.recover()
        proof = r["ready_proof"] or {}
        row = (r["state"], r["recovery_state"], [s["action"] for s in r["performed_steps"]],
               "project-write" if before != project_digest(world) else "no-project-write",
               world.micro("m1"), proof.get("microtask_id"))
        safe = row[3] == "no-project-write" and row[4] in ("VERIFIED", MicrotaskStatus.VERIFIED) and row[5] in (None, "m2")
        ok &= safe
        print(f"{action}: admission {admission}; recover {row} -> {'OK' if safe else 'FAIL'}")
    finally:
        world.close()
print("VERDICT:", "OK" if ok else "FAIL")
