"""Intentional test-system counterexamples; never added to product discovery."""
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path.cwd()))
import test_web_alarm_new_invariants as pilot


class Empty(unittest.TestCase):
    pass


class TwoSubtestFailures(unittest.TestCase):
    def test_two_bad_cases(self):
        for case in range(2):
            with self.subTest(case=case):
                self.assertEqual('deliberate observed violation', 'required invariant')


class CaughtGuardViolation(unittest.TestCase):
    def test_synthetic_audit_is_denied_without_executing_a_command(self):
        # Emits an audit notification only: no actual shell, filesystem or
        # network action. It proves successful=True alone is insufficient.
        with self.assertRaises(PermissionError):
            sys.audit('os.system', 'SYNTHETIC AUDIT EVENT ONLY; no command executes')


class Sensitivity(unittest.TestCase):
    def test_removed_fault_is_detected(self):
        test = pilot.NewInvariantTests('test_staging_fsync_failure_preserves_prestate_across_restart')
        original = pilot.NewInvariantTests.start
        def without_fault(obj, *args, **kwargs):
            if kwargs.get('mode') == 'fsync_failure':
                kwargs['mode'] = 'normal'
            return original(obj, *args, **kwargs)
        result = unittest.TestResult()
        with mock.patch.object(pilot.NewInvariantTests, 'start', without_fault):
            test.run(result)
        self.assertEqual((result.testsRun, len(result.failures), len(result.errors)), (1, 1, 0))
        self.facts = [{'negative_control': 'fault removed', 'expected_inner_failure': result.failures[0][1]}]

    def test_changed_input_bytes_are_detected_by_independent_model(self):
        test = pilot.NewInvariantTests('test_same_operation_id_in_two_workspaces_has_independent_concurrent_effects')
        original = pilot.NewInvariantTests.start
        def altered(obj, name, task, target, action, payload, **kwargs):
            if name == 'left':
                payload = b'intentionally wrong fixture bytes'
            return original(obj, name, task, target, action, payload, **kwargs)
        result = unittest.TestResult()
        with mock.patch.object(pilot.NewInvariantTests, 'start', altered):
            test.run(result)
        self.assertEqual((result.testsRun, len(result.failures), len(result.errors)), (1, 1, 0))
        self.facts = [{'negative_control': 'left input differs from model', 'expected_inner_failure': result.failures[0][1]}]


if __name__ == '__main__':
    from wa4a_acceptance import run_tests
    sys.path.insert(0, str(Path(__file__).parent))
    raise SystemExit(run_tests(['quality_cases.' + sys.argv[1]], sys.argv[2], task_id='ASTRA-WEB02-TEST-ARCH-001-QUALITY'))
