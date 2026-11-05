"""Stage 3: synthetic Turn, real shared storage, no provider transport."""
import hashlib
import json
import tempfile
import contextlib
import concurrent.futures
import os
import subprocess
import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import context_storage as cs
import run_store as rs
from web_alarm.ultra_chat import UltraChatError, UltraChatService


class TurnTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='wua_s3_')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)/'workspace'; self.root.mkdir()
        self.ws = cs.ensure_workspace_storage(self.root)['workspace_id']
        self.chat = cs.create_chat(self.root)['chat_id']
        from web_alarm.turn_service import TurnService
        self.service = TurnService(test_roots=[self.root])
        self.body = dict(idempotency_key='key_0000000000000001',text='Привет 😀',
                         model_ref='local-test:v1',context_ref='empty:v1',config_ref='test-only:v1')

    def send(self, body=None):
        return self.service.submit(self.root,self.ws,self.chat,body or self.body)

    def raw(self):
        return list((self.root/'.ultra/chats'/self.chat/'messages').glob('*.json'))

    def test_roundtrip_replay_and_reopen(self):
        result=self.send()
        self.assertEqual(result['state'],'SUCCEEDED')
        self.assertEqual(result['answer'],'TEST: сообщение принято.')
        before={p.name:p.read_bytes() for p in self.raw()}
        self.assertEqual(len(before),2)
        self.assertEqual(self.send(),result)
        from web_alarm.turn_service import TurnService
        self.service=TurnService(test_roots=[self.root])
        self.assertEqual(self.service.get(self.root,self.ws,self.chat,result['turn_id']),result)
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.raw()})

    def test_conflict_and_distinct_keys(self):
        first=self.send(); before={p.name:p.read_bytes() for p in self.raw()}
        with self.assertRaises(UltraChatError) as error: self.send({**self.body,'text':'другое'})
        self.assertEqual(error.exception.status,409)
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.raw()})
        second=self.send({**self.body,'idempotency_key':'key_0000000000000002'})
        self.assertNotEqual(first['turn_id'],second['turn_id']); self.assertEqual(len(self.raw()),4)

    def ids(self):
        from web_alarm.turn_service import identities
        return identities(self.ws,self.chat,self.body['idempotency_key'])

    def snapshot(self):
        return {p.relative_to(self.root).as_posix():p.read_bytes() for p in self.root.rglob('*') if p.is_file()}

    def test_invalid_references_schema_and_test_roots_do_not_write(self):
        before=self.snapshot()
        for key in ['model_ref','context_ref','config_ref']:
            with self.subTest(key=key), self.assertRaises(UltraChatError): self.send({**self.body,key:'unapproved'})
        for body in [{}, {**self.body,'text':''}, {**self.body,'text':'x'*3000}, {**self.body,'root':str(self.root)}]:
            with self.subTest(body=str(body)[:50]), self.assertRaises(UltraChatError): self.service.submit(self.root,self.ws,self.chat,body)
        from web_alarm.turn_service import TurnService
        with self.assertRaises(UltraChatError): TurnService().submit(self.root,self.ws,self.chat,self.body)
        self.assertEqual(before,self.snapshot())

    def test_raw_crash_before_and_after_commit(self):
        for after in [False, True]:
            with self.subTest(after=after):
                self.body['idempotency_key']='crash_key_'+str(after)+'0'*16
                original=self.service._commit
                def fail(root,turn,role,text):
                    if role=='user':
                        if after: original(root,turn,role,text)
                        raise OSError('RAW injected failure')
                    return original(root,turn,role,text)
                with patch.object(self.service,'_commit',side_effect=fail):
                    with self.assertRaises(UltraChatError): self.send()
                current=self.service.get(self.root,self.ws,self.chat,self.ids()['turn_id'])
                self.assertEqual(current['state'],'ACCEPTING')
                result=self.send(); self.assertEqual(result['state'],'SUCCEEDED')
        self.assertEqual(len(self.raw()),4)

    def test_get_never_starts_ready_turn_and_cancel_before_start(self):
        with patch.object(self.service,'_execute',side_effect=lambda root,ws,chat,tid:self.service.get(root,ws,chat,tid)):
            ready=self.send()
        with patch.object(self.service,'_imitate',side_effect=AssertionError('GET executed')):
            self.assertEqual(self.service.get(self.root,self.ws,self.chat,ready['turn_id'])['state'],'READY')
            cancelled=self.service.cancel(self.root,self.ws,self.chat,ready['turn_id'],{})
            self.assertEqual(cancelled['state'],'CANCELLED'); self.assertEqual(self.send()['state'],'CANCELLED')
        self.assertEqual(len(self.raw()),1)

    def test_late_result_after_cancel_is_not_success(self):
        entered=threading.Event(); release=threading.Event()
        def delayed():
            entered.set(); self.assertTrue(release.wait(8)); return 'TEST: сообщение принято.'
        with patch.object(self.service,'_imitate',side_effect=delayed), concurrent.futures.ThreadPoolExecutor() as pool:
            future=pool.submit(self.send)
            try:
                self.assertTrue(entered.wait(8))
                tid=self.ids()['turn_id']
                self.assertEqual(self.service.get(self.root,self.ws,self.chat,tid)['state'],'ATTEMPTING')
                self.assertEqual(self.service.cancel(self.root,self.ws,self.chat,tid,{})['state'],'UNKNOWN')
            finally: release.set()
            self.assertEqual(future.result(timeout=12)['state'],'UNKNOWN')
        self.assertEqual(len(self.raw()),1)
        self.assertEqual(self.send()['state'],'UNKNOWN')

    def test_result_fsync_lost_ack_recovers_without_second_execution(self):
        original=rs._clear_pending
        def fail_clear(path):
            intent=json.loads(path.read_bytes())
            if intent['record']['event']=='turn_result': raise OSError('lost result acknowledgment')
            return original(path)
        with patch.object(self.service,'_imitate',wraps=self.service._imitate) as imitate:
            with patch.object(rs,'_clear_pending',side_effect=fail_clear):
                with self.assertRaises(UltraChatError): self.send()
            self.assertEqual(self.send()['state'],'SUCCEEDED'); self.assertEqual(imitate.call_count,1)
        self.assertEqual(len(self.raw()),2)

    def test_adapter_failure_is_failed_and_does_not_replay(self):
        with patch.object(self.service,'_imitate',side_effect=RuntimeError('synthetic')) as imitate:
            self.assertEqual(self.send()['state'],'FAILED'); self.assertEqual(self.send()['state'],'FAILED')
            self.assertEqual(imitate.call_count,1)
        self.assertEqual(len(self.raw()),1)

    def test_started_without_result_is_unknown_after_reopen(self):
        original=self.service._event
        def stopped(root,turn,event,payload):
            if event=='turn_started': original(root,turn,event,payload); raise OSError('stopped before call')
            return original(root,turn,event,payload)
        with patch.object(self.service,'_event',side_effect=stopped), patch.object(self.service,'_imitate') as imitate:
            with self.assertRaises(UltraChatError): self.send()
            imitate.assert_not_called()
        with patch.object(self.service,'_imitate',side_effect=AssertionError('unknown replay')):
            self.assertEqual(self.send()['state'],'UNKNOWN')
        self.assertEqual(len(self.raw()),1)

    def test_two_service_writers_share_one_attempt(self):
        from web_alarm.turn_service import TurnService
        other=TurnService(test_roots=[self.root])
        with concurrent.futures.ThreadPoolExecutor() as pool:
            futures=[pool.submit(s.submit,self.root,self.ws,self.chat,self.body) for s in [self.service,other]]
            results=[f.result(timeout=20) for f in futures]
        self.assertTrue(all(r['state'] in {'SUCCEEDED','ATTEMPTING','UNKNOWN'} for r in results))
        self.assertEqual(len(self.raw()),2)
        events=rs.load_stream_records(self.root,self.ids()['run_id'],'SERVER')
        self.assertEqual([r['event'] for r in events],['turn_started','turn_result'])

    def test_corrupt_raw_or_event_is_refused_without_mutation(self):
        result=self.send()
        path=self.root/'.ultra/chats'/self.chat/'messages'/(result['assistant_message_id']+'.json')
        data=json.loads(path.read_bytes()); data['original_text']='tampered'; path.write_text(json.dumps(data),encoding='utf-8')
        before=self.snapshot()
        with self.assertRaises(UltraChatError): self.service.get(self.root,self.ws,self.chat,result['turn_id'])
        self.assertEqual(self.snapshot(),before)
        path=rs.run_component_path(self.root,result['run_id'],'server.jsonl'); path.write_bytes(path.read_bytes().replace(b'turn_result',b'TURN_result'))
        before=self.snapshot()
        with self.assertRaises(UltraChatError): self.send()
        self.assertEqual(self.snapshot(),before)

    def test_foreign_chat_and_workspace_identity_refused(self):
        before=self.snapshot()
        for ws,chat in [('ws_'+'f'*32,self.chat),(self.ws,'chat_'+'f'*32)]:
            with self.subTest(ws=ws,chat=chat),self.assertRaises(UltraChatError): self.service.submit(self.root,ws,chat,self.body)
        self.assertEqual(before,self.snapshot())

    def test_invalid_unicode_is_rejected_before_storage(self):
        before=self.snapshot()
        with self.assertRaises(UltraChatError) as error: self.send({**self.body,'text':'\ud800'})
        self.assertEqual(error.exception.status,400);self.assertEqual(before,self.snapshot())

    def test_damaged_ready_raw_prevents_execution(self):
        with patch.object(self.service,'_execute',side_effect=lambda root,ws,chat,tid:self.service.get(root,ws,chat,tid)):
            ready=self.send()
        path=self.root/'.ultra/chats'/self.chat/'messages'/(ready['user_message_id']+'.json')
        data=json.loads(path.read_bytes());data['original_text']='changed';path.write_text(json.dumps(data),encoding='utf-8')
        before=self.snapshot()
        with patch.object(self.service,'_imitate') as imitate, self.assertRaises(UltraChatError): self.send()
        imitate.assert_not_called();self.assertEqual(before,self.snapshot())

    @unittest.skipUnless(os.name=='nt','Windows junction')
    def test_turn_audit_junction_refused_without_external_bytes(self):
        import _winapi
        outside=Path(self.temp.name)/'outside';outside.mkdir();(outside/'marker').write_bytes(b'unchanged')
        link=self.root/'.ultra/audit';_winapi.CreateJunction(str(outside),str(link))
        try:
            with self.assertRaises(UltraChatError): self.send()
            self.assertEqual(list(outside.iterdir()),[outside/'marker']);self.assertEqual((outside/'marker').read_bytes(),b'unchanged')
        finally: os.rmdir(link)

    def test_two_processes_one_turn(self):
        code="from web_alarm.turn_service import TurnService;import sys,json;print(json.dumps(TurnService(test_roots=[sys.argv[1]]).submit(sys.argv[1],sys.argv[2],sys.argv[3],json.loads(sys.argv[4]))))"
        children=[subprocess.Popen([sys.executable,'-B','-c',code,str(self.root),self.ws,self.chat,json.dumps(self.body)],stdout=subprocess.PIPE,stderr=subprocess.PIPE) for _ in range(2)]
        try:
            for child in children:
                out,err=child.communicate(timeout=25);self.assertEqual(child.returncode,0,err)
                self.assertIn(json.loads(out)['state'],['UNKNOWN','SUCCEEDED'])
        finally:
            for child in children:
                if child.poll() is None: child.kill()
                child.communicate(timeout=5)
        self.assertEqual(len(self.raw()),2)
        self.assertEqual([r['event'] for r in rs.load_stream_records(self.root,self.ids()['run_id'],'SERVER')],['turn_started','turn_result'])

    def test_preexisting_raw_is_preserved_byte_for_byte(self):
        old=cs.commit_raw_message(self.root,self.chat,'msg_'+'f'*32,'user','История до Stage 3',expected_workspace_id=self.ws)
        path=Path(old['path']);before=path.read_bytes()
        self.send();self.assertEqual(path.read_bytes(),before)

    def test_stale_ready_projection_cannot_execute_a_started_turn_again(self):
        result=self.send()
        summary=rs.load_run_summary(self.root,result['run_id']);turn=summary['turn'];turn['state']='READY'
        rs.update_run_summary_index(self.root,result['run_id'],{'turn':turn,'run_status':'RUNNING'})
        before=self.snapshot()
        with patch.object(self.service,'_imitate',return_value='TEST: сообщение принято.') as imitate:
            with self.assertRaises(UltraChatError): self.send()
            imitate.assert_not_called()
        self.assertEqual(before,self.snapshot())

    def test_process_exit_recovery_and_raw_identity(self):
        code=r'''
import os,sys,json
from pathlib import Path
from web_alarm.turn_service import TurnService
s=TurnService(test_roots=[sys.argv[1]]); phase=sys.argv[5]
original=s._commit
def commit(root,turn,role,text):
    if phase=='before_user' and role=='user': os._exit(71)
    original(root,turn,role,text)
    if phase=='after_user' and role=='user': os._exit(72)
    if phase=='after_assistant' and role=='assistant': os._exit(73)
s._commit=commit
if phase=='after_start': s._imitate=lambda:os._exit(74)
s.submit(sys.argv[1],sys.argv[2],sys.argv[3],json.loads(sys.argv[4]))
'''
        for phase,exit_code in [('before_user',71),('after_user',72),('after_assistant',73),('after_start',74)]:
            with self.subTest(phase=phase):
                self.body['idempotency_key']='process_'+phase+'0'*16
                r=subprocess.run([sys.executable,'-B','-c',code,str(self.root),self.ws,self.chat,json.dumps(self.body),phase],capture_output=True,timeout=25)
                self.assertEqual(r.returncode,exit_code,r.stderr)
                result=self.send(); self.assertEqual(result['state'],'UNKNOWN' if phase=='after_start' else 'SUCCEEDED')
                self.assertEqual(self.send(),result)


if __name__=='__main__': unittest.main()
