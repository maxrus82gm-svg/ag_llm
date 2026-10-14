"""Explicit intentional-red controls; never part of ordinary Web Alarm discovery."""
from pathlib import Path
import contextlib
import hashlib
import inspect
import json
import subprocess
import sys
import textwrap
import unittest
from unittest import mock

import test_web_alarm_wa4r002_diagnostics as diagnostic
import web_alarm.closeout as closeout


class Sensitivity(unittest.TestCase):
    def expected_red(self, selector, patch, contains):
        inner = diagnostic.RaceEvidenceTests(selector)
        result = unittest.TestResult()
        with patch:
            inner.run(result)
        self.facts = [{'selector': selector, 'expected': contains,
                       'inner_tests': result.testsRun, 'inner_failures': len(result.failures),
                       'inner_errors': len(result.errors), 'inner_skips': len(result.skipped),
                       'inner_facts': inner.facts,
                       'failure': result.failures[0][1] if result.failures else None}]
        self.assertEqual((result.testsRun, len(result.failures), len(result.errors), len(result.skipped)),
                         (1, 1, 0, 0))
        self.assertIn(contains, result.failures[0][1])

    def test_missing_native_pre_move_trigger_is_detected(self):
        original = diagnostic.RaceEvidenceTests.start
        def no_native(test, name, action, mode='normal'):
            return original(test, name, action, 'normal' if mode == 'native_pre' else mode)
        self.expected_red('test_F1_native_pre_move_refusal_preserves_nonempty_evidence_and_fresh_retry',
                          mock.patch.object(diagnostic.RaceEvidenceTests, 'start', no_native), '0 != 2')

    def corrupt_record_after_status_failure(self, relative, mutate, expected):
        original = diagnostic.RaceEvidenceTests.finish
        def corrupt(test, name, process, exit_code=0):
            result = original(test, name, process, exit_code)
            if name == 'close' and exit_code == 2:
                path = test.storage / 'tasks/completed' / diagnostic.TASK / relative
                value = diagnostic.read_json(path)
                before = hashlib.sha256(path.read_bytes()).hexdigest()
                mutate(value)
                path.write_text(json.dumps(value), encoding='utf8')
                test.facts.append({'control': 'actual TEMP record corruption after native fault',
                                   'record': relative, 'before_sha256': before,
                                   'after_sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
            return result
        self.expected_red('test_F1_native_post_move_status_failure_and_fresh_recovery',
                          mock.patch.object(diagnostic.RaceEvidenceTests, 'finish', corrupt), expected)

    def test_counterfeit_persisted_receipt_is_detected(self):
        self.corrupt_record_after_status_failure('operations/op_diag.json',
            lambda value: value['receipt'].__setitem__('sha256', '0' * 64), 'operations')

    def test_lost_checkpoint_identity_is_detected(self):
        self.corrupt_record_after_status_failure('checkpoint.json',
            lambda value: value.__setitem__('last_operation_id', 'counterfeit'), 'checkpoint')

    def test_semantically_equal_rewritten_event_prefix_is_detected(self):
        original = diagnostic.RaceEvidenceTests.finish
        def rewrite(test, name, process, exit_code=0):
            result = original(test, name, process, exit_code)
            if name == 'recover' and exit_code == 0:
                path = test.storage / 'tasks/completed' / diagnostic.TASK / 'events.jsonl'
                before = path.read_bytes()
                records = [diagnostic.parse_json(line) for line in before.decode('utf8').splitlines()]
                changed = ''.join(json.dumps(record, ensure_ascii=False) + '\n' for record in records).encode('utf8')
                self.assertNotEqual(changed, before)
                path.write_bytes(changed)
                test.facts.append({'control': 'actual event bytes rewritten with identical parsed JSON',
                                   'before_sha256': hashlib.sha256(before).hexdigest(),
                                   'after_sha256': hashlib.sha256(changed).hexdigest(),
                                   'parsed_records_equal': records == [diagnostic.parse_json(line) for line in changed.decode('utf8').splitlines()]})
            return result
        self.expected_red('test_F1_native_post_move_status_failure_and_fresh_recovery',
                          mock.patch.object(diagnostic.RaceEvidenceTests, 'finish', rewrite),
                          'historical event prefix bytes changed')

    def test_missing_closeout_operations_lock_is_detected(self):
        source = textwrap.dedent(inspect.getsource(closeout.CloseoutService.complete))
        point = 'with self.operations.task_lock(task_id):'
        self.assertEqual(source.count(point), 1)
        broken = source.replace(point, 'with _no_outer_lock():')
        self.isolated_child_patch(source, broken, 'completion_gate',
            'test_F1_completion_first_serializes_RAW_admission_plan_and_new_mutation',
            'closeout did not hold the operations lock')

    def test_false_success_after_native_status_failure_is_detected(self):
        source = textwrap.dedent(inspect.getsource(closeout.CloseoutService.complete))
        point = 'raise CloseoutError(str(exc)) from exc'
        self.assertEqual(source.count(point), 1)
        broken = source.replace(point, 'return {"result": "COMPLETED", "resumed": None, "event_recorded": False}')
        self.isolated_child_patch(source, broken, 'native_status',
            'test_F1_native_post_move_status_failure_and_fresh_recovery', '0 != 2')
        facts = self.facts[0]['inner_facts']
        terminal = next(f['terminal'] for f in facts if 'terminal' in f)
        self.assertEqual(terminal['locations'], {'active': False, 'completed': True})
        self.assertEqual(terminal['task']['status'], 'PLANNED')
        closed = next(f for f in facts if f.get('worker') == 'close')
        self.assertEqual(json.loads(closed['stdout'])['result'], 'COMPLETED')
        phases = [e['phase'] for e in closed['trace']]
        self.assertIn('directory_moved', phases)
        self.assertIn('status_write_with_native_reader', phases)

    def isolated_child_patch(self, source, broken, mode_to_break, selector, expected):
        original = diagnostic.RaceEvidenceTests.start
        # Only a controlled child copy is changed. Production sources stay byte-identical.
        injection = ('\nimport contextlib as _control_context\n'
                     'import web_alarm.closeout as _control_module\n'
                     '_control_namespace = dict(vars(_control_module), _no_outer_lock=_control_context.nullcontext)\n'
                     'exec(compile(' + repr(broken) + ', "expected-closeout-lock-mutant", "exec"), _control_namespace)\n'
                     '_control_module.CloseoutService.complete = _control_namespace["complete"]\n\n')
        def unlocked(test, name, action, mode='normal'):
            if name != 'close' or mode != mode_to_break:
                return original(test, name, action, mode)
            code = Path(diagnostic.__file__).read_text(encoding='utf8')
            root_point = 'ROOT = Path(__file__).resolve().parent'
            self.assertEqual(code.count(root_point), 1)
            code = code.replace(root_point, 'ROOT = Path(' + repr(str(diagnostic.ROOT)) + ')')
            main = "if __name__ == '__main__':"
            self.assertEqual(code.count(main), 1)
            path = test.base / 'expected_unlocked_worker.py'
            path.write_text(code.replace(main, injection + main), encoding='utf8')
            cfg = dict(base=str(test.base), storage=str(test.storage), project=str(test.project),
                       name=name, action=action, mode=mode)
            config = test.base / (name + '.json')
            config.write_text(json.dumps(cfg), encoding='utf8')
            process = subprocess.Popen([sys.executable, '-B', str(path), '--worker', str(config)],
                                       cwd=diagnostic.ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       text=True, encoding='utf8')
            test.children.append(process)
            test.facts.append({'control': 'intentional closeout violation in isolated child memory',
                               'original_method_sha256': hashlib.sha256(source.encode()).hexdigest(),
                               'mutant_method_sha256': hashlib.sha256(broken.encode()).hexdigest()})
            return process
        self.expected_red(selector, mock.patch.object(diagnostic.RaceEvidenceTests, 'start', unlocked), expected)
