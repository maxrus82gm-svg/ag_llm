"""Repair #3: reproduction of findings 1-5 (+ candidates) in temp storage only.

Run from the repository root: python -B <this file>
Prints one line per scenario: ID | observed | verdict (GAP = finding reproduced).
Never touches the live storage or project files.
"""

import json
import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path.cwd()))

from web_alarm.manifest_store import ManifestSnapshotStore, ManifestStoreError
from web_alarm.models import MicrotaskStatus, OperationStatus
from web_alarm.operation_store import OperationStore
from web_alarm.projection import ProjectionService
from web_alarm.reconciliation_service import ReconciliationService
from web_alarm.recovery_coordinator import READY_FOR_EXECUTION, RecoveryCoordinator
from web_alarm.resolver_service import ResolverService
from web_alarm.state_machine import ServerStateMachine, TransitionRejected
from web_alarm.target_claim_service import TargetClaimService
from web_alarm.task_store import TaskStore
from web_alarm.workspace_registry import WorkspaceRegistry

TASK = "task_r3"
BEFORE, AFTER = b"before\n", b"after\n"
results = []


def report(case, observed, gap):
    results.append((case, observed, "GAP" if gap else "closed"))
    print(f"{case} | {observed} | {'GAP' if gap else 'closed'}", flush=True)


class World:
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.storage, self.project = root / "state", root / "project"
        self.project.mkdir()
        WorkspaceRegistry(self.storage).register("R3", self.project, workspace_id="ws_r3")
        self.tasks = TaskStore(self.storage)
        self.tasks.create_task("ws_r3", "R3", "RAW", "Repair3", task_id=TASK)
        for mid in ("m1", "m2"):
            self.tasks.create_microtask(TASK, mid.upper(), mid, microtask_id=mid)
        self.sm = ServerStateMachine(self.storage)
        self.ops = OperationStore(self.storage)
        self.claims = TargetClaimService(self.storage)

    def close(self):
        self.tmp.cleanup()

    def activate(self, mid, *targets):
        for t in targets:
            (self.project / t).write_bytes(BEFORE)
        self.sm.prepare_microtask(TASK, mid, [(t, "edit") for t in targets])
        self.sm.transition(TASK, mid, MicrotaskStatus.READY)
        self.sm.transition(TASK, mid, MicrotaskStatus.ACTIVE)

    def start(self, mid, target, op):
        self.ops.begin(TASK, mid, "write", target, operation_id=op, payload=AFTER)
        self.ops.transition(TASK, op, OperationStatus.STARTED)

    def resolve(self, action, op, mid="m1"):
        decision = ReconciliationService(self.storage).reconcile(TASK, mid, op)["DECISION"]
        out = ResolverService(self.storage).apply(
            TASK, mid, op, action,
            evidence_fingerprint=decision["evidence_fingerprint"],
            operation_revision=self.ops.get(TASK, op).revision,
        )
        assert out["accepted"], out["resolution"].result_reason
        return out

    def micro(self, mid):
        return self.tasks.open_microtask(TASK, mid).status.value

    def recover(self):
        return RecoveryCoordinator(self.storage).recover(TASK)

    def authorize(self, op):
        return self.claims.authorize(TASK, op, operation_revision=self.ops.get(TASK, op).revision)

    def acquire(self, op):
        return self.claims.acquire(TASK, op, operation_revision=self.ops.get(TASK, op).revision)


def f1_new_operation_after_abort():
    w = World()
    try:
        w.activate("m1", "a.txt", "b.txt")
        w.start("m1", "a.txt", "op_1")
        w.sm.transition(TASK, "m1", MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT)
        w.resolve("ABORT", "op_1")
        r = w.recover()
        w.ops.begin(TASK, "m1", "write", "b.txt", operation_id="op_new", payload=AFTER)
        acq = w.acquire("op_new")
        auth = w.authorize("op_new")
        report("F1a new op on RECOVERY_REQUIRED microtask after ABORT",
               f"recover={r['state']} micro={w.micro('m1')} acquire={acq['result']} authorize={auth['result']}/{auth['result_code']}",
               auth["result"] == "AUTHORIZED")
    finally:
        w.close()


def f1_old_sibling_after_abort():
    w = World()
    try:
        w.activate("m1", "a.txt", "b.txt")
        w.ops.begin(TASK, "m1", "write", "b.txt", operation_id="op_old", payload=AFTER)
        acq = w.acquire("op_old")
        w.start("m1", "a.txt", "op_1")
        w.sm.transition(TASK, "m1", MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT)
        w.resolve("ABORT", "op_1")
        w.recover()
        auth = w.authorize("op_old")
        report("F1b old sibling op (claim before ABORT)",
               f"micro={w.micro('m1')} acquire(before)={acq['result']} authorize={auth['result']}/{auth['result_code']}",
               auth["result"] == "AUTHORIZED")
    finally:
        w.close()


