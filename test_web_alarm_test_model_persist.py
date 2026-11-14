"""Permanent TEST Ordinary service: durable model metadata, synthetic roots only."""
import hashlib
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from uuid import uuid4
from unittest.mock import patch

import context_storage as core
import gigachat_transport
import httpx
from web_alarm.server import WebAlarmApi
from web_alarm.ultra_chat import OrdinaryCoreChatService, UltraChatError
from web_alarm.ordinary_chat_test_adapter import _FixtureTransport
import test_web_alarm_ultra_chat_s5 as s5


class ModelPersistenceTests(s5.Fixture):
    serve = s5.HttpAndTkTests.serve
    http = s5.HttpAndTkTests.http
    tokens = s5.HttpAndTkTests.tokens

    def setUp(self):
        super().setUp()
        self.api=WebAlarmApi(self.root/'registry')
        self.service=OrdinaryCoreChatService(self.api.registry,self.root)
        self.server=self.serve(offline_chat=self.service)
        self.cap,self.read,self.write=self.tokens(self.server)
        self.default_model=self.cap['models'][0]['model_id']
        oauth=patch.object(gigachat_transport,'get_access_token',side_effect=AssertionError('REAL OAuth forbidden'))
        self.oauth=oauth.start();self.addCleanup(oauth.stop);self.addCleanup(self.oauth.assert_not_called)

    def model_path(self,ws,cid):
        return f'/ultra/chat/workspaces/{ws}/chats/{cid}/model'

    def test_http_model_choice_survives_service_recreation(self):
        ws,cid=self.create_chat('A');path=self.model_path(ws,cid)
        code,_=self.http(self.server,'POST',path,{'model_ref':'gigachat_3_lightning'},self.write)
        self.assertEqual(code,200)
        service=OrdinaryCoreChatService(self.api.registry,self.root)
        reopened=self.serve(offline_chat=service);_,read,_=self.tokens(reopened)
        self.assertEqual(self.http(reopened,'GET',path,headers=read)[1]['model_ref'],'gigachat_3_lightning')

    def test_two_chats_two_workspaces_and_new_base(self):
        ws,a=self.create_chat('Workspace A');b='chat_'+uuid4().hex
        self.service.create_chat(ws,{'chat_id':b})
        ws2,c=self.create_chat('Workspace B')
        for wid,cid,model in ((ws,a,'gigachat_3_lightning'),(ws,b,'gigachat_ultra'),(ws2,c,'gigachat_2_pro')):
            path=self.model_path(wid,cid)
            self.assertEqual(self.http(self.server,'POST',path,{'model_ref':model},self.write)[0],200)
        fresh=OrdinaryCoreChatService(self.api.registry,self.root)
        for wid,cid,model in ((ws,a,'gigachat_3_lightning'),(ws,b,'gigachat_ultra'),(ws2,c,'gigachat_2_pro')):
            self.assertEqual(fresh.test_chat_model(wid,cid)['model_ref'],model)
            root=Path(self.api.registry.get(wid).workspace_root)
            meta=core.read_ultra_json_bounded(root,('chats',cid,'metadata.json'),max_bytes=32768)
            self.assertEqual(meta['test_chat_model'],model)
        if os.environ.get('MODEL_PERSIST_TRACE'):
            Path(os.environ['MODEL_PERSIST_TRACE']).write_text(json.dumps(dict(
                mode='TEST_OFFLINE',storage='isolated temporary Chat metadata',real_oauth_calls=self.oauth.call_count,
                choices=[dict(workspace=wid,chat=cid,model=fresh.test_chat_model(wid,cid)['model_ref'])
                         for wid,cid in ((ws,a),(ws,b),(ws2,c))],
                storage_reopened=True,raw_untouched=True),indent=2),encoding='utf-8')
        # Wrong workspace+chat pairing cannot reach the other chat.
        self.assertEqual(self.http(self.server,'GET',self.model_path(ws2,a),headers=self.read)[0],404)
        with tempfile.TemporaryDirectory(prefix='model_new_base_') as folder:
            api=WebAlarmApi(Path(folder)/'registry');service=OrdinaryCoreChatService(api.registry,Path(folder))
            _,w=service.create_workspace({'title':'Workspace A'})
            service.create_chat(w['wa_workspace_id'],{'chat_id':a,'initialize_workspace':True})
            self.assertEqual(service.test_chat_model(w['wa_workspace_id'],a),{'model_ref':self.default_model,'persisted':False})

    def snapshot(self, ws):
        root=Path(self.api.registry.get(ws).workspace_root)
        return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}

    def test_default_get_is_read_only_and_unauthorized_or_unknown_writes_are_refused(self):
        ws,cid=self.create_chat('validation');path=self.model_path(ws,cid);before=self.snapshot(ws)
        self.assertTrue(self.cap['chat_model_preferences'])
        self.assertEqual(self.http(self.server,'GET',path,headers=self.read)[1],{'model_ref':self.default_model,'persisted':False})
        for body in ({},{'model_ref':'unknown'},{'model_ref':True},{'model_ref':'local-test:v1'},
                     {'model_ref':'gigachat_ultra','real':True}):
            with self.subTest(body=body):self.assertEqual(self.http(self.server,'POST',path,body,self.write)[0],400)
        self.assertEqual(self.http(self.server,'POST',path,{'model_ref':'gigachat_ultra'},self.read)[0],403)
        self.assertEqual(self.http(self.server,'GET',path,headers={})[0],403)
        self.assertEqual(self.http(self.server,'GET',path+'?root=other',headers=self.read)[0],400)
        self.assertEqual(self.snapshot(ws),before)

    def test_corrupt_or_removed_model_is_explicit_and_can_be_repaired(self):
        ws,cid=self.create_chat('corrupt');root=Path(self.api.registry.get(ws).workspace_root)
        path=self.model_path(ws,cid)
        metadata=root/'.ultra/chats'/cid/'metadata.json'
        original=json.loads(metadata.read_text(encoding='utf-8'))
        for value in ('removed-model',None,{'invalid':'model'}):
            with self.subTest(value=value):
                metadata.write_text(json.dumps({**original,'test_chat_model':value}),encoding='utf-8')
                before=self.snapshot(ws)
                status,result=self.http(self.server,'GET',path,headers=self.read)
                self.assertEqual(status,409);self.assertEqual(result['error']['code'],'test_chat_model_invalid')
                self.assertEqual(self.snapshot(ws),before)
                self.assertEqual(self.http(self.server,'POST',path,{'model_ref':'gigachat_ultra'},self.write)[0],200)
                self.assertEqual(self.http(self.server,'GET',path,headers=self.read)[1]['model_ref'],'gigachat_ultra')

    def test_save_failure_never_acknowledges_success_or_alters_history(self):
        ws,cid=self.create_chat('write failure');path=self.model_path(ws,cid);before=self.snapshot(ws)
        with patch.object(core,'_replace_verified',side_effect=OSError('synthetic storage failure')):
            self.assertGreaterEqual(self.http(self.server,'POST',path,{'model_ref':'gigachat_ultra'},self.write)[0],400)
        self.assertEqual(self.snapshot(ws),before)
        self.assertEqual(self.http(self.server,'GET',path,headers=self.read)[1]['model_ref'],self.default_model)

    def test_model_write_preserves_raw_usage_preferences_and_completed_turn(self):
        ws,cid=self.create_chat('preservation')
        settings={'compression_threshold_tokens':12345,'answer_tokens':678}
        self.service.chat_preferences(ws,cid,settings)
        result=self.service.submit_turn(ws,cid,self.body('test send','gigachat_3_lightning'))
        before=self.snapshot(ws);page=self.service.messages(ws,cid,None,50)
        self.http(self.server,'POST',self.model_path(ws,cid),{'model_ref':'gigachat_ultra'},self.write)
        after=self.snapshot(ws)
        self.assertEqual([p for p in before if before[p]!=after[p]],[f'.ultra/chats/{cid}/metadata.json'])
        self.assertEqual(self.service.messages(ws,cid,None,50),page)
        self.assertEqual(self.service.chat_preferences(ws,cid)['settings'],settings)
        self.assertEqual(result['references']['model_ref'],'gigachat_3_lightning')

    def test_standard_still_rejects_test_model_method_and_ultra_choice(self):
        ws,cid=self.create_chat('standard boundary')
        standard=self.serve();cap,read,write=self.tokens(standard)
        self.assertFalse(cap['real_available']);self.assertFalse(cap['available'])
        self.assertNotIn('chat_model_preferences',cap)
        self.assertEqual(self.http(standard,'POST',self.model_path(ws,cid),{'model_ref':'gigachat_ultra'},write)[0],400)
        self.assertEqual(self.http(standard,'POST',self.model_path(ws,cid),{'model_ref':'gigachat_2_pro'},write)[0],200)
        with self.assertRaises(UltraChatError) as caught:
            standard.web_alarm_ultra_chat.test_chat_model(ws,cid,{'model_ref':'gigachat_ultra'})
        self.assertEqual(caught.exception.status,403)
        self.assertEqual(self.service.test_chat_model(ws,cid)['persisted'],False)

    def test_http_send_and_unknown_replay_keep_original_model_binding(self):
        ws,cid=self.create_chat('pending binding');path=self.model_path(ws,cid)
        self.http(self.server,'POST',path,{'model_ref':'gigachat_3_lightning'},self.write)
        selected=self.http(self.server,'GET',path,headers=self.read)[1]['model_ref']
        body=self.body('original pending text',selected);sent=[]
        async def fail_after_start(transport,payload,**kwargs):
            sent.append(payload);raise TimeoutError('synthetic unknown')
        with patch.object(_FixtureTransport,'send',fail_after_start):
            status,turn=self.http(self.server,'POST',path.removesuffix('/model')+'/turns',body,self.write)
            self.assertEqual((status,turn['state']),(200,'UNKNOWN'))
            self.http(self.server,'POST',path,{'model_ref':'gigachat_ultra'},self.write)
            again=self.http(self.server,'POST',path.removesuffix('/model')+'/turns',body,self.write)[1]
        self.assertEqual(again['references']['model_ref'],'gigachat_3_lightning')
        self.assertEqual(again['state'],'UNKNOWN');self.assertEqual(len(sent),1)
        self.assertEqual(self.http(self.server,'GET',path,headers=self.read)[1]['model_ref'],'gigachat_ultra')


