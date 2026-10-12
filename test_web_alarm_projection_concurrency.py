"""RC-5 races under real concurrent OS processes (start barrier, test-only widened windows).

W: gated TASK completion vs a new operation / microtask for the same TASK —
   never "TASK completed" + "new open state admitted inside it".
X: checkpoint rebuild vs an authoritative change — a later validation never
   calls a checkpoint VALID unless it equals the fresh projection.
   F-6 (CLAUDE-WA-017): a rebuild may fail closed (ProjectionError, e.g. a
   Windows sharing violation on its atomic replace); that is not lost data. A
   rebuild that reports success must leave a checkpoint behind.
Two rebuilders: serialized; JSON and Markdown always belong together.
"""

import json
import subprocess
import sys
import tempfile
import time
import unittest
from collections import Counter
from pathlib import Path

from web_alarm.closeout import CloseoutError, CloseoutService
from web_alarm.event_checkpoint_store import EventCheckpointStore
from web_alarm.operation_store import OperationStore
from web_alarm.projection import ProjectionService, checkpoint_fields
from web_alarm.state_machine import ServerStateMachine
from web_alarm.task_store import TaskStore
from web_alarm.workspace_registry import WorkspaceRegistry

REPO_ROOT = Path(__file__).resolve().parent
ROUNDS = 4

CHILD = r"""
import json, random, sys, time, traceback
from pathlib import Path
storage, barrier, name, mode, jitter = sys.argv[1:6]
trace = []
def mark(phase, **facts):
    if len(trace) < 128:
        trace.append(dict(phase=phase, ns=time.monotonic_ns(), **facts))
def error_chain(exc):
    chain, seen = [], set()
    while exc is not None and id(exc) not in seen and len(chain) < 12:
        seen.add(id(exc))
        chain.append(dict(type=type(exc).__module__ + '.' + type(exc).__qualname__,
                          message=str(exc), errno=getattr(exc, 'errno', None),
                          winerror=getattr(exc, 'winerror', None),
                          relation='cause' if exc.__cause__ else 'context',
                          frames=traceback.format_tb(exc.__traceback__)))
        exc = exc.__cause__ or exc.__context__
    return chain
from web_alarm.store_lock import InterProcessLock
real_acquire, real_release = InterProcessLock.acquire, InterProcessLock.release
def acquire(self):
    mark('lock_wait', lock=str(self.path.relative_to(storage)))
    try:
        result = real_acquire(self)
    except Exception as exc:
        mark('lock_refused', error=error_chain(exc))
        raise
    mark('lock_acquired', lock=str(self.path.relative_to(storage)))
    return result
def release(self):
    result = real_release(self)
    mark('lock_released', lock=str(self.path.relative_to(storage)))
    return result
InterProcessLock.acquire, InterProcessLock.release = acquire, release
import web_alarm.projection as projection_module
from web_alarm.closeout import CloseoutService
from web_alarm.operation_store import OperationStore
from web_alarm.projection import ProjectionService
from web_alarm.task_store import TaskStore
import web_alarm.event_checkpoint_store as ecs
if mode == "complete":
    for method in ('completion_state', 'complete_task_locked'):
        original = getattr(TaskStore, method)
        def traced(self, task_id, _original=original, _method=method):
            mark(_method + '_enter')
            try:
                result = _original(self, task_id)
            except Exception as exc:
                mark(_method + '_failed', error=error_chain(exc))
                raise
            mark(_method + '_return', state=result if isinstance(result, str) else result.status.value)
            return result
        setattr(TaskStore, method, traced)
    real = projection_module.ProjectionService.build
    def widened(self, task_id):  # test-only: hold the inspect -> complete window open
        mark('projection_enter')
        result = real(self, task_id)
        mark('projection_built', blockers=[b['code'] for b in result['closeout']])
        time.sleep(0.3)
        mark('projection_return')
        return result
    projection_module.ProjectionService.build = widened
    service = CloseoutService(storage, lock_timeout=60)
elif mode in ("rebuild", "rebuild_fail"):
    real_write = ecs.EventCheckpointStore.write_checkpoint
    def slow_write(self, record):  # test-only: projection built, file not written yet
        time.sleep(0.3)
        return real_write(self, record)
    ecs.EventCheckpointStore.write_checkpoint = slow_write
    if mode == "rebuild_fail":  # test-only: the atomic replace is refused (a Windows sharing violation)
        real_replace = ecs.os.replace
        def refuse(src, dst):
            if Path(dst).name == "checkpoint.json":
                raise PermissionError(13, "sharing violation (test)", str(dst))
            return real_replace(src, dst)
        ecs.os.replace = refuse
    service = ProjectionService(storage, lock_timeout=60)
elif mode in ("begin", "transition"):
    service = OperationStore(storage, lock_timeout=60)
else:
    service = TaskStore(storage, lock_timeout=60)
Path(barrier, f"ready_{name}").touch()
mark('ready')
deadline = time.monotonic() + 60
while not Path(barrier, "go").exists():
    if time.monotonic() > deadline:
        raise SystemExit("barrier timeout")
    time.sleep(0.0005)
if jitter == "1":
    delay = random.uniform(0, 0.6)
    mark('jitter', seconds=delay)
    time.sleep(delay)
mark('operation_enter', operation=mode)
details, failure = None, None
try:
    if mode == "complete":
        outcome = service.complete("task_r")
        result = outcome["result"]
        details = dict(completed=outcome['completed'], event_recorded=outcome.get('event_recorded'),
                       resumed=outcome.get('resumed'),
                       blockers=[b['code'] for b in outcome['closeout']['blockers']])
    elif mode in ("rebuild", "rebuild_fail"):
        service.rebuild_checkpoint("task_r")
        result = "REBUILT"
    elif mode == "begin":
        service.begin("task_r", "m2", "write", "two.txt", operation_id="op_" + name, payload=b"x\n")
        result = "BEGUN"
    elif mode == "transition":
        service.transition("task_r", "op_seed", "STARTED")
        result = "TRANSITIONED"
    else:
        service.create_microtask("task_r", "late", "late", microtask_id="late_" + name)
        result = "CREATED"
except Exception as exc:
    result = "FAILED:" + type(exc).__name__
    failure = error_chain(exc)
mark('operation_return', result=result)
print(json.dumps({"name": name, "mode": mode, "result": result, 'error': failure,
                  'closeout': details, 'trace': trace, 'trace_at_limit': len(trace) == 128}))
"""