def f1_pending_abort_sibling():
    w = World()
    try:
        w.activate("m1", "a.txt", "b.txt")
        w.ops.begin(TASK, "m1", "write", "b.txt", operation_id="op_old", payload=AFTER)
        w.acquire("op_old")
        w.start("m1", "a.txt", "op_1")
        w.resolve("ABORT", "op_1")  # accepted, not yet settled; m1 still ACTIVE
        auth = w.authorize("op_old")
        report("F1c sibling while accepted ABORT is not yet settled",
               f"micro={w.micro('m1')} authorize={auth['result']}/{auth['result_code']}",
               auth["result"] == "AUTHORIZED")
    finally:
        w.close()


def f1_verified_and_planned():
    w = World()
    try:
        w.activate("m1", "a.txt")
        w.sm.transition(TASK, "m1", MicrotaskStatus.DONE)
        w.sm.transition(TASK, "m1", MicrotaskStatus.VERIFIED, verification_evidence="ok")
        w.ops.begin(TASK, "m1", "write", "a.txt", operation_id="op_late", payload=AFTER)
        w.acquire("op_late")
        auth = w.authorize("op_late")
        w.ops.begin(TASK, "m2", "write", "a.txt", operation_id="op_planned", payload=b"x\n")
        auth2 = w.authorize("op_planned")
        report("F1d new op on VERIFIED microtask",
               f"micro={w.micro('m1')} authorize={auth['result']}/{auth['result_code']}",
               auth["result"] == "AUTHORIZED")
        report("F1e op of PLANNED microtask (no claim yet -> owner check first)",
               f"micro={w.micro('m2')} authorize={auth2['result']}/{auth2['result_code']}", False)
    finally:
        w.close()


def f2_abort_then_verified():
    w = World()
    try:
        w.activate("m1", "a.txt")
        w.start("m1", "a.txt", "op_1")
        w.resolve("ABORT", "op_1")
        w.sm.transition(TASK, "m1", MicrotaskStatus.DONE)
        try:
            w.sm.transition(TASK, "m1", MicrotaskStatus.VERIFIED, verification_evidence="ok")
            verified = "VERIFIED accepted"
        except TransitionRejected as exc:
            verified = f"VERIFIED rejected ({exc.reason[:60]})"
        states = [w.recover()["state"] for _ in range(3)]
        stuck = verified == "VERIFIED accepted" and all(s == "FAIL_CLOSED" for s in states)
        report("F2a accepted ABORT, then VERIFIED, then settlement",
               f"{verified}; recover x3={states}; micro={w.micro('m1')}", stuck)
    finally:
        w.close()


def f2_verified_then_abort():
    w = World()
    try:
        w.activate("m1", "a.txt")
        w.ops.begin(TASK, "m1", "write", "a.txt", operation_id="op_1", payload=AFTER)
        w.ops.transition(TASK, "op_1", OperationStatus.STARTED)
        (w.project / "a.txt").write_bytes(AFTER)
        w.ops.transition(TASK, "op_1", OperationStatus.DONE)
        w.sm.transition(TASK, "m1", MicrotaskStatus.DONE)
        w.sm.transition(TASK, "m1", MicrotaskStatus.VERIFIED, verification_evidence="ok")
        w.resolve("ABORT", "op_1")  # a later explicit decision about an op of a VERIFIED stage
        states = [w.recover()["state"] for _ in range(3)]
        report("F2b VERIFIED first, ABORT accepted later",
               f"recover x3={states}; micro={w.micro('m1')}",
               all(s == "FAIL_CLOSED" for s in states))
    finally:
        w.close()


def f3_tampered_restore_point_between_proof_and_return():
    w = World()
    try:
        w.activate("m1", "a.txt")
        (w.project / "z.txt").write_bytes(b"other\n")
        rp = w.tasks.task_directory(TASK) / "microtasks" / "m1" / "restore_point"
        real = RecoveryCoordinator._prove_normal_ready

        def prove_then_retarget(coordinator, task_id, projection):
            out = real(coordinator, task_id, projection)
            # consistent rewrite of entry + snapshot metadata: manifest.json (id,
            # updated_at) untouched, pure verification still passes
            for sub in ("manifest_entries", "snapshots"):
                for path in (rp / sub).glob("*.json"):
                    data = json.loads(path.read_text(encoding="utf-8"))
                    data["source_path"] = "z.txt"
                    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return out

        with mock.patch.object(RecoveryCoordinator, "_prove_normal_ready", prove_then_retarget):
            r = w.recover()
        proof = r["ready_proof"] or {}
        now = ManifestSnapshotStore(w.storage).restore_plan(TASK, "m1")["restore_point_fingerprint"]
        report("F3 restore point/target set changed after proof, surface ids unchanged",
               f"state={r['state']} proof_rpf={str(proof.get('restore_point_fingerprint'))[:12]} now_rpf={now[:12]}",
               r["state"] == READY_FOR_EXECUTION and proof.get("restore_point_fingerprint") != now)
    finally:
        w.close()


