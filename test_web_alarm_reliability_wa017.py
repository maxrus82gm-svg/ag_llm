"""CLAUDE-WA-017: crash-safe TASK completion (F-5) and checkpoint rebuild failures (F-6).

F-5  the directory move active/ -> completed/ is the one commit point of a completion and the
     COMPLETED status is written after it. Real process deaths at every point leave either the
     untouched active TASK or a closed one; a closed TASK — moved, closed by its status only (an
     interrupted pre-WA-017 completion) or completed — accepts no writer and never grants
     mutation authority again; a second gated `task complete` finishes an interrupted completion.
F-6  a failed checkpoint rebuild is a fail-closed outcome, never lost data: the previous
     checkpoint stays byte-identical, nothing half-written is left, and a missing, corrupt,
     truncated, partial or tampered checkpoint never validates as VALID.
"""

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path
from unittest import mock

import web_alarm.event_checkpoint_store as ecs
import web_alarm.task_store as task_store_module
from web_alarm.closeout import CloseoutError, CloseoutService
from web_alarm.event_checkpoint_store import EventCheckpointStore
from web_alarm.manifest_store import ManifestSnapshotStore
from web_alarm.models import TaskStatus
from web_alarm.operation_store import OperationStore
from web_alarm.projection import ProjectionError, ProjectionService
from web_alarm.recovery_coordinator import TASK_COMPLETED, RecoveryCoordinator
from web_alarm.remote_entry import RemoteEntry
from web_alarm.resolver_service import ResolverService
from web_alarm.state_machine import ServerStateMachine
from web_alarm.target_claim_service import TargetClaimService
from web_alarm.task_store import (
    COMPLETION_ACTIVE,
    COMPLETION_DONE,
    COMPLETION_MOVED_STATUS_PENDING,
    COMPLETION_STATUS_WRITTEN_NOT_MOVED,
    TaskStore,
    TaskStoreError,
)
from web_alarm.workspace_registry import WorkspaceRegistry

REPO_ROOT = Path(__file__).resolve().parent
TASK = "task_w"

# A real process death (os._exit) at one point of a gated completion.
DIE_DURING_COMPLETION = """
    import os, sys
    from pathlib import Path
    import web_alarm.task_store as ts
    point, storage, task = sys.argv[1:4]
    real_replace, real_write = ts.os.replace, ts.TaskStore._write_task
    def replace(src, dst):
        if Path(src).is_dir():  # the directory move of complete_task_locked
            if point == "before_move":
                os._exit(9)
            real_replace(src, dst)
            if point == "after_move":
                os._exit(9)
            return None
        return real_replace(src, dst)
    def write_task(self, task_dir, record):
        real_write(self, task_dir, record)
        if point == "after_status" and record.status.value == "COMPLETED":
            os._exit(9)
    ts.os.replace = replace
    ts.TaskStore._write_task = write_task
    from web_alarm.closeout import CloseoutService
    print(CloseoutService(storage).complete(task)["result"])
"""

FRESH_COMPLETE = """
    import json, sys
    from web_alarm.closeout import CloseoutService
    out = CloseoutService(sys.argv[1]).complete(sys.argv[2])
    print(json.dumps({"result": out["result"], "resumed": out.get("resumed")}))
"""

