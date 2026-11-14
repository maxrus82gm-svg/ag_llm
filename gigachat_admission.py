"""H34 server-owned S3b adapter for legacy GigaChat call sites.

One existing S2/S3a ledger, Run Store and H33 HTTP boundary. Only explicit TEMP
owners with exact synthetic profiles/fixtures exist; REAL has no factory/switch.
Capabilities are private process objects, never browser/config/receipt inputs.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
import asyncio
import hashlib
import json as json_codec
import math
from pathlib import Path
import tempfile
import uuid

import httpx
import context_storage as core
import run_store as runs
import ultra_budget_policy as policy
from ultra_budget_ledger import BudgetLedger, Receipt
from gigachat_transport import CHAT_URL
from model_registry import MODEL_REGISTRY, get_model_spec
from ordinary_chat_service import PreSendDenied, PreSendUncertain, _usage
from provider_accounting import canonical_json_text

_OWNER = ContextVar('gigachat_server_owner', default=None)
_ROUTES = frozenset({'mcp_chat','executor','audit_diagnostic','planner_session',
                     'planner_direct','verifier_final','verifier_permission','planner_review','compressor'})
_VERSION = 'H34-OFFLINE-ONLY-v1'


def _digest(value):
    return hashlib.sha256(json_codec.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class ProviderProfile:
    model_id: str
    provider_model_id: str
    endpoint: str
    context_tokens: int | None
    output_tokens: int | None
    evidence: str
    kind: str = 'UNVERIFIED'


def synthetic_profiles():
    # Fixture bounds, NOT real provider capabilities or H29 preferences.
    return tuple(ProviderProfile(m.model_id,m.provider_model_id,CHAT_URL,2_000_000,65536,
                                 'H34 synthetic fixture only','SYNTHETIC')
                 for m in MODEL_REGISTRY.values() if m.enabled and m.provider=='gigachat' and not m.is_local)


def require_real_authority():
    """No cached token, env, receipt, Boolean or verified-looking profile enables REAL."""
    raise PreSendDenied('real_provider_authority_unavailable')


class _ServerOwner:
    def __init__(self, root, workspace_id, raw_policy, fixture, profiles, *, run_id=None, chat_id=None, turn_id=None):
        from ordinary_gigachat_transport import OfflineHTTPFixture
        self.root=Path(root).absolute()
        if (type(fixture) is not OfflineHTTPFixture or Path(tempfile.gettempdir()).resolve() not in self.root.parents
                or self.root.resolve()!=self.root or _OWNER.get() is not None):
            raise PreSendDenied('explicit_offline_server_owner_required')
        self.workspace_id=workspace_id
        self.raw_policy=json_codec.loads(json_codec.dumps(raw_policy,allow_nan=False))
        self.policy_hash=policy.validate_policy(self.raw_policy).revision_sha256
        self.fixture=fixture
        self.profiles=tuple(profiles)
        self.profile_hash=_digest([vars(p) for p in self.profiles])
        if turn_id is not None:
            raise PreSendDenied('turn_requires_existing_turn_service_admission')
        self.run_id=None;self.chat_id=chat_id;self.turn_id=turn_id;self.final_audit_enabled=False
        self.owner_id='owner_'+uuid.uuid4().hex
        self.active=True;self.cancelled=False;self.inflight=None
        self.ledger=BudgetLedger(self.root,workspace_id)
        self.ledger.recover()  # Never initialize/adopt/reset at send or owner entry.
        if run_id is not None:self.bind(self.root,run_id,chat_id)

    def _owner_record(self,state='ACTIVE'):
        return dict(version=_VERSION,owner_id=self.owner_id,state=state,policy_sha256=self.policy_hash,
                    profiles_sha256=self.profile_hash,workspace_id=self.workspace_id,
                    run_id=self.run_id,chat_id=self.chat_id,turn_id=self.turn_id,inflight=self.inflight,
                    final_audit_enabled=self.final_audit_enabled)

    def bind(self, root, run_id, chat_id=None):
        if Path(root).absolute()!=self.root or not self.active or self.cancelled:
            raise PreSendDenied('server_run_scope_changed')
        if self.run_id is not None:
            if self.run_id!=run_id or self.chat_id!=chat_id:raise PreSendDenied('server_run_binding_changed')
            return
        with core._existing_workspace_writer(self.root,self.workspace_id):
            summary=runs.load_run_summary(self.root,run_id,chat_id)
            if not summary or summary.get('workspace_id')!=self.workspace_id or summary.get('chat_id')!=chat_id:
                raise PreSendDenied('server_run_identity_unavailable')
            prior=summary.get('s3b_owner')
            if prior is not None and (type(prior) is not dict or prior.get('state')!='CLOSED'
                    or set(prior)!=set(self._owner_record()) or prior.get('version')!=_VERSION
                    or prior.get('workspace_id')!=self.workspace_id or prior.get('run_id')!=run_id
                    or prior.get('chat_id')!=chat_id or prior.get('turn_id') is not None
                    or prior.get('inflight') is not None or type(prior.get('owner_id')) is not str
                    or not prior['owner_id'].startswith('owner_') or len(prior['owner_id'])!=38
                    or prior.get('policy_sha256')!=self.policy_hash or prior.get('profiles_sha256')!=self.profile_hash
                    or prior.get('final_audit_enabled')!=self.final_audit_enabled):
                raise PreSendDenied('server_run_owner_unresolved')
            recovered=self.ledger.recover()
            for record in recovered.attempts:
                _,envelope=self.ledger.reservation(record.attempt_id)
                if envelope['binding']['run_id']==run_id and (record.state in (policy.RESERVED,policy.SENT)
                        or any(o in ('timeout','cancelled','transport_error') for o in record.terminal_outcomes)):
                    raise PreSendDenied('server_run_attempt_unresolved')
            self.run_id=run_id;self.chat_id=chat_id
            runs.update_run_summary_index(self.root,run_id,{'s3b_owner':self._owner_record()})
            self.check()

    def check(self):
        if not self.active or self.cancelled or self.run_id is None:
            raise PreSendDenied('server_owner_inactive')
        try:
            current_policy=policy.validate_policy(self.raw_policy).revision_sha256
            current_profiles=_digest([vars(p) for p in self.profiles])
        except Exception:raise PreSendDenied('server_policy_or_profile_invalid') from None
        if (current_policy!=self.policy_hash or current_profiles!=self.profile_hash):
            raise PreSendDenied('server_policy_or_profile_changed')
        summary=runs.load_run_summary(self.root,self.run_id,self.chat_id)
        if not summary or summary.get('s3b_owner')!=self._owner_record():
            raise PreSendDenied('server_owner_not_durable')
        self.ledger.recover()

    def profile(self, provider_model_id, wire):
        profiles=[p for p in self.profiles if type(p) is ProviderProfile and p.provider_model_id==provider_model_id]
        if len(profiles)!=1:raise PreSendDenied('provider_profile_unavailable')
        p=profiles[0];m=get_model_spec(p.model_id)
        body=json_codec.loads(wire)
        if (p.kind!='SYNTHETIC' or p.evidence!='H34 synthetic fixture only' or p.endpoint!=CHAT_URL
                or m.provider!='gigachat' or m.is_local or m.provider_model_id!=p.provider_model_id
                or type(p.context_tokens) is not int or p.context_tokens<=0
                or type(p.output_tokens) is not int or p.output_tokens<=0
                or type(body.get('max_tokens')) is not int or not 0<body['max_tokens']<=p.output_tokens
                or len(wire)+body['max_tokens']>p.context_tokens):
            raise PreSendDenied('provider_caps_unverified_or_exceeded')
        return p

    def cancel(self):
        with core._existing_workspace_writer(self.root,self.workspace_id):
            self.check();self.cancelled=True
            runs.update_run_summary_index(self.root,self.run_id,{'s3b_owner':self._owner_record('CANCELLED')})

    def close(self, *, failed=False):
        try:
            if self.run_id is not None:
                with core._existing_workspace_writer(self.root,self.workspace_id):
                    summary=runs.load_run_summary(self.root,self.run_id,self.chat_id)
                    if summary and summary.get('s3b_owner')==self._owner_record():
                        runs.update_run_summary_index(self.root,self.run_id,
                            {'s3b_owner':self._owner_record('UNRESOLVED' if failed else 'CLOSED')})
        finally:self.active=False


@contextmanager
def offline_server_owner(root, workspace_id, raw_policy, fixture, *, profiles=None, run_id=None, chat_id=None, turn_id=None):
    owner=_ServerOwner(root,workspace_id,raw_policy,fixture,
                       synthetic_profiles() if profiles is None else profiles,run_id=run_id,chat_id=chat_id,turn_id=turn_id)
    token=_OWNER.set(owner)
    try:
        yield owner
    except BaseException:
        owner.close(failed=True)
        raise
    else:owner.close()
    finally:_OWNER.reset(token)


def _require_owner(route):
    owner=_OWNER.get()
    if route not in _ROUTES or type(owner) is not _ServerOwner or not owner.active:
        raise PreSendDenied('server_admission_required')
    return owner


def bind_server_run(root, run_id, chat_id=None, *, final_audit_enabled=False):
    owner=_OWNER.get()
    if owner is not None:
        if type(owner) is not _ServerOwner:raise PreSendDenied('server_owner_forged')
        if type(final_audit_enabled) is not bool or owner.run_id is not None:
            raise PreSendDenied('server_effective_policy_binding_changed')
        owner.final_audit_enabled=final_audit_enabled
        owner.bind(root,run_id,chat_id)


async def offline_access_token():
    # Compatibility placeholder only. The actual synthetic token boundary is in
    # H33 AFTER reserve/SENT. No real OAuth function/cache/env is consulted here.
    owner=_OWNER.get()
    if type(owner) is not _ServerOwner or not owner.active or owner.cancelled:
        raise PreSendDenied('real_oauth_disabled')
    return 'H34-SYNTHETIC-NON-CREDENTIAL'


class _ServerAttempt:
    def __init__(self,owner,route,wire,attempt,logical,timeout):
        from ordinary_gigachat_transport import GigaChatTransport
        if type(owner) is not _ServerOwner or _OWNER.get() is not owner:
            raise PreSendDenied('server_attempt_owner_forged')
        owner.check();profile=owner.profile(json_codec.loads(wire).get('model'),wire)
        self.endpoint=profile.endpoint
        self.owner=owner;self.route=route;self.wire=wire;self.attempt=attempt
        self.timeout=timeout;self.response_limit=4*1024*1024
        self.deadline=asyncio.get_running_loop().time()+timeout
        self.parent_task=asyncio.current_task();self.parent_cancels=self.parent_task.cancelling()
        self.transport=GigaChatTransport(owner.fixture)
        self.used=False;self.dispatched=False;self.sent=False
        scope=owner.run_id if policy.ROUTES[route].scope==policy.SCOPE_RUN else 'scope:'+_digest([owner.run_id,route])
        self.context=policy.RunContext(scope,owner.final_audit_enabled if policy.ROUTES[route].scope==policy.SCOPE_RUN else False)
        binding=dict(run_id=owner.run_id,chat_id=owner.chat_id,turn_id=owner.turn_id,
            logical_call_id=logical+':'+_digest(dict(endpoint=profile.endpoint,profile=vars(profile),
                owner=owner._owner_record(),route=route,wire=hashlib.sha256(wire).hexdigest())))
        self.envelope=dict(policy=owner.raw_policy,route_id=route,wire_utf8=wire.decode(),
                           context=vars(self.context),binding=binding)

    def limits(self,timeout_seconds,max_response_bytes):
        if timeout_seconds!=self.timeout or max_response_bytes!=self.response_limit:
            raise PreSendDenied('transport_limits_changed')

    def authorize(self,wire,transport):
        if (self.used or wire!=self.wire or transport is not self.transport or _OWNER.get() is not self.owner
                or transport.endpoint!=self.endpoint):
            raise PreSendDenied('server_attempt_replayed_or_forged')
        self.used=True;marking=False
        try:
            with core._existing_workspace_writer(self.owner.root,self.owner.workspace_id):
                self.owner.check();self.owner.profile(json_codec.loads(wire)['model'],wire)
                if self.owner.inflight is not None:raise PreSendDenied('server_call_inflight')
                ledger=self.owner.ledger
                receipt=ledger.reserve(self.attempt,self.envelope['policy'],self.route,wire,self.context,self.envelope['binding'])
                proof,saved=ledger.reservation(self.attempt)
                if (type(receipt) is not Receipt or receipt.replayed or receipt.record.state!=policy.RESERVED
                        or proof.record!=receipt.record or proof.revision!=receipt.revision or saved!=self.envelope):
                    raise PreSendDenied('server_reserve_not_fresh')
                self.owner.check()
                self.owner.inflight=self.attempt
                runs.update_run_summary_index(self.owner.root,self.owner.run_id,{'s3b_owner':self.owner._owner_record()})
                self.owner.check();marking=True
                sent=ledger.mark_sent(self.attempt);proof,saved=ledger.reservation(self.attempt)
                if (type(sent) is not Receipt or sent.replayed or sent.record.state!=policy.SENT
                        or proof.record!=sent.record or proof.revision!=sent.revision or saved!=self.envelope):
                    raise PreSendUncertain('server_sent_unverified')
                self.sent=True;self.check(wire,transport)
        except PreSendDenied:raise
        except Exception:
            if marking:raise PreSendUncertain('server_sent_commit_uncertain') from None
            raise PreSendDenied('server_reserve_unavailable') from None

    def check(self,wire,transport,*,physical=False):
        try:
            with core._existing_workspace_writer(self.owner.root,self.owner.workspace_id):
                self.owner.check();self.owner.profile(json_codec.loads(wire)['model'],wire)
                receipt,saved=self.owner.ledger.reservation(self.attempt)
                if (not self.used or self.dispatched or wire!=self.wire or transport is not self.transport
                        or _OWNER.get() is not self.owner or self.owner.fixture is not transport._fixture
                        or transport.endpoint!=self.endpoint
                        or receipt.record.state!=policy.SENT or saved!=self.envelope
                        or asyncio.get_running_loop().time()>=self.deadline
                        or self.parent_task.cancelling()>self.parent_cancels):
                    raise ValueError('server_attempt_changed')
                if physical:self.dispatched=True
        except Exception:raise PreSendUncertain('physical_server_admission_unverified') from None

    def terminal(self,outcome,usage=None):
        with core._existing_workspace_writer(self.owner.root,self.owner.workspace_id):
            summary=runs.load_run_summary(self.owner.root,self.owner.run_id,self.owner.chat_id)
            if (not summary or summary.get('s3b_owner')!=self.owner._owner_record('CANCELLED' if self.owner.cancelled else 'ACTIVE')
                    or self.owner.inflight!=self.attempt):
                raise PreSendUncertain('terminal_owner_unverified')
            receipt,saved=self.owner.ledger.reservation(self.attempt)
            if receipt.record.state!=policy.SENT or saved!=self.envelope:
                raise PreSendUncertain('terminal_binding_unverified')
            expected=policy.apply_terminal(receipt.record,outcome,usage)
            terminal=self.owner.ledger.terminal(self.attempt,outcome,usage)
            proof,saved=self.owner.ledger.reservation(self.attempt)
            if (type(terminal) is not Receipt or terminal.record!=expected or proof.record!=expected
                    or proof.revision!=terminal.revision or saved!=self.envelope):
                raise PreSendUncertain('server_terminal_unverified')
            if outcome in ('completed','provider_error','parse_error') and not self.owner.cancelled:
                self.owner.inflight=None
                runs.update_run_summary_index(self.owner.root,self.owner.run_id,{'s3b_owner':self.owner._owner_record()})
                self.owner.check()


class _GuardedClient:
    def __init__(self,route,timeout,owner):
        if type(timeout) not in (int,float) or not math.isfinite(timeout) or not 0<timeout<=180:
            raise PreSendDenied('invalid_transport_timeout')
        self.route=route;self.timeout=float(timeout);self.owner=owner

    async def __aenter__(self):return self
    async def __aexit__(self,*args):return False

    async def post(self,url,*,json,headers=None,attempt=None):
        if (type(self) is not _GuardedClient or _require_owner(self.route) is not self.owner or url!=CHAT_URL):
            raise PreSendDenied('server_endpoint_or_client_invalid')
        wire=policy.serialize_request_body(json)
        metadata=attempt or {}
        if type(metadata) is not dict:raise PreSendDenied('invalid_attempt_metadata')
        if attempt is not None:
            try:
                selected=get_model_spec(metadata['model_id'])
                snapshot=canonical_json_text(json).encode('utf-8')
                if (metadata['provider']!='gigachat' or metadata['role']!=policy.ROUTES[self.route].role
                        or metadata['provider_model_id']!=json['model'] or selected.provider_model_id!=json['model']
                        or metadata['request_snapshot_sha256']!=hashlib.sha256(snapshot).hexdigest()
                        or metadata['request_utf8_bytes']!=len(wire)):
                    raise ValueError('provider_snapshot_changed')
            except Exception:raise PreSendDenied('provider_event_model_or_snapshot_changed') from None
        logical=metadata.get('logical_call_id') or 'direct:'+_digest([self.owner.run_id,self.route,hashlib.sha256(wire).hexdigest()])
        attempt_id=metadata.get('provider_attempt_id') or 'pa_'+_digest([self.owner.run_id,logical])
        if any(type(v) is not str or not v or len(v)>512 for v in (attempt_id,logical)):
            raise PreSendDenied('invalid_attempt_identity')
        cap=_ServerAttempt(self.owner,self.route,wire,attempt_id,logical,self.timeout)
        timer=asyncio.timeout(self.timeout)
        try:
            async with timer:
                # Separate transport task: a token/HTTP callback can uncancel
                # itself, but cannot erase cancellation on its owning caller.
                reply=await asyncio.create_task(cap.transport.send_bytes(wire,timeout_seconds=self.timeout,
                    max_response_bytes=cap.response_limit,admission=cap))
        except PreSendDenied:raise
        except BaseException as error:
            if isinstance(error,(Exception,asyncio.CancelledError)) and cap.sent:
                cap.terminal('cancelled' if isinstance(error,asyncio.CancelledError)
                    or cap.parent_task.cancelling()>cap.parent_cancels and not timer.expired() else
                    'timeout' if isinstance(error,TimeoutError) or timer.expired() else 'transport_error')
            if isinstance(error,TimeoutError):raise httpx.ReadTimeout('provider_timeout') from None
            if isinstance(error,(PreSendUncertain,asyncio.CancelledError)):raise
            if isinstance(error,Exception):raise httpx.TransportError('provider_transport_failed') from None
            raise
        usage=_usage(reply.data)
        supplied={k:getattr(usage,k) for k in ('prompt_tokens','completion_tokens','total_tokens')} if usage.status=='complete' else None
        raw_usage=reply.data.get('usage') if type(reply.data) is dict else None
        if supplied is not None:
            status,_,_=policy.validate_usage(raw_usage)
            if status!='KNOWN':supplied=None
            elif 'precached_prompt_tokens' in raw_usage:supplied['precached_prompt_tokens']=raw_usage['precached_prompt_tokens']
        cancelled=self.owner.cancelled or cap.parent_task.cancelling()>cap.parent_cancels and not timer.expired()
        if timer.expired() or asyncio.get_running_loop().time()>=cap.deadline or cancelled:
            cap.terminal('cancelled' if cancelled else 'timeout',supplied)
            raise httpx.ReadTimeout('late_or_cancelled_provider_response')
        cap.terminal('provider_error' if not 200<=reply.status<300 else 'parse_error' if reply.error_code else 'completed',supplied)
        content=b'INVALID JSON' if reply.error_code else json_codec.dumps(reply.data,ensure_ascii=False,allow_nan=False).encode()
        return httpx.Response(reply.status,content=content,request=httpx.Request('POST',CHAT_URL))


def guarded_client(route,*,timeout,parent=None):
    owner=_require_owner(route)
    if parent is not None and (type(parent) is not _GuardedClient or parent.owner is not owner):
        raise PreSendDenied('injected_client_not_authorized')
    return _GuardedClient(route,timeout,owner)