CRASH_CHILD = """
import os, sys
sys.path.insert(0, {repo!r})
from web_alarm.task_store import TaskStore
from web_alarm.state_machine import ServerStateMachine
from web_alarm.models import MicrotaskStatus
real_plan = TaskStore._write_plan
def plan_then_die(self, task_dir, plan):
    real_plan(self, task_dir, plan)
    if plan.current_microtask_id == "m1":
        os._exit(17)   # process crash between the plan write and the status write
TaskStore._write_plan = plan_then_die
ServerStateMachine({storage!r}).transition({task!r}, "m1", MicrotaskStatus.ACTIVE)
"""


def f4_activation_crash():
    w = World()
    try:
        (w.project / "a.txt").write_bytes(BEFORE)
        w.sm.prepare_microtask(TASK, "m1", [("a.txt", "edit")])
        w.sm.transition(TASK, "m1", MicrotaskStatus.READY)
        child = subprocess.run(
            [sys.executable, "-B", "-c", CRASH_CHILD.format(repo=str(Path.cwd()), storage=str(w.storage), task=TASK)],
            capture_output=True, text=True,
        )
        plan = w.tasks.open_plan(TASK)
        projection = ProjectionService(w.storage).build(TASK)
        pos = projection["position"]
        after = w.recover()["state"]
        w.sm.transition(TASK, "m1", MicrotaskStatus.ACTIVE)
        report("F4 crash between plan pointer and ACTIVE write",
               f"exit={child.returncode} plan.current={plan.current_microtask_id} micro_after_crash=READY? "
               f"pointer_state={pos['plan_pointer_state']} blockers={[b['code'] for b in projection['blockers']]} "
               f"recover={after} reactivate->micro={w.micro('m1')}",
               pos["plan_pointer_state"] not in ("CORROBORATED",) or projection["blockers"])
    finally:
        w.close()


def f5_stale_verification_blocks_advanced_restore_point():
    w = World()
    try:
        (w.project / "a.txt").write_bytes(BEFORE)
        w.sm.prepare_microtask(TASK, "m1", [("a.txt", "edit")])
        w.sm.transition(TASK, "m1", MicrotaskStatus.READY)
        real = ManifestSnapshotStore._load_paired_records
        fired = []

        def concurrent_winner_then_transient_failure(self, task_id, microtask_id, *, active_only=False):
            if active_only and not fired:
                fired.append(1)
                # the concurrent winner: the microtask advances meanwhile ...
                for status in (MicrotaskStatus.ACTIVE, MicrotaskStatus.DONE, MicrotaskStatus.VERIFIED):
                    TaskStore(w.storage).set_microtask_status(task_id, microtask_id, status)
                # ... and this stale verification meets a transient read failure
                raise ManifestStoreError("transient: cannot read JSON record (sharing violation)")
            return real(self, task_id, microtask_id, active_only=active_only)

        with mock.patch.object(ManifestSnapshotStore, "_load_paired_records", concurrent_winner_then_transient_failure):
            try:
                w.sm.transition(TASK, "m1", MicrotaskStatus.ACTIVE)
                outcome = "transition accepted"
            except TransitionRejected:
                outcome = "stale transition rejected"
        manifest = ManifestSnapshotStore(w.storage).open_manifest(TASK, "m1").status.value
        report("F5 stale failing verification vs advanced microtask",
               f"{outcome}; micro={w.micro('m1')} manifest={manifest}",
               w.micro("m1") == "VERIFIED" and manifest == "BLOCKED_PREPARE")
    finally:
        w.close()


def c1_abort_on_failed_operation():
    w = World()
    try:
        w.activate("m1", "a.txt")
        w.ops.begin(TASK, "m1", "write", "a.txt", operation_id="op_f", payload=AFTER)
        w.ops.transition(TASK, "op_f", OperationStatus.FAILED)
        w.resolve("ABORT", "op_f")
        states = [w.recover()["state"] for _ in range(2)]
        report("C1 accepted ABORT for a FAILED (terminal) operation",
               f"recover x2={states}; micro={w.micro('m1')}",
               all(s == "FAIL_CLOSED" for s in states))
    finally:
        w.close()


if __name__ == "__main__":
    for case in (f1_new_operation_after_abort, f1_old_sibling_after_abort, f1_pending_abort_sibling,
                 f1_verified_and_planned, f2_abort_then_verified, f2_verified_then_abort,
                 f3_tampered_restore_point_between_proof_and_return, f4_activation_crash,
                 f5_stale_verification_blocks_advanced_restore_point, c1_abort_on_failed_operation):
        try:
            case()
        except Exception as exc:  # a probe must report, not hide, an unexpected path
            report(case.__name__, f"EXCEPTION {type(exc).__name__}: {exc}", True)