# Read-only terminal evidence, also executed in a fresh process. No recovery or
# checkpoint rebuild here: diagnosis must not repair the state being inspected.
SNAPSHOT = r'''
def terminal_snapshot(storage):
    import hashlib, json
    from pathlib import Path
    from web_alarm.task_store import TaskStore
    from web_alarm.operation_store import OperationStore
    from web_alarm.event_checkpoint_store import EventCheckpointStore
    from web_alarm.projection import ProjectionService
    from web_alarm.models import record_to_dict
    storage = Path(storage)
    result = {'locations': {name: (storage/'tasks'/name/'task_r').is_dir()
                            for name in ('active', 'completed')}, 'read_errors': []}
    def read(key, action):
        try:
            result[key] = action()
        except Exception as exc:
            chain = []
            while exc is not None and len(chain) < 12:
                chain.append({'type': type(exc).__name__, 'message': str(exc)})
                exc = exc.__cause__ or exc.__context__
            result['read_errors'].append({'read': key, 'chain': chain})
    tasks = TaskStore(storage)
    read('task', lambda: record_to_dict(tasks.open_task('task_r')))
    read('plan', lambda: record_to_dict(tasks.open_plan('task_r')))
    read('microtasks', lambda: [record_to_dict(m) for m in tasks.list_microtasks('task_r')])
    read('operations', lambda: [record_to_dict(o) for o in OperationStore(storage).list('task_r')])
    read('history', lambda: [hashlib.sha256(json.dumps(record_to_dict(e), sort_keys=True).encode()).hexdigest()
                             for e in EventCheckpointStore(storage).read_events('task_r')])
    def projection():
        service = ProjectionService(storage)
        p = service.build('task_r')
        return {key: p[key] for key in ('task', 'source_fingerprint', 'projection_fingerprint',
                                        'closeout', 'diagnostics', 'next_safe_action', 'authority_source')}
    read('projection', projection)
    read('checkpoint', lambda: ProjectionService(storage).validate_checkpoint('task_r'))
    def files():
        directory = tasks.task_directory('task_r')
        return {p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(directory.rglob('*')) if p.is_file()}
    read('files', files)
    return result
'''
exec(SNAPSHOT)