HOLD_OPEN = """
    import sys, time
    handle = open(sys.argv[1], "rb")
    print("held", flush=True)
    time.sleep(float(sys.argv[2]))
"""


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        root = Path(self.tempdir.name)
        self.storage, self.project = root / "state", root / "project"
        self.project.mkdir()
        for name in ("one.txt", "two.txt"):
            (self.project / name).write_bytes(name.encode() + b"\n")
        WorkspaceRegistry(self.storage).register("Project", self.project, workspace_id="ws_w")
        self.tasks = TaskStore(self.storage)
        self.tasks.create_task("ws_w", TASK, "RAW TASK", "WA-017", task_id=TASK)
        self.machine = ServerStateMachine(self.storage)

    def stage(self, mid, target, *, upto="VERIFIED", task=TASK):
        self.tasks.create_microtask(task, mid.upper(), mid, microtask_id=mid)
        self.machine.prepare_microtask(task, mid, [(target, "edit")])
        for status in ("READY", "ACTIVE", "DONE", "VERIFIED"):
            if status == "VERIFIED":
                self.machine.transition(task, mid, status, verification_evidence="checked")
            else:
                self.machine.transition(task, mid, status)
            if status == upto:
                return

    def child(self, script, *args):
        return subprocess.run([sys.executable, "-B", "-c", textwrap.dedent(script), *args],
                              cwd=REPO_ROOT, capture_output=True, text=True, timeout=120)

    def die_during_completion(self, point):
        out = self.child(DIE_DURING_COMPLETION, point, str(self.storage), TASK)
        self.assertEqual(out.returncode, 9, out.stderr)

    def fresh_complete(self):
        out = self.child(FRESH_COMPLETE, str(self.storage), TASK)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout)

    def where(self):
        if (self.tasks.active_dir / TASK).is_dir():
            return "active"
        return "completed" if (self.tasks.completed_dir / TASK).is_dir() else "missing"

    def interrupt_pre_wa017(self):
        """The shape a pre-WA-017 crash left: COMPLETED written, the TASK never moved."""
        task = self.tasks.open_task(TASK)
        task.status = TaskStatus.COMPLETED
        self.tasks._write_task(self.tasks.active_dir / TASK, task)

    def assert_closed_for_every_writer(self, operation_id=None):
        writers = {
            "operation begin": lambda: OperationStore(self.storage).begin(
                TASK, "m1", "write", "two.txt", operation_id="op_late", payload=b"late\n"),
            "microtask create": lambda: self.tasks.create_microtask(TASK, "late", "late", microtask_id="late"),
            "microtask status": lambda: self.tasks.set_microtask_status(TASK, "m1", "ACTIVE"),
            "restore point": lambda: ManifestSnapshotStore(self.storage).prepare_microtask(
                TASK, "m1", [("two.txt", "edit")]),
            "checkpoint rebuild": lambda: ProjectionService(self.storage).rebuild_checkpoint(TASK),
        }
        if operation_id is not None:
            writers["operation transition"] = lambda: OperationStore(self.storage).transition(
                TASK, operation_id, "FAILED")
            writers["resolution"] = lambda: ResolverService(self.storage).apply(
                TASK, "m1", operation_id, "ABORT", evidence_fingerprint="0" * 64, operation_revision=1)
        accepted = []
        for name, write in writers.items():
            try:
                write()
                accepted.append(name)
            except Exception:  # noqa: BLE001 — every refusal type is fine, an acceptance is not
                pass
        self.assertEqual(accepted, [])
        self.assertNotIn(TASK, RemoteEntry(self.storage).active_task_ids())
        self.assertEqual(RecoveryCoordinator(self.storage).recover(TASK)["state"], TASK_COMPLETED)


