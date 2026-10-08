"""RC-5 Repair #2 (CLAUDE-WA-016): closeout consistency with RC-6.

A-I  an accepted ROLLBACK of a VERIFIED stage (RC-6 R1: ROLLBACK_STAGE_PROTECTED) keeps
     ROLLBACK_PENDING: the TASK never closes over RC-6's human-decision boundary;
A-II an accepted ABORT / ADOPT, or a settlement whose administration is not finished, blocks
     closeout (RECOVERY_SETTLEMENT_PENDING) until RC-6 recover settles it; a contradicting
     settlement and any other non-advisory recovery state block too;
B    a COMPLETED / ARCHIVED TASK is read-only history: NEXT and authority come from the TASK
     status, the recovery facts it still carries stay as diagnostics;
plus real-process races of the gated completion against Resolver ABORT and RC-6 settlement.
"""

import json
import subprocess
import sys
import tempfile
import time
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock

import web_alarm.rollback_service as rs
from web_alarm.closeout import CloseoutService
from web_alarm.operation_store import OperationStore
from web_alarm.projection import ProjectionService, closeout_blockers
from web_alarm.reconciliation_service import ReconciliationService
from web_alarm.recovery_coordinator import RECOVERY_BLOCKED, TASK_COMPLETED, TASK_READY_TO_CLOSE, RecoveryCoordinator
from web_alarm.resolver_service import ResolverService
from web_alarm.rollback_service import RollbackService
from web_alarm.server import ApiError, WebAlarmApi
from web_alarm.state_machine import ServerStateMachine
from web_alarm.target_claim_service import TargetClaimError, TargetClaimService
from web_alarm.task_store import TaskStore
from web_alarm.workspace_registry import WorkspaceRegistry

REPO_ROOT = Path(__file__).resolve().parent
TASK = "task_c"
BEFORE, AFTER, KEEP = b"before\n", b"after-content\n", b"keep\n"
READ_ONLY = "TASK is COMPLETED; its state is read-only history"

FRESH_RECOVER = r"""
import json, sys
from web_alarm.closeout import CloseoutService
from web_alarm.recovery_coordinator import RecoveryCoordinator
storage, task_id = sys.argv[1:3]
before = [b["code"] for b in CloseoutService(storage).inspect(task_id)["blockers"]]
result = RecoveryCoordinator(storage).recover(task_id)
after = [b["code"] for b in CloseoutService(storage).inspect(task_id)["blockers"]]
print(json.dumps({"before": before, "state": result["state"],
                  "steps": [s["action"] for s in result["performed_steps"]], "after": after}))
"""


