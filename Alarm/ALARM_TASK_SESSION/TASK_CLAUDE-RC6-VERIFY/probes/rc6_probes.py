"""Independent adversarial probes for RC-6 (isolated temp storage only)."""
import sys
import tempfile
import traceback
from pathlib import Path
from unittest import mock

sys.path.insert(0, r"M:\GitHub\ag_llm")

from web_alarm.manifest_store import ManifestSnapshotStore  # noqa: E402
from web_alarm.models import MicrotaskStatus  # noqa: E402
from web_alarm.operation_store import OperationStore  # noqa: E402
from web_alarm.projection import ProjectionService  # noqa: E402
from web_alarm.reconciliation_service import ReconciliationService  # noqa: E402
from web_alarm.recovery_coordinator import RecoveryCoordinator  # noqa: E402
from web_alarm.resolver_service import ResolverService  # noqa: E402
from web_alarm.state_machine import ServerStateMachine  # noqa: E402
from web_alarm.target_claim_service import TargetClaimService  # noqa: E402
from web_alarm.task_store import TaskStore  # noqa: E402
from web_alarm.workspace_registry import WorkspaceRegistry  # noqa: E402

TASK = "task_v"
BEFORE, AFTER = b"before\n", b"after\n"


class World:
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.storage, self.project = root / "state", root / "project"
        self.project.mkdir()
        WorkspaceRegistry(self.storage).register("P", self.project, workspace_id="ws")
        self.tasks = TaskStore(self.storage)
        for task in (TASK, "task_foreign"):
            self.tasks.create_task("ws", task, "RAW", "Goal", task_id=task)
        for mid in ("m1", "m2"):
            self.tasks.create_microtask(TASK, mid, mid, microtask_id=mid)
        self.tasks.create_microtask("task_foreign", "f1", "f1", microtask_id="f1")
        self.machine = ServerStateMachine(self.storage)
        self.ops = OperationStore(self.storage)

    def close(self):
        self.tmp.cleanup()

    def write(self, name, data):
        (self.project / name).write_bytes(data)

    def to_active(self, mid, target):
        self.write(target, BEFORE)
        self.machine.prepare_microtask(TASK, mid, [(target, "edit")])
        self.machine.transition(TASK, mid, "READY")
        self.machine.transition(TASK, mid, "ACTIVE")

    def verify(self, mid):
        self.machine.transition(TASK, mid, "DONE")
        self.machine.transition(TASK, mid, "VERIFIED", verification_evidence="ok")

    def started(self, mid, target, op="op_1", *, landed):
        self.ops.begin(TASK, mid, "write", target, operation_id=op, payload=AFTER)
        self.ops.transition(TASK, op, "STARTED")
        if landed:
            self.write(target, AFTER)

    def resolve(self, action, mid="m1", op="op_1"):
        decision = ReconciliationService(self.storage).reconcile(TASK, mid, op)["DECISION"]
        out = ResolverService(self.storage).apply(
            TASK, mid, op, action, evidence_fingerprint=decision["evidence_fingerprint"],
            operation_revision=self.ops.get(TASK, op).revision)
        assert out["accepted"], (action, out["resolution"].result_code, out["resolution"].result_reason)
        return out["resolution"]

    def recover(self, **kw):
        return RecoveryCoordinator(self.storage).recover(TASK, **kw)

    def micro(self, mid):
        return self.tasks.open_microtask(TASK, mid).status.value


def show(label, result):
    steps = [s["action"] for s in result["performed_steps"]]
    print(f"  {label}: state={result['state']} recovery={result['recovery_state']} steps={steps}")
    if result["error"]:
        print(f"     error={result['error']} reason={result['reason'][:160]}")


def probe(name):
    def wrap(fn):
        print(f"\n### {name}")
        world = World()
        try:
            fn(world)
        except Exception:
            traceback.print_exc(limit=3)
        finally:
            world.close()
        return fn
    return wrap


@probe("P1 ADOPT settled -> microtask verified -> next microtask: does recover keep working?")
def p1(w):
    w.to_active("m1", "one.txt")
    w.started("m1", "one.txt", landed=True)
    w.machine.transition(TASK, "m1", "UNKNOWN_AFTER_DISCONNECT")
    w.resolve("ADOPT")
    show("recover#1", w.recover())
    print("  m1 =", w.micro("m1"))
    w.machine.transition(TASK, "m1", "VERIFIED", verification_evidence="adopted and checked")
    w.to_active("m2", "two.txt")
    projection = ProjectionService(w.storage).build(TASK)
    print("  projection after m2 ACTIVE: authority=", projection["authority_source"],
          "| recovery=", projection["recovery"]["state"], "| NEXT=", projection["next_safe_action"][:100])
    show("recover#2 (m2 ACTIVE, expected READY_FOR_EXECUTION)", w.recover())
    print("  m1 =", w.micro("m1"), "m2 =", w.micro("m2"))