class CrashSafeCompletionTests(Fixture):
    """F-5: process deaths and failures at every point of a gated completion."""

    def test_death_after_the_move_leaves_a_closed_task_that_a_fresh_process_finishes(self):
        self.stage("m1", "one.txt")
        self.die_during_completion("after_move")

        self.assertEqual((self.where(), self.tasks.open_task(TASK).status), ("completed", TaskStatus.PLANNED))
        self.assertEqual(self.tasks.completion_state(TASK), COMPLETION_MOVED_STATUS_PENDING)
        projection = ProjectionService(self.storage).build(TASK)
        self.assertIn("INTERRUPTED_COMPLETION", [d["code"] for d in projection["diagnostics"]])
        self.assertEqual(projection["authority_source"], "task_status")
        self.assertIn("finish its completion record with the gated `task complete`", projection["next_safe_action"])
        self.assertEqual([b["code"] for b in CloseoutService(self.storage).inspect(TASK)["blockers"]],
                         ["TASK_NOT_ACTIVE"])
        self.assert_closed_for_every_writer()

        self.assertEqual(self.fresh_complete(), {"result": "COMPLETED", "resumed": COMPLETION_MOVED_STATUS_PENDING})
        self.assertEqual((self.where(), self.tasks.open_task(TASK).status), ("completed", TaskStatus.COMPLETED))
        events = EventCheckpointStore(self.storage).read_events(TASK)
        self.assertEqual((events[-1].event_type, events[-1].payload["resumed"]),
                         ("TASK_COMPLETED", COMPLETION_MOVED_STATUS_PENDING))
        self.assertEqual(ProjectionService(self.storage).build(TASK)["next_safe_action"],
                         "TASK is COMPLETED; its state is read-only history")
        self.assertEqual(CloseoutService(self.storage).complete(TASK)["result"], "REJECTED")  # replay

    def test_death_before_the_move_changes_nothing(self):
        self.stage("m1", "one.txt")
        before = self.tasks.open_task(TASK)
        self.die_during_completion("before_move")

        self.assertEqual(self.where(), "active")
        self.assertEqual(self.tasks.open_task(TASK), before)  # not a byte of task.json changed
        self.assertEqual(self.tasks.completion_state(TASK), COMPLETION_ACTIVE)
        self.assertEqual([b["code"] for b in CloseoutService(self.storage).inspect(TASK)["blockers"]], [])
        self.assertEqual(self.fresh_complete(), {"result": "COMPLETED", "resumed": None})

    def test_death_after_the_status_write_is_a_finished_completion(self):
        self.stage("m1", "one.txt")
        self.die_during_completion("after_status")

        self.assertEqual((self.where(), self.tasks.completion_state(TASK)), ("completed", COMPLETION_DONE))
        self.assertEqual(ProjectionService(self.storage).build(TASK)["next_safe_action"],
                         "TASK is COMPLETED; its state is read-only history")
        self.assert_closed_for_every_writer()
        self.assertEqual(self.fresh_complete(), {"result": "REJECTED", "resumed": None})  # nothing left to do

    def test_a_failed_move_writes_nothing_and_the_task_stays_active(self):
        self.stage("m1", "one.txt")
        before = (self.tasks.active_dir / TASK / "task.json").read_bytes()
        real = task_store_module.os.replace

        def refuse_directory(src, dst):
            if Path(src).is_dir():
                raise PermissionError(13, "a file of the TASK is open (test)")
            return real(src, dst)
        with mock.patch.object(task_store_module.os, "replace", refuse_directory):
            with self.assertRaises(CloseoutError):
                CloseoutService(self.storage).complete(TASK)

        self.assertEqual(self.where(), "active")
        self.assertEqual((self.tasks.active_dir / TASK / "task.json").read_bytes(), before)
        self.assertEqual(CloseoutService(self.storage).complete(TASK)["result"], "COMPLETED")

    def test_a_failed_status_write_after_the_move_is_finished_later(self):
        self.stage("m1", "one.txt")
        with mock.patch.object(TaskStore, "_write_task", side_effect=TaskStoreError("disk full (test)")):
            with self.assertRaises(CloseoutError):
                CloseoutService(self.storage).complete(TASK)
        self.assertEqual(self.tasks.completion_state(TASK), COMPLETION_MOVED_STATUS_PENDING)
        self.assert_closed_for_every_writer()
        self.assertEqual(CloseoutService(self.storage).complete(TASK)["resumed"], COMPLETION_MOVED_STATUS_PENDING)
        self.assertEqual(self.tasks.completion_state(TASK), COMPLETION_DONE)