class Repair2Fixture(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        root = Path(self.tempdir.name)
        self.storage, self.project = root / "state", root / "project"
        self.project.mkdir()
        WorkspaceRegistry(self.storage).register("Project", self.project, workspace_id="ws_c")
        self.tasks = TaskStore(self.storage)
        self.tasks.create_task("ws_c", TASK, "RAW TASK", "Repair 2", task_id=TASK)
        self.ops = OperationStore(self.storage)
        self.machine = ServerStateMachine(self.storage)
        self.api = WebAlarmApi(self.storage)

    def write(self, name, data):
        (self.project / name).write_bytes(data)

    def stage(self, mid, specs, *, upto="VERIFIED"):
        """Create ``mid`` and walk it through the server state machine up to ``upto``."""
        for target, _ in specs:
            if not (self.project / target).exists():
                self.write(target, BEFORE)
        self.tasks.create_microtask(TASK, mid.upper(), mid, microtask_id=mid)
        self.machine.prepare_microtask(TASK, mid, specs)
        for status in ("READY", "ACTIVE", "DONE", "VERIFIED"):
            if status == "VERIFIED":
                self.machine.transition(TASK, mid, status, verification_evidence="checked")
            else:
                self.machine.transition(TASK, mid, status)
            if status == upto:
                return

    def resolve(self, action, op="op_1", mid="m2"):
        decision = ReconciliationService(self.storage).reconcile(TASK, mid, op)["DECISION"]
        outcome = ResolverService(self.storage).apply(
            TASK, mid, op, action, evidence_fingerprint=decision["evidence_fingerprint"],
            operation_revision=self.ops.get(TASK, op).revision)
        self.assertTrue(outcome["accepted"], outcome["resolution"].result_reason)
        return outcome["resolution"]

    def blockers(self):
        return [b["code"] for b in CloseoutService(self.storage).inspect(TASK)["blockers"]]

    def complete_via_api(self):
        try:
            return self.api.dispatch("POST", f"/tasks/{TASK}/complete", {})[1]["result"]
        except ApiError as exc:
            return exc.code

    def recover(self):
        return RecoveryCoordinator(self.storage).recover(TASK)

    def projection(self):
        return ProjectionService(self.storage).build(TASK)

    def two_verified_stages(self):
        self.stage("m1", [("one.txt", "edit")])
        self.stage("m2", [("two.txt", "edit"), ("keep.txt", "edit")])

    def assert_read_only_history(self, *, facts):
        projection = self.projection()
        self.assertEqual(projection["authority_source"], "task_status")
        self.assertTrue(projection["next_safe_action"].startswith(READ_ONLY), projection["next_safe_action"])
        if facts:  # the recovery facts stay visible as diagnostics
            self.assertTrue(projection["recovery"]["attention"])
            self.assertIn("historical evidence only", projection["next_safe_action"])
        else:
            self.assertEqual(projection["next_safe_action"], READ_ONLY)
        bundle = self.api.dispatch("GET", f"/tasks/{TASK}")[1]
        context = self.api.dispatch("GET", f"/tasks/{TASK}/context")[1]
        ui = self.api.dispatch("GET", f"/tasks/{TASK}/ui")[1]
        self.assertEqual(
            {bundle["projection"]["next_safe_action"], context["NEXT_SAFE_ACTION"], ui["next_safe_action"]},
            {projection["next_safe_action"]})
        self.assertEqual((context["AUTHORITY_SOURCE"], ui["authority_source"]), ("task_status", "task_status"))
        result = self.recover()
        self.assertEqual((result["state"], result["performed_steps"]), (TASK_COMPLETED, []))
        self.assertEqual(result["reason"], projection["next_safe_action"])
        return projection


class ProtectedRollbackTests(Repair2Fixture):
    """A-I: the RC-6 R1 rename never hides ROLLBACK_PENDING from the closeout gate."""

    def failed_operation_with_landed_write(self, *, begin_after_verification):
        self.stage("m1", [("one.txt", "edit")])
        specs = [("two.txt", "edit"), ("keep.txt", "edit")]
        self.stage("m2", specs, upto="VERIFIED" if begin_after_verification else "ACTIVE")
        self.ops.begin(TASK, "m2", "write", "two.txt", operation_id="op_1", payload=AFTER)
        self.ops.transition(TASK, "op_1", "FAILED")  # reported failure ...
        self.write("two.txt", AFTER)  # ... but the write landed
        if not begin_after_verification:
            self.machine.transition(TASK, "m2", "DONE")  # a FAILED operation does not hold verification
            self.machine.transition(TASK, "m2", "VERIFIED", verification_evidence="checked")

    def test_rollback_of_a_verified_stage_blocks_completion(self):
        for after in (False, True):
            with self.subTest(begin_after_verification=after):
                self.setUp()
                self.failed_operation_with_landed_write(begin_after_verification=after)
                self.assertEqual(self.blockers(), [])
                self.resolve("ROLLBACK")
                projection = self.projection()
                view = projection["operations"][0]["recovery"]
                self.assertEqual((view["state"], view["protected_state"]), ("ROLLBACK_STAGE_PROTECTED", "ROLLBACK_ACCEPTED"))

                self.assertEqual(self.blockers(), ["ROLLBACK_PENDING"])
                self.assertEqual(self.complete_via_api(), "closeout_rejected")
                self.assertEqual(self.recover()["state"], RECOVERY_BLOCKED)  # RC-6: a human decision
                self.assertTrue((self.storage / "tasks" / "active" / TASK).is_dir())
                self.assertEqual((self.project / "two.txt").read_bytes(), AFTER)  # nothing restored

    def test_explicit_abort_decision_makes_the_task_completable_again(self):
        self.failed_operation_with_landed_write(begin_after_verification=False)
        self.resolve("ROLLBACK")
        self.resolve("ABORT")  # the explicit project-level decision: keep the verified stage as it is
        self.assertEqual(self.blockers(), ["RECOVERY_SETTLEMENT_PENDING"])
        result = self.recover()
        self.assertEqual(([s["action"] for s in result["performed_steps"]], result["state"]),
                         (["SETTLE_ABORT"], TASK_READY_TO_CLOSE))
        self.assertEqual(self.blockers(), [])
        self.assertEqual(self.complete_via_api(), "COMPLETED")
        self.assertEqual((self.project / "two.txt").read_bytes(), AFTER)
        self.assert_read_only_history(facts=False)


class SettlementPendingTests(Repair2Fixture):
    """A-II: closeout waits for RC-6 to settle an accepted ABORT / ADOPT."""

    def test_unsettled_abort_blocks_until_recover_settles_it(self):
        for path in (["STARTED"], ["UNKNOWN_AFTER_DISCONNECT"], [], ["STARTED", "DONE", "VERIFIED"]):
            with self.subTest(operation_path=path):
                self.setUp()
                self.two_verified_stages()
                self.ops.begin(TASK, "m2", "write", "two.txt", operation_id="op_1", payload=AFTER)
                if "DONE" in path:
                    self.write("two.txt", AFTER)
                for status in path:
                    self.ops.transition(TASK, "op_1", status)
                self.resolve("ABORT")

                self.assertEqual(self.blockers(), ["RECOVERY_SETTLEMENT_PENDING"])
                self.assertEqual(self.complete_via_api(), "closeout_rejected")
                result = self.recover()
                self.assertEqual(([s["action"] for s in result["performed_steps"]], result["state"]),
                                 (["SETTLE_ABORT"], TASK_READY_TO_CLOSE))
                settlement = self.ops.get(TASK, "op_1").recovery_settlement
                self.assertEqual((settlement["action"], settlement["microtask_status"]), ("ABORT", "VERIFIED"))
                self.assertEqual(self.blockers(), [])
                self.assertEqual(self.complete_via_api(), "COMPLETED")
                self.assert_read_only_history(facts=False)

    def test_unsettled_adopt_blocks_until_recover_settles_it(self):
        self.stage("m1", [("one.txt", "edit")])
        self.stage("m2", [("two.txt", "edit")])
        self.ops.begin(TASK, "m2", "write", "two.txt", operation_id="op_1", payload=AFTER)
        self.ops.transition(TASK, "op_1", "STARTED")
        self.write("two.txt", AFTER)
        self.resolve("ADOPT")
        self.assertEqual(self.blockers(), ["RECOVERY_SETTLEMENT_PENDING"])
        self.assertEqual(self.complete_via_api(), "closeout_rejected")
        result = self.recover()
        self.assertEqual(([s["action"] for s in result["performed_steps"]], result["state"]),
                         (["SETTLE_ADOPT"], TASK_READY_TO_CLOSE))
        self.assertEqual(self.ops.get(TASK, "op_1").status.value, "VERIFIED")  # adopted with a receipt
        self.assertEqual(self.blockers(), [])

    def test_interrupted_settlement_blocks_until_a_fresh_process_finishes_it(self):
        self.stage("m1", [("one.txt", "edit")])
        self.stage("m2", [("two.txt", "edit")], upto="ACTIVE")
        self.ops.begin(TASK, "m2", "write", "two.txt", operation_id="op_1", payload=AFTER)
        self.assertEqual(TargetClaimService(self.storage).acquire(TASK, "op_1", operation_revision=1)["result"],
                         "ACQUIRED")
        self.ops.transition(TASK, "op_1", "STARTED")
        self.write("two.txt", AFTER)
        self.resolve("ADOPT")
        # the settlement and DONE are written, the claim release fails afterwards
        with mock.patch.object(TargetClaimService, "release", side_effect=TargetClaimError("io")):
            self.assertEqual(self.recover()["state"], "FAIL_CLOSED")
        self.assertEqual(self.ops.get(TASK, "op_1").recovery_settlement["action"], "ADOPT")
        self.machine.transition(TASK, "m2", "VERIFIED", verification_evidence="checked")  # only release is left

        blockers = self.blockers()
        self.assertIn("RECOVERY_SETTLEMENT_PENDING", blockers)
        self.assertIn("ACTIVE_CLAIM", blockers)
        self.assertEqual(self.complete_via_api(), "closeout_rejected")
        fresh = subprocess.run([sys.executable, "-B", "-c", FRESH_RECOVER, str(self.storage), TASK],
                               cwd=REPO_ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(fresh.returncode, 0, fresh.stderr)
        seen = json.loads(fresh.stdout)
        self.assertEqual(seen["before"], blockers)  # the same verdict after a restart
        self.assertEqual((seen["steps"], seen["state"], seen["after"]),
                         (["FINISH_SETTLEMENT"], TASK_READY_TO_CLOSE, []))
        self.assertEqual(self.complete_via_api(), "COMPLETED")


class CloseoutRuleTests(unittest.TestCase):
    """The pure rule over synthetic projections: contradictions, unknown states, advice."""

    @staticmethod
    def projection(state, *, op_status="FAILED", **recovery):
        view = {
            "operation_id": "op_1", "microtask_id": "m1", "status": op_status, "resolutions": [],
            "rollback_ids": [],
            "recovery": None if state is None else dict(
                {"state": state, "source": "resolver", "resolution_id": "res_1", "rollback_id": None,
                 "next_safe_action": f"next of {state}"}, **recovery),
        }
        return {
            "task": {"task_id": TASK, "status": "PLANNED", "location": "active"},
            "position": {"microtasks": [{"microtask_id": "m1", "status": "VERIFIED"}]},
            "blockers": [], "diagnostics": [], "operations": [view], "rollbacks": [],
            "ownership": {"active_claims": []},
        }

    def codes(self, *args, **kwargs):
        return [b["code"] for b in closeout_blockers(self.projection(*args, **kwargs))]

    def test_contradicting_and_pending_settlements_block(self):
        self.assertEqual(self.codes("SETTLEMENT_CONTRADICTION"), ["SETTLEMENT_CONTRADICTION"])
        for state in ("ABORT_ACCEPTED", "ADOPT_ACCEPTED", "ABORT_OVER_SETTLEMENT", "ADOPT_SETTLED",
                      "ABORT_SETTLED", "ROLLBACK_SETTLED"):
            with self.subTest(state=state):
                self.assertEqual(self.codes(state), ["RECOVERY_SETTLEMENT_PENDING"])
        self.assertEqual(self.codes("ROLLBACK_STAGE_PROTECTED", protected_state="ROLLBACK_ACCEPTED"),
                         ["ROLLBACK_PENDING"])

    def test_any_other_recovery_state_fails_closed(self):
        for state in ("ROLLBACK_CLOSED", "ROLLBACK_VERIFIED", "SOME_FUTURE_STATE"):
            with self.subTest(state=state):
                blockers = closeout_blockers(self.projection(state))
                self.assertEqual([b["code"] for b in blockers], ["RECOVERY_OPEN"])
                self.assertEqual(blockers[0]["next"], f"next of {state}")

    def test_advice_on_a_terminal_operation_and_no_recovery_stay_eligible(self):
        for state in ("ADOPT_REJECTED", "ROLLBACK_REJECTED", "RESOLUTION_STALE", None):
            with self.subTest(state=state):
                self.assertEqual(self.codes(state), [])

    def test_an_open_rollback_session_is_reported_once(self):
        projection = self.projection("ROLLBACK_PRESERVED", rollback_id="rb_1")
        projection["operations"][0]["rollback_ids"] = ["rb_1"]
        projection["rollbacks"] = [{"rollback_id": "rb_1", "status": "PRESERVED", "claims_released": False,
                                    "next_safe_action": "apply"}]
        self.assertEqual([b["code"] for b in closeout_blockers(projection)], ["ROLLBACK_OPEN"])


class _ProcessDeath(BaseException):
    """Simulated process death inside RC-4 apply (escapes every ``except Exception``)."""


class HistoricalTaskTests(Repair2Fixture):
    """B: a closed TASK shows read-only history, never an executable recovery NEXT."""

    def open_stage(self):
        self.stage("m1", [("a.txt", "edit"), ("keep.txt", "edit")], upto="ACTIVE")
        self.ops.begin(TASK, "m1", "write", "a.txt", operation_id="op_1", payload=AFTER)
        self.ops.transition(TASK, "op_1", "STARTED")
        self.write("a.txt", AFTER)

    def rollback_session(self):
        resolution = self.resolve("ROLLBACK", mid="m1")
        return RollbackService(self.storage).prepare(TASK, "m1", "op_1", resolution.resolution_id)["rollback"]

    def apply_with(self, rollback_id, patched):
        real = rs._write_restored_bytes
        rs._write_restored_bytes = patched
        try:
            RollbackService(self.storage).apply(TASK, rollback_id)
        except _ProcessDeath:
            pass
        finally:
            rs._write_restored_bytes = real

    def fixtures(self):
        def b1():
            pass

        def b2():
            self.resolve("ROLLBACK", mid="m1")

        def b3():
            self.rollback_session()

        def b4():
            record = self.rollback_session()

            def die(path, data):  # the write lands, then the process dies
                rs._atomic_write_bytes(path, data)
                raise _ProcessDeath
            self.apply_with(record["rollback_id"], die)

        def b5():
            record = self.rollback_session()

            def drift(path, data):
                rs._atomic_write_bytes(path, data)
                self.write("keep.txt", b"external drift\n")
            self.apply_with(record["rollback_id"], drift)

        def abort_unsettled():
            self.resolve("ABORT", mid="m1")

        return {"B1": b1, "B2": b2, "B3": b3, "B4": b4, "B5": b5, "ABORT": abort_unsettled}

    def test_legacy_completed_tasks_with_open_recovery_are_read_only(self):
        for name, build in self.fixtures().items():
            with self.subTest(fixture=name):
                self.setUp()
                self.open_stage()
                build()
                before = self.projection()
                self.assertNotEqual(before["recovery"]["state"], "NORMAL")
                self.tasks.complete_task(TASK)  # the old ungated storage primitive (legacy data)

                projection = self.assert_read_only_history(facts=True)
                # the facts stay as diagnostics (freshness of a closed TASK is unprovable, so a fresh
                # resolution may now read as stale: still a fact, never a NEXT)
                self.assertEqual(projection["recovery"]["attention"], ["op_1"])
                self.assertIsNotNone(projection["operations"][0]["recovery"])
                self.assertEqual(projection["rollbacks"], before["rollbacks"])

    def test_clean_and_archived_history(self):
        self.stage("m1", [("one.txt", "edit")])
        self.assertEqual(self.complete_via_api(), "COMPLETED")
        self.assert_read_only_history(facts=False)
        self.tasks.archive_task(TASK)
        projection = self.projection()
        self.assertEqual((projection["next_safe_action"], projection["authority_source"]),
                         ("TASK is ARCHIVED; its state is read-only history", "task_status"))


CHILD = r"""
import json, sys, time
from pathlib import Path
storage, barrier, name, mode = sys.argv[1:5]
import web_alarm.projection as projection_module
from web_alarm.closeout import CloseoutService
from web_alarm.recovery_coordinator import RecoveryCoordinator
from web_alarm.resolver_service import ResolverService
if mode == "complete":
    real = projection_module.ProjectionService.build
    def widened(self, task_id):  # test-only: hold the inspect -> complete window open
        result = real(self, task_id)
        time.sleep(0.3)
        return result
    projection_module.ProjectionService.build = widened
Path(barrier, f"ready_{name}").touch()
deadline = time.monotonic() + 60
while not Path(barrier, "go").exists():
    if time.monotonic() > deadline:
        raise SystemExit("barrier timeout")
    time.sleep(0.0005)
try:
    if mode == "complete":
        result = CloseoutService(storage, lock_timeout=60).complete("task_c")["result"]
    elif mode == "abort":
        fingerprint, revision = sys.argv[5:7]
        out = ResolverService(storage).apply("task_c", "m2", "op_1", "ABORT", evidence_fingerprint=fingerprint,
                                             operation_revision=int(revision))
        result = "ACCEPTED" if out["accepted"] else "REFUSED"
    else:
        result = RecoveryCoordinator(storage).recover("task_c")["state"]
except Exception as exc:
    result = "FAILED:" + type(exc).__name__
print(json.dumps({"name": name, "result": result}))
"""
ROUNDS = 4


class CloseoutRaceTests(Repair2Fixture):
    """Real processes: completion vs Resolver ABORT / RC-6 settlement never closes an unsettled ABORT."""

    def verified_operation(self):
        self.two_verified_stages()
        self.ops.begin(TASK, "m2", "write", "two.txt", operation_id="op_1", payload=AFTER)
        self.write("two.txt", AFTER)
        for status in ("STARTED", "DONE", "VERIFIED"):
            self.ops.transition(TASK, "op_1", status)
        self.assertEqual(self.blockers(), [])

    def race(self, jobs, extra=()):
        barrier = Path(self.tempdir.name) / "barrier"
        barrier.mkdir()
        processes = [subprocess.Popen([sys.executable, "-B", "-c", CHILD, str(self.storage), str(barrier), name, mode,
                                       *extra], cwd=REPO_ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                     for name, mode in jobs]
        try:
            deadline = time.monotonic() + 60
            while len(list(barrier.glob("ready_*"))) < len(jobs):
                if time.monotonic() > deadline:
                    self.fail("workers did not reach the start barrier")
                time.sleep(0.01)
            (barrier / "go").touch()
            results = {}
            for process in processes:
                stdout, stderr = process.communicate(timeout=120)
                self.assertEqual(process.returncode, 0, stderr)
                item = json.loads(stdout)
                results[item["name"]] = item["result"]
        finally:
            for process in processes:
                if process.poll() is None:
                    process.kill()
        return results

    def accepted_abort(self):
        return [r for r in ResolverService(self.storage).store.list(TASK, operation_id="op_1")
                if r.action.value == "ABORT" and r.result.value == "ACCEPTED"]

    def test_completion_racing_an_abort_acceptance(self):
        outcomes = Counter()
        for _ in range(ROUNDS):
            self.setUp()
            self.verified_operation()
            decision = ReconciliationService(self.storage).reconcile(TASK, "m2", "op_1")["DECISION"]
            results = self.race([("c", "complete"), ("a", "abort")],
                                (decision["evidence_fingerprint"], str(self.ops.get(TASK, "op_1").revision)))
            completed = (self.storage / "tasks" / "completed" / TASK).is_dir()
            outcomes[results["c"]] += 1
            if completed:
                self.assertEqual(results["c"], "COMPLETED")
                self.assertEqual(self.accepted_abort(), [])  # nothing accepted inside a closed TASK
            else:
                self.assertEqual((results["c"], results["a"]), ("REJECTED", "ACCEPTED"))
                self.assertEqual(self.blockers(), ["RECOVERY_SETTLEMENT_PENDING"])
        self.assertEqual(sum(outcomes.values()), ROUNDS)

    def test_completion_racing_the_rc6_settlement(self):
        outcomes = Counter()
        for _ in range(ROUNDS):
            self.setUp()
            self.verified_operation()
            self.resolve("ABORT")
            results = self.race([("c", "complete"), ("r", "recover")])
            outcomes[results["c"]] += 1
            settlement = OperationStore(self.storage).get(TASK, "op_1").recovery_settlement
            # no store writes into a closed TASK: a settlement present was written before completion
            self.assertIsNotNone(settlement)
            if results["c"] == "COMPLETED":
                self.assertTrue((self.storage / "tasks" / "completed" / TASK).is_dir())
            else:
                self.assertEqual(results["c"], "REJECTED")
                self.assertEqual(self.blockers(), [])  # settled afterwards: completable now
        self.assertEqual(sum(outcomes.values()), ROUNDS)


if __name__ == "__main__":
    unittest.main()