@probe("P2 restore point corrupted under an ACTIVE microtask: false READY?")
def p2(w):
    w.to_active("m1", "one.txt")
    restore = w.tasks.task_directory(TASK) / "microtasks" / "m1" / "restore_point"
    next(restore.glob("snapshots/*.bin")).write_bytes(b"corrupt")
    projection = ProjectionService(w.storage).build(TASK)
    print("  restore point:", projection["restore_point"]["status"])
    show("recover", w.recover())


@probe("P3 RETRY accepted, then snapshot corrupted before re-arm: re-armed anyway?")
def p3(w):
    w.to_active("m1", "one.txt")
    w.started("m1", "one.txt", landed=False)
    w.machine.transition(TASK, "m1", "UNKNOWN_AFTER_DISCONNECT")
    w.resolve("RETRY")
    restore = w.tasks.task_directory(TASK) / "microtasks" / "m1" / "restore_point"
    next(restore.glob("snapshots/*.bin")).write_bytes(b"corrupt")
    show("recover", w.recover())
    print("  m1 =", w.micro("m1"))


@probe("P4 RETRY re-armed (READY), then a foreign TASK claims the primary target: replay still READY?")
def p4(w):
    w.to_active("m1", "one.txt")
    w.started("m1", "one.txt", landed=False)
    w.machine.transition(TASK, "m1", "UNKNOWN_AFTER_DISCONNECT")
    w.resolve("RETRY")
    show("recover#1", w.recover())
    w.ops.begin("task_foreign", "f1", "write", "one.txt", operation_id="op_f", payload=b"foreign\n")
    print("  foreign acquire:", TargetClaimService(w.storage).acquire("task_foreign", "op_f", operation_revision=1)["result"])
    show("recover#2 (foreign owner holds one.txt)", w.recover())


@probe("P5 RETRY for an operation of a VERIFIED microtask while the next microtask is ACTIVE")
def p5(w):
    w.to_active("m1", "one.txt")
    w.started("m1", "one.txt", landed=False)  # op never finished; microtask verified anyway
    w.verify("m1")
    w.resolve("RETRY")
    w.to_active("m2", "two.txt")
    projection = ProjectionService(w.storage).build(TASK)
    print("  recovery focus:", projection["recovery"]["state"], projection["recovery"]["operation_id"],
          "| lifecycle current:", projection["position"]["current_microtask_id"], projection["position"]["current_status"])
    show("recover", w.recover())


@probe("P6 ABORT for an operation of a VERIFIED microtask: persisted half-settlement?")
def p6(w):
    w.to_active("m1", "one.txt")
    w.started("m1", "one.txt", landed=False)
    w.verify("m1")
    w.resolve("ABORT")
    show("recover#1", w.recover())
    print("  op settlement:", w.ops.get(TASK, "op_1").recovery_settlement and w.ops.get(TASK, "op_1").recovery_settlement["action"],
          "| m1 =", w.micro("m1"))
    show("recover#2", w.recover())


@probe("P7 ABORT settled: is there any lifecycle way forward for the microtask?")
def p7(w):
    w.to_active("m1", "one.txt")
    w.started("m1", "one.txt", landed=True)
    w.machine.transition(TASK, "m1", "UNKNOWN_AFTER_DISCONNECT")
    w.resolve("ABORT")
    show("recover", w.recover())
    print("  m1 =", w.micro("m1"), "| state-machine exits from RECOVERY_REQUIRED:",
          sorted(s.value for s in ServerStateMachine._ALLOWED[MicrotaskStatus.RECOVERY_REQUIRED]))


@probe("P8 two coordinators decide SETTLE_ADOPT from the same projection (lost race)")
def p8(w):
    w.to_active("m1", "one.txt")
    w.started("m1", "one.txt", landed=True)
    w.machine.transition(TASK, "m1", "UNKNOWN_AFTER_DISCONNECT")
    w.resolve("ADOPT")
    slow, fast = RecoveryCoordinator(w.storage), RecoveryCoordinator(w.storage)
    stale_projection = slow.projection.build(TASK)
    show("fast", fast.recover(TASK))
    try:
        outcome = slow._perform(TASK, stale_projection, "SETTLE_ADOPT")
        print("  slow step on stale projection:", outcome.get("result"))
    except Exception as exc:
        print("  slow step on stale projection raised:", type(exc).__name__, str(exc)[:120])
    print("  op status:", w.ops.get(TASK, "op_1").status.value, "| m1 =", w.micro("m1"))


