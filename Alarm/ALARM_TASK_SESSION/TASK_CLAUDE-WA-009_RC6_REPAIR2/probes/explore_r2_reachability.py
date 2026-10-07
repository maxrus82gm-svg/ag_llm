import sys
sys.path.insert(0, r"M:\GitHub\ag_llm\Alarm\ALARM_TASK_SESSION\TASK_CLAUDE-RC6-REVERIFY\probes")
import reverify_probes as p  # noqa: E402
from web_alarm.reconciliation_service import ReconciliationService  # noqa: E402

TASK = p.TASK


def dec(w, op):
    d = ReconciliationService(w.storage).reconcile(TASK, "m1", op)["DECISION"]
    return d["decision"], d["reason_code"]


print("== R2-G: ABORT op_a settled, then op_b begun (not landed), RETRY op_b")
w = p.World()
w.to_active("m1", "a.txt")
w.started("m1", "a.txt", op="op_a", landed=False)
w.machine.transition(TASK, "m1", "UNKNOWN_AFTER_DISCONNECT")
w.resolve("ABORT", op="op_a")
p.show("recover#1", w.recover())
w.started("m1", "a.txt", op="op_b", landed=False, payload=b"after2\n")
print(" decision op_b:", dec(w, "op_b"))
out = w.resolve("RETRY", op="op_b", must=False)
print(" RETRY op_b:", out["resolution"].result.value, out["resolution"].result_code)
if out["accepted"]:
    for i in (2, 3):
        r = w.recover()
        p.show(f"recover#{i}", r)
        print("   m1 =", w.micro("m1"))
w.close()

print("== R2-E: ADOPT op_a settled (m1 DONE), then op_b begun, partial landed?, ROLLBACK op_b")
w = p.World()
w.to_active("m1", "a.txt")
w.started("m1", "a.txt", op="op_a", landed=True)
w.machine.transition(TASK, "m1", "UNKNOWN_AFTER_DISCONNECT")
w.resolve("ADOPT", op="op_a")
p.show("recover#1", w.recover())
w.started("m1", "a.txt", op="op_b", landed=True, payload=b"after2\n")
print(" decision op_b:", dec(w, "op_b"))
for action in ("ROLLBACK", "ADOPT", "RETRY"):
    out = w.resolve(action, op="op_b", must=False)
    print(f" {action} op_b:", out["resolution"].result.value, out["resolution"].result_code)
w.close()

print("== R2-E2: ROLLBACK op_b in a 2-target microtask after ADOPT op_a? (a declared, b declared)")
w = p.World()
w.to_active("m1", "a.txt", "b.txt")
w.started("m1", "a.txt", op="op_a", landed=True)
w.started("m1", "b.txt", op="op_b", landed=True)
w.machine.transition(TASK, "m1", "UNKNOWN_AFTER_DISCONNECT")
print(" decisions:", dec(w, "op_a"), dec(w, "op_b"))
w.close()

print("== R2-E3: one op landed in 2-target microtask -> ROLLBACK op_a settled, then op_b begun in RECOVERY_REQUIRED m1 landed -> ADOPT?")
w = p.World()
w.to_active("m1", "a.txt", "b.txt")
w.started("m1", "a.txt", op="op_a", landed=True)
w.machine.transition(TASK, "m1", "UNKNOWN_AFTER_DISCONNECT")
print(" decision op_a:", dec(w, "op_a"))
w.resolve("ROLLBACK", op="op_a")
p.show("recover#1", w.recover())
print("  m1 =", w.micro("m1"), "| a =", w.read("a.txt"))
w.started("m1", "a.txt", op="op_b", landed=True, payload=b"after2\n")
w.write("b.txt", p.AFTER)
print(" decision op_b:", dec(w, "op_b"))
out = w.resolve("ADOPT", op="op_b", must=False)
print(" ADOPT op_b:", out["resolution"].result.value, out["resolution"].result_code)
w.close()
