"""WA4-O acceptance: real HTTP + disposable authoritative stores, no live data."""
import hashlib
import json
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

from web_alarm.models import MicrotaskStatus
from web_alarm.server import WebAlarmApi, create_server
from web_alarm.recovery_report_store import RecoveryReportStoreError

ROOT = Path(__file__).resolve().parent


def tree(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}


class OperatorFixture:
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='wa4o_')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.api = WebAlarmApi(self.root / 'storage')
        for wid in ('ws_a', 'ws_b'):
            project = self.root / wid
            project.mkdir()
            (project / 'a.txt').write_bytes(b'before')
            self.api.registry.register(wid, project, workspace_id=wid)
        for tid, wid in (('task_a', 'ws_a'), ('task_b', 'ws_b'), ('task_c', 'ws_a')):
            self.api.tasks.create_task(wid, tid, '<img src=x onerror=alert(1)>', 'Operator goal', task_id=tid)
            for mid in ('m1', 'm2', 'm3'):
                self.api.tasks.create_microtask(tid, mid, 'Goal '+mid, microtask_id=mid)
        self.server = create_server(self.api, host='127.0.0.1', port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = 'http://127.0.0.1:'+str(self.server.server_port)
        self.addCleanup(self.stop)

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(5)

    def http(self, path, method='GET', body=None):
        raw = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(self.url+path, data=raw, method=method,
                                         headers={'Content-Type': 'application/json'})
        try:
            response = urllib.request.urlopen(request, timeout=10)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            return response.status, json.loads(response.read())

    def ui(self, task='task_a'):
        status, data = self.http('/tasks/'+task+'/ui')
        self.assertEqual(status, 200, data)
        return data

    def status(self, mid, status, tid='task_a'):
        self.api.tasks.set_microtask_status(tid, mid, MicrotaskStatus(status))

    def prepare(self, mid='m1', tid='task_a'):
        self.api.machine.prepare_microtask(tid, mid, [('a.txt', 'edit')])

    def begin(self, op='op_1', mid='m1'):
        return self.api.operations.begin('task_a', mid, 'write', 'a.txt', operation_id=op, payload=b'after')


class OperatorHttpTests(OperatorFixture, unittest.TestCase):
    def test_o1_navigation_two_workspaces_and_three_tasks(self):
        status, data = self.http('/ui/tasks')
        self.assertEqual(status, 200)
        self.assertEqual({t['workspace_id'] for t in data['active']}, {'ws_a', 'ws_b'})
        self.assertEqual([t['task_id'] for t in data['active']], ['task_a', 'task_b', 'task_c'])
        for tid, wid in [('task_a','ws_a'),('task_b','ws_b')]:
            v = self.ui(tid)
            self.assertEqual(v['workspace']['workspace_id'], wid)
            self.assertEqual(v['task_state']['task']['task_id'], tid)
            self.assertEqual(v['current_microtask_id'], 'm1')

    def test_o1_corrupt_task_does_not_hide_other_workspaces(self):
        (self.api.tasks.task_directory('task_b')/'task.json').write_text('broken')
        _, v = self.http('/ui/tasks')
        self.assertEqual([r['task_id'] for r in v['errors']], ['task_b'])
        self.assertEqual({r['task_id'] for r in v['active']}, {'task_a','task_c'})

    def test_o2_plan_order_is_not_creation_sequence(self):
        self.api.tasks.set_plan('task_a',['m3','m1','m2'])
        v = self.ui()['operator']
        self.assertEqual([m['microtask_id'] for m in v['stages']], ['m3','m1','m2'])
        self.assertEqual(v['stages'][1]['prerequisites'], ['m3'])
        self.assertEqual([m['position'] for m in v['stages']], [1,2,3])

    def test_o2_real_lifecycle_statuses_are_not_ui_statuses(self):
        for status in MicrotaskStatus:
            with self.subTest(status=status.value):
                if status == MicrotaskStatus.ACTIVE:
                    self.status('m1','PLANNED')
                    self.prepare()
                self.status('m1', status.value)
                v = self.ui()
                self.assertEqual(v['operator']['stages'][0]['status'], status.value)

    def test_o3_done_and_unknown_do_not_count_as_verified(self):
        self.status('m1','VERIFIED')
        self.status('m2','DONE')
        v = self.ui()['operator']['progress']
        self.assertEqual(v, {'verified':1,'persisted_verified':1,'total':3,'done':1})
        self.status('m2','UNKNOWN_AFTER_DISCONNECT')
        self.assertEqual(self.ui()['operator']['progress']['verified'], 1)

    def test_o3_conflicting_verified_order_withholds_progress(self):
        self.status('m2','VERIFIED')
        v = self.ui()
        self.assertIsNone(v['operator']['progress']['verified'])
        self.assertEqual(v['operator']['progress']['persisted_verified'],1)
        self.assertEqual(v['recovery_state'],'PROJECTION_BLOCKED')

    def test_o4_unique_unfinished_operation_has_exact_identity(self):
        self.prepare()
        self.begin()
        self.api.operations.transition('task_a','op_1','STARTED')
        op = self.ui()['operator']['current_operation']
        self.assertEqual(op['record']['operation_id'],'op_1')
        self.assertEqual(op['record']['target'],'a.txt')
        self.assertEqual(op['record']['status'],'STARTED')
        self.assertIsNone(op['record']['receipt'])

    def test_o4_ambiguous_operations_never_pick_latest(self):
        self.prepare()
        self.begin('op_a')
        self.begin('op_z')
        o = self.ui()['operator']
        self.assertIsNone(o['current_operation'])
        self.assertIn('Несколько',o['current_operation_reason'])

    def test_o4_terminal_receipt_is_history_not_current_or_byte_proof(self):
        self.prepare()
        self.begin()
        self.api.operations.transition('task_a','op_1','STARTED')
        (self.root/'ws_a'/'a.txt').write_bytes(b'after')
        self.api.operations.transition('task_a','op_1','DONE')
        (self.root/'ws_a'/'a.txt').write_bytes(b'external drift')
        o = self.ui()['operator']
        self.assertIsNone(o['current_operation'])
        self.assertEqual(o['operations'][0]['receipt_scope'],'HISTORICAL_ONLY')
        self.assertTrue(o['operations'][0]['record']['receipt']['matches_expected_post'])
        self.assertIsNone(o['operations'][0]['current_post_state_matches'])
        self.assertEqual(o['progress']['verified'],0)

    def test_o4_operation_of_later_stage_is_not_current(self):
        self.status('m1','VERIFIED')
        self.prepare(mid='m2')
        self.begin(mid='m2')
        self.status('m1','PLANNED')
        self.assertIsNone(self.ui()['operator']['current_operation'])

    def test_o5_unknown_is_not_failed_and_next_is_projection_decision(self):
        self.prepare()
        self.begin()
        self.api.operations.transition('task_a','op_1','UNKNOWN_AFTER_DISCONNECT')
        v = self.ui()
        self.assertEqual(v['operator']['operations'][0]['record']['status'],'UNKNOWN_AFTER_DISCONNECT')
        self.assertEqual(v['next_safe_action'],v['task_state']['projection']['next_safe_action'])
        self.assertNotEqual(v['recovery_state'],'NORMAL')

    def test_o5_stale_checkpoint_is_never_shown_valid(self):
        self.api.projection.rebuild_checkpoint('task_a')
        self.status('m1','READY')
        v = self.ui()
        self.assertEqual(v['checkpoint_validation']['status'],'STALE')
        self.assertTrue(v['operator']['coherent'])

    def test_o5_corrupt_checkpoint_is_visible_and_not_repaired_by_get(self):
        path = self.api.tasks.task_directory('task_a')/'checkpoint.json'
        path.write_text('{corrupt')
        before = tree(self.root)
        self.assertEqual(self.ui()['checkpoint_validation']['status'],'CORRUPT')
        self.assertEqual(before,tree(self.root))

    def test_o5_missing_recovery_evidence_is_explicit(self):
        with mock.patch.object(self.api.recovery_reports,'list_reports',side_effect=RecoveryReportStoreError('bad report')):
            errors = self.ui()['operator']['evidence_errors']
        self.assertEqual(errors[0]['source'],'recovery_reports')

    def test_o5_real_partial_rollback_is_visible_over_http(self):
        import test_web_alarm_rollback as fixture_module
        import web_alarm.rollback_service as rollback_module
        f = fixture_module.RollbackFixture()
        f.setUp()
        try:
            resolution = f.scenario('two')
            rollback = f.prepare(resolution)['rollback']
            order = [t['source_path'] for t in rollback['targets'] if t['planned_action']=='WRITE_RESTORE']
            real = rollback_module._write_restored_bytes
            def drift(path, data):
                real(path,data)
                f.write(order[1],b'external drift\n')
            with mock.patch.object(rollback_module,'_write_restored_bytes',drift):
                outcome = f.rollbacks.apply(fixture_module.TASK,rollback['rollback_id'])
            self.assertEqual(outcome['result'],'PARTIAL')
            server = create_server(WebAlarmApi(f.storage),port=0)
            thread = threading.Thread(target=server.serve_forever,daemon=True)
            thread.start()
            try:
                with urllib.request.urlopen('http://127.0.0.1:'+str(server.server_port)+'/tasks/'+fixture_module.TASK+'/ui') as response:
                    v = json.load(response)
                self.assertEqual(v['task_state']['projection']['rollbacks'][0]['status'],'PARTIAL')
                self.assertIn('PARTIAL',v['recovery_state'])
                self.assertNotEqual(v['next_safe_action'],'SUCCESS')
            finally:
                server.shutdown(); server.server_close(); thread.join(5)
        finally:
            f.tearDown()

    def test_o5_stale_resolver_decision_never_overrides_new_next(self):
        self.prepare()
        self.begin()
        self.api.operations.transition('task_a','op_1','STARTED')
        target = self.root/'ws_a'/'a.txt'
        target.write_bytes(b'after')
        decision = self.api.reconciliation.reconcile('task_a','m1','op_1')['DECISION']
        r = self.api.resolver.apply('task_a','m1','op_1','ADOPT',
                                   evidence_fingerprint=decision['evidence_fingerprint'],operation_revision=2)
        self.assertTrue(r['accepted'])
        target.write_bytes(b'new writer')
        v = self.ui()
        self.assertEqual(v['recovery_state'],'RESOLUTION_STALE')
        self.assertNotEqual(v['next_safe_action'],r['resolution'].next_safe_action)

    def test_o5_corrupt_operations_withhold_progress_and_identity(self):
        self.prepare()
        self.begin()
        path = self.api.tasks.task_directory('task_a')/'operations'/'op_1.json'
        path.write_text('{corrupt')
        v = self.ui()
        self.assertEqual(v['recovery_state'],'PROJECTION_BLOCKED')
        self.assertIsNone(v['operator']['current_operation'])
        self.assertIsNone(v['operator']['progress']['verified'])
        self.assertIn('operations',[e['source'] for e in v['operator']['evidence_errors']])

    def test_o4_closed_task_has_only_history_despite_unfinished_operation(self):
        self.prepare()
        self.begin()
        path = self.api.tasks.task_directory('task_a')/'task.json'
        raw = json.loads(path.read_text())
        raw['status']='COMPLETED'
        path.write_text(json.dumps(raw))
        v = self.ui()
        self.assertIsNone(v['operator']['current_operation'])
        self.assertEqual(v['authority_source'],'task_status')
        self.assertIn('read-only',v['next_safe_action'])

    def test_o5_read_race_is_bounded_and_withholds_current_and_progress(self):
        real = self.api.projection.build
        count = 0
        def racing(tid):
            nonlocal count
            count += 1
            if count == 2:
                self.status('m1','READY')
            return real(tid)
        with mock.patch.object(self.api.projection,'build',side_effect=racing):
            o = self.ui()['operator']
        self.assertEqual(count,2)
        self.assertFalse(o['coherent'])
        self.assertIsNone(o['progress']['verified'])
        self.assertIsNone(o['current_operation'])

    def test_o6_recovery_report_cannot_override_authoritative_next(self):
        from web_alarm.recovery_report_store import RecoveryReportRecord, SideEffectScope
        self.api.recovery_reports.store.append(RecoveryReportRecord(
            incident_id='old',task_id='task_a',microtask_id='m1',
            side_effect_scope=SideEffectScope.NONE,next_safe_action='DO NOT USE THIS HISTORY'))
        v = self.ui()
        self.assertNotEqual(v['next_safe_action'],'DO NOT USE THIS HISTORY')
        self.assertEqual(v['operator']['recovery_reports'][0]['next_safe_action'],'DO NOT USE THIS HISTORY')

    def test_o7_refresh_and_evidence_have_no_persistent_side_effect(self):
        self.prepare()
        self.begin()
        before = tree(self.root)
        for _ in range(3):
            self.http('/ui/tasks')
            self.ui()
        self.assertEqual(tree(self.root),before)

    def test_o7_get_never_calls_execution_or_recovery_or_rebuild(self):
        with mock.patch.object(self.api.executor,'execute',side_effect=AssertionError('mutation')), \
             mock.patch.object(self.api.recovery,'recover',side_effect=AssertionError('recovery')), \
             mock.patch.object(self.api.projection,'rebuild_checkpoint',side_effect=AssertionError('checkpoint write')):
            self.ui()
            self.http('/ui/tasks')

    def test_o7_navigation_rejects_mutating_method(self):
        before = tree(self.root)
        status, _ = self.http('/ui/tasks','POST',{})
        self.assertEqual(status,405)
        self.assertEqual(before,tree(self.root))

    def test_o8_fresh_api_and_new_http_server_same_persisted_state(self):
        self.prepare()
        self.begin()
        before = self.ui()
        second = create_server(WebAlarmApi(self.root/'storage'),port=0)
        thread = threading.Thread(target=second.serve_forever,daemon=True)
        thread.start()
        try:
            with urllib.request.urlopen('http://127.0.0.1:'+str(second.server_port)+'/tasks/task_a/ui') as response:
                after = json.load(response)
            for key in ('next_safe_action','recovery_state','current_microtask_id','checkpoint_validation'):
                self.assertEqual(before[key],after[key])
            self.assertEqual(before['operator']['stages'],after['operator']['stages'])
        finally:
            second.shutdown(); second.server_close(); thread.join(5)

    def test_o8_new_process_starts_http_and_reopens_authoritative_state(self):
        before = self.ui()
        script = '''import json,sys,threading,urllib.request
from web_alarm.server import WebAlarmApi,create_server
s=create_server(WebAlarmApi(sys.argv[1]),port=0)
t=threading.Thread(target=s.serve_forever);t.start()
try:
 with urllib.request.urlopen('http://127.0.0.1:'+str(s.server_port)+'/tasks/task_a/ui') as r: print(r.read().decode())
finally: s.shutdown();s.server_close();t.join()
'''
        r = subprocess.run([sys.executable,'-B','-c',script,str(self.root/'storage')],
                           cwd=ROOT,capture_output=True,text=True,timeout=20)
        self.assertEqual(r.returncode,0,r.stderr)
        after = json.loads(r.stdout)
        self.assertEqual(before['next_safe_action'],after['next_safe_action'])
        self.assertEqual(before['operator']['stages'],after['operator']['stages'])

    def test_o9_incorrect_status_returns_honest_http_error(self):
        path = self.api.tasks.task_directory('task_a')/'microtasks'/'m1.json'
        raw = json.loads(path.read_text())
        raw['status']='SUCCESS'
        path.write_text(json.dumps(raw))
        status, data = self.http('/tasks/task_a/ui')
        self.assertEqual(status,409)
        self.assertIn('error',data)

    def test_o9_user_text_remains_data_and_root_does_not_embed_it(self):
        v = self.ui()
        self.assertEqual(v['task_state']['task']['raw_task'],'<img src=x onerror=alert(1)>')
        with urllib.request.urlopen(self.url+'/') as r:
            html = r.read().decode()
        self.assertNotIn('<img src=x',html)
        self.assertNotIn('innerHTML',html)

    def test_o10_existing_workspace_task_creation_and_api_preserved(self):
        status, data = self.http('/tasks','POST',{'workspace_id':'ws_b','title':'Created',
                                               'goal':'Check','raw_task':'raw'})
        self.assertEqual(status,201)
        v = self.ui(data['task']['task_id'])
        self.assertEqual(v['operator']['progress']['total'],0)
        self.assertEqual(self.http('/tasks')[0],200)


if __name__ == '__main__':
    unittest.main()