@probe("P9 ROLLBACK settled, then a fresh RETRY: does recover re-arm?")
def p9(w):
    w.write("keep.txt", b"keep\n")
    w.write("one.txt", BEFORE)
    w.machine.prepare_microtask(TASK, "m1", [("one.txt", "edit"), ("keep.txt", "delete")])
    w.machine.transition(TASK, "m1", "READY")
    w.machine.transition(TASK, "m1", "ACTIVE")
    w.started("m1", "one.txt", landed=True)
    w.machine.transition(TASK, "m1", "UNKNOWN_AFTER_DISCONNECT")
    w.resolve("ROLLBACK")
    show("recover#1", w.recover())
    print("  one.txt restored:", (w.project / "one.txt").read_bytes() == BEFORE, "| m1 =", w.micro("m1"))
    try:
        w.resolve("RETRY")
        show("recover#2 after fresh RETRY", w.recover())
        print("  m1 =", w.micro("m1"))
    except AssertionError as exc:
        print("  RETRY not accepted:", exc)


@probe("P1b same as P1, carried to the end: closeout-eligible task vs recover")
def p1b(w):
    from web_alarm.closeout import CloseoutService
    w.to_active("m1", "one.txt")
    w.started("m1", "one.txt", landed=True)
    w.machine.transition(TASK, "m1", "UNKNOWN_AFTER_DISCONNECT")
    w.resolve("ADOPT")
    w.recover()
    w.machine.transition(TASK, "m1", "VERIFIED", verification_evidence="adopted and checked")
    w.to_active("m2", "two.txt")
    w.verify("m2")
    print("  closeout eligible:", CloseoutService(w.storage).inspect(TASK)["eligible"])
    show("recover (expected TASK_READY_TO_CLOSE)", w.recover())


@probe("P14 rollback VERIFIED but claim release interrupted -> recover")
def p14(w):
    import web_alarm.rollback_service as rsm
    from web_alarm.rollback_service import RollbackService
    w.write("keep.txt", b"keep\n")
    w.write("one.txt", BEFORE)
    w.machine.prepare_microtask(TASK, "m1", [("one.txt", "edit"), ("keep.txt", "delete")])
    w.machine.transition(TASK, "m1", "READY")
    w.machine.transition(TASK, "m1", "ACTIVE")
    w.started("m1", "one.txt", landed=True)
    w.machine.transition(TASK, "m1", "UNKNOWN_AFTER_DISCONNECT")
    res = w.resolve("ROLLBACK")
    rb = RollbackService(w.storage)
    record = rb.prepare(TASK, "m1", "op_1", res.resolution_id)["rollback"]
    with mock.patch.object(rsm.RollbackService, "_release_claims", side_effect=rsm.TargetClaimStoreError("io")):
        rb.apply(TASK, record["rollback_id"])
    print("  session:", rb.inspect(TASK, record["rollback_id"])["status"], "released:", rb.inspect(TASK, record["rollback_id"])["claims_released"])
    show("recover", w.recover())
    print("  released now:", rb.inspect(TASK, record["rollback_id"])["claims_released"], "| restores in events:",
          sum(1 for e in __import__("web_alarm.event_checkpoint_store", fromlist=["x"]).EventCheckpointStore(w.storage).read_events(TASK) if e.event_type == "ROLLBACK_TARGET_RESTORED"))


@probe("P18 public entry input validation (server / CLI)")
def p18(w):
    import io
    from contextlib import redirect_stderr, redirect_stdout
    from web_alarm.cli import main
    from web_alarm.server import ApiError, WebAlarmApi
    api = WebAlarmApi(w.storage)
    for body in ({"max_recovery_steps": 0}, {"max_recovery_steps": True}, {"max_recovery_steps": "3"}, {"max_recovery_steps": 10**9}):
        try:
            status, payload = api.dispatch("POST", f"/tasks/{TASK}/recover", body)
            print("  server", body, "->", status, payload["state"])
        except ApiError as exc:
            print("  server", body, "->", exc.status, exc.code)
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(["--storage-root", str(w.storage), "task", "recover", "--task-id", TASK])
    print("  cli task recover ->", code, (err.getvalue() or out.getvalue())[:80].replace("\n", " "))
    try:
        status, payload = api.dispatch("POST", "/tasks/missing_task/recover", {})
        print("  server unknown task ->", status)
    except ApiError as exc:
        print("  server unknown task ->", exc.status, exc.code)


if __name__ == "__main__":
    pass