class PermanentProfileTests(unittest.TestCase):
    def test_existing_test_profile_python_entrypoint_persists_models_and_cleans_up(self):
        root=Path(__file__).resolve().parent
        env={k:os.environ[k] for k in os.environ if not k.upper().startswith('GIGACHAT_')}
        cmd=[sys.executable,'-B','-X','utf8',str(root/'web_alarm/ordinary_test_fixture.py'),'--no-browser']
        process=subprocess.Popen(cmd,cwd=root,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        lines,output=queue.Queue(),[]
        def consume():
            for raw in iter(process.stdout.readline,b''):
                line=raw.decode('utf-8',errors='replace');output.append(line);lines.put(line)
        reader=threading.Thread(target=consume,daemon=True);reader.start()
        ready=None;fixture_root=None
        try:
            deadline=time.monotonic()+20
            while time.monotonic()<deadline:
                try:line=lines.get(timeout=.2)
                except queue.Empty:
                    self.assertIsNone(process.poll(),''.join(output));continue
                if line.startswith('ORDINARY_TEST_READY '):ready=json.loads(line.split(' ',1)[1]);break
            self.assertIsNotNone(ready,''.join(output))
            fixture_root=Path(ready['root']).resolve()
            self.assertEqual(fixture_root.parent,Path(tempfile.gettempdir()).resolve())
            self.assertTrue(fixture_root.name.startswith('ordinary_core_TEST_'))
            self.assertFalse(ready['real_available']);self.assertFalse(ready['browser_requested'])
            origin=ready['url'].rstrip('/')
            self.assertTrue(origin.startswith('http://127.0.0.1:'))
            with httpx.Client(base_url=origin,trust_env=False,timeout=8) as client:
                def call(method,path,body=None,headers=None):
                    reply=client.request(method,path,json=body,headers=headers)
                    return reply.status_code,reply.json()
                _,cap=call('GET','/ui/ultra-chat/capability')
                self.assertTrue(cap['turn_test']['chat_model_preferences'])
                read={cap['ultra_chat']['header']:cap['ultra_chat']['token']}
                _,writecap=call('GET','/ui/ultra-chat/write-capability');writecap=writecap['ultra_chat_write']
                write={writecap['header']:writecap['token'],'Origin':origin}
                code,ws=call('POST','/ultra/chat/workspaces',{'title':'profile persistence'},write)
                self.assertEqual(code,201);base=f"/ultra/chat/workspaces/{ws['wa_workspace_id']}/chats"
                choices=[]
                for i,model in enumerate(('gigachat_3_lightning','gigachat_ultra')):
                    cid='chat_'+uuid4().hex;body={'chat_id':cid}
                    if i==0:body['initialize_workspace']=True
                    self.assertEqual(call('POST',base,body,write)[0],201)
                    path=base+'/'+cid
                    self.assertEqual(call('POST',path+'/model',{'model_ref':model},write)[0],200)
                    choices.append((path,model))
                for path,model in choices+choices[:1]:
                    self.assertEqual(call('GET',path+'/model',headers=read)[1]['model_ref'],model)
                path,model=choices[0]
                status,turn=call('POST',path+'/turns',self_body:=dict(idempotency_key=uuid4().hex,
                    model_ref=model,text='profile synthetic text'),write)
                self.assertEqual((status,turn['state']),(200,'SUCCEEDED'))
                self.assertEqual(turn['references']['model_ref'],model)
                self.assertEqual(call('POST',path+'/turns',self_body,write)[1],turn)
                self.assertEqual(len(call('GET',path+'/messages',headers=read)[1]['messages']),2)
            guard=fixture_root/'guard.jsonl'
            self.assertFalse(guard.exists() and guard.read_text(encoding='utf-8').strip())
        finally:
            if process.poll() is None:
                process.stdin.write(b'\n');process.stdin.flush();process.stdin.close()
            try:code=process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                process.kill();process.wait(timeout=5);raise
            reader.join(5)
        self.assertEqual(code,0,''.join(output));self.assertFalse(fixture_root.exists())
        self.assertIn('ORDINARY_TEST_CLEANED',''.join(output))
        if os.environ.get('MODEL_PERSIST_TRACE'):
            trace=Path(os.environ['MODEL_PERSIST_TRACE'])
            trace.with_name(trace.stem+'.profile.json').write_text(json.dumps(dict(
                entrypoint='web_alarm/ordinary_test_fixture.py --no-browser',
                mode='TEST_OFFLINE',models=['gigachat_3_lightning','gigachat_ultra'],
                fake_turn='SUCCEEDED',repeat_same_turn=True,guard_denials=0,cleanup=True,
                physical_cmd=False,physical_browser=False),indent=2),encoding='utf-8')
