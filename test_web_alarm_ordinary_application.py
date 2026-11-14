"""H35: actual STANDARD application entrypoint, isolated H33 HTTP boundary only."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
import threading
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import httpx
import context_storage as core
import gigachat_transport as legacy
import ordinary_gigachat_transport as transport
import ordinary_chat_service as chat
import run_store as runs
import ultra_budget_policy as policy
from ultra_budget_ledger import BudgetLedger
from web_alarm.server import WebAlarmApi, create_server
from web_alarm.ordinary_provider import (OrdinaryApplicationChatService, OrdinaryProviderFactory,
                                       MODEL_ID, RELEASE_HOLDS)
from web_alarm.ultra_chat import OrdinaryCoreChatService
import test_web_alarm_ultra_chat_s5 as s5


class ApplicationTests(s5.Fixture):
    serve = s5.HttpAndTkTests.serve
    http = s5.HttpAndTkTests.http
    tokens = s5.HttpAndTkTests.tokens

    def setUp(self):
        super().setUp()
        self.api = WebAlarmApi(self.root / 'registry')
        self.service = OrdinaryCoreChatService(self.api.registry, self.root)
        self.fixture = transport.OfflineHTTPFixture(body=json.dumps({
            'choices':[{'message':{'role':'assistant','content':'H35 synthetic answer'}}],
            'usage':{'prompt_tokens':7,'completion_tokens':5,'total_tokens':12}}).encode())
        self.factory = OrdinaryProviderFactory.offline_application(self.api.registry, self.root, self.fixture)
        oauth = patch.object(legacy, 'get_access_token', side_effect=AssertionError('REAL OAuth forbidden'))
        self.oauth = oauth.start(); self.addCleanup(oauth.stop)
        self.addCleanup(self.oauth.assert_not_called)

    def application(self, **kwargs):
        _,workspace=self.service.create_workspace({'title':'H35 isolated normal application'})
        ws,cid=workspace['wa_workspace_id'],'chat_'+uuid4().hex
        server = self.serve(ordinary_factory=self.factory, **kwargs)
        cap,read,write = self.tokens(server)
        self.assertEqual(self.http(server,'POST',f'/ultra/chat/workspaces/{ws}/chats',
            {'chat_id':cid,'initialize_workspace':True},write)[0],201)
        base = f'/ultra/chat/workspaces/{ws}/chats/{cid}'
        root = Path(self.api.registry.get(ws).workspace_root)
        wid = core.read_workspace_identity_bounded(root)['workspace_id']
        return ws,cid,server,cap,read,write,base,root,wid

    def test_standard_exact_wire_terminal_history_usage_model_and_reopen(self):
        ws,cid,server,cap,read,write,base,root,wid = self.application()
        self.assertIsNone(server.web_alarm_offline_chat)
        self.assertIs(type(server.web_alarm_ultra_chat), OrdinaryApplicationChatService)
        self.assertNotIn('data-stage5-offline="true"', self.http(server,'GET','/')[1])
        self.assertEqual(self.http(server,'GET','/status')[0],200)
        self.assertEqual(cap['mode'],'ORDINARY'); self.assertFalse(cap['real_available'])
        self.assertEqual(cap['release_holds'],list(RELEASE_HOLDS))
        self.assertEqual(self.http(server,'POST','/ultra/chat/workspaces',{'title':'forbidden'},write)[0],405)
        self.assertEqual(self.http(server,'POST',base+'/model',{'model_ref':MODEL_ID},write)[0],200)
        self.assertTrue(self.http(server,'GET',base+'/model',headers=read)[1]['persisted'])
        body = self.body('Hello 🌍')
        seen=[]; original=httpx.MockTransport.handle_async_request
        async def observe(mock, request):
            ledger=BudgetLedger(root,wid); saved=ledger.recover().attempts[-1]
            self.assertEqual(saved.state,policy.SENT)
            _,env=ledger.reservation(saved.attempt_id)
            self.assertEqual(env['wire_utf8'].encode(),request.content)
            self.assertEqual(json.loads(request.content)['model'],'GigaChat-2-Pro')
            seen.append(hashlib.sha256(request.content).hexdigest())
            return await original(mock,request)
        with patch.object(httpx.MockTransport,'handle_async_request',observe):
            status,result=self.http(server,'POST',base+'/turns',body,write)
        self.assertEqual((status,result['state'],result['mode']),(200,'SUCCEEDED','ORDINARY'))
        self.assertEqual(result['execution_mode'],'OFFLINE_APPLICATION')
        self.assertEqual(self.fixture.token_calls,1); self.assertEqual(len(seen),1)
        page=self.http(server,'GET',base+'/messages?limit=50',headers=read)[1]
        self.assertEqual([m['text'] for m in page['messages']],['Hello 🌍','H35 synthetic answer'])
        self.assertEqual(page['usage_summary']['known']['total_tokens'],12)
        self.assertTrue(page['usage_summary']['synthetic'])
        self.assertEqual(BudgetLedger(root,wid).recover().attempts[-1].state,policy.KNOWN_TERMINAL)
        # New server/service instance: durable Turn, model, RAW and usage, no resend.
        second=self.serve(ordinary_factory=self.factory)
        _,r2,w2=self.tokens(second)
        self.assertEqual(self.http(second,'POST',base+'/turns',body,w2)[1],result)
        self.assertEqual(self.http(second,'GET',base+'/model',headers=r2)[1]['model_ref'],MODEL_ID)
        self.assertEqual(self.http(second,'GET',base+'/turns/latest',headers=r2)[1]['turn'],result)
        self.assertEqual(self.fixture.token_calls,1)
        if os.environ.get('H35_TRACE'):
            Path(os.environ['H35_TRACE']).write_text(json.dumps(dict(entrypoint='web_alarm.server.create_server',
                normal_dom=True,mode=cap['mode'],physical_synthetic_posts=len(seen),wire_sha256=seen,
                terminal='KNOWN_TERMINAL',history_messages=2,usage_total=12,reopen_no_resend=True)),encoding='utf-8')

    def test_default_standard_hold_before_turn_raw_token_or_network(self):
        ws,cid = self.create_chat('HOLD')
        server=self.serve();cap,read,write=self.tokens(server)
        base=f'/ultra/chat/workspaces/{ws}/chats/{cid}'
        root=Path(self.api.registry.get(ws).workspace_root)
        before={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
        for extra in ({},{'real':True},{'scope':'GIGACHAT_API_PERS'}, {'authority':{}}, {'endpoint':legacy.CHAT_URL}):
            with self.subTest(extra=extra):
                status,result=self.http(server,'POST',base+'/turns',{**self.body('hold'),**extra},write)
                self.assertIn(status,(400,403))
        after={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
        self.assertEqual(before,after); self.assertEqual(self.fixture.token_calls,0)
        self.assertFalse(cap['available']); self.assertEqual(cap['real_factory'],'BLOCKED')
        self.assertIsNone(cap['context_tokens']);self.assertIsNone(cap['output_tokens'])
        self.assertEqual(self.http(server,'GET',base+'/messages',headers=read)[0],200)
        self.assertFalse(self.http(server,'GET',base+'/messages',headers=read)[1]['usage_summary']['available'])

    def test_model_settings_and_workspace_isolation(self):
        ws,cid,server,_,read,write,base,root,wid=self.application()
        ws2,cid2=self.create_chat('neighbour')
        base2=f'/ultra/chat/workspaces/{ws2}/chats/{cid2}'
        self.assertEqual(self.http(server,'POST',base+'/model',{'model_ref':'gigachat_ultra'},write)[0],400)
        for bad in ('gigachat_ultra','local-test:v1','GigaChat-2-Pro'):
            self.assertEqual(self.http(server,'POST',base+'/turns',self.body('no',bad),write)[0],400)
        self.assertEqual(self.fixture.token_calls,0)
        settings={'compression_threshold_tokens':3000,'answer_tokens':20000}
        self.assertEqual(self.http(server,'POST',base+'/settings',settings,write)[0],200)
        saved=self.http(server,'GET',base+'/settings',headers=read)[1]
        self.assertFalse(saved['applied_to_provider']);self.assertEqual(saved['settings'],settings)
        self.assertNotEqual(self.http(server,'GET',base2+'/settings',headers=read)[1]['settings'],settings)
        self.assertEqual(self.http(server,'POST',base+'/turns',self.body('one'),write)[0],200)
        self.assertEqual(self.http(server,'GET',base2+'/messages',headers=read)[1]['messages'],[])
        self.assertEqual(len(BudgetLedger(root,wid).recover().attempts),1)

    def test_timeout_unknown_reopen_retains_liability_without_resend(self):
        _,_,server,_,read,write,base,root,wid=self.application()
        self.fixture.error='timeout';body=self.body('timeout')
        result=self.http(server,'POST',base+'/turns',body,write)[1]
        self.assertEqual(result['state'],'UNKNOWN')
        before=BudgetLedger(root,wid).recover().attempts[-1]
        second=self.serve(ordinary_factory=self.factory);_,r2,w2=self.tokens(second)
        self.assertEqual(self.http(second,'GET',base+'/turns/latest',headers=r2)[1]['turn']['state'],'UNKNOWN')
        self.assertEqual(self.http(second,'POST',base+'/turns',body,w2)[1]['state'],'UNKNOWN')
        self.assertEqual(self.fixture.token_calls,1);self.assertEqual(len(self.fixture.requests),1)
        self.assertEqual(BudgetLedger(root,wid).recover().attempts[-1],before)
        usage=self.http(second,'GET',base+'/messages',headers=r2)[1]['usage_summary']
        self.assertEqual(usage['missing']['total_tokens'],1)

    def test_http_auth_rate_server_and_bad_json_are_not_retried(self):
        for status in (401,403,429,500,200):
            with self.subTest(status=status):
                _,_,server,_,_,write,base,_,_=self.application()
                self.fixture.status=status;self.fixture.body=b'not json'
                old=len(self.fixture.requests);body=self.body('failure')
                reply=self.http(server,'POST',base+'/turns',body,write)[1]
                self.assertIn(reply['state'],('FAILED','UNKNOWN'))
                self.http(server,'POST',base+'/turns',body,write)
                self.assertEqual(len(self.fixture.requests),old+1)

    def test_synthetic_oauth_boundary_failure_is_not_real_and_not_retried(self):
        _,_,server,_,_,write,base,_,_=self.application()
        self.fixture.token_error=True;body=self.body('token boundary')
        result=self.http(server,'POST',base+'/turns',body,write)[1]
        self.assertIn(result['state'],('FAILED','UNKNOWN'))
        self.http(server,'POST',base+'/turns',body,write)
        self.assertEqual(self.fixture.token_calls,1);self.assertEqual(self.fixture.requests,[])

    def test_factory_scope_and_forged_real_authority_denied(self):
        for value in (True,{},object(),lambda:None):
            with self.assertRaises(ValueError):create_server(self.api,port=0,ordinary_factory=value)
        with self.assertRaises(ValueError):
            OrdinaryProviderFactory.offline_application(self.api.registry,Path.cwd(),self.fixture)
        for value in (None,{},True,object()):
            with self.assertRaises(chat.PreSendDenied):transport.GigaChatTransport(value)
        with self.assertRaises(chat.PreSendDenied):OrdinaryProviderFactory().require_real()
        self.assertEqual(self.fixture.token_calls,0)

    def test_application_cancel_during_http_keeps_unknown_and_no_retry(self):
        _,_,server,_,read,write,base,root,wid=self.application()
        entered,release=threading.Event(),threading.Event()
        original=httpx.MockTransport.handle_async_request
        async def hold(mock, request):
            entered.set()
            if not release.wait(6):raise TimeoutError('synthetic barrier')
            return await original(mock,request)
        body=self.body('cancel')
        with patch.object(httpx.MockTransport,'handle_async_request',hold), ThreadPoolExecutor() as pool:
            future=pool.submit(self.http,server,'POST',base+'/turns',body,write)
            try:
                self.assertTrue(entered.wait(5))
                turn=self.http(server,'GET',base+'/turns/latest',headers=read)[1]['turn']
                self.assertEqual(turn['state'],'ATTEMPTING')
                status,_=self.http(server,'POST',base+'/turns/'+turn['turn_id']+'/cancel',{},write)
                self.assertEqual(status,200)
            finally:release.set()
            result=future.result()[1]
        self.assertEqual(result['state'],'UNKNOWN')
        self.assertEqual(self.http(server,'POST',base+'/turns',body,write)[1]['state'],'UNKNOWN')
        self.assertEqual(self.fixture.token_calls,1)
        self.assertLessEqual(len(self.fixture.requests),1)
        self.assertNotEqual(BudgetLedger(root,wid).recover().attempts[-1].state,policy.KNOWN_TERMINAL)

    def test_application_terminal_failure_does_not_publish_or_resend(self):
        _,_,server,_,read,write,base,root,wid=self.application()
        body=self.body('terminal storage failure')
        with patch.object(BudgetLedger,'terminal',side_effect=OSError('synthetic disk')):
            self.assertEqual(self.http(server,'POST',base+'/turns',body,write)[0],503)
        page=self.http(server,'GET',base+'/messages',headers=read)[1]
        self.assertEqual([m['role'] for m in page['messages']],['user'])
        self.assertEqual(self.http(server,'POST',base+'/turns',body,write)[1]['state'],'UNKNOWN')
        self.assertEqual(len(self.fixture.requests),1)
        self.assertEqual(BudgetLedger(root,wid).recover().attempts[-1].state,policy.SENT)