class ProjectionRaceTests(unittest.TestCase):
    def setup_task(self, root: Path, *, verified: bool) -> Path:
        storage, project = root / "state", root / "project"
        project.mkdir()
        WorkspaceRegistry(storage).register("Project", project, workspace_id="ws")
        tasks = TaskStore(storage)
        tasks.create_task("ws", "task_r", "RAW", "Race", task_id="task_r")
        machine = ServerStateMachine(storage)
        for microtask_id, target in (("m1", "one.txt"), ("m2", "two.txt")):
            tasks.create_microtask("task_r", microtask_id, "step", microtask_id=microtask_id)
            if verified:
                (project / target).write_bytes(b"before\n")
                machine.prepare_microtask("task_r", microtask_id, [(target, "edit")])
                for status in ("READY", "ACTIVE", "DONE"):
                    machine.transition("task_r", microtask_id, status)
                machine.transition("task_r", microtask_id, "VERIFIED", verification_evidence="ok")
        return storage

    def run_jobs(self, storage: Path, root: Path, jobs, jitter: bool) -> list[dict]:
        barrier = root / "barrier"
        barrier.mkdir()
        processes = [
            subprocess.Popen([sys.executable, "-B", "-c", CHILD, str(storage), str(barrier), name, mode,
                              "1" if jitter and mode not in ("complete", "rebuild", "rebuild_fail") else "0"],
                             cwd=REPO_ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            for name, mode in jobs
        ]
        try:
            deadline = time.monotonic() + 60
            while len(list(barrier.glob("ready_*"))) < len(jobs):
                if time.monotonic() > deadline:
                    self.fail("workers did not reach the start barrier")
                time.sleep(0.01)
            (barrier / "go").touch()
            results = []
            for process in processes:
                stdout, stderr = process.communicate(timeout=120)
                self.assertEqual(process.returncode, 0, stderr)
                results.append(json.loads(stdout))
            if not hasattr(self, 'facts'):
                self.facts = []
            self.facts.append({'workers': results})
        finally:
            for process in processes:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=10)
        return results

    def capture_terminal(self, storage, before):
        """Keep evidence before strict result assertions, including on a FAIL."""
        after = terminal_snapshot(storage)
        reopened = subprocess.run(
            [sys.executable, '-B', '-c', SNAPSHOT +
             '\nimport json,sys; print(json.dumps(terminal_snapshot(sys.argv[1])))', str(storage)],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=60)
        record = {'terminal': after, 'baseline': before, 'reopen_exit': reopened.returncode}
        self.facts.append(record)
        self.assertEqual(reopened.returncode, 0, reopened.stderr)
        record['reopened'] = json.loads(reopened.stdout)
        self.assertEqual(after, record['reopened'])
        self.assertFalse(after['read_errors'], after['read_errors'])
        self.assertEqual(sum(after['locations'].values()), 1)
        self.assertEqual(after['plan']['microtask_ids'][:2], before['plan']['microtask_ids'])
        self.assertEqual(after['history'][:len(before['history'])], before['history'])
        self.assertEqual(after['microtasks'][:2], before['microtasks'])
        # Completion may update task.json and append history; a writer may
        # update plan/checkpoint. Existing immutable records must survive.
        for path, digest in before['files'].items():
            if path not in ('task.json', 'plan.json', 'events.jsonl', 'checkpoint.json', 'checkpoint.md'):
                self.assertEqual(after['files'].get(path), digest, path)
        return after

    def assert_known_windows_move_refusal(self, worker):
        """Only a native pre-commit directory move refusal is an expected failure.

        Do not accept arbitrary CloseoutError, lock timeouts, read errors,
        completed-but-pending state or unknown outcomes as a safe race.
        """
        self.assertEqual(worker["result"], "FAILED:CloseoutError")
        chain = worker.get("error") or []
        self.assertEqual([item["type"] for item in chain], [
            "web_alarm.closeout.CloseoutError",
            "web_alarm.task_store.TaskStoreError",
            "builtins.PermissionError",
        ])
        self.assertEqual(chain[0]["message"], "cannot move task to completed: task_r")
        self.assertEqual(chain[1]["message"], "cannot move task to completed: task_r")
        self.assertEqual(chain[2]["errno"], 13)
        self.assertIn(chain[2]["winerror"], (5, 32))
        self.assertTrue(any("os.replace(task_dir, destination)" in frame
                            for frame in chain[2].get("frames", [])))
        phases = [item["phase"] for item in worker.get("trace", [])]
        self.assertIn("complete_task_locked_failed", phases)
        self.assertNotIn("complete_task_locked_return", phases)

    @unittest.skipUnless(sys.platform == "win32", "requires Windows directory rename sharing semantics")
    def test_native_windows_reader_refuses_move_and_preserves_active_task(self):
        # A real held file handle, not a patched os.replace or fault injection.
        with tempfile.TemporaryDirectory() as tmp:
            storage = self.setup_task(Path(tmp), verified=True)
            before = terminal_snapshot(storage)
            with (storage / "tasks" / "active" / "task_r" / "task.md").open("rb"):
                with self.assertRaises(CloseoutError) as outcome:
                    CloseoutService(storage).complete("task_r")
                cause = outcome.exception.__cause__
                self.assertEqual(str(outcome.exception), "cannot move task to completed: task_r")
                self.assertEqual(type(cause).__name__, "TaskStoreError")
                self.assertIsInstance(cause.__cause__, PermissionError)
                self.assertEqual(cause.__cause__.errno, 13)
                self.assertIn(cause.__cause__.winerror, (5, 32))
                self.assertEqual(terminal_snapshot(storage), before)
            self.facts = []
            self.assertEqual(self.capture_terminal(storage, before), before)

    def test_completion_never_admits_new_open_state(self):  # W
        outcomes = Counter()
        for index in range(ROUNDS):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                storage = self.setup_task(root, verified=True)
                before = terminal_snapshot(storage)
                jobs = [("a", "complete"), ("b1", "begin"), ("b2", "begin"), ("c1", "microtask")]
                results = self.run_jobs(storage, root, jobs, jitter=bool(index % 2))
                terminal = self.capture_terminal(storage, before)
                self.facts[-1]['round'] = index
                by_mode = {r["name"]: r["result"] for r in results}
                self.assertEqual(
                    sorted(o['operation_id'] for o in terminal['operations']),
                    sorted('op_' + r['name'] for r in results if r['result'] == 'BEGUN'))
                self.assertEqual(
                    sorted(terminal['plan']['microtask_ids']),
                    sorted(['m1', 'm2'] + ['late_' + r['name'] for r in results if r['result'] == 'CREATED']))
                completed_dir = storage / "tasks" / "completed" / "task_r"
                active_dir = storage / "tasks" / "active" / "task_r"
                if by_mode["a"] == "COMPLETED":
                    self.assertEqual(terminal['task']['status'], 'COMPLETED')
                    outcomes["completion_won"] += 1
                    self.assertTrue(completed_dir.is_dir())
                    self.assertFalse(active_dir.exists())  # no write recreated the active TASK
                    ops = OperationStore(storage).list("task_r")
                    self.assertEqual([op.operation_id for op in ops], [])  # nothing admitted inside
                    plan = TaskStore(storage).open_plan("task_r")
                    self.assertEqual(plan.microtask_ids, ["m1", "m2"])
                    self.assertTrue(all(r["result"].startswith("FAILED") for r in results if r["name"] != "a"))
                else:
                    self.assertEqual(terminal['task']['status'], before['task']['status'])
                    self.assertTrue(active_dir.is_dir())
                    self.assertFalse(completed_dir.exists())
                    admitted = [r for r in results if r["result"] in ("BEGUN", "CREATED")]
                    if by_mode["a"] == "REJECTED":
                        outcomes["writer_won"] += 1
                        self.assertEqual(by_mode["a"], "REJECTED")
                        self.assertTrue(admitted)
                    else:
                        # The ONLY permitted failed closeout is a proven native
                        # Windows refusal of the directory move BEFORE commit.
                        # capture_terminal above confirms active-only location,
                        # no phantom operations, retained records, immutable
                        # history and fresh-process agreement.
                        self.assert_known_windows_move_refusal(
                            next(r for r in results if r["name"] == "a"))
                        self.assertEqual(
                            terminal["locations"], {"active": True, "completed": False})
                        outcomes["native_precommit_refusal"] += 1
        self.assertEqual(sum(outcomes.values()), ROUNDS)

    def race_rebuild(self, rebuild_mode: str) -> Counter:
        outcomes = Counter()
        for _ in range(ROUNDS):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                storage = self.setup_task(root, verified=False)
                (root / "project" / "two.txt").write_bytes(b"before\n")
                OperationStore(storage).begin("task_r", "m2", "write", "two.txt", operation_id="op_seed",
                                              payload=b"after\n")
                jobs = [("r", rebuild_mode), ("m", "microtask"), ("t", "transition")]
                rebuild = {r["name"]: r["result"] for r in self.run_jobs(storage, root, jobs, jitter=True)}["r"]
                # F-6: the only admissible rebuild failure is the fail-closed ProjectionError
                self.assertIn(rebuild, ("REBUILT", "FAILED:ProjectionError"))
                service = ProjectionService(storage)
                projection = service.build("task_r")
                validation = service.validate_checkpoint("task_r", projection)
                checkpoint_file = TaskStore(storage).task_directory("task_r") / "checkpoint.json"
                outcomes[(rebuild, validation["status"])] += 1
                if checkpoint_file.is_file():
                    state = EventCheckpointStore(storage)
                    record = state.read_checkpoint("task_r")
                    matches = (
                        record.projection is not None
                        and record.projection["source_fingerprint"] == projection["source_fingerprint"]
                        and checkpoint_fields(projection) == {
                            "last_verified_microtask_id": record.last_verified_microtask_id,
                            "current_microtask_id": record.current_microtask_id,
                            "current_status": record.current_status.value,
                            "snapshot_status": record.snapshot_status,
                            "last_operation_id": record.last_operation_id,
                            "next_safe_action": record.next_safe_action,
                        }
                        and state.checkpoint_markdown("task_r") == state.render_checkpoint_md(record)
                    )
                    self.assertEqual(validation["status"] == "VALID", matches)  # never falsely VALID
                    self.assertIn(validation["status"], ("VALID", "STALE", "INCONSISTENT"))
                else:
                    # nothing existed before the race: only a rebuild that failed may leave none;
                    # a rebuild reporting success without a checkpoint would be lost data
                    self.assertEqual((rebuild, validation["status"]), ("FAILED:ProjectionError", "MISSING"))
                self.assertEqual(service.rebuild_checkpoint("task_r")["validation"]["status"], "VALID")
        self.assertEqual(sum(outcomes.values()), ROUNDS)
        return outcomes

    def test_rebuild_racing_an_authoritative_change_is_never_falsely_valid(self):  # X
        self.race_rebuild("rebuild")

    def test_a_failed_rebuild_in_the_race_fails_closed_and_loses_nothing(self):  # X, F-6
        outcomes = self.race_rebuild("rebuild_fail")
        self.assertEqual(set(outcomes), {("FAILED:ProjectionError", "MISSING")})

    def test_concurrent_rebuilders_keep_json_and_markdown_together(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            storage = self.setup_task(root, verified=True)
            self.run_jobs(storage, root, [("r1", "rebuild"), ("r2", "rebuild"), ("r3", "rebuild")], jitter=False)
            validation = ProjectionService(storage).validate_checkpoint("task_r")
            self.assertEqual(validation["status"], "VALID", validation["reasons"])


if __name__ == "__main__":
    unittest.main()