class InterruptedPreWA017CompletionTests(Fixture):
    """F-5: the shape a pre-WA-017 crash left (COMPLETED written, TASK never moved)."""

    def test_status_closed_task_in_active_accepts_no_writer_and_is_finished_after_a_new_proof(self):
        self.tasks.create_task("ws_w", "other", "RAW", "other", task_id="other")
        self.stage("m1", "one.txt")
        self.interrupt_pre_wa017()

        self.assertEqual(self.tasks.completion_state(TASK), COMPLETION_STATUS_WRITTEN_NOT_MOVED)
        self.assert_closed_for_every_writer()
        self.assertEqual(RemoteEntry(self.storage).resolve_task_id(), "other")  # the entry still works
        projection = ProjectionService(self.storage).build(TASK)
        self.assertIn("INTERRUPTED_COMPLETION", [d["code"] for d in projection["diagnostics"]])
        self.assertIn("pre-WA-017 order", projection["next_safe_action"])

        out = CloseoutService(self.storage).complete(TASK)
        self.assertEqual((out["result"], out["resumed"]), ("COMPLETED", COMPLETION_STATUS_WRITTEN_NOT_MOVED))
        self.assertEqual((self.where(), self.tasks.completion_state(TASK)), ("completed", COMPLETION_DONE))

    def test_state_added_before_the_crash_by_older_writers_keeps_it_unmoved(self):
        self.stage("m1", "one.txt")
        OperationStore(self.storage).begin(TASK, "m1", "write", "two.txt", operation_id="op_old", payload=b"x\n")
        self.interrupt_pre_wa017()

        out = CloseoutService(self.storage).complete(TASK)
        self.assertEqual((out["result"], [b["code"] for b in out["closeout"]["blockers"]]),
                         ("REJECTED", ["OPERATION_OPEN"]))
        self.assertEqual(self.where(), "active")  # not moved over an open operation
        self.assert_closed_for_every_writer(operation_id="op_old")  # and still closed for writers


class ClosedTaskAuthorityTests(Fixture):
    """F-5 invariant: a closed TASK never grants mutation authority again (RC-3 boundary)."""

    def test_no_mutation_authority_for_any_closed_shape(self):
        for shape in ("completed by the storage primitive", "moved, status pending", "status closed in active/"):
            with self.subTest(shape=shape):
                self.setUp()
                self.stage("m1", "one.txt", upto="ACTIVE")  # deliberately not closable through the gate
                OperationStore(self.storage).begin(TASK, "m1", "write", "one.txt", operation_id="op_1",
                                                   payload=b"x\n")
                claims = TargetClaimService(self.storage)
                self.assertEqual(claims.acquire(TASK, "op_1", operation_revision=1)["result"], "ACQUIRED")
                self.assertTrue(claims.authorize(TASK, "op_1", operation_revision=1)["authorized"])
                if shape == "completed by the storage primitive":
                    self.tasks.complete_task(TASK)
                elif shape == "moved, status pending":
                    with mock.patch.object(TaskStore, "_write_task", side_effect=TaskStoreError("test")):
                        with self.assertRaises(TaskStoreError):
                            self.tasks.complete_task(TASK)
                else:
                    self.interrupt_pre_wa017()

                outcome = claims.authorize(TASK, "op_1", operation_revision=1)
                self.assertEqual((outcome["result"], outcome["result_code"], outcome["authorized"]),
                                 ("DENIED", "TASK_CLOSED", False))
                with claims.mutation_boundary(TASK, "op_1", operation_revision=1) as boundary:
                    self.assertFalse(boundary["mutation_authority"])


CRASH_RACE_CHILD = r"""
import json, os, sys, time
from pathlib import Path
storage, barrier, name, mode = sys.argv[1:5]
import web_alarm.task_store as ts
if mode == "complete_die":
    real_replace = ts.os.replace
    def replace(src, dst):
        if Path(src).is_dir():
            real_replace(src, dst)
            os._exit(9)  # dies right after the commit point, holding both TASK locks
        return real_replace(src, dst)
    ts.os.replace = replace
from web_alarm.closeout import CloseoutService
from web_alarm.operation_store import OperationStore
from web_alarm.task_store import TaskStore
Path(barrier, f"ready_{name}").touch()
while not Path(barrier, "go").exists():
    time.sleep(0.0005)
if mode != "complete_die":
    time.sleep(0.05 * int(name[-1]))
try:
    if mode == "complete_die":
        result = CloseoutService(storage, lock_timeout=60).complete("task_w")["result"]
    elif mode == "begin":
        OperationStore(storage, lock_timeout=60).begin("task_w", "m1", "write", "two.txt",
                                                       operation_id="op_" + name, payload=b"x\n")
        result = "BEGUN"
    else:
        TaskStore(storage, lock_timeout=60).create_microtask("task_w", "late", "late", microtask_id="late_" + name)
        result = "CREATED"
except Exception as exc:
    result = "FAILED:" + type(exc).__name__
print(json.dumps({"name": name, "result": result}))
"""


