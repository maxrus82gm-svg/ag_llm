"""Manual negative controls using sealed local before sources, outside FULL."""
from pathlib import Path
import json
import sys
import textwrap
import unittest
from unittest import mock

sys.path.insert(0,str(Path.cwd()))
import test_web_alarm_wa4r002_diagnostics as diagnostic
import web_alarm.task_store as task_store
import test_web_alarm_mutation_executor as mutation_test


def old_method(key,module=task_store):
    item=json.loads(Path(__file__).with_name('control-inputs.json').read_text(encoding='utf-8'))[key]
    namespace=dict(vars(module))
    exec(compile(textwrap.dedent(item['code']),item['source_path']+':'+item['method'],'exec'),namespace)
    return namespace[item['method']]


class Sensitivity(unittest.TestCase):
    def run_broken(self,name,patch,*,errors=0,contains=None):
        test=diagnostic.RaceEvidenceTests(name)
        result=unittest.TestResult()
        with patch:
            test.run(result)
        self.assertEqual((result.testsRun,len(result.failures),len(result.errors),len(result.skipped)),(1,1-errors,errors,0))
        message=(result.errors if errors else result.failures)[0][1]
        if contains:
            self.assertIn(contains,message)
        self.facts=[{'intentional_inner_red':message,'control_selector':name}]

    def test_restored_old_lookup_reproduces_phantom_duplicate(self):
        method=old_method('old_lookup')
        self.run_broken('test_F2_directory_probes_do_not_invent_duplicate_during_real_move',
                        mock.patch.object(task_store.TaskStore,'_task_path',method),errors=1,
                        contains='exists in active and completed')

    def test_removing_gap_recheck_reproduces_false_unknown(self):
        method=old_method('gap_lookup')
        self.run_broken('test_F2_move_between_destination_and_source_probe_is_resolved',
                        mock.patch.object(task_store.TaskStore,'_task_path',method),errors=1,
                        contains='unknown task_id')

    def test_removing_completion_outer_lock_is_detected(self):
        method=old_method('old_complete')
        self.run_broken('test_F2_completion_lock_timeout_writes_nothing_and_releases_locks',
                        mock.patch.object(task_store.TaskStore,'complete_task',method),
                        contains='TaskStoreError not raised')

    def test_missing_native_trigger_is_detected(self):
        original=diagnostic.RaceEvidenceTests.start
        def normal(obj,name,action,mode='normal'):
            return original(obj,name,action,'normal' if mode=='native_status' else mode)
        self.run_broken('test_F1_native_post_move_status_failure_and_fresh_recovery',
                        mock.patch.object(diagnostic.RaceEvidenceTests,'start',normal))

    def test_counterfeit_raw_receipt_is_detected(self):
        original=diagnostic.read_json
        def corrupt(path):
            value=original(path)
            if Path(path).parent.name=='operations' and value.get('receipt'):
                value['receipt']['sha256']='0'*64
            return value
        self.run_broken('test_F2_release_event_error_after_DONE_is_replayed_without_second_apply',
                        mock.patch.object(diagnostic,'read_json',corrupt))

    def test_old_start_barrier_oracle_falsely_rejects_legal_sequential_contracts(self):
        name='test_two_executors_on_one_physical_target_never_both_write'
        method=old_method('old_race',mutation_test)
        def sequential(test,jobs):
            test.facts=[]
            results={}
            for worker,point,request in jobs:
                child=test.child(point,'-',worker,json.dumps(request))
                test.assertEqual(child.returncode,0,child.stderr)
                results[worker]=json.loads(child.stdout)
                record=json.loads((test.tasks.active_dir/mutation_test.TASK/'operations'/f'op_{worker}.json').read_text(encoding='utf-8'))
                test.facts.append({'worker':worker,'record':record,'delivered':results[worker]})
            return results
        test=mutation_test.RaceTests(name)
        result=unittest.TestResult()
        with mock.patch.object(mutation_test.RaceTests,name,method),mock.patch.object(mutation_test.RaceTests,'race',sequential):
            test.run(result)
        self.assertEqual((result.testsRun,len(result.failures),len(result.errors),len(result.skipped)),(1,1,0,0))
        self.assertIn('2 != 1',result.failures[0][1])
        self.assertNotEqual(test.facts[0]['record']['contract']['pre_state']['sha256'],
                            test.facts[1]['record']['contract']['pre_state']['sha256'])
        self.assertEqual(test.facts[1]['record']['contract']['pre_state']['sha256'],
                         test.facts[0]['record']['receipt']['sha256'])
        self.facts=[{'intentional_inner_red':result.failures[0][1],'raw':test.facts}]


if __name__=='__main__':
    from wa4a_acceptance import run_tests
    sys.path.insert(0,str(Path(__file__).parent))
    raise SystemExit(run_tests(['quality_controls.Sensitivity'],sys.argv[1],task_id='CODEX-WA4-R-003-F2F3-LOCAL-REPAIR-QUALITY'))
