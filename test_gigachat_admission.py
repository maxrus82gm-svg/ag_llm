"""H34 common server admission, seven-site safety and synthetic fixture helpers."""
import asyncio
import ast
from contextlib import contextmanager
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

import httpx
import context_storage as core
import run_store as runs
import gigachat_admission as admission
import gigachat_transport as oauth
import ordinary_gigachat_transport as http_transport
import ultra_budget_policy as policy
from ultra_budget_ledger import BudgetLedger, LedgerDenied
from web_alarm.ordinary_chat_bridge import offline_policy
from ordinary_chat_service import PreSendDenied, PreSendUncertain

BODY={'model':'GigaChat-2-Pro','messages':[{'role':'user','content':'synthetic 🌍'}],
      'max_tokens':128,'stream':False}
REPLY={'choices':[{'message':{'role':'assistant','content':'ok'},'finish_reason':'stop'}],
       'usage':{'prompt_tokens':7,'completion_tokens':5,'total_tokens':12}}

LEGACY_SITES={'server.py':{'ask_gigachat':'mcp_chat','_run_agent_task_impl':'executor','_request_audit_diagnostic':'audit_diagnostic'},
              'planner_runtime.py':{'call':'planner_session','run_planner':'planner_direct'},
              'verifier_runtime.py':{'_request_gigachat':'_route'},'compressor_runtime.py':{'_request_gigachat':'compressor'}}

def legacy_contract_issues(sources):
    issues=[]
    for module,expected in LEGACY_SITES.items():
        tree=ast.parse(sources[module])
        for name,route in expected.items():
            function=next(n for n in ast.walk(tree) if isinstance(n,ast.AsyncFunctionDef) and n.name==name)
            calls=[n for n in ast.walk(function) if isinstance(n,ast.Call)]
            factories=[n for n in calls if isinstance(n.func,ast.Name) and n.func.id=='guarded_client']
            valid=len(factories)==1 and bool(factories[0].args)
            if valid:
                arg=factories[0].args[0]
                valid=(isinstance(arg,ast.Name) and arg.id=='_route') if route=='_route' else (isinstance(arg,ast.Constant) and arg.value==route)
            if not valid:issues.append((module,name,'unguarded_or_wrong_route_factory'))
            if any((isinstance(n.func,ast.Attribute) and n.func.attr in {'AsyncClient','Client'})
                   or (isinstance(n.func,ast.Name) and n.func.id=='get_access_token') for n in calls):
                issues.append((module,name,'raw_http_or_oauth'))
    return issues


def synthetic_policy():
    raw=offline_policy();raw['revision_label']='H34 SYNTHETIC OFFLINE ONLY'
    raw['run'].update(max_request_bytes=2_000_000,max_request_input_tokens_est=2_000_000,
        max_verification_request_bytes=2_000_000,max_verification_request_input_tokens_est=2_000_000,
        max_run_liability_tokens=50_000_000,max_run_attempts=100)
    for scope in ('compressor','mcp'):
        raw[scope]=dict(mode='BUDGET',max_request_bytes=2_000_000,max_request_input_tokens_est=2_000_000,
                       max_scope_liability_tokens=50_000_000,max_scope_attempts=100)
    return raw


@contextmanager
def synthetic_owner(*,root=None,run_id='h34_run',fixture=None,raw=None,profiles=None):
    with tempfile.TemporaryDirectory(prefix='h34_owner_') as directory:
        location=Path(directory) if root is None else Path(root)
        location.mkdir(parents=True,exist_ok=True)
        wid=core.ensure_workspace_storage(location)['workspace_id']
        ledger=BudgetLedger(location,wid);ledger.initialize()  # explicit fresh fixture provisioning
        if run_id is not None:runs.create_run_summary(location,wid,None,'h34_task',run_id)
        fixture=fixture or http_transport.OfflineHTTPFixture(body=json.dumps(REPLY).encode())
        with admission.offline_server_owner(location,wid,synthetic_policy() if raw is None else raw,fixture,
                                             run_id=run_id,profiles=profiles) as owner:
            yield owner


