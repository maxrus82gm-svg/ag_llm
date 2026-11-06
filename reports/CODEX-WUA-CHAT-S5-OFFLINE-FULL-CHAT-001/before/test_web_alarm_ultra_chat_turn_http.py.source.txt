"""Real loopback HTTP gate for TEST Turns; all roots and API storage are disposable."""
import concurrent.futures
import http.client
import json
import threading
from unittest.mock import patch

import context_storage as cs
import run_store as rs
from test_web_alarm_ultra_chat_storage import Base, READ
from web_alarm import server as module


class TurnHttpTests(Base):
    def setUp(self):
        super().setUp()
        self.server=self.start(test_turn_roots=[self.base/'project'])
        self.root,self.ws,self.chat=self.project(self.server,'project')
        self.path=f'/ultra/chat/workspaces/{self.ws}/chats/{self.chat}/turns'
        self.body=dict(idempotency_key='http_key_00000000001',text='HTTP тест',model_ref='local-test:v1',context_ref='empty:v1',config_ref='test-only:v1')

    def send(self,**kw):
        status,_,raw=self.server.post(self.path,self.body,**kw)
        return status,json.loads(raw)

    def snapshot(self):
        return {p.relative_to(self.root).as_posix():p.read_bytes() for p in self.root.rglob('*') if p.is_file()}

    def test_send_read_tokens_history_and_restart(self):
        code,result=self.send(); self.assertEqual(code,200,result);self.assertEqual(result['state'],'SUCCEEDED')
        before=self.snapshot()
        code,read=self.server.read(self.path+'/'+result['turn_id']);self.assertEqual((code,read),(200,result))
        code,history=self.server.read(self.path.replace('/turns','/messages'))
        self.assertEqual(code,200);self.assertEqual([m['text'] for m in history['messages']],['HTTP тест','TEST: сообщение принято.'])
        self.server.stop()
        # Avoid duplicate cleanup of an already stopped server by making stop idempotent for the old wrapper.
        self.server.stop=lambda:None
        self.server=self.start(test_turn_roots=[self.root])
        self.assertEqual(self.send(),(200,result));self.assertEqual(before,self.snapshot())

    def test_two_clients_one_key_one_attempt(self):
        with concurrent.futures.ThreadPoolExecutor() as pool:
            results=list(pool.map(lambda _:self.send(),range(2)))
        self.assertTrue(all(code==200 for code,_ in results),results)
        turn_id=results[0][1]['turn_id']
        records=rs.load_stream_records(self.root,turn_id,'SERVER')
        self.assertEqual([r['event'] for r in records],['turn_started','turn_result'])
        self.assertEqual(len(list((self.root/'.ultra/chats'/self.chat/'messages').glob('*.json'))),2)

    def test_lost_physical_http_reply_replays_saved_turn(self):
        original=module._JsonHandler._send_json
        def drop(handler,status,payload):
            if handler.command=='POST' and isinstance(payload,dict) and 'turn_id' in payload:
                handler.close_connection=True
                return
            return original(handler,status,payload)
        with patch.object(module._JsonHandler,'_send_json',drop):
            with self.assertRaises((http.client.RemoteDisconnected,ConnectionError)): self.send()
        code,result=self.send();self.assertEqual(code,200);self.assertEqual(result['state'],'SUCCEEDED')
        self.assertEqual(len(rs.list_run_records(self.root,result['run_id'])),2)

    def test_auth_origin_size_schema_and_unknown_references_do_not_write(self):
        before=self.snapshot()
        cases=[dict(token='bad'),dict(headers={'Origin':'https://foreign.invalid'}),dict(omit=['Origin']),
               dict(extra=[('Origin',self.server.origin)]),dict(token=self.server.capability('/ui/ultra-chat/capability','ultra_chat')['token']),
               dict(raw_body=b'x'*5000),dict(raw_body=b'{'),dict(raw_body=b'[]')]
        for kw in cases:
            with self.subTest(kw=str(kw)[:60]): self.assertIn(self.send(**kw)[0],[400,403,413])
        for key in ['model_ref','context_ref','config_ref']:
            body={**self.body,key:'real-or-unknown'}
            code,_,_=self.server.post(self.path,body);self.assertEqual(code,409)
        self.assertEqual(before,self.snapshot())

    def test_foreign_chat_registered_root_not_allowlisted_and_methods(self):
        before=self.snapshot()
        for path,expected in [(self.path.replace(self.chat,'chat_'+'e'*32),404),
                              (self.path.replace(self.ws,'ws_'+'e'*32),404)]:
            code,_,_=self.server.post(path,self.body);self.assertEqual(code,expected)
        other,ws,chat=self.project(self.server,'other')
        other_before={p.relative_to(other).as_posix():p.read_bytes() for p in other.rglob('*') if p.is_file()}
        code,_,_=self.server.post(f'/ultra/chat/workspaces/{ws}/chats/{chat}/turns',self.body);self.assertEqual(code,403)
        code,_,_=self.server.request('PUT',self.path,body=b'{}');self.assertEqual(code,405)
        code,_,_=self.server.post(self.path+'?root=x',self.body);self.assertEqual(code,400)
        self.assertEqual(before,self.snapshot());self.assertEqual(other_before,{p.relative_to(other).as_posix():p.read_bytes() for p in other.rglob('*') if p.is_file()})

    def test_standard_has_no_send_and_read_capability_cannot_cancel(self):
        standard=self.start(name='standard')
        standard.api.registry.register('Same synthetic',self.root)
        ws=standard.api.registry.list()[0].workspace_id
        code,_,_=standard.post(self.path.replace(self.ws,ws),self.body);self.assertEqual(code,403)
        _,result=self.send()
        read_token=self.server.capability('/ui/ultra-chat/capability','ultra_chat')['token']
        code,_,_=self.server.post(self.path+'/'+result['turn_id']+'/cancel',{},token=read_token);self.assertEqual(code,403)

    def test_turn_read_requires_read_authority_and_valid_scope(self):
        _,result=self.send();before=self.snapshot()
        path=self.path+'/'+result['turn_id']
        for headers in [{},{READ:'bad'},{READ:self.server.capability()['token']}]:
            with self.subTest(headers=str(headers)[:30]):
                code,_,_=self.server.request('GET',path,headers);self.assertEqual(code,403)
        code,_=self.server.read(path+'?root=elsewhere');self.assertEqual(code,400)
        code,_=self.server.read(path.replace(result['turn_id'],'turn_invalid'));self.assertEqual(code,400)
        self.assertEqual(before,self.snapshot())

    def test_http_cancel_rejects_late_result(self):
        service=self.server.server.web_alarm_ultra_chat.turns
        entered=threading.Event();release=threading.Event()
        def imitate():
            entered.set();self.assertTrue(release.wait(8));return 'TEST: сообщение принято.'
        with patch.object(service,'_imitate',side_effect=imitate), concurrent.futures.ThreadPoolExecutor() as pool:
            future=pool.submit(self.send)
            try:
                self.assertTrue(entered.wait(8))
                code,current=self.server.read(self.path+'/by-key/'+self.body['idempotency_key']);self.assertEqual(code,200)
                code,_,raw=self.server.post(self.path+'/'+current['turn_id']+'/cancel',{})
                self.assertEqual(code,200,raw);self.assertEqual(json.loads(raw)['state'],'UNKNOWN')
            finally:release.set()
            self.assertEqual(future.result(timeout=15)[1]['state'],'UNKNOWN')


