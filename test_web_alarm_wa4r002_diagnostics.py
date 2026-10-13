"""CODEX-WA4-R-002: bounded diagnostic schedules, never production repair.

Expected API errors are asserted as reproduced defects, not accepted business
outcomes. Safety/restart oracles read raw files; actors use real production APIs.
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


def read_json(path):
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError('duplicate JSON key: ' + key)
            value[key] = item
        return value
    return json.loads(Path(path).read_text(encoding='utf8'), object_pairs_hook=pairs)


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


def worker(config_path):
    from web_alarm.closeout import CloseoutService
    from web_alarm.event_checkpoint_store import EventCheckpointStore
    from web_alarm.mutation_executor import MutationExecutor
    from web_alarm.operation_store import OperationStore
    from web_alarm.target_claim_service import TargetClaimService
    from web_alarm.task_store import TaskStore
    cfg = read_json(config_path)
    base, storage = Path(cfg['base']), Path(cfg['storage'])
    name, mode = cfg['name'], cfg['mode']
    armed = {'acquire': False, 'event': None, 'paused': False}
    def mark(phase, **facts):
        with (base / (name + '.trace')).open('a', encoding='utf8') as stream:
            stream.write(json.dumps(dict(phase=phase, **facts)) + '\n')
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
    def text(path, *args, **kwargs):
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

    try:
        with mock.patch.object(Path, 'read_text', text), mock.patch.object(Path, 'read_bytes', binary), \
             mock.patch.object(TargetClaimService, 'acquire', acquire), \
             mock.patch.object(EventCheckpointStore, 'append_event', event), \
             mock.patch.object(EventCheckpointStore, '_events_path', events_path), \
             mock.patch.object(MutationExecutor, '_apply', staticmethod(apply)), \
             mock.patch.object(OperationStore, '_transition_locked', transition), \
             mock.patch.object(os, 'replace', replace), \
             mock.patch.object(TaskStore, '_write_task', write_task), \
             mock.patch.object(TaskStore, 'mutation_lock', lock):
            action = cfg['action']
            mark('actor_enter', action=action, mode=mode)
            if action == 'mutate':
                result = MutationExecutor(storage).execute(TASK, 'm1', 'op_diag', 'write', 'data.bin', payload=POST)
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
        active = self.storage / 'tasks/active' / TASK
        completed = self.storage / 'tasks/completed' / TASK
        location = active if active.exists() else completed
        tree = {p.relative_to(location).as_posix(): sha(p.read_bytes()) for p in location.rglob('*') if p.is_file()}
        def records(folder):
            return {p.stem: read_json(p) for p in folder.glob('*.json')}
        events = location / 'events.jsonl'
        return dict(locations={'active': active.is_dir(), 'completed': completed.is_dir()},
                    task=read_json(location / 'task.json') if (location / 'task.json').exists() else None,
                    plan=read_json(location / 'plan.json') if (location / 'plan.json').exists() else None,
                    operations=records(location / 'operations'), microtasks=records(location / 'microtasks'),
                    events=[json.loads(line) for line in events.read_text(encoding='utf8').splitlines()] if events.exists() else [],
                    checkpoint=read_json(location / 'checkpoint.json') if (location / 'checkpoint.json').exists() else None,
                    files_sha256=tree,
                    claims=records(self.storage / 'target_claims'),
                    target_sha256=sha((self.project / 'data.bin').read_bytes()),
                    target_size=(self.project / 'data.bin').stat().st_size)

    def state(self, label):
        value = self.observe()
        self.facts.append({label: value})
        return value

    def start(self, name, action, mode='normal'):
        cfg = dict(base=str(self.base), storage=str(self.storage), name=name, action=action, mode=mode)
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
        self.facts.append({'worker': name, 'exit': process.returncode, 'stdout': out, 'stderr': err, 'trace': trace})
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

    @unittest.skipUnless(sys.platform == 'win32', 'requires native Windows reader/replace semantics')
    def test_F1_native_post_move_status_failure_and_fresh_recovery(self):
        self.setup_fixture(verified=True)
        out = self.run_actor('close', 'complete', 'native_status', 2)
        self.assert_error(out, 'CloseoutError', deepest='PermissionError')
        self.assertIn(out['error'][-1]['winerror'], (5,32))
        pending = self.state('status_pending_before_recovery')
        self.assert_closed(pending, PRE, 'PLANNED')
        self.assertEqual(pending['task'], self.initial['task'])
        self.assertFalse(any(path.endswith('.tmp') for path in pending['files_sha256']))
        denied = self.run_actor('late', 'mutate')
        self.assertEqual(denied['result'], 'REFUSED')
        recovered = self.run_actor('recover', 'complete')
        self.assertEqual((recovered['result'], recovered['resumed']), ('COMPLETED','MOVED_STATUS_PENDING'))
        self.assert_closed(self.state('after_fresh_recovery'), PRE)
        self.assertEqual(self.run_actor('again','complete')['result'], 'REJECTED')
        self.assertEqual(sum(e['event_type']=='TASK_COMPLETED' for e in self.observe()['events']),1)
        self.assertEqual(self.apply_count(), 0)

    def moved_reader(self, mode, phase):
        self.setup_fixture()
        process = self.start('mutation', 'mutate', mode)
        self.phase('mutation', phase, process)
        self.assertEqual(self.state('before_direct_move')['target_sha256'], sha(PRE))
        self.assertEqual(self.run_actor('close', 'direct_close')['result'], 'COMPLETED')
        self.release('mutation')
        return process

    def test_F2_cached_snapshot_read_is_refused_without_physical_effect(self):
        process = self.moved_reader('snapshot_read','cached_snapshot_read')
        out = self.finish('mutation', process)
        self.assertEqual((out['result'], out['result_code']), ('REFUSED','RESTORE_POINT_NOT_VERIFIED'))
        self.assert_closed(self.state('terminal'), PRE)
        self.assertEqual(self.run_actor('replay','mutate')['result'], 'REFUSED')
        self.assert_closed(self.state('after_fresh_refusal'),PRE)
        self.assertEqual(self.apply_count(), 0)

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
        process = self.moved_reader('acquire_read','cached_task_read')
        out = self.finish('mutation', process, 2)
        self.assert_error(out, 'TaskStoreError', deepest='FileNotFoundError')
        terminal = self.state('terminal_before_replay')
        self.assert_closed(terminal, PRE)
        self.assertEqual(terminal['operations']['op_diag']['status'], 'INTENT')
        self.assertIsNone(terminal['operations']['op_diag']['receipt'])
        self.assertEqual(self.run_actor('replay','mutate')['result'], 'REFUSED')
        after=self.state('after_fresh_refusal')
        self.assert_closed(after,PRE)
        self.assertEqual(after['operations']['op_diag'],terminal['operations']['op_diag'])
        self.assertEqual(self.apply_count(), 0)

    def test_F2_release_event_error_after_DONE_is_replayed_without_second_apply(self):
        self.setup_fixture()
        process = self.start('mutation','mutate','release_event')
        self.phase('mutation','cached_release_event',process)
        before = self.state('DONE_before_move')
        self.assertEqual(before['operations']['op_diag']['status'],'DONE')
        self.assertEqual(before['target_sha256'],sha(POST))
        self.assertEqual(self.run_actor('close','direct_close')['result'],'COMPLETED')
        self.release('mutation')
        out = self.finish('mutation',process,2)
        self.assert_error(out,'EventCheckpointStoreError',deepest='FileNotFoundError')
        terminal = self.state('error_before_replay')
        self.assert_closed(terminal,POST)
        receipt = terminal['operations']['op_diag']['receipt']
        self.assertEqual((receipt['exists'],receipt['size'],receipt['sha256']), (True,len(POST),sha(POST)))
        self.assertIs(receipt['matches_expected_post'],True)
        self.assertTrue(terminal['claims'])
        self.assertTrue(all(c['active'] is None for c in terminal['claims'].values()))
        self.assertFalse(any(e['event_type']=='TARGET_CLAIM_RELEASED' for e in terminal['events']))
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
        closer=self.start('close','direct_close','close_hold')
        self.phase('close','mutation_lock_attempt',closer)
        with self.assertRaises(TaskStoreError):
            with TaskStore(self.storage,lock_timeout=.1).mutation_lock(TASK):
                self.fail('execution boundary did not hold mutation lock')
        self.assertFalse((self.base/'close.mutation_lock_acquired').exists())
        self.release('mutation')
        self.phase('close','mutation_lock_acquired',closer)
        self.assertEqual(self.finish('mutation',writer)['result'],'EXECUTED')
        done=self.state('DONE_before_move')
        self.assertTrue(done['locations']['active'])
        self.assertEqual(done['operations']['op_diag']['status'],'DONE')
        self.assertEqual(done['target_sha256'],sha(POST))
        self.release('close')
        self.assertEqual(self.finish('close',closer)['result'],'COMPLETED')
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


if __name__ == '__main__':
    if sys.argv[1:2] == ['--worker']:
        worker(sys.argv[2])
    else:
        unittest.main()
