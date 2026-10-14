"""WA4-R bounded diagnostic schedules; R-004 adds nonempty closeout evidence.

Expected API failures require exact phase/type/raw-state proof, never blanket
acceptance. Safety/restart oracles read raw files; actors use real production APIs.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import traceback
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parent
TASK = 'task_diag'
PRE = b'PRE\r\n\x00\xff'
POST = b'POST\n\x00\xfe'
TIMEOUT = 25


def sha(data):
    return hashlib.sha256(data).hexdigest()


def parse_json(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError('duplicate JSON key: ' + key)
            value[key] = item
        return value
    return json.loads(raw, object_pairs_hook=pairs)


def read_json(path):
    return parse_json(Path(path).read_text(encoding='utf8'))


def error_chain(exc):
    result, seen = [], set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        result.append(dict(type=type(exc).__name__, message=str(exc),
                           errno=getattr(exc, 'errno', None), winerror=getattr(exc, 'winerror', None),
                           frames=traceback.format_tb(exc.__traceback__)))
        exc = exc.__cause__ or exc.__context__
    return result


def wait(path, processes=()):
    deadline = time.monotonic() + TIMEOUT
    while not Path(path).exists():
        if any(p.poll() is not None for p in processes):
            raise RuntimeError('worker exited before barrier: ' + str(path))
        if time.monotonic() >= deadline:
            raise TimeoutError('barrier not reached: ' + str(path))
        time.sleep(.005)


def raw_state(storage, project):
    """Quiescent byte/JSON oracle; independent of production projection/state enums."""
    storage, project = Path(storage), Path(project)
    active, completed = storage / 'tasks/active' / TASK, storage / 'tasks/completed' / TASK
    location = active if active.exists() else completed
    files = {p.relative_to(location).as_posix(): sha(p.read_bytes())
             for p in location.rglob('*') if p.is_file()}
    def records(folder):
        return {p.stem: read_json(p) for p in folder.glob('*.json')}
    events = location / 'events.jsonl'
    event_bytes = events.read_bytes() if events.exists() else b''
    target = (project / 'data.bin').read_bytes()
    return dict(locations={'active': active.is_dir(), 'completed': completed.is_dir()},
                task=read_json(location / 'task.json') if (location / 'task.json').exists() else None,
                plan=read_json(location / 'plan.json') if (location / 'plan.json').exists() else None,
                operations=records(location / 'operations'), microtasks=records(location / 'microtasks'),
                events=[parse_json(line) for line in event_bytes.decode('utf8').splitlines()],
                events_hex=event_bytes.hex(),
                checkpoint=read_json(location / 'checkpoint.json') if (location / 'checkpoint.json').exists() else None,
                files_sha256=files, claims=records(storage / 'target_claims'),
                restore_records={p.relative_to(location).as_posix(): read_json(p)
                                 for p in location.glob('microtasks/*/restore_point/**/*.json')},
                snapshot_hex={p.relative_to(location).as_posix(): p.read_bytes().hex()
                              for p in location.glob('microtasks/*/restore_point/snapshots/*.bin')},
                target_sha256=sha(target), target_size=len(target), target_hex=target.hex())


def worker(config_path):
    from web_alarm.closeout import CloseoutService
    from web_alarm.event_checkpoint_store import EventCheckpointStore
    from web_alarm.mutation_executor import MutationExecutor
    from web_alarm.operation_store import OperationStore
    from web_alarm.target_claim_service import TargetClaimService
    from web_alarm.task_store import TaskStore
    from web_alarm.store_lock import InterProcessLock
    cfg = read_json(config_path)
    base, storage = Path(cfg['base']), Path(cfg['storage'])
    name, mode = cfg['name'], cfg['mode']
    armed = {'acquire': False, 'event': None, 'paused': False}
    def mark(phase, **facts):
        with (base / (name + '.trace')).open('a', encoding='utf8') as stream:
            stream.write(json.dumps(dict(phase=phase, pid=os.getpid(), **facts)) + '\n')
            stream.flush()
        (base / (name + '.' + phase)).touch()
    def pause(phase, **facts):
        mark(phase, **facts)
        wait(base / (name + '.release'))

    actual_text, actual_bytes = Path.read_text, Path.read_bytes
    actual_acquire = TargetClaimService.acquire
    actual_event, actual_path = EventCheckpointStore.append_event, EventCheckpointStore._events_path
    actual_apply, actual_transition = MutationExecutor._apply, OperationStore._transition_locked
    actual_replace, actual_lock, actual_write = os.replace, TaskStore.mutation_lock, TaskStore._write_task
    actual_lock_acquire = InterProcessLock.acquire
    actual_verdict = CloseoutService.verdict
    def text(path, *args, **kwargs):
        if mode == 'held_RAW_read' and not armed['paused'] and path.name == 'task.md' and 'active' in path.parts:
            armed['paused'] = True
            with path.open('r', encoding=kwargs.get('encoding', 'utf8')) as handle:
                data = handle.read()
                pause('held_RAW_read', path=str(path), frames=traceback.format_stack(limit=8))
                return data
        if mode == 'acquire_read' and armed['acquire'] and not armed['paused'] and path.name == 'task.md' and 'active' in path.parts:
            armed['paused'] = True
            pause('cached_task_read', path=str(path), frames=traceback.format_stack(limit=8))
        return actual_text(path, *args, **kwargs)
    def binary(path, *args, **kwargs):
        if mode == 'snapshot_read' and not armed['paused'] and path.suffix == '.bin' and 'snapshots' in path.parts and 'active' in path.parts:
            armed['paused'] = True
            pause('cached_snapshot_read', path=str(path), frames=traceback.format_stack(limit=8))
        return actual_bytes(path, *args, **kwargs)
    def acquire(service, *args, **kwargs):
        armed['acquire'] = True
        try:
            return actual_acquire(service, *args, **kwargs)
        finally:
            armed['acquire'] = False
    def event(service, task, kind, **kwargs):
        previous = armed['event']
        armed['event'] = kind
        try:
            return actual_event(service, task, kind, **kwargs)
        finally:
            armed['event'] = previous
    def events_path(service, task):
        path = actual_path(service, task)
        if mode == 'release_event' and armed['event'] == 'TARGET_CLAIM_RELEASED' and not armed['paused']:
            armed['paused'] = True
            pause('cached_release_event', path=str(path))
        return path
    def apply(kind, path, data):
        mark('apply_enter', path=str(path))
        if mode == 'boundary':
            pause('before_apply')
        result = actual_apply(kind, path, data)
        mark('apply_exit', file_sha256=sha(actual_bytes(path)))
        return result
    def transition(store, task, op, requested, **kwargs):
        result = actual_transition(store, task, op, requested, **kwargs)
        value = getattr(requested, 'value', requested)
        if value in ('STARTED', 'DONE'):
            mark('durable_' + value)
        return result
    def replace(src, dst):
        moving = Path(src) == storage / 'tasks/active' / TASK and Path(dst) == storage / 'tasks/completed' / TASK
        if moving and mode in ('close_trace', 'completion_gate', 'native_pre', 'reject_gate'):
            op_path=storage/'tasks/active'/TASK/'operations/op_diag.json'
            mark('before_directory_move', operation=read_json(op_path) if op_path.exists() else None)
        if moving and mode == 'completion_gate':
            pause('fresh_gate_before_move')
        if moving and mode == 'native_pre':
            # A real no-delete-share Windows RAW handle, not an injected exception.
            with (Path(src) / 'task.md').open('rb'):
                mark('native_pre_handle_open', path=str(Path(src) / 'task.md'))
                return actual_replace(src, dst)
        result = actual_replace(src, dst)
        if moving:
            mark('directory_moved')
            if mode == 'crash_move':
                pause('crash_phase_reached', exit_code=91)
                os._exit(91)
        return result
    def write_task(store, directory, task):
        if mode == 'native_status' and Path(directory).parent.name == 'completed':
            # Native Windows refusal: no injected exception or altered write.
            mark('status_write_with_native_reader')
            with (Path(directory) / 'task.json').open('rb'):
                return actual_write(store, directory, task)
        return actual_write(store, directory, task)
    @contextmanager
    def lock(store, task):
        if mode in ('close_hold', 'lock_trace'):
            mark('mutation_lock_attempt')
        with actual_lock(store, task):
            if mode == 'lock_trace':
                mark('mutation_lock_acquired')
            if mode == 'close_hold':
                pause('mutation_lock_acquired')
            yield
    def lock_acquire(lock):
        traced = mode in ('close_trace', 'completion_gate', 'reject_gate', 'held_RAW_read') and lock.path == storage/'locks/operations'/f'{TASK}.lock'
        if traced:
            mark('operations_lock_attempt')
        result = actual_lock_acquire(lock)
        if traced:
            mark('operations_lock_acquired')
        return result
    def verdict(projection):
        value = actual_verdict(projection)
        if mode == 'reject_gate':
            pause('fresh_reject_gate', eligible=value['eligible'],
                  blocker_codes=[b['code'] for b in value['blockers']])
        return value

    try:
        with mock.patch.object(Path, 'read_text', text), mock.patch.object(Path, 'read_bytes', binary), \
             mock.patch.object(TargetClaimService, 'acquire', acquire), \
             mock.patch.object(EventCheckpointStore, 'append_event', event), \
             mock.patch.object(EventCheckpointStore, '_events_path', events_path), \
             mock.patch.object(MutationExecutor, '_apply', staticmethod(apply)), \
             mock.patch.object(OperationStore, '_transition_locked', transition), \
             mock.patch.object(os, 'replace', replace), \
             mock.patch.object(TaskStore, '_write_task', write_task), \
             mock.patch.object(TaskStore, 'mutation_lock', lock), \
             mock.patch.object(InterProcessLock, 'acquire', lock_acquire), \
             mock.patch.object(CloseoutService, 'verdict', staticmethod(verdict)):
            action = cfg['action']
            mark('actor_enter', action=action, mode=mode)
            if action in ('mutate', 'mutate_late'):
                op = 'op_diag' if action == 'mutate' else 'op_late'
                result = MutationExecutor(storage).execute(TASK, 'm1', op, 'write', 'data.bin', payload=POST)
                result = {key: result.get(key) for key in ('result', 'result_code', 'receipt', 'claim_release')}
            elif action == 'direct_close':
                result = {'result': TaskStore(storage).complete_task(TASK).status.value}
            elif action == 'complete':
                value = CloseoutService(storage).complete(TASK)
                result = {key: value.get(key) for key in ('result', 'resumed', 'event_recorded')}
            elif action == 'begin':
                OperationStore(storage).begin(TASK, 'm1', 'write', 'data.bin', operation_id='op_late', payload=POST)
                result = {'result': 'BEGUN'}
            elif action == 'microtask':
                TaskStore(storage).create_microtask(TASK, 'late', 'late', microtask_id='m_late')
                result = {'result': 'CREATED'}
            elif action == 'projection':
                from web_alarm.projection import ProjectionService
                service = ProjectionService(storage)
                projection = service.build(TASK)
                result = {'checkpoint': service.validate_checkpoint(TASK, projection)}
            elif action == 'raw_read':
                result = raw_state(storage, cfg['project'])
            else:
                raise ValueError('unknown action')
        print(json.dumps(result))
    except Exception as exc:
        print(json.dumps({'error': error_chain(exc)}))
        raise SystemExit(2)


class RaceEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='wa4r002_')
        self.base = Path(self.temp.name)
        self.storage, self.project = self.base / 'state', self.base / 'project'
        self.children = []
        self.facts = [{'task': 'CODEX-WA4-R-002', 'test': self.id(), 'oracle': 'raw files, literal expected bytes'}]
        self.addCleanup(self.cleanup)

    def cleanup(self):
        for process in self.children:
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=10)
        self.facts.append({'terminal': self.observe() if self.project.exists() else None})
        self.temp.cleanup()

    def setup_fixture(self, *, verified=False):
        from web_alarm.workspace_registry import WorkspaceRegistry
        from web_alarm.task_store import TaskStore
        from web_alarm.state_machine import ServerStateMachine
        self.project.mkdir()
        (self.project / 'data.bin').write_bytes(PRE)
        WorkspaceRegistry(self.storage).register('diagnostic', self.project, workspace_id='ws_diag')
        tasks = TaskStore(self.storage)
        tasks.create_task('ws_diag', 'diagnostic', 'synthetic RAW TASK', 'race', task_id=TASK)
        tasks.create_microtask(TASK, 'one', 'one', microtask_id='m1')
        machine = ServerStateMachine(self.storage)
        machine.prepare_microtask(TASK, 'm1', [('data.bin', 'edit')])
        for status in ('READY', 'ACTIVE'):
            machine.transition(TASK, 'm1', status)
        if verified:
            machine.transition(TASK, 'm1', 'DONE')
            machine.transition(TASK, 'm1', 'VERIFIED', verification_evidence='fixture verified')
        self.initial = self.observe()
        self.facts.append({'PRE': self.initial})

    def observe(self):
        return raw_state(self.storage, self.project)

    def state(self, label):
        value = self.observe()
        self.facts.append({label: value})
        return value

    def start(self, name, action, mode='normal'):
        cfg = dict(base=str(self.base), storage=str(self.storage), project=str(self.project),
                   name=name, action=action, mode=mode)
        path = self.base / (name + '.json')
        path.write_text(json.dumps(cfg), encoding='utf8')
        process = subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()), '--worker', str(path)],
                                   cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf8')
        self.children.append(process)
        return process

    def finish(self, name, process, exit_code=0):
        out, err = process.communicate(timeout=TIMEOUT+5)
        path = self.base / (name + '.trace')
        trace = [json.loads(line) for line in path.read_text(encoding='utf8').splitlines()] if path.exists() else []
        self.facts.append({'worker': name, 'pid': process.pid, 'exit': process.returncode,
                           'stdout': out, 'stderr': err, 'trace': trace})
        self.assertEqual(process.returncode, exit_code, (out, err))
        if exit_code == 91:
            self.assertEqual(out, '')
            self.assertEqual(sum(x['phase']=='crash_phase_reached' for x in trace), 1)
            return None
        return json.loads(out)

    def run_actor(self, name, action, mode='normal', exit_code=0):
        return self.finish(name, self.start(name, action, mode), exit_code)

    def release(self, name):
        (self.base / (name + '.release')).touch()

    def phase(self, name, phase, *processes):
        wait(self.base / (name + '.' + phase), processes)

    def unchanged_evidence(self, state, data):
        self.assertEqual(state['target_sha256'], sha(data))
        self.assertEqual(state['target_size'], len(data))
        self.assertEqual(state['task']['task_id'], TASK)
        self.assertEqual(state['plan'], self.initial['plan'])
        self.assertEqual(state['microtasks'], self.initial['microtasks'])
        self.assertEqual(state['events'][:len(self.initial['events'])], self.initial['events'])
        self.assertTrue(state['events_hex'].startswith(self.initial['events_hex']), 'historical event prefix bytes changed')
        for path, digest in self.initial['files_sha256'].items():
            if path.startswith('microtasks/m1/restore_point/') or path == 'task.md':
                self.assertEqual(state['files_sha256'].get(path), digest, path)

    def assert_closed(self, state, data, status='COMPLETED'):
        self.assertEqual(state['locations'], {'active': False, 'completed': True})
        self.assertEqual(state['task']['status'], status)
        self.unchanged_evidence(state, data)

    def assert_error(self, out, kind, *, deepest=None):
        self.assertEqual(out['error'][0]['type'], kind, out)
        if deepest:
            self.assertEqual(out['error'][-1]['type'], deepest, out)

    def apply_count(self):
        return sum(json.loads(line)['phase']=='apply_enter' for path in self.base.glob('*.trace')
                   for line in path.read_text(encoding='utf8').splitlines())

    def setup_closeout_evidence(self):
        """Use one actual apply and independently checked bytes, never synthetic receipts."""
        from web_alarm.operation_store import OperationStore
        from web_alarm.state_machine import ServerStateMachine
        from web_alarm.projection import ProjectionService
        self.facts.append({'execution_task': 'CODEX-WA4-R-004-F1-CLOSEOUT-GATE',
                           'input_quality': 'one real tracked apply; nonempty receipt/checkpoint/snapshot'})
        self.setup_fixture()
        self.assertEqual(self.run_actor('fixture_apply', 'mutate')['result'], 'EXECUTED')
        OperationStore(self.storage).transition(TASK, 'op_diag', 'VERIFIED')
        machine = ServerStateMachine(self.storage)
        machine.transition(TASK, 'm1', 'DONE')
        machine.transition(TASK, 'm1', 'VERIFIED', verification_evidence='independent POST bytes checked')
        ProjectionService(self.storage).rebuild_checkpoint(TASK)
        self.initial = self.state('F1_quiescent_PRE_with_receipt_checkpoint_snapshot')
        receipt = self.initial['operations']['op_diag']['receipt']
        self.assertEqual((receipt['exists'], receipt['size'], receipt['sha256']), (True, len(POST), sha(POST)))
        self.assertIs(receipt['matches_expected_post'], True)
        self.assertEqual(self.initial['operations']['op_diag']['status'], 'VERIFIED')
        self.assertEqual(self.initial['target_hex'], POST.hex())
        self.assertIn(PRE.hex(), self.initial['snapshot_hex'].values())
        self.assertTrue(self.initial['restore_records'])
        self.assertEqual(self.initial['checkpoint']['last_verified_microtask_id'], 'm1')
        self.assertTrue(self.initial['claims'])
        self.assertTrue(all(c['active'] is None for c in self.initial['claims'].values()))
        self.assertEqual(self.apply_count(), 1)

    def assert_closeout_evidence(self, state, *, completed=False):
        self.unchanged_evidence(state, POST)
        for field in ('operations', 'checkpoint', 'restore_records', 'snapshot_hex', 'claims', 'target_hex'):
            self.assertEqual(state[field], self.initial[field], field)
        self.assertEqual(set(state['files_sha256']), set(self.initial['files_sha256']))
        for path, digest in self.initial['files_sha256'].items():
            if not completed or path not in ('task.json', 'events.jsonl'):
                self.assertEqual(state['files_sha256'][path], digest, path)
        if completed:
            self.assertEqual(state['locations'], {'active': False, 'completed': True})
            self.assertEqual(state['task']['status'], 'COMPLETED')
            before, after = dict(self.initial['task']), dict(state['task'])
            before.pop('status'); before.pop('updated_at'); after.pop('status'); after.pop('updated_at')
            self.assertEqual(before, after)
            tail = state['events'][len(self.initial['events']):]
            self.assertEqual([e['event_type'] for e in tail], ['TASK_COMPLETED'])
        else:
            self.assertEqual(state['task'], self.initial['task'])
            self.assertEqual(state['events'], self.initial['events'])
        self.assertEqual(self.apply_count(), 1)

    def assert_fresh_closed_evidence(self):
        state = self.state('after_fresh_process_completion')
        self.assert_closeout_evidence(state, completed=True)
        self.assertEqual(self.run_actor('raw_reopen', 'raw_read'), state)
        replay = self.run_actor('historical_replay', 'mutate')
        self.assertEqual((replay['result'], replay['receipt']),
                         ('REPLAYED', self.initial['operations']['op_diag']['receipt']))
        self.assertEqual(self.observe(), state)
        self.assertEqual(self.apply_count(), 1)

    @unittest.skipUnless(sys.platform == 'win32', 'requires native Windows reader/replace semantics')
    def test_F1_native_pre_move_refusal_preserves_nonempty_evidence_and_fresh_retry(self):
        self.setup_closeout_evidence()
        out = self.run_actor('close', 'complete', 'native_pre', 2)
        self.assert_error(out, 'CloseoutError', deepest='PermissionError')
        self.assertIn(out['error'][-1]['winerror'], (5, 32))
        self.assertTrue((self.base / 'close.native_pre_handle_open').is_file())
        self.assertFalse((self.base / 'close.directory_moved').exists())
        self.assertEqual(self.state('native_pre_move_refusal'), self.initial)
        self.assertEqual(self.run_actor('raw_before_retry', 'raw_read'), self.initial)
        result = self.run_actor('fresh_retry', 'complete')
        self.assertEqual((result['result'], result['resumed']), ('COMPLETED', None))
        self.assert_fresh_closed_evidence()

    @unittest.skipUnless(sys.platform == 'win32', 'requires native Windows reader/replace semantics')
    def test_F1_native_post_move_status_failure_and_fresh_recovery(self):
        self.setup_closeout_evidence()
        out = self.run_actor('close', 'complete', 'native_status', 2)
        self.assert_error(out, 'CloseoutError', deepest='PermissionError')
        self.assertIn(out['error'][-1]['winerror'], (5,32))
        pending = self.state('status_pending_before_recovery')
        self.assert_closed(pending, POST, 'PLANNED')
        self.assert_closeout_evidence(pending)
        self.assertTrue((self.base / 'close.directory_moved').is_file())
        self.assertTrue((self.base / 'close.status_write_with_native_reader').is_file())
        from web_alarm.task_store import TaskStore
        self.assertEqual(TaskStore(self.storage).completion_state(TASK), 'MOVED_STATUS_PENDING')
        self.assertEqual(self.run_actor('raw_pending', 'raw_read'), pending)
        denied = self.run_actor('late', 'mutate_late')
        self.assertEqual(denied['result'], 'REFUSED')
        replay = self.run_actor('pending_replay', 'mutate')
        self.assertEqual((replay['result'], replay['receipt']),
                         ('REPLAYED', self.initial['operations']['op_diag']['receipt']))
        self.assertEqual(self.observe(), pending)
        recovered = self.run_actor('recover', 'complete')
        self.assertEqual((recovered['result'], recovered['resumed']), ('COMPLETED','MOVED_STATUS_PENDING'))
        self.assert_fresh_closed_evidence()
        self.assertEqual(self.run_actor('again','complete')['result'], 'REJECTED')
        self.assertEqual(sum(e['event_type']=='TASK_COMPLETED' for e in self.observe()['events']),1)
        self.assertEqual(self.apply_count(), 1)

    def test_F1_completion_first_serializes_RAW_admission_plan_and_new_mutation(self):
        from web_alarm.store_lock import InterProcessLock, StoreLockTimeout
        from web_alarm.task_store import TaskStore, TaskStoreError
        self.setup_closeout_evidence()
        closer = self.start('close', 'complete', 'completion_gate')
        self.phase('close', 'fresh_gate_before_move', closer)
        self.assertEqual(self.state('fresh_gate_under_both_locks'), self.initial)
        with self.assertRaises(StoreLockTimeout):
            with InterProcessLock(self.storage/'locks/operations'/f'{TASK}.lock', timeout=.05):
                self.fail('closeout did not hold the operations lock')
        with self.assertRaises(TaskStoreError):
            with TaskStore(self.storage, lock_timeout=.05).mutation_lock(TASK):
                self.fail('closeout did not hold the mutation lock')
        reader = self.start('reader', 'begin', 'held_RAW_read')
        self.phase('reader', 'operations_lock_attempt', reader)
        plan = self.start('plan', 'microtask', 'lock_trace')
        self.phase('plan', 'mutation_lock_attempt', plan)
        writer = self.start('writer', 'mutate_late')
        self.phase('writer', 'actor_enter', writer)
        self.release('close')
        self.assertEqual(self.finish('close', closer)['result'], 'COMPLETED')
        self.assert_error(self.finish('reader', reader, 2), 'TaskStoreError')
        self.assert_error(self.finish('plan', plan, 2), 'TaskStoreError')
        self.assertEqual(self.finish('writer', writer)['result'], 'REFUSED')
        self.assertFalse((self.base/'reader.held_RAW_read').exists())
        self.assert_fresh_closed_evidence()

    def test_F1_admission_first_rejects_closeout_without_touching_existing_evidence(self):
        self.setup_closeout_evidence()
        reader = self.start('reader', 'begin', 'held_RAW_read')
        self.phase('reader', 'held_RAW_read', reader)
        closer = self.start('close', 'complete', 'reject_gate')
        self.phase('close', 'operations_lock_attempt', closer)
        self.assertFalse((self.base/'close.before_directory_move').exists())
        self.release('reader')
        self.assertEqual(self.finish('reader', reader)['result'], 'BEGUN')
        self.phase('close', 'fresh_reject_gate', closer)
        admitted = self.state('admission_committed_before_closeout_refusal')
        self.assertEqual(admitted['operations']['op_late']['status'], 'INTENT')
        self.assertIsNone(admitted['operations']['op_late']['receipt'])
        self.assertEqual(admitted['operations']['op_diag'], self.initial['operations']['op_diag'])
        # Admission is allowed to refresh its derived checkpoint before closeout.
        self.assertEqual(admitted['checkpoint']['last_operation_id'], 'op_late')
        self.assertEqual(admitted['checkpoint']['last_verified_microtask_id'], 'm1')
        self.assertEqual(set(admitted['files_sha256']),
                         set(self.initial['files_sha256']) | {'operations/op_late.json'})
        for path, digest in self.initial['files_sha256'].items():
            if path not in ('events.jsonl', 'checkpoint.json', 'checkpoint.md'):
                self.assertEqual(admitted['files_sha256'][path], digest, path)
        self.release('close')
        result = self.finish('close', closer)
        self.assertEqual((result['result'], result['resumed']), ('REJECTED', None))
        gates = [json.loads(line) for line in (self.base/'close.trace').read_text(encoding='utf8').splitlines()
                 if json.loads(line)['phase'] == 'fresh_reject_gate']
        self.assertEqual(len(gates), 1)
        self.assertIs(gates[0]['eligible'], False)
        self.assertIn('OPERATION_OPEN', gates[0]['blocker_codes'])
        self.assertFalse((self.base/'close.before_directory_move').exists())
        self.assertEqual(self.observe(), admitted)
        self.assertEqual(self.run_actor('raw_rejected', 'raw_read'), admitted)
        self.assertEqual(admitted['locations'], {'active': True, 'completed': False})
        self.unchanged_evidence(admitted, POST)
        self.assertEqual(admitted['claims'], self.initial['claims'])
        self.assertEqual(self.apply_count(), 1)

    def moved_reader(self, mode, phase):
        self.setup_fixture()
        process = self.start('mutation', 'mutate', mode)
        self.phase('mutation', phase, process)
        self.assertEqual(self.state('before_direct_move')['target_sha256'], sha(PRE))
        self.assertEqual(self.run_actor('close', 'direct_close')['result'], 'COMPLETED')
        self.release('mutation')
        return process

    def test_F2_cached_snapshot_read_is_refused_without_physical_effect(self):
        # Historical selector retained: read/move is now serialized instead
        # of deliberately producing the old typed refusal.
        self.setup_fixture()
        writer=self.start('mutation','mutate','snapshot_read')
        self.phase('mutation','cached_snapshot_read',writer)
        closer=self.start('close','direct_close','close_trace')
        self.phase('close','operations_lock_attempt',closer)
        self.assertFalse((self.base/'close.directory_moved').exists())
        self.release('mutation')
        out=self.finish('mutation',writer)
        self.assertEqual(self.finish('close',closer)['result'],'COMPLETED')
        self.check_closed_delivery(out)

    def test_F2_projection_cached_snapshot_error_preserves_checkpoint_and_raw_state(self):
        from web_alarm.projection import ProjectionService
        self.setup_fixture()
        ProjectionService(self.storage).rebuild_checkpoint(TASK)
        self.initial=self.state('valid_checkpoint_fixture')
        process=self.start('projection','projection','snapshot_read')
        self.phase('projection','cached_snapshot_read',process)
        self.assertEqual(self.run_actor('close','direct_close')['result'],'COMPLETED')
        self.release('projection')
        out=self.finish('projection',process,2)
        self.assert_error(out,'FileNotFoundError')
        state=self.state('projection_failure_before_restart')
        self.assert_closed(state,PRE)
        self.assertEqual(state['checkpoint'],self.initial['checkpoint'])
        self.assertEqual(state['files_sha256']['checkpoint.json'],self.initial['files_sha256']['checkpoint.json'])
        self.assertEqual(state['files_sha256']['checkpoint.md'],self.initial['files_sha256']['checkpoint.md'])
        fresh=self.run_actor('fresh_projection','projection')
        self.assertEqual(fresh['checkpoint']['status'],'STALE')
        self.assertIs(fresh['checkpoint']['authoritative'],False)
        self.assert_closed(self.state('after_fresh_projection'),PRE)
        self.assertEqual(self.apply_count(),0)

    def test_F2_cached_acquire_task_read_reproduces_error_but_preserves_PRE(self):
        self.setup_fixture()
        writer=self.start('mutation','mutate','acquire_read')
        self.phase('mutation','cached_task_read',writer)
        closer=self.start('close','direct_close','close_trace')
        self.phase('close','operations_lock_attempt',closer)
        self.assertFalse((self.base/'close.directory_moved').exists())
        self.release('mutation')
        out=self.finish('mutation',writer)
        self.assertEqual(self.finish('close',closer)['result'],'COMPLETED')
        self.check_closed_delivery(out)

    def check_closed_delivery(self,out):
        self.assertIn(out['result'],('EXECUTED','REFUSED'))
        executed=out['result']=='EXECUTED'
        data=POST if executed else PRE
        terminal=self.state('serialized_terminal_before_replay')
        self.assert_closed(terminal,data)
        record=terminal['operations']['op_diag']
        self.assertEqual(record['status'],'DONE' if executed else 'INTENT')
        if executed:
            self.assertEqual(record['receipt']['sha256'],sha(POST))
            self.assertIs(record['receipt']['matches_expected_post'],True)
        else:
            self.assertIsNone(record['receipt'])
        replay=self.run_actor('replay','mutate')
        self.assertEqual(replay['result'],'REPLAYED' if executed else 'REFUSED')
        after=self.state('after_fresh_serialized_replay')
        self.assert_closed(after,data)
        self.assertEqual(after['operations']['op_diag'],record)
        self.assertEqual(self.apply_count(),1 if executed else 0)

    def test_F2_release_event_error_after_DONE_is_replayed_without_second_apply(self):
        self.setup_fixture()
        process = self.start('mutation','mutate','release_event')
        self.phase('mutation','cached_release_event',process)
        before = self.state('DONE_before_move')
        self.assertEqual(before['operations']['op_diag']['status'],'DONE')
        self.assertEqual(before['target_sha256'],sha(POST))
        closer=self.start('close','direct_close','close_trace')
        self.phase('close','operations_lock_attempt',closer)
        self.assertFalse((self.base/'close.directory_moved').exists())
        self.release('mutation')
        out = self.finish('mutation',process)
        self.assertEqual(out['result'],'EXECUTED')
        self.assertEqual(self.finish('close',closer)['result'],'COMPLETED')
        terminal = self.state('error_before_replay')
        self.assert_closed(terminal,POST)
        receipt = terminal['operations']['op_diag']['receipt']
        self.assertEqual((receipt['exists'],receipt['size'],receipt['sha256']), (True,len(POST),sha(POST)))
        self.assertIs(receipt['matches_expected_post'],True)
        self.assertTrue(terminal['claims'])
        self.assertTrue(all(c['active'] is None for c in terminal['claims'].values()))
        self.assertEqual(sum(e['event_type']=='TARGET_CLAIM_RELEASED' for e in terminal['events']),1)
        replay = self.run_actor('replay','mutate')
        self.assertEqual((replay['result'],replay['receipt']),('REPLAYED',receipt))
        self.assert_closed(self.state('after_fresh_replay'),POST)
        self.assertEqual(self.apply_count(),1)

    def test_F2_move_cannot_interleave_START_APPLY_DONE_boundary(self):
        from web_alarm.task_store import TaskStore, TaskStoreError
        self.setup_fixture()
        writer=self.start('mutation','mutate','boundary')
        self.phase('mutation','before_apply',writer)
        self.assertEqual(self.state('STARTED_at_barrier')['operations']['op_diag']['status'],'STARTED')
        closer=self.start('close','direct_close','close_trace')
        self.phase('close','operations_lock_attempt',closer)
        with self.assertRaises(TaskStoreError):
            with TaskStore(self.storage,lock_timeout=.1).mutation_lock(TASK):
                self.fail('execution boundary did not hold mutation lock')
        self.assertFalse((self.base/'close.directory_moved').exists())
        self.release('mutation')
        self.assertEqual(self.finish('mutation',writer)['result'],'EXECUTED')
        self.assertEqual(self.finish('close',closer)['result'],'COMPLETED')
        before_move=[e for f in self.facts for e in f.get('trace',[]) if e['phase']=='before_directory_move']
        self.assertEqual(len(before_move),1)
        self.assertEqual(before_move[0]['operation']['status'],'DONE')
        self.assert_closed(self.state('after_move'),POST)
        self.assertEqual(self.run_actor('replay','mutate')['result'],'REPLAYED')
        self.assertEqual(self.apply_count(),1)

    def test_F3_marked_post_move_crash_late_writers_and_fresh_completion(self):
        self.setup_fixture(verified=True)
        closer=self.start('close','complete','crash_move')
        self.phase('close','crash_phase_reached',closer)
        self.assert_closed(self.state('at_crash_phase'),PRE,'PLANNED')
        begin=self.start('begin','begin')
        micro=self.start('micro','microtask','lock_trace')
        self.phase('begin','actor_enter')
        self.phase('micro','mutation_lock_attempt',micro)
        self.assertFalse((self.base/'micro.mutation_lock_acquired').exists())
        self.release('close')
        self.finish('close',closer,91)
        self.assert_error(self.finish('begin',begin,2),'TaskStoreError')
        self.assert_error(self.finish('micro',micro,2),'TaskStoreError')
        before=self.state('after_crash_before_recovery')
        self.assert_closed(before,PRE,'PLANNED')
        self.assertEqual(before['operations'],{})
        self.assertNotIn('m_late',before['microtasks'])
        self.assertEqual(self.run_actor('recover','complete')['resumed'],'MOVED_STATUS_PENDING')
        self.assert_closed(self.state('recovered'),PRE)
        self.assertEqual(self.run_actor('again','complete')['result'],'REJECTED')
        self.assertEqual(sum(e['event_type']=='TASK_COMPLETED' for e in self.observe()['events']),1)
        self.assertEqual(self.apply_count(),0)

    def test_F3_writer_first_refusal_does_not_claim_crash_phase(self):
        self.setup_fixture(verified=True)
        self.assertEqual(self.run_actor('begin','begin')['result'],'BEGUN')
        out=self.run_actor('close','complete','crash_move')
        self.assertEqual(out['result'],'REJECTED')
        self.assertFalse((self.base/'close.crash_phase_reached').exists())
        state=self.state('rejected_before_crash')
        self.assertEqual(state['locations'],{'active':True,'completed':False})
        self.assertEqual(state['operations']['op_late']['status'],'INTENT')
        self.unchanged_evidence(state,PRE)

    def test_F2_directory_probes_do_not_invent_duplicate_during_real_move(self):
        from web_alarm.task_store import TaskStore
        self.setup_fixture(verified=True)
        tasks=TaskStore(self.storage)
        active=self.storage/'tasks/active'/TASK
        completed=self.storage/'tasks/completed'/TASK
        real=Path.is_dir
        moved=[]
        def interleave(path):
            if path==completed and not moved:
                moved.append(True)
                tasks.complete_task(TASK)
                self.facts.append({'phase':'real_move_between_directory_probes','raw':self.observe()})
            return real(path)
        with mock.patch.object(Path,'is_dir',interleave):
            located=tasks.task_directory(TASK)
        self.assertEqual(len(moved),1)
        self.assertEqual(located,completed)
        self.assert_closed(self.state('after_interleaved_lookup'),PRE)

    def test_F2_genuine_duplicate_directory_still_fails_closed(self):
        import shutil
        from web_alarm.task_store import TaskStore, TaskStoreError
        self.setup_fixture()
        shutil.copytree(self.storage/'tasks/active'/TASK,self.storage/'tasks/completed'/TASK)
        with self.assertRaisesRegex(TaskStoreError,'exists in active and completed'):
            TaskStore(self.storage).task_directory(TASK)
        self.assertEqual(self.run_actor('mutate','mutate')['result'],'REFUSED')
        self.assertEqual(self.apply_count(),0)
        self.assertEqual((self.project/'data.bin').read_bytes(),PRE)

    def test_F2_move_between_destination_and_source_probe_is_resolved(self):
        from web_alarm.task_store import TaskStore
        self.setup_fixture(verified=True)
        tasks=TaskStore(self.storage)
        active=self.storage/'tasks/active'/TASK
        completed=self.storage/'tasks/completed'/TASK
        real=Path.is_dir
        moved=[]
        def interleave(path):
            if path==active and not moved:
                moved.append(True)
                tasks.complete_task(TASK)
                self.facts.append({'phase':'move_after_destination_false_before_source_probe','raw':self.observe()})
            return real(path)
        with mock.patch.object(Path,'is_dir',interleave):
            located=tasks.task_directory(TASK)
        self.assertEqual(located,completed)
        self.assertEqual(len(moved),1)
        self.assert_closed(self.state('resolved_move_gap'),PRE)

    def test_F2_completion_lock_timeout_writes_nothing_and_releases_locks(self):
        from web_alarm.task_store import TaskStore, TaskStoreError
        from web_alarm.operation_store import OperationStore
        self.setup_fixture(verified=True)
        with OperationStore(self.storage).task_lock(TASK):
            with self.assertRaises(TaskStoreError) as caught:
                TaskStore(self.storage,lock_timeout=.05).complete_task(TASK)
        self.facts.append({'expected_lock_timeout':error_chain(caught.exception)})
        self.assertEqual(error_chain(caught.exception)[-1]['type'],'StoreLockTimeout')
        self.assertEqual(self.state('timeout_preserves_task'),self.initial)
        self.assertEqual(self.run_actor('complete','complete')['result'],'COMPLETED')
        self.assert_closed(self.state('after_lock_release'),PRE)

    def test_F2_invalid_completion_identity_creates_no_lock_files(self):
        from web_alarm.task_store import TaskStore, TaskStoreError
        self.setup_fixture()
        before={p.relative_to(self.storage).as_posix() for p in self.storage.rglob('*')}
        with self.assertRaises(TaskStoreError):
            TaskStore(self.storage).complete_task('../escape')
        self.assertEqual({p.relative_to(self.storage).as_posix() for p in self.storage.rglob('*')},before)
        self.assertEqual(self.state('invalid_id_unchanged'),self.initial)

    def test_F2_preflight_lock_failure_refuses_without_apply_and_replay_is_safe(self):
        from web_alarm.mutation_executor import MutationExecutor
        from web_alarm.operation_store import OperationStoreError
        self.setup_fixture()
        executor=MutationExecutor(self.storage)
        @contextmanager
        def unavailable(task):
            raise OperationStoreError('injected preflight lock unavailable')
            yield
        with mock.patch.object(MutationExecutor,'_apply',wraps=MutationExecutor._apply) as apply:
            with mock.patch.object(executor.operations,'task_lock',unavailable):
                out=executor.execute(TASK,'m1','op_diag','write','data.bin',payload=POST)
            self.assertEqual((out['result'],out['result_code']),('REFUSED','ADMISSION_UNAVAILABLE'))
            apply.assert_not_called()
            state=self.state('preflight_refused')
            self.unchanged_evidence(state,PRE)
            self.assertEqual(state['operations']['op_diag']['status'],'INTENT')
            self.assertIsNone(state['operations']['op_diag']['receipt'])
            self.assertEqual(executor.execute(TASK,'m1','op_diag','write','data.bin',payload=POST)['result'],'EXECUTED')
            self.assertEqual(apply.call_count,1)
        self.unchanged_evidence(self.state('replayed_after_lock_recovery'),POST)

    @unittest.skipUnless(sys.platform=='win32','native Windows RAW-reader overlap')
    def test_F3_RAW_reader_is_inside_operations_lock_before_admission(self):
        from web_alarm.closeout import CloseoutService, CloseoutError
        self.setup_fixture(verified=True)
        reader=self.start('begin','begin','held_RAW_read')
        self.phase('begin','held_RAW_read',reader)
        with self.assertRaises(CloseoutError) as caught:
            CloseoutService(self.storage,lock_timeout=.1).complete(TASK)
        chain=error_chain(caught.exception)
        self.facts.append({'blocked_closeout_chain':chain,'intermediate':self.observe()})
        self.assertEqual(chain[-1]['type'],'StoreLockTimeout',chain)
        self.release('begin')
        self.assertEqual(self.finish('begin',reader)['result'],'BEGUN')
        self.assertEqual(self.run_actor('close','complete')['result'],'REJECTED')
        terminal=self.state('after_serialized_admission')
        self.assertEqual(terminal['locations'],{'active':True,'completed':False})
        self.assertEqual(terminal['operations']['op_late']['status'],'INTENT')
        self.unchanged_evidence(terminal,PRE)


if __name__ == '__main__':
    if sys.argv[1:2] == ['--worker']:
        worker(sys.argv[2])
    else:
        unittest.main()
