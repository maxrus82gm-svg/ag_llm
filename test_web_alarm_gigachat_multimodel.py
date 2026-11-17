"""Same production protocol and application core over explicit MockTransport.

No credentials, OAuth/API network, user Workspace, live enrollment or paid calls.
"""
import asyncio
from dataclasses import replace
import json
import ssl
import time
import unittest
from unittest.mock import patch
from uuid import uuid4

import httpx
import context_storage as core
import gigachat_transport as oauth
from gigachat_runtime import ProviderSession, LiveApproval, ModelContract, MODELS_URL
from model_registry import list_model_specs
from ordinary_chat_service import PreSendDenied
from ultra_budget_ledger import BudgetLedger
from web_alarm.ordinary_provider import OrdinaryProviderFactory, OrdinaryApplicationChatService
from web_alarm.ultra_chat import OrdinaryCoreChatService, UltraChatError
import test_web_alarm_ultra_chat_s5 as s5


class ProtocolTests(s5.Fixture):
    def setUp(self):
        super().setUp()
        self.service = OrdinaryCoreChatService(self.registry, self.root)
        self.ws, self.cid = self.create_chat('Protocol fixture')
        self.workspace = self.registry.get(self.ws).workspace_root
        self.wid = core.read_workspace_identity_bounded(self.workspace)['workspace_id']
        self.calls = []
        self.status, self.error, self.model, self.usage = 200, None, None, True
        self.oauth_status = self.catalog_status = 200
        self.oauth_reply = None
        self.bad_json = False
        self.answer_text = 'Protocol answer'
        self.catalog = [m.provider_model_id for m in list_model_specs()]
        self.approval = LiveApproval(uuid4().hex, 'SYNTHETIC GO', 'SYNTHETIC review', uuid4().hex,
            'GIGACHAT_API_PERS', time.time()+3600,
            tuple(ModelContract(m.model_id, 32768, 1024, (m.provider_model_id, m.provider_model_id+':1.0'),
                                'SYNTHETIC bounds, not provider evidence') for m in list_model_specs()),
            12, 2, 12, 100000)
        self.transport = httpx.MockTransport(self.handle)
        self.session = ProviderSession.offline(self.workspace, self.wid, self.approval, self.transport)
        self.addCleanup(self.session.close)
        self.factory = OrdinaryProviderFactory.for_session(self.registry, self.session)
        self.app = OrdinaryApplicationChatService(self.registry, self.factory)

    async def handle(self, request):
        url = str(request.url)
        self.calls.append((request.method, url, request.content))
        if url == oauth.OAUTH_URL:
            self.assertEqual(request.headers['Authorization'], 'Basic SYNTHETIC')
            return httpx.Response(self.oauth_status, json=self.oauth_reply if self.oauth_reply is not None else
                {'access_token':'SYNTHETIC-TOKEN', 'expires_at':int((time.time()+1800)*1000)})
        if url == MODELS_URL:
            return httpx.Response(self.catalog_status, json={'data':[{'id':s} for s in self.catalog]})
        self.assertEqual(url, oauth.CHAT_URL)
        attempt = BudgetLedger(self.workspace, self.wid).recover().attempts[-1]
        self.assertEqual(attempt.state, 'SENT')
        _, envelope = BudgetLedger(self.workspace,self.wid).reservation(attempt.attempt_id)
        self.assertEqual(envelope['wire_utf8'].encode(), request.content)
        self.assertEqual(self.session._counts['inference'], len(self.posts()))
        if self.error:
            raise self.error
        if self.bad_json:
            return httpx.Response(200, content=b'not JSON SECRET')
        data = {'model': self.model or json.loads(request.content)['model']+':1.0',
                'choices':[{'message':{'role':'assistant','content':self.answer_text}, 'finish_reason':'stop'}]}
        if self.usage:
            data['usage'] = dict(prompt_tokens=7, completion_tokens=5, total_tokens=12,
                precached_prompt_tokens=3, completion_tokens_details={'reasoning_tokens':2})
        return httpx.Response(self.status, json=data)

    def posts(self):
        return [c for c in self.calls if c[1] == oauth.CHAT_URL]

    def discover(self):
        return asyncio.run(self.session.discover_models())

    def first_lite_session(self):
        self.session.close()
        contract = ModelContract('gigachat_2', 128000, 32, (),
            'OFFLINE official-context/operator-attempt fixture; provider output cap UNKNOWN',
            provider_output_cap_tokens=None, version_mode='DISCOVER_GIGACHAT_2')
        grant = replace(self.approval, grant_id=uuid4().hex, contracts=(contract,),
            max_oauth=1, max_catalog=1, max_inference=1, max_liability_tokens=1056,
            max_request_bytes=1024, max_answer_tokens=32)
        self.session = ProviderSession.offline(self.workspace, self.wid, grant, self.transport)
        self.addCleanup(self.session.close)
        self.factory = OrdinaryProviderFactory.for_session(self.registry, self.session)
        self.app = OrdinaryApplicationChatService(self.registry, self.factory)
        return contract

    def send(self, model='gigachat_2_pro', text='Hello', cid=None, body=None):
        cid = cid or self.cid
        self.app.chat_model(self.ws, cid, {'model_ref':model})
        return self.app.submit_turn(self.ws, cid, body or self.body(text,model))

    def _older_registered_workspace(self):
        from ultra_budget_ledger import LedgerDenied
        other_root = self.root / ('old_workspace_' + uuid4().hex)
        other_root.mkdir()
        identity = core.ensure_workspace_storage(other_root)
        other_id = identity['workspace_id']
        record = self.registry.register('Existing Workspace', other_root)
        chat_record = core.create_chat_record(other_root, title='Исторический чат',
                                               expected_workspace_id=other_id)
        self.assertRaises(LedgerDenied, BudgetLedger(other_root, other_id).recover)
        return record.workspace_id, chat_record['chat']['chat_id'], other_root, other_id

    def test_one_provider_session_serves_personal_and_existing_registered_workspace(self):
        self.discover()
        ws, chat_id, root, wid = self._older_registered_workspace()
        legacy = core.append_raw_message(root, chat_id, 'user', 'LEGACY_HISTORY_NOT_CONTEXT')
        personal_root, personal_wid = self.workspace, self.wid
        original_count = len(self.posts())
        self.assertEqual(self.app.chat_model(ws, chat_id)['model_ref'], 'gigachat_2_pro')
        self.assertFalse(self.app.chat_model(ws, chat_id)['enrolled'])
        self.assertEqual(len(self.posts()), original_count)  # GET must not enroll or send
        from ultra_budget_ledger import LedgerDenied
        self.assertRaises(LedgerDenied, BudgetLedger(root, wid).recover)
        selected = self.app.chat_model(ws, chat_id, {'model_ref':'gigachat_ultra'})
        self.assertEqual(selected['model_ref'], 'gigachat_ultra')
        self.assertTrue(selected['persisted'])
        self.assertTrue(selected['enrolled'])
        self.assertEqual(BudgetLedger(root, wid).recover().attempts, ())
        self.assertEqual(len(self.posts()), original_count)
        # The simulated HTTP provider handler verifies the target Workspace ledger.
        self.workspace, self.wid = root, wid
        try:
            body = self.body('From existing Workspace', 'gigachat_ultra')
            result = self.app.submit_turn(ws, chat_id, body)
            self.assertEqual(result['state'], 'SUCCEEDED')
            self.assertEqual(result['execution_mode'], 'PROTOCOL_TEST')
            self.assertEqual(len(self.posts()), original_count + 1)
            self.assertNotIn(b'LEGACY_HISTORY_NOT_CONTEXT', self.posts()[-1][2])
            self.assertIn(legacy['message_id'],
                          {m['message_id'] for m in core.read_chat_history_bounded(root, chat_id)['messages']})
            self.assertEqual(BudgetLedger(root, wid).recover().attempts[-1].state, 'KNOWN_TERMINAL')
            self.assertEqual(self.app.chat_model(ws, chat_id)['model_ref'], 'gigachat_ultra')
            self.assertEqual(self.app.submit_turn(ws, chat_id, body)['turn_id'], result['turn_id'])
            self.assertEqual(len(self.posts()), original_count + 1)  # replay did not resend
        finally:
            self.workspace, self.wid = personal_root, personal_wid
        self.assertEqual(BudgetLedger(personal_root, personal_wid).recover().attempts, ())
        self.assertEqual(self.app.chat_model(self.ws, self.cid)['model_ref'], 'gigachat_2_pro')
        personal = self.send(text='Personal after Workspace')
        self.assertEqual(personal['state'], 'SUCCEEDED')
        self.assertEqual(len(self.posts()), original_count + 2)
        self.assertEqual(len(BudgetLedger(root, wid).recover().attempts), 1)
        self.assertEqual(len(BudgetLedger(personal_root, personal_wid).recover().attempts), 1)

    def test_http_model_and_turn_routing_to_registered_old_workspace(self):
        from web_alarm.server import WebAlarmApi, create_server
        import threading
        self.discover()
        ws, chat_id, root, wid = self._older_registered_workspace()
        api = WebAlarmApi(self.root / 'registry')
        factory = OrdinaryProviderFactory.for_session(api.registry, self.session)
        server = create_server(api, host='127.0.0.1', port=0, ordinary_factory=factory)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.http = lambda *a, **k: s5.HttpAndTkTests.http(self, *a, **k)
        http = lambda method, uri, body=None, headers=None: s5.HttpAndTkTests.http(
            self, server, method, uri, body, headers)
        _, read, write = s5.HttpAndTkTests.tokens(self, server)
        base = f'/ultra/chat/workspaces/{ws}/chats/{chat_id}'
        self.assertEqual(http('GET', base+'/model', headers=read)[0], 200)
        from ultra_budget_ledger import LedgerDenied
        self.assertRaises(LedgerDenied, BudgetLedger(root, wid).recover)
        code, selected = http('POST',base+'/model',{'model_ref':'gigachat_ultra'},write)
        self.assertEqual((code, selected['model_ref'], selected['persisted']),
                         (200, 'gigachat_ultra', True))
        original_root, original_wid = self.workspace, self.wid
        self.workspace, self.wid = root, wid
        try:
            body = self.body('HTTP from old Workspace', 'gigachat_ultra')
            code, reply = http('POST',base+'/turns',body,write)
            self.assertEqual((code, reply['state']), (200,'SUCCEEDED'))
            self.assertEqual(http('POST',base+'/turns',body,write)[1]['turn_id'], reply['turn_id'])
            self.assertEqual(http('GET',base+'/model',headers=read)[1]['model_ref'],'gigachat_ultra')
            self.assertEqual(http('GET',base+'/messages?limit=50',headers=read)[0],200)
        finally:
            self.workspace, self.wid = original_root, original_wid
        self.assertEqual(len(self.posts()),1)
        self.assertEqual(len(BudgetLedger(root, wid).recover().attempts),1)

    def test_unregistered_and_damaged_workspaces_never_gain_provider_send(self):
        self.discover()
        ws, chat_id, root, wid = self._older_registered_workspace()
        outside = self.root / ('unregistered_' + uuid4().hex)
        outside.mkdir()
        core.ensure_workspace_storage(outside)
        before = len(self.posts())
        with self.assertRaisesRegex(UltraChatError, 'Only registered Workspace roots'):
            self.factory.fixture_for(self.registry, outside)
        self.assertEqual(len(self.posts()), before)
        # A corrupted/incomplete existing audit cannot be replaced by a fresh zero.
        marker = BudgetLedger(root, wid)._marker()
        marker.parent.mkdir(exist_ok=True)
        marker.write_text('not-json', encoding='utf-8')
        with self.assertRaisesRegex(UltraChatError, 'Workspace audit needs review'):
            self.app.chat_model(ws, chat_id, {'model_ref':'gigachat_2_pro'})
        self.assertEqual(len(self.posts()), before)
        self.assertFalse(self.app.chat_model(ws, chat_id)['persisted'])

    def test_evm_profile_timeout_is_bound_to_existing_provider_adapter(self):
        from web_alarm.ordinary_chat_bridge import OrdinaryCoreAdapter
        profile = {'profile_id': 'gigachat-default', 'settings_version': 'a'*16,
                   'timeout_seconds': 67}
        adapter = OrdinaryCoreAdapter.for_provider(self.session, context_ref='stage5:'+self.cid,
            model_id='gigachat_2_pro', evm_profile=profile)
        self.assertEqual(adapter._limits.timeout_seconds, 67.0)
        self.assertEqual(adapter._evm_profile, profile)
        self.assertEqual(self.posts(), [])
        with self.assertRaisesRegex(PreSendDenied, 'evm_profile_invalid'):
            OrdinaryCoreAdapter.for_provider(self.session, context_ref='stage5:'+self.cid,
                model_id='gigachat_2_pro', evm_profile={**profile, 'timeout_seconds': 121})

    def test_user_turn_mode_uses_preference_and_keeps_full_large_reply(self):
        self.session.close()
        contract = ModelContract('gigachat_2', 128000, 20000, ('GigaChat-2:1.0',),
            'OFFLINE operator output ceiling; provider maximum unknown')
        grant = replace(self.approval, grant_id=uuid4().hex, contracts=(contract,),
            max_oauth=None, max_catalog=1, max_inference=None, max_liability_tokens=None,
            max_request_bytes=4096, max_answer_tokens=20000, user_turn_mode=True)
        self.session = ProviderSession.offline(self.workspace, self.wid, grant, self.transport)
        self.addCleanup(self.session.close)
        self.app = OrdinaryApplicationChatService(self.registry,
            OrdinaryProviderFactory.for_session(self.registry, self.session))
        self.discover()
        self.app.chat_preferences(self.ws, self.cid,
            {'compression_threshold_tokens':250000, 'answer_tokens':20000})
        self.answer_text = 'Длинный ответ. ' * 1000
        body = self.body('Full reply', 'gigachat_2')
        result = self.send('gigachat_2', body=body)
        self.assertEqual(result['state'], 'SUCCEEDED')
        self.assertEqual(self.app.messages(self.ws, self.cid, None, 50)['messages'][-1]['text'], self.answer_text)
        self.assertEqual(json.loads(self.posts()[0][2])['max_tokens'], 20000)
        self.assertEqual(self.app.submit_turn(self.ws, self.cid, body), result)
        self.assertEqual(len(self.posts()), 1)
        self.assertEqual(self.session._counts['inference'], 1)
        self.assertLess(self.session._counts['liability'], 24097)

    def test_user_turn_mode_rejects_oversized_attempt_before_io(self):
        self.session.close()
        contract = ModelContract('gigachat_2', 128000, 20000, ('GigaChat-2:1.0',), 'OFFLINE')
        grant = replace(self.approval, grant_id=uuid4().hex, contracts=(contract,),
            max_oauth=None, max_catalog=1, max_inference=None, max_liability_tokens=None,
            max_request_bytes=4096, max_answer_tokens=20000, user_turn_mode=True)
        self.session = ProviderSession.offline(self.workspace, self.wid, grant, self.transport)
        self.addCleanup(self.session.close)
        with self.assertRaisesRegex(PreSendDenied, 'live_call_or_token_limit'):
            self.session._consume('inference', 24097)
        self.assertEqual(self.posts(), [])

    def test_user_turn_mode_has_no_twelve_send_cutoff_and_no_replay(self):
        self.session.close()
        contract = ModelContract('gigachat_2', 128000, 20000, ('GigaChat-2:1.0',), 'OFFLINE')
        grant = replace(self.approval, grant_id=uuid4().hex, contracts=(contract,),
            max_oauth=None, max_catalog=1, max_inference=None, max_liability_tokens=None,
            max_request_bytes=4096, max_answer_tokens=20000, user_turn_mode=True)
        self.session = ProviderSession.offline(self.workspace, self.wid, grant, self.transport)
        self.addCleanup(self.session.close)
        self.app = OrdinaryApplicationChatService(self.registry,
            OrdinaryProviderFactory.for_session(self.registry, self.session))
        self.discover()
        for number in range(13):
            cid = 'chat_'+uuid4().hex
            self.app.create_chat(self.ws, {'chat_id':cid})
            body = self.body('Question '+str(number), 'gigachat_2')
            self.assertEqual(self.send('gigachat_2', cid=cid, body=body)['state'], 'SUCCEEDED')
            if number == 12:
                self.assertEqual(self.app.submit_turn(self.ws, cid, body)['state'], 'SUCCEEDED')
        self.assertEqual(len(self.posts()), 13)
        self.assertEqual(self.session._counts['inference'], 13)

    def test_large_provider_reply_hits_memory_guard_once(self):
        self.discover()
        self.answer_text = 'x' * 524288
        result = self.send()
        self.assertNotEqual(result['state'], 'SUCCEEDED')
        self.assertEqual(result.get('diagnostic_code'), 'response_limit_exceeded')
        self.assertEqual(len(self.posts()), 1)

    def test_user_turn_mode_requires_the_exact_operational_envelope(self):
        self.session.close()
        invalid = replace(self.approval, grant_id=uuid4().hex, user_turn_mode=True,
            max_oauth=None, max_inference=12, max_liability_tokens=None, max_catalog=1)
        with self.assertRaisesRegex(PreSendDenied, 'reviewed_live_approval_required'):
            ProviderSession.offline(self.workspace, self.wid, invalid, self.transport)
        self.assertEqual(self.posts(), [])

    def test_discovered_family_version_is_exact_after_first_response(self):
        self.session.close()
        contract = ModelContract('gigachat_2_pro', 32768, 20000, (),
            'OFFLINE first-family pin', version_mode='DISCOVER_FAMILY')
        grant = replace(self.approval, grant_id=uuid4().hex, contracts=(contract,),
            max_oauth=None, max_catalog=1, max_inference=None, max_liability_tokens=None,
            max_request_bytes=4096, max_answer_tokens=20000, user_turn_mode=True)
        self.session = ProviderSession.offline(self.workspace, self.wid, grant, self.transport)
        self.addCleanup(self.session.close)
        self.app = OrdinaryApplicationChatService(self.registry,
            OrdinaryProviderFactory.for_session(self.registry, self.session))
        self.discover()
        self.assertEqual(self.send('gigachat_2_pro')['state'], 'SUCCEEDED')
        self.assertEqual(self.session._confirmed_versions['gigachat_2_pro'], 'GigaChat-2-Pro:1.0')
        self.model = 'GigaChat-2-Pro:1.1'
        second = self.send('gigachat_2_pro', 'second question')
        self.assertNotEqual(second['state'], 'SUCCEEDED')
        self.assertEqual(second.get('diagnostic_code'), 'response_model_version_mismatch')
        self.assertEqual(len(self.posts()), 2)

    def test_real_route_six_models_history_cached_reasoning_reopen_and_no_replay(self):
        self.discover()
        second = 'chat_'+uuid4().hex
        self.app.create_chat(self.ws, {'chat_id':second})
        for m in list_model_specs():
            result = self.send(m.model_id)
            self.assertEqual(result['state'], 'SUCCEEDED', result)
            self.assertEqual(result['execution_mode'],'PROTOCOL_TEST')
            self.assertEqual(result['usage']['precached_prompt_tokens'],3)
        self.send('gigachat_ultra', 'Separate history', second)
        self.assertNotIn('Hello', repr(json.loads(self.posts()[-1][2])['messages']))
        self.assertEqual(self.app.chat_model(self.ws,self.cid)['model_ref'], 'gigachat_ultra')
        self.assertEqual(len(self.posts()),7)
        usage=self.app.messages(self.ws,self.cid,None,50)['usage_summary']
        self.assertEqual(usage['known']['total_tokens'],72)
        self.assertEqual(usage['known']['reasoning_tokens'],12)
        self.assertEqual(usage['cached_input'],dict(known=18,missing=0,full_input_known=60,full_input_missing=0))
        self.assertTrue(result['response_model'].endswith(':1.0'))
        # Restart with HOLD can read history, latest result and usage without
        # requiring a fresh live authority or calling OAuth.
        reopened = OrdinaryApplicationChatService(self.registry, OrdinaryProviderFactory())
        self.assertEqual(len(reopened.messages(self.ws,self.cid,None,50)['messages']),12)
        self.assertEqual(reopened.latest_turn(self.ws,self.cid)['turn']['state'], 'SUCCEEDED')
        self.assertEqual(reopened.messages(self.ws,self.cid,None,50)['usage_summary']['known']['total_tokens'],72)
        body=self.body('Idempotent')
        first=self.send(body=body)
        self.assertEqual(self.app.submit_turn(self.ws,self.cid,body),first)
        self.assertEqual(len(self.posts()),8)
        record=BudgetLedger(self.workspace,self.wid).recover().attempts[0]
        self.assertEqual(record.state,'KNOWN_TERMINAL')

    def test_catalog_unavailable_and_caps_are_not_preferences(self):
        self.catalog=['GigaChat-2-Pro']
        self.discover()
        self.assertEqual(self.app.capability()['models'][-1]['availability'],'UNAVAILABLE')
        result=self.send('gigachat_ultra')
        self.assertNotEqual(result['state'],'SUCCEEDED')
        self.assertEqual(self.posts(),[])

    def test_oauth_expiry_scope_binding_and_no_duplicate_web_cache(self):
        self.discover()
        self.assertEqual(self.session._counts['oauth'],1)
        self.send()
        self.assertEqual(self.session._counts['oauth'],1)
        with patch.object(oauth,'_access_token_valid_until',time.time()-1):
            self.send()
        self.assertEqual(self.session._counts['oauth'],2)
        self.session._credentials=('SYNTHETIC','GIGACHAT_API_B2B')
        with self.assertRaisesRegex(PreSendDenied,'credentials_or_scope_invalid'):
            asyncio.run(oauth.get_access_token(authority=self.session))

    def test_errors_one_physical_post_no_auto_refresh_retry(self):
        self.discover()
        for status in (301,307,401,403,404,429,500):
            with self.subTest(status=status):
                self.status=status
                result=self.send()
                self.assertEqual(result['state'],'FAILED')
        self.assertEqual(len(self.posts()),7)
        self.assertEqual(self.session._counts['oauth'],1)

    def test_timeout_tls_transport_errors_unknown_no_replay(self):
        self.discover()
        for error in (httpx.ReadTimeout('SECRET'),httpx.ConnectError('SECRET TLS')):
            self.error=error
            body=self.body('Fault')
            result=self.send(body=body)
            self.assertEqual(result['state'],'UNKNOWN')
            self.assertNotIn('SECRET',repr(result))
            self.assertEqual(self.app.submit_turn(self.ws,self.cid,body),result)
        self.assertEqual(len(self.posts()),2)

    def test_version_mismatch_missing_usage_and_budget_limit(self):
        self.discover()
        self.model='GigaChat-2-Pro:UNAPPROVED'
        self.assertEqual(self.send()['state'],'FAILED')
        self.model=None;self.usage=False
        result=self.send()
        self.assertEqual(result['state'],'SUCCEEDED')
        self.assertIsNone(result['usage']['total_tokens'])
        self.session._counts['inference']=12
        with core._existing_workspace_writer(self.workspace,self.wid) as writer:
            self.session._save(writer)
        self.assertEqual(self.send()['state'],'UNKNOWN')
        self.assertEqual(len(self.posts()),2)

    def test_approval_reuse_expiry_tls_and_default_authority_denied(self):
        with self.assertRaisesRegex(PreSendDenied,'account_owner_live'):
            ProviderSession.offline(self.workspace,self.wid,self.approval,self.transport)
        insecure=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        insecure.check_hostname=False;insecure.verify_mode=ssl.CERT_NONE
        with self.assertRaisesRegex(PreSendDenied,'verified_tls_required'):
            ProviderSession(self.workspace,self.wid,replace(self.approval,grant_id=uuid4().hex),tls_context=insecure)
        with self.assertRaises(PreSendDenied):
            asyncio.run(oauth.get_access_token())
        self.assertEqual(self.calls,[])

    def test_oauth_error_redirect_invalid_token_and_expires_at(self):
        for status in (301,401,403,429,500):
            with self.subTest(status=status):
                with patch.object(oauth,'_access_token',None):
                    self.oauth_status=status
                    before=len(self.calls)
                    try:
                        asyncio.run(oauth.get_access_token(authority=self.session))
                    except PreSendDenied:
                        pass
                    else:
                        self.fail('OAuth rejection accepted')
                    self.assertLessEqual(len(self.calls)-before,1)
        # A separate isolated grant for malformed successful replies.
        other=ProviderSession.offline(self.workspace,self.wid,
            replace(self.approval,grant_id=uuid4().hex,account_id=uuid4().hex,max_oauth=10),self.transport)
        self.addCleanup(other.close)
        self.oauth_status=200
        for value in ({}, {'access_token':'SECRET','expires_at':0},
                      {'access_token':'SECRET\r\nINJECT','expires_at':int((time.time()+1800)*1000)},
                      {'access_token':'SECRET','expires_at':True}):
            with self.subTest(reply=list(value)):
                self.oauth_reply=value
                with patch.object(oauth,'_access_token',None), self.assertRaisesRegex(PreSendDenied,'oauth_response_invalid'):
                    asyncio.run(oauth.get_access_token(authority=other))
        self.assertEqual(self.posts(),[])

    def test_malformed_response_and_usage_survives_model_rejection(self):
        self.discover()
        self.bad_json=True
        self.assertEqual(self.send()['state'],'FAILED')
        self.bad_json=False; self.model='GigaChat-2-Pro:unexpected'
        result=self.send()
        self.assertEqual(result['state'],'FAILED')
        self.assertEqual(result['usage']['total_tokens'],12)
        self.assertEqual(BudgetLedger(self.workspace,self.wid).recover().attempts[-1].state,'KNOWN_TERMINAL')

    def test_close_expiry_and_foreign_workspace_do_not_hide_history(self):
        self.discover();self.send()
        self.session.close()
        self.assertFalse(self.app.capability()['available'])
        self.assertEqual(len(self.app.messages(self.ws,self.cid,None,50)['messages']),2)
        self.assertEqual(self.app.latest_turn(self.ws,self.cid)['turn']['state'],'SUCCEEDED')
        with self.assertRaises(UltraChatError):
            self.send()
        self.assertEqual(len(self.posts()),1)

    def test_raw_commit_failure_recovery_does_not_resend(self):
        self.discover()
        commit=core.commit_raw_message
        def fail_assistant(root,chat,message,role,*args,**kwargs):
            if role=='assistant':
                raise OSError('synthetic RAW write failure')
            return commit(root,chat,message,role,*args,**kwargs)
        body=self.body('RAW crash')
        with patch.object(core,'commit_raw_message',fail_assistant):
            with self.assertRaises((OSError,UltraChatError)):
                self.send(body=body)
        self.assertEqual(len(self.posts()),1)
        result=self.app.submit_turn(self.ws,self.cid,body)
        self.assertEqual(result['state'],'SUCCEEDED')
        self.assertEqual(len(self.posts()),1)

    def test_transport_options_are_verified_and_no_env_proxy(self):
        self.discover()
        original=httpx.AsyncClient
        options=[]
        def capture(*args,**kwargs):
            options.append(kwargs)
            return original(*args,**kwargs)
        with patch('httpx.AsyncClient',capture):
            self.send()
        self.assertTrue(options)
        self.assertTrue(all(o['trust_env'] is False and o['follow_redirects'] is False for o in options))
        self.assertEqual(self.session._tls.verify_mode,ssl.CERT_REQUIRED)
        self.assertTrue(self.session._tls.check_hostname)
        # Construct (never send) the actual network branch under the early
        # socket/DNS guard and inspect its exact httpcore TLS/retry settings.
        self.session.synthetic=False
        async def inspect_client():
            async with self.session.client(8) as client:
                self.assertIs(client._transport._pool._ssl_context,self.session._tls)
                self.assertEqual(client._transport._pool._retries,0)
                self.assertFalse(client.follow_redirects)
        try:
            asyncio.run(inspect_client())
        finally:
            self.session.synthetic=True

    def test_cancel_at_final_boundary_no_post_and_reserved_unknown(self):
        self.discover()
        from web_alarm.turn_service import _TurnAdmission
        check=_TurnAdmission.check
        def cancel(cap,wire,transport,*,physical=False):
            if physical:
                root,wid,cid,tid,*_=cap.args
                cap.owner.cancel(root,wid,cid,tid,{})
            return check(cap,wire,transport,physical=physical)
        with patch.object(_TurnAdmission,'check',cancel):
            result=self.send()
        self.assertIn(result['state'],('CANCELLED','UNKNOWN'))
        self.assertTrue(result['cancel_requested'])
        self.assertEqual(self.posts(),[])

    def test_http_application_uses_same_protocol_and_tokens(self):
        from web_alarm.server import WebAlarmApi,create_server
        import threading
        self.discover()
        api=WebAlarmApi(self.root/'registry')
        # Same storage, exact registry object belongs to this server.
        factory=OrdinaryProviderFactory.for_session(api.registry,self.session)
        server=create_server(api,host='127.0.0.1',port=0,ordinary_factory=factory)
        worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        self.http=lambda *a,**k:s5.HttpAndTkTests.http(self,*a,**k)
        cap,read,write=s5.HttpAndTkTests.tokens(self,server)
        base=f'/ultra/chat/workspaces/{self.ws}/chats/{self.cid}'
        status,result=s5.HttpAndTkTests.http(self,server,'POST',base+'/turns',self.body('HTTP real protocol fixture'),write)
        self.assertEqual((status,result['state']),(200,'SUCCEEDED'))
        self.assertEqual(result['execution_mode'],'PROTOCOL_TEST')
        self.assertEqual(s5.HttpAndTkTests.http(self,server,'GET',base+'/messages?limit=50',headers=read)[0],200)
        self.assertEqual(s5.HttpAndTkTests.http(self,server,'POST',base+'/turns',self.body('denied'),{})[0],403)
        self.assertEqual(len(self.posts()),1)

    def test_exact_census_rejects_new_runtime_send_or_changed_authority(self):
        import test_rt002_s1_routes as census
        from pathlib import Path
        path=Path(__file__).parent/'gigachat_runtime.py'
        source=path.read_text(encoding='utf-8')
        analysis=census.analyze_module(path.name,source)
        self.assertEqual(analysis['reconciliation_issues'],[])
        self.assertEqual(len(analysis['sites']),2)
        mutated=source.replace("session.check()\n                admission.check", "await client.post('https://example.invalid')\n                admission.check")
        self.assertNotEqual(mutated,source)
        self.assertTrue(census.analyze_module(path.name,mutated)['reconciliation_issues'])
        weakened=source.replace("and _FIRST_LITE_VERSION.fullmatch(observed) is not None)",
                                "and True)")
        self.assertNotEqual(weakened,source)
        self.assertTrue(census.analyze_module(path.name,weakened)['reconciliation_issues'])

    def test_account_owner_fences_other_grant_and_restart(self):
        with self.assertRaisesRegex(PreSendDenied,'account_owner_live'):
            ProviderSession.offline(self.workspace,self.wid,replace(self.approval,grant_id=uuid4().hex),self.transport)
        self.assertEqual(self.calls,[])

    def test_crashed_lock_owner_recovers_without_reusing_grant_or_provider_calls(self):
        old = self.session
        old._owner_lock.release()  # Simulates OS release at process death.
        old._closed = True  # The dead process cannot execute test cleanup.
        next_grant = replace(self.approval, grant_id=uuid4().hex)
        recovered = ProviderSession.offline(self.workspace,self.wid,next_grant,self.transport)
        self.addCleanup(recovered.close)
        with core._existing_workspace_writer(self.workspace,self.wid) as writer:
            evidence = core._read_existing_raw(writer, old._parts[:-1]+('recovery_'+old.approval.grant_id+'.json',))
            previous = core._read_existing_raw(writer, old._parts)
        self.assertEqual(evidence['reason'], 'owner_os_lock_released')
        self.assertEqual(evidence['previous']['grant_id'], old.approval.grant_id)
        self.assertEqual(previous['state'], 'ACTIVE')
        old._closed = False
        with self.assertRaisesRegex(PreSendDenied, 'account_owner_changed'):
            old.check()
        old._closed = True
        self.assertEqual(self.calls, [])

    def test_legacy_active_without_owner_proof_is_preserved(self):
        old = self.session
        old._owner_lock.release()
        old._closed = True
        with core._existing_workspace_writer(self.workspace,self.wid) as writer:
            prior = core._read_existing_raw(writer, old._account_parts)
            legacy = {key:value for key,value in prior.items() if key != 'owner_lock'}
            core._replace_verified(writer.anchor, old._account_parts, core._json_bytes(legacy))
        with self.assertRaisesRegex(PreSendDenied, 'account_owner_unresolved_legacy_active'):
            ProviderSession.offline(self.workspace,self.wid,replace(self.approval,grant_id=uuid4().hex),self.transport)
        with core._existing_workspace_writer(self.workspace,self.wid) as writer:
            self.assertEqual(core._read_existing_raw(writer, old._account_parts), legacy)
        self.assertEqual(self.calls, [])

    def test_probe_only_approval_has_zero_inference_without_model_caps(self):
        grant=replace(self.approval,grant_id=uuid4().hex,account_id=uuid4().hex,
                      contracts=(),max_inference=0,max_oauth=1,max_catalog=1)
        probe=ProviderSession.offline(self.workspace,self.wid,grant,self.transport)
        self.addCleanup(probe.close)
        self.assertTrue(asyncio.run(probe.discover_models()))
        from ordinary_gigachat_transport import create_real_transport
        with self.assertRaisesRegex(PreSendDenied,'model_not_approved'):
            create_real_transport('gigachat_2_pro',authority=probe)
        with self.assertRaisesRegex(PreSendDenied,'live_call_or_token_limit'):
            probe._consume('inference')
        self.assertEqual(self.posts(),[])

    def test_first_lite_version_is_pinned_and_future_grant_requires_exact_id(self):
        contract = self.first_lite_session()
        self.assertIsNone(contract.provider_output_cap_tokens)
        self.model = 'GigaChat-2:2.0.30.01'
        self.discover()
        body = self.body('First version', 'gigachat_2')
        result = self.send('gigachat_2', body=body)
        self.assertEqual(result['state'], 'SUCCEEDED', result)
        self.assertEqual(result['response_model'], self.model)
        self.assertEqual(json.loads(self.posts()[0][2])['max_tokens'], 32)
        self.assertLessEqual(len(self.posts()[0][2]), 1024)
        self.assertEqual(self.app.submit_turn(self.ws, self.cid, body), result)
        self.assertEqual(len(self.posts()), 1)
        self.send('gigachat_2', text='Second physical send denied')
        self.assertEqual(len(self.posts()), 1)
        self.session.check()
        self.session.close()
        with self.assertRaisesRegex(PreSendDenied, 'confirmed_version_requires_exact_pin'):
            ProviderSession.offline(self.workspace, self.wid,
                replace(self.session.approval, grant_id=uuid4().hex), self.transport)
        wrong_exact = replace(self.session.approval, grant_id=uuid4().hex,
            contracts=(replace(contract, response_models=('GigaChat-2:2.0.99.99',), version_mode='EXACT'),))
        with self.assertRaisesRegex(PreSendDenied, 'confirmed_version_requires_exact_pin'):
            ProviderSession.offline(self.workspace, self.wid, wrong_exact, self.transport)
        exact = replace(self.session.approval, grant_id=uuid4().hex,
            contracts=(replace(contract, response_models=(self.model,), version_mode='EXACT'),))
        followup = ProviderSession.offline(self.workspace, self.wid, exact, self.transport)
        self.addCleanup(followup.close)
        self.assertEqual(followup._confirmed_versions['gigachat_2'], self.model)

    def test_first_lite_rejects_other_family_and_bad_suffix_with_usage_no_replay(self):
        for wrong in ('GigaChat-2-Pro:2.0.30.01', 'GigaChat-2:2.0.30.01-extra'):
            with self.subTest(wrong=wrong):
                self.first_lite_session()
                self.calls.clear()  # the fixture handler compares this grant's physical count
                self.model = wrong
                self.discover()
                body = self.body('Reject version', 'gigachat_2')
                result = self.send('gigachat_2', body=body)
                self.assertNotEqual(result['state'], 'SUCCEEDED')
                self.assertEqual(result['usage']['total_tokens'], 12, result)
                before = len(self.posts())
                self.assertEqual(self.app.submit_turn(self.ws, self.cid, body), result)
                self.assertEqual(len(self.posts()), before)
                self.assertNotIn('gigachat_2', self.session._confirmed_versions)
                self.assertTrue(all(m.get('role') != 'assistant'
                    for m in self.app.messages(self.ws, self.cid, None, 50)['messages']))

    def test_first_lite_bounds_stop_before_physical_post(self):
        self.first_lite_session()
        self.discover()
        try:
            self.send('gigachat_2', text='x'*2000)
        except (PreSendDenied, UltraChatError):
            pass
        self.assertEqual(self.posts(), [])
        self.session.close()
        too_broad = replace(self.session.approval, grant_id=uuid4().hex, max_answer_tokens=33)
        with self.assertRaisesRegex(PreSendDenied, 'first_version_discovery_envelope_invalid'):
            ProviderSession.offline(self.workspace, self.wid, too_broad, self.transport)
        with self.assertRaisesRegex(PreSendDenied, 'provider_contract_invalid'):
            replace(self.session.approval.contracts[0], provider_output_cap_tokens=16).validate()

    def test_first_lite_http_turn_reopen_reads_without_second_post(self):
        from web_alarm.server import WebAlarmApi, create_server
        import threading
        self.first_lite_session()
        self.model = 'GigaChat-2:2.0.30.01'
        self.discover()
        api = WebAlarmApi(self.root/'registry')
        factory = OrdinaryProviderFactory.for_session(api.registry, self.session)
        server = create_server(api, host='127.0.0.1', port=0, ordinary_factory=factory)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.http = lambda *args, **kwargs: s5.HttpAndTkTests.http(self, *args, **kwargs)
        _cap, read, write = s5.HttpAndTkTests.tokens(self, server)
        base = f'/ultra/chat/workspaces/{self.ws}/chats/{self.cid}'
        self.app.chat_model(self.ws, self.cid, {'model_ref':'gigachat_2'})
        body = self.body('Ответь одним словом: готово', 'gigachat_2')
        status, result = s5.HttpAndTkTests.http(self, server, 'POST', base+'/turns', body, write)
        self.assertEqual((status, result['state']), (200, 'SUCCEEDED'))
        self.assertEqual(result['response_model'], self.model)
        self.assertEqual(s5.HttpAndTkTests.http(self, server, 'GET', '/', headers={})[0], 200)
        self.assertEqual(s5.HttpAndTkTests.http(self, server, 'GET', base+'/messages?limit=50',
            headers=read)[0], 200)
        self.assertEqual(len(self.posts()), 1)

    def test_first_lite_pin_failure_is_unknown_and_never_resends(self):
        self.first_lite_session()
        self.model = 'GigaChat-2:2.0.30.01'
        self.discover()
        body = self.body('Pin failure', 'gigachat_2')
        with patch.object(self.session, 'pin_discovered_version', side_effect=OSError('synthetic pin error')):
            result = self.send('gigachat_2', body=body)
        self.assertEqual(result['state'], 'UNKNOWN')
        self.assertEqual(len(self.posts()), 1)
        self.assertEqual(self.app.submit_turn(self.ws, self.cid, body), result)
        self.assertEqual(len(self.posts()), 1)


if __name__ == '__main__':
    unittest.main()