@contextmanager
def capture_owner(capture):
    """S1 explicit fixture authority, not installed in production or by config."""
    root=getattr(capture,'workspace',None)
    with synthetic_owner(root=root,run_id=None if root is not None else 'h34_s1_run') as owner:
        yield owner


class ServerAdmissionTests(unittest.IsolatedAsyncioTestCase):
    async def send(self,owner,route='executor',*,body=None,attempt='pa_h34',timeout=8):
        from provider_accounting import build_provider_attempt_started
        payload=BODY if body is None else body
        model=next(m for m in admission.MODEL_REGISTRY.values() if m.provider_model_id==payload['model'])
        started=build_provider_attempt_started(role=policy.ROUTES[route].role,mode='H34',provider='gigachat',
            model_id=model.model_id,provider_model_id=model.provider_model_id,body=payload,blocks=[],
            provider_attempt_id=attempt,logical_call_id='logical:'+attempt)
        async with admission.guarded_client(route,timeout=timeout) as client:
            return await client.post(oauth.CHAT_URL,json=payload,attempt=started)

    async def test_all_routes_exact_wire_sent_and_terminal_readback(self):
        trace=[]
        for route in sorted(admission._ROUTES):
            with self.subTest(route=route),synthetic_owner() as owner:
                original=httpx.MockTransport.handle_async_request
                async def capture(mock,request):
                    proof,envelope=owner.ledger.reservation('pa_h34')
                    self.assertEqual(proof.record.state,policy.SENT)
                    self.assertEqual(envelope['wire_utf8'].encode(),request.content)
                    self.assertEqual(envelope['route_id'],route)
                    self.assertEqual(envelope['binding']['run_id'],owner.run_id)
                    self.assertEqual(request.content,policy.serialize_request_body(BODY))
                    return await original(mock,request)
                with patch.object(httpx.MockTransport,'handle_async_request',capture):
                    response=await self.send(owner,route)
                self.assertEqual(response.json(),REPLY);self.assertEqual(len(owner.fixture.requests),1)
                record=owner.ledger.recover().attempts[0]
                self.assertEqual(record.state,policy.KNOWN_TERMINAL)
                self.assertEqual(record.terminal_outcomes,('completed',))
                self.assertIsNone(owner.inflight)
                trace.append(dict(route=route,workspace_id=owner.workspace_id,run_id=owner.run_id,
                    attempt=record.attempt_id,policy_sha256=owner.policy_hash,model=BODY['model'],
                    terminal_state=record.state,**owner.fixture.requests[0]))
        if os.environ.get('H34_TRACE'):
            Path(os.environ['H34_TRACE']).write_text(json.dumps(dict(real_enabled=False,routes=trace,
                token_kind='synthetic only',physical_POST_count=len(trace)),indent=2),encoding='utf-8')

    async def test_seven_real_call_sites_without_owner_are_zero_http_oauth(self):
        import server, planner_runtime, verifier_runtime, compressor_runtime, agent_global_context
        agent_global_context.save_agent_global_context('H34 SYNTHETIC GLOBAL CONTEXT','ultra')
        with tempfile.TemporaryDirectory(prefix='h34_unowned_') as directory:
            root=Path(directory)
            calls=[('mcp',lambda:server.ask_gigachat('synthetic')),
                ('executor',lambda:server.run_agent_task('synthetic',str(root),planner_enabled=False,final_audit_enabled=False,
                    permissions=dict(allow_read=True,allow_write=False,allow_delete=False,allow_verify=False,allow_guard_p1=True,
                        read_scope='.',write_scope='.',delete_scope='.',tool_limit=1,auto_backup=True))),
                ('audit',lambda:server._request_audit_diagnostic(object(),{},'GigaChat-2-Pro',[],'candidate','why')),
                ('planner_session',lambda:planner_runtime.PlannerSession(raw_task='synthetic').call(mode='INITIAL',raw_task='synthetic',context={})),
                ('planner_direct',lambda:planner_runtime.run_planner(mode='INITIAL',raw_task='synthetic',context={})),
                ('verifier',lambda:verifier_runtime._request_gigachat(BODY)),
                ('compressor',lambda:compressor_runtime._request_gigachat(BODY))]
            with patch.object(httpx,'AsyncClient',side_effect=AssertionError('HTTP factory reached')) as client:
                for name,call in calls:
                    with self.subTest(site=name):
                        with self.assertRaises(Exception) as denied:await call()
                        chain=[];error=denied.exception
                        while error is not None:
                            chain.append(str(error));error=error.__cause__
                        self.assertTrue(any(code in message for message in chain
                            for code in ('real_oauth_disabled','server_admission_required')),chain)
                client.assert_not_called()

    async def test_all_seven_sources_have_guarded_factories_and_no_direct_oauth(self):
        root=Path(__file__).resolve().parent
        sources={n:(root/n).read_text() for n in LEGACY_SITES}
        self.assertEqual(legacy_contract_issues(sources),[])
        changed=dict(sources);changed['server.py']=changed['server.py'].replace(
            "guarded_client('mcp_chat', timeout=180.0)","httpx.AsyncClient(timeout=180.0)",1)
        self.assertTrue(legacy_contract_issues(changed))

    async def test_fresh_process_cannot_replace_durable_owner_after_sent(self):
        import subprocess,sys
        class PowerLoss(BaseException):pass
        with synthetic_owner() as owner:
            original=BudgetLedger.mark_sent
            def crash(ledger,attempt):original(ledger,attempt);raise PowerLoss()
            with patch.object(BudgetLedger,'mark_sent',crash):
                with self.assertRaises(PowerLoss):await self.send(owner)
            code='''import sys
from gigachat_admission import offline_server_owner
from ordinary_gigachat_transport import OfflineHTTPFixture
from ordinary_chat_service import PreSendDenied
from test_gigachat_admission import synthetic_policy
try:
    with offline_server_owner(sys.argv[1],sys.argv[2],synthetic_policy(),OfflineHTTPFixture(),run_id=sys.argv[3]):
        raise AssertionError('second process obtained owner')
except PreSendDenied:
    print('DENIED / SENT retained')
'''
            result=await asyncio.to_thread(subprocess.run,[sys.executable,'-B','-c',code,str(owner.root),owner.workspace_id,owner.run_id],capture_output=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'))
            self.assertIn(b'DENIED',result.stdout)
            self.assertEqual(owner.ledger.recover().attempts[0].state,policy.SENT)

    async def test_no_authority_or_forged_context_zero_http_token(self):
        for fake in (None,{},True,object()):
            token=admission._OWNER.set(fake)
            try:
                with self.assertRaises(PreSendDenied):admission.guarded_client('executor',timeout=2)
                with self.assertRaises(PreSendDenied):await admission.offline_access_token()
                with self.assertRaises(PreSendDenied):await oauth.get_access_token()
            finally:admission._OWNER.reset(token)

    async def test_unknown_profiles_caps_endpoint_model_zero_http(self):
        for mode in ('unknown','caps','endpoint','model','real_kind'):
            with self.subTest(mode=mode):
                profiles=admission.synthetic_profiles();p=next(p for p in profiles if p.model_id=='gigachat_2_pro')
                p=replace(p,**{'unknown':{'context_tokens':None},'caps':{'output_tokens':1},
                    'endpoint':{'endpoint':'https://invalid.example'},'model':{'provider_model_id':'Unknown'},
                    'real_kind':{'kind':'VERIFIED_REAL'}}[mode])
                profiles=tuple(p if q.model_id==p.model_id else q for q in profiles)
                with synthetic_owner(profiles=profiles) as owner:
                    with self.assertRaises(PreSendDenied):await self.send(owner)
                    self.assertEqual(owner.fixture.requests,[]);self.assertEqual(owner.fixture.token_calls,0)

    async def test_model_snapshot_substitution_before_admission_is_denied(self):
        from provider_accounting import build_provider_attempt_started
        with synthetic_owner() as owner:
            body=json.loads(json.dumps(BODY))
            started=build_provider_attempt_started(role='executor',mode='H34',provider='gigachat',
                model_id='gigachat_2_pro',provider_model_id=body['model'],body=body,blocks=[])
            body['model']='GigaChat-2-Max'
            with self.assertRaises(PreSendDenied):
                await admission.guarded_client('executor',timeout=2).post(oauth.CHAT_URL,json=body,attempt=started)
            self.assertEqual(owner.fixture.requests,[]);self.assertEqual(owner.fixture.token_calls,0)

    async def test_external_cancel_suppressed_by_token_provider_is_zero_http(self):
        with synthetic_owner() as owner:
            entered=asyncio.Event();release=asyncio.Event();original=http_transport.OfflineHTTPFixture.token
            async def token(fixture):
                entered.set()
                try:await release.wait()
                except asyncio.CancelledError:asyncio.current_task().uncancel()
                return await original(fixture)
            with patch.object(http_transport.OfflineHTTPFixture,'token',token):
                pending=asyncio.create_task(self.send(owner))
                await entered.wait();pending.cancel()
                with self.assertRaises(PreSendUncertain):await pending
            self.assertEqual(owner.fixture.requests,[])
            self.assertGreater(owner.ledger.recover().attempts[0].liability_tokens,0)

    async def test_budget_deny_missing_corrupt_upgrade_ledger_zero_http(self):
        for mode in ('deny','missing','corrupt','upgrade'):
            with self.subTest(mode=mode),synthetic_owner() as owner:
                if mode=='deny':
                    owner.raw_policy['run']['max_run_liability_tokens']=1
                    # A policy substitution is itself denied, before admission.
                marker=owner.root/'.ultra/audit/budget.enrollment.json'
                if mode=='missing':marker.unlink()
                if mode=='corrupt':marker.write_text('{}')
                if mode=='upgrade':
                    data=json.loads(marker.read_text());data['policy_engine_sha256']='0'*64;marker.write_text(json.dumps(data))
                with self.assertRaises((PreSendDenied,LedgerDenied)):await self.send(owner)
                self.assertEqual(owner.fixture.requests,[]);self.assertEqual(owner.fixture.token_calls,0)

    async def test_s2_real_denial_zero_http(self):
        raw=synthetic_policy();raw['run']['max_request_bytes']=1
        with synthetic_owner(raw=raw) as owner:
            with self.assertRaises(PreSendDenied):await self.send(owner)
            self.assertEqual(owner.fixture.requests,[]);self.assertEqual(owner.fixture.token_calls,0)
            self.assertEqual(owner.ledger.recover().attempts,())

    async def test_replay_same_attempt_cannot_post_again(self):
        with synthetic_owner() as owner:
            await self.send(owner)
            with self.assertRaises(PreSendDenied):await self.send(owner)
            self.assertEqual(len(owner.fixture.requests),1)
            self.assertEqual(len(owner.ledger.recover().attempts),1)

    async def test_injected_client_wrong_endpoint_and_direct_transport_denied(self):
        with synthetic_owner() as owner:
            with self.assertRaises(PreSendDenied):admission.guarded_client('audit_diagnostic',timeout=2,parent=object())
            client=admission.guarded_client('executor',timeout=2)
            with self.assertRaises(PreSendDenied):await client.post('https://invalid.example',json=BODY)
            transport=http_transport.GigaChatTransport(owner.fixture)
            with self.assertRaises(PreSendDenied):await transport.send_bytes(b'{}',timeout_seconds=2,max_response_bytes=8192,admission={})
            self.assertEqual(owner.fixture.token_calls,0)

    async def test_cancel_before_reserve_and_after_reserve_zero_http(self):
        for point in ('before','reserved'):
            with self.subTest(point=point),synthetic_owner() as owner:
                original=BudgetLedger.reserve
                def reserve(ledger,*args):
                    receipt=original(ledger,*args);owner.cancel();return receipt
                if point=='before':owner.cancel()
                with patch.object(BudgetLedger,'reserve',reserve) if point=='reserved' else patch.object(owner.fixture,'delay',0):
                    with self.assertRaises(PreSendDenied):await self.send(owner)
                self.assertEqual(owner.fixture.requests,[])
                if point=='reserved':self.assertGreater(owner.ledger.recover().attempts[0].liability_tokens,0)

    async def test_cancel_after_sent_in_token_boundary_zero_http(self):
        with synthetic_owner() as owner:
            original=http_transport.OfflineHTTPFixture.token
            async def token(fixture):
                value=await original(fixture);owner.cancel();return value
            with patch.object(http_transport.OfflineHTTPFixture,'token',token):
                with self.assertRaises(PreSendUncertain):await self.send(owner)
            self.assertEqual(owner.fixture.requests,[])
            self.assertGreater(owner.ledger.recover().attempts[0].liability_tokens,0)

    async def test_post_admission_wire_substitution_is_blocked(self):
        with synthetic_owner() as owner:
            original=httpx.MockTransport.handle_async_request
            async def change(mock,request):
                request._content=request.content+b' ';return await original(mock,request)
            with patch.object(httpx.MockTransport,'handle_async_request',change):
                with self.assertRaises(PreSendUncertain):await self.send(owner)
            self.assertEqual(owner.fixture.requests,[])
            self.assertGreater(owner.ledger.recover().attempts[0].liability_tokens,0)

    async def test_terminal_commit_failure_cannot_publish_response(self):
        with synthetic_owner() as owner:
            with patch.object(BudgetLedger,'terminal',side_effect=OSError('synthetic')):
                with self.assertRaises(OSError):await self.send(owner)
            self.assertEqual(len(owner.fixture.requests),1)
            self.assertEqual(owner.ledger.recover().attempts[0].state,policy.SENT)
            with self.assertRaises(PreSendDenied):await self.send(owner,attempt='pa_next')

    async def test_timeout_and_transport_error_do_not_zero_or_retry(self):
        for mode in ('timeout','transport'):
            with self.subTest(mode=mode),synthetic_owner() as owner:
                owner.fixture.error=mode
                with self.assertRaises(httpx.HTTPError):await self.send(owner)
                self.assertEqual(len(owner.fixture.requests),1)
                self.assertEqual(owner.ledger.recover().attempts[0].state,policy.UNKNOWN_TERMINAL)
                self.assertGreater(owner.ledger.recover().attempts[0].liability_tokens,0)
                with self.assertRaises(PreSendDenied):await self.send(owner,attempt='pa_next')

    async def test_late_response_after_suppressed_cancellation_is_discarded(self):
        with synthetic_owner() as owner:
            original=httpx.MockTransport.handle_async_request
            async def late(mock,request):
                response=await original(mock,request)
                try:await asyncio.sleep(3)
                except asyncio.CancelledError:pass
                return response
            with patch.object(httpx.MockTransport,'handle_async_request',late):
                with self.assertRaises(httpx.ReadTimeout):await self.send(owner,timeout=2)
            record=owner.ledger.recover().attempts[0]
            self.assertGreater(record.liability_tokens,0)
            self.assertEqual(record.terminal_outcomes,('timeout',))

    async def test_concurrent_requests_and_second_owner_fail_closed(self):
        with synthetic_owner() as owner:
            entered=asyncio.Event();release=asyncio.Event();original=http_transport.OfflineHTTPFixture.token
            async def token(fixture):
                entered.set();await release.wait();return await original(fixture)
            with patch.object(http_transport.OfflineHTTPFixture,'token',token):
                pending=asyncio.create_task(self.send(owner))
                await entered.wait()
                try:
                    with self.assertRaises(PreSendDenied):await self.send(owner,attempt='pa_other')
                    with self.assertRaises(PreSendDenied):
                        with admission.offline_server_owner(owner.root,owner.workspace_id,owner.raw_policy,owner.fixture,run_id=owner.run_id):pass
                finally:release.set()
                await pending
            self.assertEqual(len(owner.fixture.requests),1)

    async def test_oauth_cache_and_env_cannot_grant_real(self):
        with patch.object(oauth,'_access_token','SYNTHETIC-CACHED'),patch.object(oauth,'_access_token_valid_until',float('inf')):
            with patch.object(oauth.os,'getenv',side_effect=AssertionError('credential read')),patch.object(oauth.httpx,'AsyncClient',side_effect=AssertionError('HTTP')):
                with self.assertRaises(PreSendDenied):await oauth.get_access_token()
        with self.assertRaises(PreSendDenied):admission.require_real_authority()

    async def test_provider_envelope_repr_hides_raw_secret_fields(self):
        from ordinary_chat_service import ProviderResponse
        secret='SYNTHETIC-SECRET-DO-NOT-LOG'
        self.assertNotIn(secret,repr(ProviderResponse(200,{'access_token':secret})))

    async def test_legacy_protocol_errors_do_not_echo_raw_provider_fields(self):
        import server,compressor_runtime,verifier_runtime
        secret='SYNTHETIC-SECRET-DO-NOT-LOG'
        calls=[lambda:server.ask_gigachat('synthetic'),
               lambda:compressor_runtime._request_gigachat(BODY,model_id='gigachat_2_pro'),
               lambda:verifier_runtime._request_gigachat(BODY)]
        for call in calls:
            with self.subTest(site=call),synthetic_owner() as owner:
                owner.fixture.body=json.dumps({'access_token':secret,'untrusted_field':secret}).encode()
                with self.assertRaises(Exception) as error:await call()
                self.assertNotIn(secret,str(error.exception))

    async def test_legacy_success_status_preserves_httpx_contract(self):
        with synthetic_owner() as owner:
            owner.fixture.status=201
            response=await self.send(owner)
            response.raise_for_status()
            self.assertEqual(owner.ledger.recover().attempts[0].terminal_outcomes,('completed',))

    async def test_durable_second_owner_and_reopen_after_sent_denied(self):
        class PowerLoss(BaseException):pass
        with synthetic_owner() as owner:
            original=BudgetLedger.mark_sent
            def crash(ledger,attempt):original(ledger,attempt);raise PowerLoss()
            with patch.object(BudgetLedger,'mark_sent',crash):
                with self.assertRaises(PowerLoss):await self.send(owner)
            self.assertEqual(owner.ledger.recover().attempts[0].state,policy.SENT)
            self.assertEqual(owner.fixture.requests,[])
            token=admission._OWNER.set(None)  # simulate independent process context; durable owner still ACTIVE
            try:
                with self.assertRaises(PreSendDenied):
                    with admission.offline_server_owner(owner.root,owner.workspace_id,owner.raw_policy,owner.fixture,run_id=owner.run_id):pass
            finally:admission._OWNER.reset(token)
            self.assertGreater(owner.ledger.recover().attempts[0].liability_tokens,0)

    async def test_clean_reopen_can_read_but_cannot_replay_old_attempt(self):
        with tempfile.TemporaryDirectory(prefix='h34_reopen_') as directory:
            root=Path(directory);fixture=http_transport.OfflineHTTPFixture(body=json.dumps(REPLY).encode())
            with synthetic_owner(root=root,fixture=fixture) as owner:
                wid=owner.workspace_id;raw=owner.raw_policy;await self.send(owner)
            with admission.offline_server_owner(root,wid,raw,fixture,run_id='h34_run') as reopened:
                with self.assertRaises(PreSendDenied):await self.send(reopened)
            self.assertEqual(len(fixture.requests),1)

    async def test_corrupt_or_old_closed_owner_is_not_silently_adopted(self):
        for mode in ('version','run','chat','missing','inflight'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory(prefix='h34_old_owner_') as folder:
                root=Path(folder);fixture=http_transport.OfflineHTTPFixture(body=json.dumps(REPLY).encode())
                with synthetic_owner(root=root,fixture=fixture) as owner:
                    wid=owner.workspace_id;raw=owner.raw_policy;await self.send(owner)
                summary=runs.load_run_summary(root,'h34_run');saved=summary['s3b_owner']
                if mode=='version':saved['version']='OLD'
                if mode=='run':saved['run_id']='different_run'
                if mode=='chat':saved['chat_id']='different_chat'
                if mode=='missing':del saved['owner_id']
                if mode=='inflight':saved['inflight']='unresolved_attempt'
                runs.update_run_summary_index(root,'h34_run',{'s3b_owner':saved})
                with self.assertRaises(PreSendDenied):
                    with admission.offline_server_owner(root,wid,raw,fixture,run_id='h34_run'):pass
                self.assertEqual(len(fixture.requests),1)

    async def test_forged_reserve_and_sent_ack_zero_http(self):
        for mode in ('replay','wrong_wire','sent_ack'):
            with self.subTest(mode=mode),synthetic_owner() as owner:
                reserve=BudgetLedger.reserve;mark=BudgetLedger.mark_sent
                def changed(ledger,attempt,raw,route,wire,context,binding):
                    if mode=='wrong_wire':wire=policy.serialize_request_body({**json.loads(wire),'max_tokens':1})
                    receipt=reserve(ledger,attempt,raw,route,wire,context,binding)
                    return replace(receipt,replayed=True) if mode=='replay' else receipt
                def sent_ack(ledger,attempt):
                    receipt,_=ledger.reservation(attempt)
                    return replace(receipt,record=policy.mark_sent(receipt.record),replayed=False)
                with patch.object(BudgetLedger,'reserve',changed),patch.object(BudgetLedger,'mark_sent',sent_ack if mode=='sent_ack' else mark):
                    with self.assertRaises((PreSendDenied,PreSendUncertain)):await self.send(owner)
                self.assertEqual(owner.fixture.requests,[]);self.assertEqual(owner.fixture.token_calls,0)
                self.assertGreater(owner.ledger.recover().attempts[0].liability_tokens,0)

    async def test_owner_policy_profile_endpoint_tamper_after_sent_zero_http(self):
        for mode in ('policy','profile','endpoint','owner'):
            with self.subTest(mode=mode),synthetic_owner() as owner:
                mark=BudgetLedger.mark_sent;patches=[]
                def changed(ledger,attempt):
                    receipt=mark(ledger,attempt)
                    if mode=='policy':owner.raw_policy['revision_label']='CHANGED'
                    if mode=='profile':owner.profiles=()
                    if mode=='endpoint':
                        p=patch.object(http_transport,'CHAT_URL','https://invalid.example');p.start();patches.append(p)
                    if mode=='owner':runs.update_run_summary_index(owner.root,owner.run_id,{'s3b_owner':{}})
                    return receipt
                try:
                    with patch.object(BudgetLedger,'mark_sent',changed):
                        with self.assertRaises(PreSendUncertain):await self.send(owner)
                finally:
                    for p in patches:p.stop()
                self.assertEqual(owner.fixture.requests,[]);self.assertEqual(owner.fixture.token_calls,0)
                self.assertGreater(owner.ledger.recover().attempts[0].liability_tokens,0)

    async def test_capacity_failure_preserves_reserved_liability_zero_http(self):
        import ultra_budget_ledger as ledger_module
        with synthetic_owner() as owner,patch.object(ledger_module,'MAX_EVENTS',1):
            with self.assertRaises(PreSendUncertain):await self.send(owner)
            self.assertEqual(owner.fixture.requests,[])
            self.assertGreater(owner.ledger.recover().attempts[0].liability_tokens,0)

    async def test_terminal_fake_ack_and_owner_tamper_cannot_publish(self):
        for mode in ('ack','owner'):
            with self.subTest(mode=mode),synthetic_owner() as owner:
                original=httpx.MockTransport.handle_async_request
                async def response(mock,request):
                    reply=await original(mock,request)
                    if mode=='owner':runs.update_run_summary_index(owner.root,owner.run_id,{'s3b_owner':{}})
                    return reply
                def fake(ledger,attempt,outcome,usage):
                    receipt,_=ledger.reservation(attempt)
                    return replace(receipt,record=policy.apply_terminal(receipt.record,outcome,usage))
                with patch.object(httpx.MockTransport,'handle_async_request',response),patch.object(BudgetLedger,'terminal',fake) if mode=='ack' else patch.object(owner.fixture,'delay',0):
                    with self.assertRaises(PreSendUncertain):await self.send(owner)
                self.assertEqual(len(owner.fixture.requests),1)
                self.assertEqual(owner.ledger.recover().attempts[0].state,policy.SENT)

    async def test_unknown_usage_keeps_liability_and_error_status_never_retries(self):
        for status,body in ((200,{'choices':REPLY['choices']}),(401,{'error':'SYNTHETIC-SECRET'}),(200,{'usage':{'prompt_tokens':True}})):
            with self.subTest(status=status),synthetic_owner() as owner:
                owner.fixture.status=status;owner.fixture.body=json.dumps(body).encode()
                response=await self.send(owner)
                self.assertEqual(response.status_code,status)
                self.assertGreater(owner.ledger.recover().attempts[0].liability_tokens,0)
                self.assertEqual(len(owner.fixture.requests),1)


if __name__=='__main__':unittest.main()