class CompletionCrashRaceTests(Fixture):
    """F-5, real processes: a completion dying right after its commit point vs concurrent writers."""

    def test_writers_racing_a_dying_completion_never_land_in_the_closed_task(self):
        for _ in range(4):
            self.setUp()
            self.stage("m1", "one.txt")
            barrier = Path(self.tempdir.name) / "barrier"
            barrier.mkdir()
            jobs = [("c0", "complete_die"), ("b1", "begin"), ("b2", "begin"), ("m3", "microtask")]
            procs = [subprocess.Popen([sys.executable, "-B", "-c", CRASH_RACE_CHILD, str(self.storage), str(barrier),
                                       name, mode], cwd=REPO_ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      text=True) for name, mode in jobs]
            try:
                deadline = time.monotonic() + 60
                while len(list(barrier.glob("ready_*"))) < len(jobs):
                    self.assertLess(time.monotonic(), deadline, "workers did not reach the barrier")
                    time.sleep(0.01)
                (barrier / "go").touch()
                results = {}
                for proc, (name, _) in zip(procs, jobs):
                    out, err = proc.communicate(timeout=120)
                    results[name] = json.loads(out)["result"] if out.strip() else f"EXIT {proc.returncode}"
            finally:
                for proc in procs:
                    if proc.poll() is None:
                        proc.kill()
            ops = [op.operation_id for op in OperationStore(self.storage).list(TASK)]
            plan = self.tasks.open_plan(TASK).microtask_ids
            if self.where() == "completed":  # the dying completion committed first
                self.assertEqual(results["c0"], "EXIT 9")
                self.assertEqual((ops, plan), ([], ["m1"]))  # nothing landed inside the closed TASK
                self.assertTrue(all(results[n].startswith("FAILED") for n in ("b1", "b2", "m3")), results)
                self.assertEqual(CloseoutService(self.storage).complete(TASK)["resumed"],
                                 COMPLETION_MOVED_STATUS_PENDING)
            else:  # a writer came first: the gate refused, the TASK stays active with what was admitted
                self.assertEqual(results["c0"], "REJECTED")
                self.assertTrue(ops or plan != ["m1"])


