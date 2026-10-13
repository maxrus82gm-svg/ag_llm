"""Explicit negative controls; not part of product unittest discovery."""
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0,str(Path.cwd()))
import test_web_alarm_wa4r002_diagnostics as diagnostic


class Sensitivity(unittest.TestCase):
    def check_inner_failure(self, test, patch):
        result=unittest.TestResult()
        with patch:
            test.run(result)
        self.assertEqual((result.testsRun,len(result.failures),len(result.errors),len(result.skipped)),(1,1,0,0))
        self.facts=[{'control':'intentional oracle/trigger violation',
                     'expected_inner_failure':result.failures[0][1]}]

    def test_removing_native_reader_does_not_fake_the_expected_failure(self):
        test=diagnostic.RaceEvidenceTests('test_F1_native_post_move_status_failure_and_fresh_recovery')
        original=diagnostic.RaceEvidenceTests.start
        def normal(obj,name,action,mode='normal'):
            return original(obj,name,action,'normal' if mode=='native_status' else mode)
        self.check_inner_failure(test,mock.patch.object(diagnostic.RaceEvidenceTests,'start',normal))

    def test_counterfeit_raw_receipt_is_rejected(self):
        test=diagnostic.RaceEvidenceTests('test_F2_release_event_error_after_DONE_is_replayed_without_second_apply')
        original=diagnostic.read_json
        def corrupt(path):
            value=original(path)
            if Path(path).parent.name=='operations' and value.get('receipt'):
                value['receipt']['sha256']='0'*64
            return value
        self.check_inner_failure(test,mock.patch.object(diagnostic,'read_json',corrupt))


if __name__=='__main__':
    from wa4a_acceptance import run_tests
    sys.path.insert(0,str(Path(__file__).parent))
    raise SystemExit(run_tests(['quality_controls.Sensitivity'],sys.argv[1],task_id='CODEX-WA4-R-002-QUALITY'))
