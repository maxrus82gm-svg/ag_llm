"""ASTRA-WEB02-TEST-ARCH-001 pilot: three new scenarios, independent disk oracles.

No production getters/projection are used to calculate expected state. All actor
calls use production APIs; observers read exact bytes and raw records with stdlib.
Run via wa4a_acceptance.py; no agent-specific logic or non-stdlib dependencies.
"""
from __future__ import annotations

import base64
import errno
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import time
import traceback
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parent
SEED = 742919
TIMEOUT = 30


def digest(data):
    return hashlib.sha256(data).hexdigest()


def strict_json(path):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError('duplicate JSON key: ' + key)
            out[key] = value
        return out
    def invalid(value):
        raise ValueError('non-JSON constant: ' + value)
    return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=pairs,
                      parse_constant=invalid)


def file_fact(path):
    path = Path(path)
    if not path.exists():
        return {'exists': False, 'size': None, 'sha256': None}
    data = path.read_bytes()
    return {'exists': True, 'size': len(data), 'sha256': digest(data)}


def expected_file(data):
    return ({'exists': False, 'size': None, 'sha256': None} if data is None else
            {'exists': True, 'size': len(data), 'sha256': digest(data)})


def assert_receipt(test, receipt, data):
    test.assertIsInstance(receipt, dict)
    for key, value in expected_file(data).items():
        test.assertEqual(receipt[key], value, 'independent receipt field ' + key)
    test.assertIs(receipt['matches_expected_post'], True)


def tree_facts(root):
    return {p.relative_to(root).as_posix(): digest(p.read_bytes())
            for p in sorted(Path(root).rglob('*')) if p.is_file()}


def wait_for(path, processes=()):
    deadline = time.monotonic() + TIMEOUT
    while not Path(path).exists():
        if any(p.poll() is not None for p in processes):
            raise RuntimeError('worker exited before phase ' + str(path))
        if time.monotonic() >= deadline:
            raise TimeoutError('phase not reached: ' + str(path))
        time.sleep(.005)


def worker(config_path):
    from web_alarm.mutation_executor import MutationExecutor
    from web_alarm.operation_store import OperationStore
    config = strict_json(config_path)
    trace = Path(config['trace'])
    def mark(phase, **facts):
        with trace.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(dict(phase=phase, ns=time.monotonic_ns(), **facts)) + '\n')
            stream.flush()
    actual_apply = MutationExecutor._apply
    actual_transition = OperationStore._transition_locked
    mode = config['mode']
    def apply(kind, path, data):
        mark('apply_enter', kind=kind.value)
        if mode == 'barrier':
            Path(config['entered']).touch()
            wait_for(config['release'])
        if mode == 'fsync_failure':
            def refuse(fd):
                mark('fault_triggered', fault='target_staging_fsync', errno=errno.ENOSPC)
                raise OSError(errno.ENOSPC, 'injected target staging fsync failure')
            # STARTED is already durable. The real helper still writes/flushes
            # its staging file and must clean it up when fsync refuses it.
            with mock.patch.object(os, 'fsync', refuse):
                return actual_apply(kind, path, data)
        return actual_apply(kind, path, data)
    def transition(store, task, op, status, **kwargs):
        result = actual_transition(store, task, op, status, **kwargs)
        if mode == 'crash_after_done' and str(getattr(status, 'value', status)) == 'DONE':
            mark('crash_triggered', point='durable_DONE_before_response', exit_code=91)
            os._exit(91)
        return result
    try:
        with mock.patch.object(MutationExecutor, '_apply', staticmethod(apply)), \
             mock.patch.object(OperationStore, '_transition_locked', transition):
            result = MutationExecutor(config['storage']).execute(
                config['task'], 'm1', config['operation'], config['action'], config['target'],
                payload=base64.b64decode(config['payload']) if config['payload'] is not None else None)
        print(json.dumps({k: result[k] for k in ('result', 'result_code', 'receipt')}))
    except Exception as exc:
        chain, seen = [], set()
        while exc is not None and id(exc) not in seen:
            seen.add(id(exc))
            chain.append({'type': type(exc).__name__, 'message': str(exc),
                          'frames': traceback.format_tb(exc.__traceback__)})
            exc = exc.__cause__ or exc.__context__
        print(json.dumps({'worker_error': chain}))
        raise SystemExit(2)


class NewInvariantTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='astra_invariant_')
        self.base = Path(self.temp.name)
        self.storage = self.base / 'storage'
        self.processes = []
        self.facts = [{'schema': 'web-alarm-pilot/v1', 'seed': SEED,
                       'test': self.id(), 'oracle': 'stdlib raw bytes/JSON; no production readers',
                       'command': 'python -B wa4a_acceptance.py --task ASTRA-WEB02-TEST-ARCH-001 '
                                  '--output <fresh-system-TEMP> ' + self.id()}]
        self.addCleanup(self.cleanup_owned)

    def cleanup_owned(self):
        for process in self.processes:
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=10)
        self.facts.append({'terminal_fixture_files': tree_facts(self.base)})
        self.temp.cleanup()

    def fixture(self, task, workspace, target, before):
        from web_alarm.workspace_registry import WorkspaceRegistry
        from web_alarm.task_store import TaskStore
        from web_alarm.state_machine import ServerStateMachine
        project = self.base / ('workspace ' + workspace)
        project.mkdir()
        if before is not None:
            (project / target).write_bytes(before)
        WorkspaceRegistry(self.storage).register('pilot', project, workspace_id=workspace)
        tasks = TaskStore(self.storage)
        tasks.create_task(workspace, 'pilot', 'synthetic fixture', 'invariant', task_id=task)
        tasks.create_microtask(task, 'm1', 'step', microtask_id='m1')
        machine = ServerStateMachine(self.storage)
        machine.prepare_microtask(task, 'm1', [(target, 'create' if before is None else 'edit')])
        machine.transition(task, 'm1', 'READY')
        machine.transition(task, 'm1', 'ACTIVE')
        self.facts.append({'fixture': task, 'workspace': workspace, 'target': target,
                           'initial_file': file_fact(project / target)})
        return project

    def task_dir(self, task):
        return self.storage / 'tasks' / 'active' / task

    def raw_op(self, task, op):
        return strict_json(self.task_dir(task) / 'operations' / (op + '.json'))

    def start(self, name, task, target, action, payload, *, operation='op_shared', mode='normal'):
        config = dict(storage=str(self.storage), task=task, target=target, action=action,
                      payload=base64.b64encode(payload).decode('ascii') if payload is not None else None,
                      operation=operation, mode=mode, trace=str(self.base / (name + '.jsonl')),
                      entered=str(self.base / (name + '.entered')), release=str(self.base / 'release'))
        path = self.base / (name + '.json')
        path.write_text(json.dumps(config), encoding='utf-8')
        process = subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()), '--worker', str(path)],
                                   cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, encoding='utf-8')
        self.processes.append(process)
        return process

    def finish(self, process, name, expected_exit=0):
        stdout, stderr = process.communicate(timeout=TIMEOUT + 10)
        trace = self.base / (name + '.jsonl')
        events = [json.loads(line) for line in trace.read_text(encoding='utf-8').splitlines()] if trace.exists() else []
        observation = {'worker': name, 'exit': process.returncode, 'trace': events,
                       'stdout': stdout, 'stderr': stderr}
        self.facts.append(observation)
        self.assertEqual(process.returncode, expected_exit, observation)
        if expected_exit == 91:
            self.assertEqual(stdout, '')
            self.assertEqual(sum(e['phase'] == 'crash_triggered' for e in events), 1)
            return None
        return json.loads(stdout)

    def run_actor(self, name, *args, **kwargs):
        return self.finish(self.start(name, *args, **kwargs), name)

    def apply_attempts(self):
        return sum(json.loads(line)['phase'] == 'apply_enter' for path in self.base.glob('*.jsonl')
                   for line in path.read_text(encoding='utf-8').splitlines())

    def check_file(self, path, data):
        observed = file_fact(path)
        self.facts.append({'observed_file': observed, 'expected_file': expected_file(data)})
        self.assertEqual(observed, expected_file(data))

    def test_staging_fsync_failure_preserves_prestate_across_restart(self):
        """P1 / WA-I07,I10: real staging cleanup, injected fsync, no blind replay."""
        before, after = b'PRE\r\n\x00\xff', b'POST\n\x00\xfe'
        project = self.fixture('task_fault', 'ws_fault', 'data.bin', before)
        snapshot = self.task_dir('task_fault') / 'microtasks/m1/restore_point'
        saved_snapshot = tree_facts(snapshot)
        self.assertTrue(saved_snapshot, 'fixture must have real snapshot evidence')
        out = self.run_actor('fault', 'task_fault', 'data.bin', 'write', after, mode='fsync_failure')
        self.assertEqual((out['result'], out['result_code']),
                         ('RECONCILIATION_REQUIRED', 'WRITE_REFUSED_TARGET_UNCHANGED'))
        faults = [e for f in self.facts for e in f.get('trace', []) if e['phase'] == 'fault_triggered']
        self.assertEqual(len(faults), 1, 'fault must actually execute exactly once')
        self.check_file(project / 'data.bin', before)
        self.assertEqual(sorted(p.name for p in project.iterdir()), ['data.bin'], 'no staging orphan')
        record = self.raw_op('task_fault', 'op_shared')
        self.assertEqual(record['status'], 'STARTED')
        self.assertIsNone(record['receipt'])
        replay = self.run_actor('reopen', 'task_fault', 'data.bin', 'write', after)
        self.assertEqual(replay['result'], 'RECONCILIATION_REQUIRED')
        self.assertEqual(self.apply_attempts(), 1, 'fresh replay must not enter physical apply')
        self.check_file(project / 'data.bin', before)
        self.assertEqual(tree_facts(snapshot), saved_snapshot)
        self.assertEqual(self.raw_op('task_fault', 'op_shared'), record)
        self.facts.append({'invariants': ['WA-I07', 'WA-I10'], 'fault_hits': 1, 'apply_attempts': 1,
                           'raw_operation': record, 'snapshot_preserved': True})

    def test_empty_create_crash_delete_and_historical_replay_never_resurrects(self):
        """P2 / WA-I04,I11,I13: empty existing file differs from absent file."""
        project = self.fixture('task_empty', 'ws_empty', 'empty.bin', None)
        process = self.start('crash', 'task_empty', 'empty.bin', 'create', b'', mode='crash_after_done')
        self.finish(process, 'crash', expected_exit=91)
        self.check_file(project / 'empty.bin', b'')
        record = self.raw_op('task_empty', 'op_shared')
        self.assertEqual(record['status'], 'DONE')
        assert_receipt(self, record['receipt'], b'')
        replay = self.run_actor('reopen', 'task_empty', 'empty.bin', 'create', b'')
        self.assertEqual((replay['result'], replay['receipt']), ('REPLAYED', record['receipt']))
        deleted = self.run_actor('delete', 'task_empty', 'empty.bin', 'delete', None, operation='op_delete')
        self.assertEqual(deleted['result'], 'EXECUTED')
        assert_receipt(self, self.raw_op('task_empty', 'op_delete')['receipt'], None)
        self.check_file(project / 'empty.bin', None)
        replay = self.run_actor('history', 'task_empty', 'empty.bin', 'create', b'')
        self.assertEqual((replay['result'], replay['receipt']), ('REPLAYED', record['receipt']))
        self.check_file(project / 'empty.bin', None)
        self.assertEqual(self.raw_op('task_empty', 'op_shared'), record)
        self.assertEqual(self.apply_attempts(), 2, 'one CREATE and one DELETE; neither replay applies')
        self.facts.append({'invariants': ['WA-I04', 'WA-I11', 'WA-I13'], 'apply_attempts': 2,
                           'historical_create_receipt': record['receipt'], 'current_file': file_fact(project / 'empty.bin')})

    def test_same_operation_id_in_two_workspaces_has_independent_concurrent_effects(self):
        """P3 / WA-I03,I11,I13: task-local identity, real overlapping boundaries."""
        random_source = random.Random(SEED)
        target = '\u0434\u0430\u043d\u043d\u044b\u0435 space.bin'
        sides = []
        for name in ('left', 'right'):
            before = name.encode() + b'\r\n\x00'
            after = b'\xef\xbb\xbf' + name.encode() + random_source.randbytes(257) + b'\r\n\x00\xff'
            project = self.fixture('task_' + name, 'ws_' + name, target, before)
            sides.append((name, project, before, after))
        processes = [(name, self.start(name, 'task_' + name, target, 'write', after, mode='barrier'))
                     for name, _, _, after in sides]
        for name, process in processes:
            wait_for(self.base / (name + '.entered'), [p for _, p in processes])
        for name, project, before, after in sides:
            record = self.raw_op('task_' + name, 'op_shared')
            self.assertEqual(record['status'], 'STARTED')
            self.assertIsNone(record['receipt'])
            self.check_file(project / target, before)
        self.facts.append({'schedule': 'both workers entered apply with durable STARTED before release'})
        (self.base / 'release').touch()
        for name, process in processes:
            self.assertEqual(self.finish(process, name)['result'], 'EXECUTED')
        for name, project, _, after in sides:
            self.check_file(project / target, after)
            record = self.raw_op('task_' + name, 'op_shared')
            self.assertEqual((record['task_id'], record['contract']['workspace_id']), ('task_' + name, 'ws_' + name))
            self.assertEqual(record['status'], 'DONE')
            assert_receipt(self, record['receipt'], after)
            replay = self.run_actor('replay_' + name, 'task_' + name, target, 'write', after)
            self.assertEqual((replay['result'], replay['receipt']), ('REPLAYED', record['receipt']))
            self.assertEqual(self.raw_op('task_' + name, 'op_shared'), record)
            events = [json.loads(line) for line in (self.task_dir('task_' + name) / 'events.jsonl').read_text(encoding='utf-8').splitlines()]
            self.assertTrue(all(e['task_id'] == 'task_' + name for e in events))
            self.assertEqual(sum(e['event_type'] == 'MUTATION_EXECUTED' for e in events), 1)
        self.assertEqual(self.apply_attempts(), 2)
        self.facts.append({'invariants': ['WA-I03', 'WA-I11', 'WA-I13'], 'apply_attempts': 2,
                           'input_seed': SEED, 'payload_hashes': [digest(s[3]) for s in sides]})


if __name__ == '__main__':
    if sys.argv[1:2] == ['--worker']:
        worker(sys.argv[2])
    else:
        unittest.main()