class CheckpointRebuildFailureTests(Fixture):
    """F-6: a failed rebuild is fail-closed, never lost or falsely VALID data."""

    def setUp(self):
        super().setUp()
        self.tasks.create_microtask(TASK, "M1", "m1", microtask_id="m1")
        self.projection = ProjectionService(self.storage)
        self.checkpoint = self.tasks.task_directory(TASK) / "checkpoint.json"

    def refuse_replace(self, name):
        real = ecs.os.replace

        def refuse(src, dst):
            if Path(dst).name == name:
                raise PermissionError(13, "sharing violation (test)", str(dst))
            return real(src, dst)
        return mock.patch.object(ecs.os, "replace", refuse)

    def leftovers(self):
        return [p.name for p in self.checkpoint.parent.iterdir() if p.name.endswith(".tmp")]

    def test_a_failed_first_rebuild_leaves_nothing_and_validates_missing(self):
        with self.refuse_replace("checkpoint.json"), self.assertRaises(ProjectionError):
            self.projection.rebuild_checkpoint(TASK)
        self.assertFalse(self.checkpoint.exists())
        self.assertEqual(self.leftovers(), [])
        self.assertEqual(self.projection.validate_checkpoint(TASK)["status"], "MISSING")
        self.assertEqual(self.projection.rebuild_checkpoint(TASK)["validation"]["status"], "VALID")

    def test_a_failed_rebuild_keeps_the_previous_checkpoint_byte_identical(self):
        self.projection.rebuild_checkpoint(TASK)
        before = (self.checkpoint.read_bytes(), self.checkpoint.with_suffix(".md").read_bytes())
        self.tasks.create_microtask(TASK, "M2", "m2", microtask_id="m2")  # authority moves on
        for name in ("checkpoint.json", "checkpoint.md"):
            with self.subTest(refused=name):
                with self.refuse_replace(name), self.assertRaises(ProjectionError):
                    self.projection.rebuild_checkpoint(TASK)
                self.assertEqual(self.leftovers(), [])
                status = self.projection.validate_checkpoint(TASK)["status"]
                self.assertNotEqual(status, "VALID")
                if name == "checkpoint.json":
                    self.assertEqual((self.checkpoint.read_bytes(), self.checkpoint.with_suffix(".md").read_bytes()),
                                     before)
                    self.assertEqual(status, "STALE")
                else:  # the JSON landed, the Markdown did not: the pair no longer belongs together
                    self.assertEqual(self.checkpoint.with_suffix(".md").read_bytes(), before[1])
                    self.assertEqual(status, "INCONSISTENT")
        self.assertEqual(self.projection.rebuild_checkpoint(TASK)["validation"]["status"], "VALID")

    def test_missing_corrupt_partial_or_tampered_checkpoints_are_never_valid(self):
        def rebuild():
            self.projection.rebuild_checkpoint(TASK)

        def edit_json(**fields):
            data = json.loads(self.checkpoint.read_text(encoding="utf-8"))
            data.update(fields)
            self.checkpoint.write_text(json.dumps(data), encoding="utf-8")

        def strip_meta():
            data = json.loads(self.checkpoint.read_text(encoding="utf-8"))
            data.pop("projection")
            self.checkpoint.write_text(json.dumps(data), encoding="utf-8")

        cases = {
            "json deleted": (lambda: self.checkpoint.unlink(), "MISSING"),
            "json empty": (lambda: self.checkpoint.write_bytes(b""), "CORRUPT"),
            "json truncated": (lambda: self.checkpoint.write_bytes(self.checkpoint.read_bytes()[:40]), "CORRUPT"),
            "json not an object": (lambda: self.checkpoint.write_text("[1, 2]", encoding="utf-8"), "CORRUPT"),
            "unknown schema": (lambda: edit_json(schema_version=999), "CORRUPT"),
            "NEXT tampered": (lambda: edit_json(next_safe_action="apply rollback now"), "INCONSISTENT"),
            "markdown deleted": (lambda: self.checkpoint.with_suffix(".md").unlink(), "INCONSISTENT"),
            "markdown tampered": (lambda: self.checkpoint.with_suffix(".md").write_text("x", encoding="utf-8"),
                                  "INCONSISTENT"),
            "basis stripped": (strip_meta, "LEGACY_UNVALIDATED"),
        }
        for name, (damage, expected) in cases.items():
            with self.subTest(case=name):
                rebuild()
                damage()
                validation = self.projection.validate_checkpoint(TASK)
                self.assertEqual((validation["status"], validation["authoritative"]), (expected, False))
                context = EntryContextPackBuilderShim.next_of(self.storage)
                self.assertNotEqual(context, "apply rollback now")  # never steers NEXT

    @unittest.skipUnless(os.name == "nt", "Windows sharing semantics")
    def test_a_real_windows_sharing_violation_is_a_failed_rebuild_not_lost_data(self):
        self.projection.rebuild_checkpoint(TASK)
        before = self.checkpoint.read_bytes()
        self.tasks.create_microtask(TASK, "M2", "m2", microtask_id="m2")
        holder = subprocess.Popen([sys.executable, "-c", textwrap.dedent(HOLD_OPEN), str(self.checkpoint), "5"],
                                  stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual(holder.stdout.readline().strip(), "held")
            with self.assertRaises(ProjectionError) as caught:
                self.projection.rebuild_checkpoint(TASK)
        finally:
            holder.kill()
            holder.communicate()
        chain, error = [], caught.exception
        while error is not None:
            chain.append(type(error).__name__)
            error = error.__cause__
        self.assertIn("PermissionError", chain)
        self.assertEqual(self.checkpoint.read_bytes(), before)
        self.assertEqual(self.leftovers(), [])
        self.assertEqual(self.projection.validate_checkpoint(TASK)["status"], "STALE")
        self.assertEqual(self.projection.rebuild_checkpoint(TASK)["validation"]["status"], "VALID")


class EntryContextPackBuilderShim:
    @staticmethod
    def next_of(storage):
        from web_alarm.context_pack import EntryContextPackBuilder
        return EntryContextPackBuilder(storage).build(TASK)["NEXT_SAFE_ACTION"]


if __name__ == "__main__":
    unittest.main()
