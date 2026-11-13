"""H33 adversarial HTTP fixtures over the accepted H32 durable chain."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import threading
import unittest
from unittest.mock import patch
from uuid import uuid4

import httpx
import context_storage as core
import gigachat_transport as legacy
import ordinary_chat_service as chat
import ordinary_gigachat_transport as transport
import run_store as runs
import ultra_budget_policy as policy
from ultra_budget_ledger import BudgetLedger, LedgerDenied
from web_alarm import ordinary_chat_bridge as bridge
from web_alarm.turn_service import TurnService, _TurnAdmission
from web_alarm.ultra_chat import OrdinaryCoreChatService, UltraChatError
from web_alarm.server import WebAlarmApi, create_server
import test_web_alarm_ultra_chat_s5 as s5
import test_web_alarm_ordinary_core_bridge as old_bridge_tests
from test_web_alarm_ordinary_core_bridge import reply


USAGE = {'prompt_tokens':7, 'completion_tokens':5, 'total_tokens':12,
         'completion_tokens_details':{'reasoning_tokens':3}}


class HTTPTransportTests(s5.Fixture):
    def setUp(self):
        super().setUp()
        self.fixture = transport.OfflineHTTPFixture(body=json.dumps(reply(USAGE)).encode())
        self.service = OrdinaryCoreChatService(self.registry, self.root, http_fixture=self.fixture)
        # Real OAuth is a tripwire, independently of the process credential guard.
        oauth = patch.object(legacy, 'get_access_token', side_effect=AssertionError('REAL OAuth forbidden'))
        self.oauth = oauth.start(); self.addCleanup(oauth.stop)
        self.addCleanup(lambda: self.oauth.assert_not_called())

    def project(self):
        ws, cid = self.create_chat('H33 synthetic')
        root = Path(self.registry.get(ws).workspace_root)
        wid = core.read_workspace_identity_bounded(root)['workspace_id']
        return ws, cid, root, wid, BudgetLedger(root, wid)

    def test_exact_http_bytes_headers_sent_binding_usage_and_reopen(self):
        ws,cid,root,wid,ledger = self.project()
        observed=[]; original=httpx.MockTransport.handle_async_request
        async def capture(mock, request):
            wire=request.content
            saved=ledger.recover().attempts[-1]
            self.assertEqual(saved.state, policy.SENT)
            receipt,env=ledger.reservation(saved.attempt_id)
            turn=runs.load_run_summary(root,env['binding']['turn_id'],cid)['turn']
            self.assertEqual(wire,env['wire_utf8'].encode())
            self.assertEqual(hashlib.sha256(wire).hexdigest(),turn['ordinary_admission']['wire_sha256'])
            self.assertEqual(turn['ordinary_admission']['endpoint'],legacy.CHAT_URL)
            self.assertEqual(request.headers['authorization'],'Bearer H33-SYNTHETIC-NON-CREDENTIAL')
            self.assertEqual(request.headers['content-type'],'application/json; charset=utf-8')
            self.assertEqual(json.loads(wire)['model'],'GigaChat-2-Pro')
            self.assertEqual(request.extensions['timeout'],dict(connect=8.,read=8.,write=8.,pool=8.))
            observed.append(wire)
            return await original(mock,request)
        body=self.body('Привет 🌍')
        with patch.object(httpx.MockTransport,'handle_async_request',capture):
            result=self.service.submit_turn(ws,cid,body)
        self.assertEqual(result['state'],'SUCCEEDED')
        self.service=OrdinaryCoreChatService(self.registry,self.root,http_fixture=self.fixture)
        self.assertEqual(self.service.submit_turn(ws,cid,body),result)
        self.assertEqual(len(observed),1); self.assertEqual(len(self.fixture.requests),1)
        page=self.service.messages(ws,cid,None,50)
        self.assertEqual(len(page['messages']),2)
        self.assertEqual(page['usage_summary']['known']['total_tokens'],12)
        self.assertEqual(page['usage_summary']['known']['reasoning_tokens'],3)
        self.assertEqual(ledger.recover().attempts[0].state,policy.KNOWN_TERMINAL)

    def test_direct_untrusted_authority_and_real_factory_are_zero_token_http(self):
        sender=transport.GigaChatTransport(self.fixture)
        for authority in (None,{},True,lambda wire:None, object()):
            with self.subTest(authority=type(authority).__name__), self.assertRaises(chat.PreSendDenied):
                asyncio.run(sender.send_bytes(b'{}',timeout_seconds=1,max_response_bytes=100,admission=authority))
        for fixture in (None,{},True,httpx.MockTransport(lambda r:httpx.Response(200)),object()):
            with self.assertRaises(chat.PreSendDenied): transport.GigaChatTransport(fixture)
        self.assertEqual(self.fixture.token_calls,0); self.assertEqual(self.fixture.requests,[])

    def test_low_level_forged_turn_and_replayed_capability_are_denied(self):
        sender=transport.GigaChatTransport(self.fixture)
        forged=_TurnAdmission(object(),None,None,None,None,None,None)
        with self.assertRaises(chat.PreSendDenied):
            asyncio.run(sender.send_bytes(b'{}',timeout_seconds=1,max_response_bytes=100,admission=forged))
        ws,cid,_,_,_=self.project(); captured=[]; original=_TurnAdmission.authorize
        def authorize(cap,wire,sender):
            captured.append((cap,wire,sender)); return original(cap,wire,sender)
        with patch.object(_TurnAdmission,'authorize',authorize): self.service.submit_turn(ws,cid,self.body('one'))
        cap,wire,sender=captured[0]
        with self.assertRaises(chat.PreSendDenied):
            asyncio.run(sender.send_bytes(wire,timeout_seconds=1,max_response_bytes=100,admission=cap))
        self.assertEqual(len(self.fixture.requests),1);self.assertEqual(self.fixture.token_calls,1)

    def test_budget_denials_and_invalid_enrollment_zero_token_http(self):
        for mode in ('deny','caps','missing','corrupt','upgrade'):
            with self.subTest(mode=mode):
                ws,cid,root,_,ledger=self.project()
                raw=bridge.offline_policy()
                if mode=='deny': raw['ordinary']={'mode':'DENY'}
                if mode=='caps': raw['ordinary']['max_scope_liability_tokens']=1
                marker=root/'.ultra/audit/budget.enrollment.json'
                if mode=='missing': marker.unlink()
                elif mode=='corrupt': marker.write_text('{}')
                elif mode=='upgrade':
                    data=json.loads(marker.read_text());data['policy_engine_sha256']='0'*64;marker.write_text(json.dumps(data))
                with patch.object(bridge,'offline_policy',return_value=raw):
                    self.assertEqual(self.service.submit_turn(ws,cid,self.body(mode))['state'],'FAILED')
                self.assertEqual(self.fixture.token_calls,0); self.assertEqual(self.fixture.requests,[])

    def test_forged_missing_replay_wrongwire_receipt_zero_token_http(self):
        original=BudgetLedger.reserve
        for mode in ('missing','replayed','wrongwire','sent_ack'):
            with self.subTest(mode=mode):
                ws,cid,_,_,ledger=self.project()
                def reserve(obj,attempt,raw,route,wire,context,binding):
                    if mode=='missing':raise LedgerDenied('synthetic')
                    if mode=='wrongwire': wire=wire.replace(b'hello',b'other')
                    receipt=original(obj,attempt,raw,route,wire,context,binding)
                    return replace(receipt,replayed=True) if mode=='replayed' else receipt
                with patch.object(BudgetLedger,'reserve',reserve), patch.object(BudgetLedger,'mark_sent',
                        return_value=None) if mode=='sent_ack' else patch.object(legacy,'CHAT_URL',legacy.CHAT_URL):
                    try:self.assertNotEqual(self.service.submit_turn(ws,cid,self.body('hello'))['state'],'SUCCEEDED')
                    except UltraChatError as error:self.assertEqual(error.status,503)
                self.assertEqual(self.fixture.token_calls,0);self.assertEqual(self.fixture.requests,[])

    def test_post_sent_changes_block_before_token(self):
        original=BudgetLedger.mark_sent
        for mode in ('endpoint','policy','model','transport'):
            with self.subTest(mode=mode):
                ws,cid,_,wid,ledger=self.project(); patches=[]
                def marked(obj,attempt):
                    receipt=original(obj,attempt)
                    if mode=='endpoint': p=patch.object(transport,'CHAT_URL','https://invalid.example/')
                    elif mode=='policy':
                        raw=bridge.offline_policy();raw['revision_label']='changed';p=patch.object(bridge,'offline_policy',return_value=raw)
                    elif mode=='model': p=patch.object(chat,'_model',side_effect=ValueError('changed'))
                    else:
                        self.service._owners[(wid,cid)][1]._offline_adapter._transport=object();return receipt
                    p.start();patches.append(p);return receipt
                try:
                    with patch.object(BudgetLedger,'mark_sent',marked):
                        try:self.service.submit_turn(ws,cid,self.body(mode))
                        except UltraChatError:pass
                finally:
                    for p in patches:p.stop()
                self.assertEqual(self.fixture.token_calls,0);self.assertEqual(self.fixture.requests,[])
                self.assertGreater(ledger.recover().attempts[0].liability_tokens,0)

    def test_post_admission_http_byte_substitution_is_zero_http(self):
        ws,cid,_,_,ledger=self.project(); original=httpx.MockTransport.handle_async_request
        async def substitute(mock,request):
            request._content=request.content+b' '
            return await original(mock,request)
        with patch.object(httpx.MockTransport,'handle_async_request',substitute):
            result=self.service.submit_turn(ws,cid,self.body('wire integrity'))
        self.assertEqual(result['state'],'UNKNOWN');self.assertEqual(self.fixture.requests,[])
        self.assertEqual(self.fixture.token_calls,1)
        self.assertGreater(ledger.recover().attempts[0].liability_tokens,0)

    def test_cancel_during_token_wait_zero_http_no_retry(self):
        ws,cid,_,_,ledger=self.project(); entered=threading.Event();release=threading.Event()
        original=transport.OfflineHTTPFixture.token
        async def token(fixture):
            entered.set()
            await asyncio.to_thread(release.wait,5)
            return await original(fixture)
        body=self.body('cancel before HTTP')
        with patch.object(transport.OfflineHTTPFixture,'token',token),ThreadPoolExecutor() as pool:
            pending=pool.submit(self.service.submit_turn,ws,cid,body)
            try:
                self.assertTrue(entered.wait(5));tid=self.service.latest_turn(ws,cid)['turn']['turn_id']
                self.service._turn_request('cancel',ws,cid,tid,{})
            finally:release.set()
            result=pending.result(10)
        self.assertEqual(result['state'],'UNKNOWN');self.assertEqual(self.fixture.requests,[])
        self.assertEqual(self.service.submit_turn(ws,cid,body)['state'],'UNKNOWN')
        self.assertGreater(ledger.recover().attempts[0].liability_tokens,0)

    def test_http_status_json_size_and_provider_errors_no_refresh_retry(self):
        scenarios=[(401,json.dumps(reply(USAGE)).encode()),(429,b'{"error":"synthetic secret"}'),
                   (500,b'{}'),(302,b'{}'),(200,b'not json'),(200,b'\xff'),(200,b'x'*8193),
                   (200,b'{"choices":[]}'),(200,b'{"error":{"secret":"masked"}}')]
        for status,body in scenarios:
            with self.subTest(status=status,size=len(body)):
                ws,cid,_,_,ledger=self.project();self.fixture.status=status;self.fixture.body=body
                before=len(self.fixture.requests);token_before=self.fixture.token_calls
                payload=self.body('status');result=self.service.submit_turn(ws,cid,payload)
                self.assertEqual(result['state'],'FAILED')
                self.assertEqual(len(self.fixture.requests),before+1);self.assertEqual(self.fixture.token_calls,token_before+1)
                self.assertEqual(self.service.submit_turn(ws,cid,payload),result)
                self.assertNotIn('synthetic secret',json.dumps(result))
                record=ledger.recover().attempts[0]
                self.assertIn(record.state,(policy.KNOWN_TERMINAL,policy.UNKNOWN_TERMINAL))
                if status==401:self.assertEqual(record.terminal_outcomes,('provider_error',))

    def test_transport_timeout_token_failure_no_automatic_retry(self):
        for mode in ('timeout','transport','token'):
            with self.subTest(mode=mode):
                ws,cid,_,_,ledger=self.project();self.fixture.error=None if mode=='token' else mode
                self.fixture.token_error=mode=='token';before=len(self.fixture.requests);tokens=self.fixture.token_calls
                body=self.body(mode);result=self.service.submit_turn(ws,cid,body)
                self.assertEqual(result['state'],'UNKNOWN')
                self.assertEqual(len(self.fixture.requests),before+(mode!='token'))
                self.assertEqual(self.fixture.token_calls,tokens+1)
                self.assertEqual(self.service.submit_turn(ws,cid,body),result)
                self.assertGreater(ledger.recover().attempts[0].liability_tokens,0)

    def test_terminal_failure_reopen_does_not_resend(self):
        ws,cid,_,_,ledger=self.project();body=self.body('disk unavailable')
        with patch.object(BudgetLedger,'terminal',side_effect=OSError('synthetic disk')):
            with self.assertRaises(UltraChatError):self.service.submit_turn(ws,cid,body)
        self.assertEqual(len(self.fixture.requests),1)
        self.service=OrdinaryCoreChatService(self.registry,self.root,http_fixture=self.fixture)
        self.assertEqual(self.service.submit_turn(ws,cid,body)['state'],'UNKNOWN')
        self.assertEqual(len(self.fixture.requests),1);self.assertEqual(ledger.recover().attempts[0].state,policy.SENT)

    def test_post_token_binding_or_client_url_changes_are_zero_http(self):
        for mode in ('wire','url','policy','transport'):
            with self.subTest(mode=mode):
                ws,cid,_,wid,ledger=self.project();patches=[]
                original=transport.OfflineHTTPFixture.token
                async def token(fixture):
                    value=await original(fixture)
                    if mode=='policy':
                        raw=bridge.offline_policy();raw['revision_label']='changed after token'
                        p=patch.object(bridge,'offline_policy',return_value=raw);p.start();patches.append(p)
                    elif mode=='transport':self.service._owners[(wid,cid)][1]._offline_adapter._transport=object()
                    return value
                stream=httpx.AsyncClient.stream
                def mutate(client,method,url,**kwargs):
                    if mode=='wire':kwargs['content']+=b' '
                    if mode=='url':url='https://invalid.example/changed'
                    return stream(client,method,url,**kwargs)
                try:
                    with patch.object(transport.OfflineHTTPFixture,'token',token),patch.object(httpx.AsyncClient,'stream',mutate):
                        try:self.assertNotEqual(self.service.submit_turn(ws,cid,self.body(mode))['state'],'SUCCEEDED')
                        except UltraChatError:pass
                finally:
                    for p in patches:p.stop()
                self.assertEqual(self.fixture.requests,[])
                self.assertGreater(ledger.recover().attempts[0].liability_tokens,0)

    def test_concurrent_duplicate_has_single_http_and_no_second_owner(self):
        ws,cid,_,_,_=self.project();entered=threading.Event();release=threading.Event()
        original=httpx.MockTransport.handle_async_request
        async def waiting(mock,request):
            entered.set();await asyncio.to_thread(release.wait,5)
            return await original(mock,request)
        body=self.body('one concurrent send')
        other=OrdinaryCoreChatService(self.registry,self.root,http_fixture=self.fixture)
        with patch.object(httpx.MockTransport,'handle_async_request',waiting),ThreadPoolExecutor() as pool:
            pending=pool.submit(self.service.submit_turn,ws,cid,body)
            try:
                self.assertTrue(entered.wait(5))
                self.assertNotEqual(self.service.submit_turn(ws,cid,body)['state'],'SUCCEEDED')
                with self.assertRaises(UltraChatError):other.submit_turn(ws,cid,self.body('second owner'))
            finally:release.set()
            result=pending.result(10)
        self.assertEqual(result['state'],'SUCCEEDED');self.assertEqual(len(self.fixture.requests),1)

    def test_crash_after_sent_or_after_http_reopen_no_retry(self):
        class PowerLoss(BaseException):pass
        for point in ('sent','http'):
            with self.subTest(point=point):
                ws,cid,_,_,ledger=self.project();body=self.body('power loss');before=len(self.fixture.requests)
                mark=BudgetLedger.mark_sent;handle=httpx.MockTransport.handle_async_request
                def crash_sent(obj,attempt):
                    mark(obj,attempt);raise PowerLoss()
                async def crash_http(mock,request):
                    await handle(mock,request);raise PowerLoss()
                hook=patch.object(BudgetLedger,'mark_sent',crash_sent) if point=='sent' else patch.object(httpx.MockTransport,'handle_async_request',crash_http)
                with hook,self.assertRaises(PowerLoss):self.service.submit_turn(ws,cid,body)
                self.service=OrdinaryCoreChatService(self.registry,self.root,http_fixture=self.fixture)
                self.assertEqual(self.service.submit_turn(ws,cid,body)['state'],'UNKNOWN')
                self.assertEqual(len(self.fixture.requests),before+(point=='http'))
                self.assertEqual(ledger.recover().attempts[0].state,policy.SENT)

    def test_deadline_after_http_preserves_unknown_liability(self):
        ws,cid,_,_,ledger=self.project();original=bridge.OrdinaryCoreAdapter.__init__
        def bounded(adapter,**kwargs):
            original(adapter,**kwargs);adapter._limits=replace(adapter._limits,timeout_seconds=2)
        self.fixture.delay=3
        with patch.object(bridge.OrdinaryCoreAdapter,'__init__',bounded):
            result=self.service.submit_turn(ws,cid,self.body('deadline'))
        self.assertEqual(result['state'],'UNKNOWN');self.assertEqual(len(self.fixture.requests),1)
        self.assertGreater(ledger.recover().attempts[0].liability_tokens,0)

    def test_multi_chat_context_and_partial_invalid_missing_reasoning_usage(self):
        ws,a,_,_,_=self.project();b='chat_'+uuid4().hex
        self.service.create_chat(ws,{'chat_id':b})
        for usage in (None,{'prompt_tokens':2}, {'prompt_tokens':True},
                      {**USAGE,'completion_tokens_details':{'reasoning_tokens':99}}):
            self.fixture.body=json.dumps(reply(usage)).encode()
            result=self.service.submit_turn(ws,a,self.body('A'))
            self.assertEqual(result['state'],'SUCCEEDED')
            self.assertIsNone(result['usage']['reasoning_tokens'])
        self.service.submit_turn(ws,b,self.body('B','gigachat_ultra'))
        self.assertEqual(len(self.service.messages(ws,b,None,50)['messages']),2)
        self.assertEqual(self.service.messages(ws,b,None,50)['usage_summary']['attempts'],1)

    def test_browser_config_unknown_models_and_env_do_not_enable_real(self):
        ws,cid,_,_,_=self.project()
        for body in ({**self.body('x'),'config_ref':'REAL'},self.body('x','unknown-model')):
            with self.assertRaises(UltraChatError):self.service.submit_turn(ws,cid,body)
        self.assertEqual(self.fixture.token_calls,0);self.assertEqual(self.fixture.requests,[])
        with patch.dict('os.environ',{'GIGACHAT_LIVE':'1','WUA_REAL':'1'}):
            with self.assertRaises(chat.PreSendDenied):transport.GigaChatTransport()


class WebHTTPTransportTests(unittest.TestCase):
    def test_loopback_web_two_workspaces_four_chats_replay_f5(self):
        import tempfile
        helper=old_bridge_tests.CoreBridgeHttpTests()
        with tempfile.TemporaryDirectory(prefix='h33web_') as folder:
            root=Path(folder).resolve();api=WebAlarmApi(root/'registry')
            fixture=transport.OfflineHTTPFixture(body=json.dumps(reply(USAGE)).encode())
            service=OrdinaryCoreChatService(api.registry,root,http_fixture=fixture)
            server=create_server(api,port=0,offline_chat=service);thread=threading.Thread(target=server.serve_forever);thread.start()
            try:
                cap,read,write=helper.tokens(server)
                self.assertFalse(cap['real_available']);self.assertTrue(cap['core_bridge'])
                trace=[]
                for i in range(2):
                    code,ws=helper.http(server,'POST','/ultra/chat/workspaces',{'title':'synthetic'},write)
                    base=f'/ultra/chat/workspaces/{ws["wa_workspace_id"]}/chats'
                    for j in range(2):
                        cid='chat_'+uuid4().hex
                        self.assertEqual(helper.http(server,'POST',base,{'chat_id':cid,'initialize_workspace':True},write)[0],201)
                        body=s5.Fixture.body('HTTP isolated')
                        url=base+'/'+cid+'/turns'
                        code,result=helper.http(server,'POST',url,body,write)
                        self.assertEqual(result['state'],'SUCCEEDED')
                        self.assertEqual(helper.http(server,'POST',url,body,write)[1],result)
                        self.assertEqual(helper.http(server,'GET',base+'/'+cid+'/messages',headers=read)[1]['usage_summary']['known']['total_tokens'],12)
                        trace.append(dict(workspace=ws['wa_workspace_id'],chat=cid,turn=result['turn_id'],
                                          **fixture.requests[-1]))
                self.assertEqual(len(fixture.requests),4)
                self.assertEqual(helper.http(server,'GET','/')[0],200)
                if os.environ.get('H33_TRACE'):
                    Path(os.environ['H33_TRACE']).write_text(json.dumps(dict(real_available=cap['real_available'],
                        sends=trace,replay_extra_sends=0,total_tokens_per_chat=12),indent=2),encoding='utf-8')
            finally:server.shutdown();server.server_close();thread.join()
