"""Server-only bounded GigaChat session. No launcher/env/browser activation.

The owner supplies a reviewed, expiring approval in Python. TEST can construct
only the same protocol over MockTransport in TEMP. OAuth cache stays in the
legacy gigachat_transport module; inference uses the existing Turn/S2/S3a ledger.
"""
from dataclasses import dataclass, field
import asyncio
import hashlib
import json
from pathlib import Path
import re
import ssl
import tempfile
import threading
import time

import httpx
import context_storage as core
from gigachat_transport import CHAT_URL, OAUTH_URL, get_access_token
from model_registry import get_model_spec
from ordinary_chat_service import PreSendDenied, PreSendUncertain, ProviderResponse

MODELS_URL = 'https://api.giga.chat/v1/models'
_ACTIVE = set()
_LOCK = threading.Lock()
_SCOPES = {'GIGACHAT_API_PERS', 'GIGACHAT_API_B2B', 'GIGACHAT_API_CORP'}


@dataclass(frozen=True)
class ModelContract:
    model_id: str
    context_tokens: int
    output_tokens: int  # operator limit for one attempt, not a claimed provider maximum
    response_models: tuple[str, ...]
    evidence: str
    provider_output_cap_tokens: int | None = None  # UNKNOWN is explicit
    version_mode: str = 'EXACT'

    def validate(self):
        model = get_model_spec(self.model_id)
        if (model.provider != 'gigachat' or model.is_local
                or any(type(v) is not int or v <= 0 for v in (self.context_tokens, self.output_tokens))
                or self.output_tokens >= self.context_tokens or not self.evidence
                or (self.provider_output_cap_tokens is not None and
                    (type(self.provider_output_cap_tokens) is not int or
                     self.provider_output_cap_tokens < self.output_tokens or
                     self.provider_output_cap_tokens >= self.context_tokens))
                or type(self.response_models) is not tuple or self.version_mode not in ('EXACT', 'DISCOVER_GIGACHAT_2', 'DISCOVER_FAMILY')
                or (self.version_mode == 'EXACT' and
                    (not self.response_models or any(type(s) is not str or not re.fullmatch(
                        re.escape(model.provider_model_id)+r'(?:[:_][A-Za-z0-9_.-]+)?', s)
                        for s in self.response_models)))
                or (self.version_mode == 'DISCOVER_GIGACHAT_2' and
                    (self.model_id != 'gigachat_2' or self.response_models != () or self.output_tokens > 32))
                or (self.version_mode == 'DISCOVER_FAMILY' and
                    (self.model_id == 'gigachat_2' or self.response_models != () or self.output_tokens > 128))):
            raise PreSendDenied('provider_contract_invalid')
        return model


_FIRST_LITE_VERSION = re.compile(r'GigaChat-2:2\.0\.[0-9]{1,3}\.[0-9]{1,3}\Z', re.ASCII)


def response_model_allowed(contract, observed):
    """Exact historical pin, or one bounded first observation for GigaChat-2."""
    if type(observed) is not str:
        return False
    if type(contract) is ModelContract:
        model_id, mode, allowed = contract.model_id, contract.version_mode, contract.response_models
    elif type(contract) is dict:
        model_id, mode, allowed = (contract.get('model_id'), contract.get('version_mode', 'EXACT'),
                                   contract.get('response_models'))
    else:
        return False
    if mode == 'EXACT':
        return type(allowed) in (list, tuple) and observed in allowed
    if mode == 'DISCOVER_FAMILY' and allowed in ((), []):
        try:
            base = get_model_spec(model_id).provider_model_id
        except (ValueError, KeyError, RuntimeError):
            return False
        # Bounded first observation: same exact family, numeric release suffix only.
        # Persist the observed version; another family or arbitrary suffix is refused.
        return re.fullmatch(re.escape(base)+r'(?::[0-9]+(?:\.[0-9]+){0,5})?', observed, re.ASCII) is not None
    return (mode == 'DISCOVER_GIGACHAT_2' and model_id == 'gigachat_2'
            and allowed in ((), []) and _FIRST_LITE_VERSION.fullmatch(observed) is not None)


@dataclass(frozen=True)
class LiveApproval:
    """Trusted server handoff only, NEVER deserialize from HTTP, env or launcher.

    Grant IDs are single-use across restart. All counters are committed before
    I/O. New grants need a new explicit owner decision and independent review.
    Token limits are conservative liabilities, not a monetary price assertion.
    """
    grant_id: str
    user_go: str
    independent_review: str
    account_id: str
    scope: str
    expires_at: float
    contracts: tuple[ModelContract, ...]
    max_oauth: int
    max_catalog: int
    max_inference: int
    max_liability_tokens: int
    max_request_bytes: int = 8192
    max_answer_tokens: int = 128


class ProviderSession:
    def __init__(self, root, workspace_id, approval, *, tls_context=None):
        self._setup(root, workspace_id, approval, tls_context=tls_context)

    @classmethod
    def offline(cls, root, workspace_id, approval, transport, *, credentials=('SYNTHETIC', 'GIGACHAT_API_PERS')):
        root = Path(root).absolute()
        if (cls is not ProviderSession or Path(tempfile.gettempdir()).resolve() not in root.parents
                or type(transport) is not httpx.MockTransport):
            raise PreSendDenied('isolated_protocol_fixture_required')
        owner = cls.__new__(cls)
        owner._setup(root, workspace_id, approval, transport=transport, credentials=credentials)
        return owner

    def _setup(self, root, workspace_id, approval, *, tls_context=None, transport=None, credentials=None):
        self.root = Path(root).absolute()
        if (type(approval) is not LiveApproval or self.root.resolve() != self.root
                or not re.fullmatch(r'[A-Za-z0-9_-]{16,80}', approval.grant_id)
                or not approval.user_go.strip() or not approval.independent_review.strip()
                or not approval.account_id.strip() or approval.scope not in _SCOPES
                or type(approval.expires_at) not in (int, float)
                or not time.time() < approval.expires_at <= time.time()+86400
                or type(approval.contracts) is not tuple or (approval.max_inference != 0 and not approval.contracts)
                or any(type(c) is not ModelContract for c in approval.contracts)
                or any(type(n) is not int or n < 0 for n in (approval.max_oauth, approval.max_catalog, approval.max_inference))
                or approval.max_oauth+approval.max_catalog+approval.max_inference == 0
                or any(type(n) is not int or n <= 0 for n in (approval.max_liability_tokens, approval.max_request_bytes, approval.max_answer_tokens))
                or approval.max_request_bytes > 8192 or approval.max_answer_tokens > 20000):
            raise PreSendDenied('reviewed_live_approval_required')
        for contract in approval.contracts:
            contract.validate()
        if len({c.model_id for c in approval.contracts}) != len(approval.contracts):
            raise PreSendDenied('duplicate_model_contract')
        discovering = [c for c in approval.contracts if c.version_mode == 'DISCOVER_GIGACHAT_2']
        if discovering and (len(approval.contracts) != 1 or approval.max_inference != 1
                or approval.max_answer_tokens > 32 or approval.max_request_bytes > 1024
                or approval.max_liability_tokens > 1056):
            raise PreSendDenied('first_version_discovery_envelope_invalid')
        family = [c for c in approval.contracts if c.version_mode == 'DISCOVER_FAMILY']
        if family and (approval.max_inference > 12 or approval.max_answer_tokens > 128
                or approval.max_request_bytes > 4096 or approval.max_liability_tokens > 50688):
            raise PreSendDenied('family_discovery_envelope_invalid')
        self.approval = approval
        self.account_id, self.scope = approval.account_id, approval.scope
        self.workspace_id = workspace_id
        self.synthetic = transport is not None
        self._transport, self._credentials = transport, credentials
        self._tls = tls_context if tls_context is not None else ssl.create_default_context()
        if (type(self._tls) is not ssl.SSLContext or self._tls.verify_mode != ssl.CERT_REQUIRED
                or not self._tls.check_hostname):
            raise PreSendDenied('verified_tls_required')
        self.trust_identity = hashlib.sha256(b''.join(sorted(self._tls.get_ca_certs(binary_form=True)))).hexdigest()
        self._mutex = threading.Lock()
        self._closed = False
        self._available = frozenset()
        self._confirmed_versions = {}
        self._counts = dict(oauth=0, catalog=0, inference=0, liability=0)
        self._parts = (core.ULTRA_DIRNAME, 'provider_sessions', approval.grant_id+'.json')
        self._account_parts = self._parts[:-1]+('account_'+hashlib.sha256(self.account_id.encode()).hexdigest()+'.json',)
        # Explicit enrollment, never on a browser send or read. No automatic
        # historical ledger adoption; a previously initialized S3a is required.
        from ultra_budget_ledger import BudgetLedger
        with core._existing_workspace_writer(self.root, workspace_id) as writer:
            BudgetLedger(self.root, workspace_id).recover()
            core._ensure_write_directory(writer.anchor, self._parts[:-1])
            if core._read_existing_raw(writer, self._parts) is not None:
                raise PreSendDenied('grant_already_used_requires_new_go')
            prior = core._read_existing_raw(writer, self._account_parts)
            if prior is not None and prior.get('state') != 'CLOSED':
                raise PreSendDenied('account_owner_unresolved')
            pinned = prior.get('confirmed_versions', {}) if prior is not None else {}
            if (type(pinned) is not dict or any(type(k) is not str or type(v) is not str
                    for k, v in pinned.items())):
                raise PreSendDenied('confirmed_versions_unreadable')
            if pinned.get('gigachat_2'):
                if discovering or any(c.model_id == 'gigachat_2' and
                        (c.version_mode != 'EXACT' or c.response_models != (pinned['gigachat_2'],))
                        for c in approval.contracts):
                    raise PreSendDenied('confirmed_version_requires_exact_pin')
            self._confirmed_versions = dict(pinned)
            self._save(writer)
            core._replace_verified(writer.anchor, self._account_parts, core._json_bytes(self._account_record()))

    def _account_record(self):
        return dict(schema=1, grant_id=self.approval.grant_id, state='CLOSED' if self._closed else 'ACTIVE',
                    confirmed_versions=self._confirmed_versions)

    def pin_discovered_version(self, observed, model_id='gigachat_2'):
        c = self.contract(model_id)
        if (c.version_mode not in ('DISCOVER_GIGACHAT_2', 'DISCOVER_FAMILY')
                or not response_model_allowed(c, observed)):
            raise PreSendDenied('first_version_discovery_invalid')
        with core._existing_workspace_writer(self.root, self.workspace_id) as writer:
            self.check()
            prior = self._confirmed_versions.get(model_id)
            if prior is not None:
                if prior != observed:
                    raise PreSendDenied('confirmed_version_changed')
                return
            candidate = {**self._account_record(), 'confirmed_versions':
                         {**self._confirmed_versions, model_id: observed}}
            core._replace_verified(writer.anchor, self._account_parts, core._json_bytes(candidate))
            if core._read_existing_raw(writer, self._account_parts) != candidate:
                raise PreSendDenied('first_version_pin_readback_failed')
            self._confirmed_versions = candidate['confirmed_versions']

    def _record(self):
        return dict(schema=1, grant_id=self.approval.grant_id, workspace_id=self.workspace_id,
                    account_sha256=hashlib.sha256(self.account_id.encode()).hexdigest(),
                    counts=self._counts, state='CLOSED' if self._closed else 'ACTIVE')

    def _save(self, writer):
        core._replace_verified(writer.anchor, self._parts, core._json_bytes(self._record()))

    def check(self):
        if (self._closed or time.time() >= self.approval.expires_at
                or self._tls.verify_mode != ssl.CERT_REQUIRED or not self._tls.check_hostname):
            raise PreSendDenied('provider_session_inactive')
        with core._existing_workspace_writer(self.root, self.workspace_id) as writer:
            if core._read_existing_raw(writer, self._parts) != self._record():
                raise PreSendDenied('provider_session_changed')
            if core._read_existing_raw(writer, self._account_parts) != self._account_record():
                raise PreSendDenied('account_owner_changed')

    def credentials(self):
        self.check()
        if self.synthetic:
            credentials, scope = self._credentials
        else:
            import os
            credentials = os.getenv('GIGACHAT_CREDENTIALS')
            scope = os.getenv('GIGACHAT_SCOPE', 'GIGACHAT_API_PERS')
        if (type(credentials) is not str or not credentials or len(credentials) > 8192
                or any(ord(c) < 33 or ord(c) > 126 for c in credentials) or scope != self.scope):
            raise PreSendDenied('credentials_or_scope_invalid')
        return credentials, scope

    def _consume(self, kind, liability=0):
        self.check()
        if (kind not in ('oauth', 'catalog', 'inference')
                or self._counts[kind] >= getattr(self.approval, 'max_'+kind)
                or self._counts['liability']+liability > self.approval.max_liability_tokens):
            raise PreSendDenied('live_call_or_token_limit')
        with core._existing_workspace_writer(self.root, self.workspace_id) as writer:
            self.check()
            self._counts[kind] += 1
            self._counts['liability'] += liability
            self._save(writer)  # Uncertain write stops before I/O; never release.

    def contract(self, model_id):
        self.check()
        found = [c for c in self.approval.contracts if c.model_id == model_id]
        if len(found) != 1:
            raise PreSendDenied('model_not_approved')
        found[0].validate()
        return found[0]

    def validate_wire(self, model_id, wire):
        c = self.contract(model_id)
        body = json.loads(wire)
        output = body.get('max_tokens')
        if (get_model_spec(model_id).provider_model_id not in self._available
                or body.get('model') != get_model_spec(model_id).provider_model_id
                or body.get('stream') is not False or type(output) is not int
                or not 0 < output <= min(c.output_tokens, self.approval.max_answer_tokens)
                or len(wire) > self.approval.max_request_bytes
                or len(wire)+output > c.context_tokens):
            raise PreSendDenied('model_unavailable_or_caps_exceeded')
        return c

    def client(self, timeout):
        # No ambient proxy/CA/redirect/retry and no user URL. Separate clients
        # share one legacy OAuth cache. Test passes only exact MockTransport.
        transport = self._transport if self.synthetic else httpx.AsyncHTTPTransport(verify=self._tls, retries=0, trust_env=False)
        return httpx.AsyncClient(transport=transport, trust_env=False, follow_redirects=False,
                                timeout=httpx.Timeout(timeout))

    async def request(self, kind, url, *, method, headers, maximum, data=None):
        expected = OAUTH_URL if kind == 'oauth' else MODELS_URL
        if url != expected or method != ('POST' if kind == 'oauth' else 'GET'):
            raise PreSendDenied('provider_endpoint_invalid')
        self._consume(kind)
        try:
            async with self.client(10) as client:
                async with client.stream(method, url, headers=headers, data=data) as response:
                    raw = bytearray()
                    async for chunk in response.aiter_bytes():
                        if len(raw)+len(chunk) > maximum:
                            raise PreSendDenied('provider_response_limit')
                        raw.extend(chunk)
                    if response.status_code != 200:
                        raise PreSendDenied('oauth_http_rejected' if kind == 'oauth' else 'catalog_http_rejected')
                    result = json.loads(raw)
                    if type(result) is not dict:
                        raise ValueError
                    return result
        except PreSendDenied:
            raise
        except Exception:
            raise PreSendDenied('provider_control_request_failed') from None

    async def discover_models(self):
        # Explicit account probe, consumes a separately approved call. Never
        # called by capability(), F5 or the launcher.
        if not self._mutex.acquire(blocking=False):
            raise PreSendDenied('provider_account_busy')
        try:
            token = await get_access_token(authority=self)
            reply = await self.request('catalog', MODELS_URL, method='GET',
                headers={'Authorization': 'Bearer '+token}, maximum=65536)
            data = reply.get('data')
            if type(data) is not list or any(type(m) is not dict or type(m.get('id')) is not str for m in data):
                raise PreSendDenied('catalog_response_invalid')
            self._available = frozenset(m['id'] for m in data)
            return self._available
        finally:
            self._mutex.release()

    def close(self):
        if self._closed:
            return
        with _LOCK:
            if (self.account_id, self.synthetic) in _ACTIVE or self._mutex.locked():
                raise PreSendDenied('provider_account_busy')
        self._closed = True
        with core._existing_workspace_writer(self.root, self.workspace_id) as writer:
            self._save(writer)
            core._replace_verified(writer.anchor, self._account_parts, core._json_bytes(self._account_record()))


class RealGigaChatTransport:
    endpoint = CHAT_URL

    def __init__(self, session, model_id):
        if type(session) is not ProviderSession:
            raise PreSendDenied('server_provider_session_required')
        session.contract(model_id)
        self.session, self.model_id = session, model_id

    async def send_bytes(self, wire, *, timeout_seconds, max_response_bytes, admission=None):
        from web_alarm.turn_service import _TurnAdmission
        if type(admission) is not _TurnAdmission or type(wire) is not bytes:
            raise PreSendDenied('server_turn_authority_required')
        session = self.session
        task = asyncio.current_task()
        deadline = asyncio.get_running_loop().time()+timeout_seconds
        session.validate_wire(self.model_id, wire)
        admission.limits(timeout_seconds, max_response_bytes)
        # Serialize all model streams for this account within this process. The
        # workspace's durable single-use grant fences restart/replay as well.
        key = (session.account_id, session.synthetic)
        with _LOCK:
            if key in _ACTIVE:
                raise PreSendDenied('provider_account_busy')
            _ACTIVE.add(key)
        try:
            admission.authorize(wire, self)  # Existing durable reserve + SENT.
            token = await get_access_token(authority=session)
            if task.cancelling() or asyncio.get_running_loop().time() >= deadline:
                raise PreSendUncertain('provider_deadline_or_cancel')
            admission.check(wire, self)
            c = session.validate_wire(self.model_id, wire)
            session._consume('inference', len(wire)+json.loads(wire)['max_tokens'])
            async with session.client(timeout_seconds) as client:
                request = client.build_request('POST', self.endpoint, content=wire, headers={
                    'Authorization': 'Bearer '+token, 'Accept': 'application/json',
                    'Content-Type': 'application/json; charset=utf-8'})
                if request.content != wire or str(request.url) != CHAT_URL or request.method != 'POST':
                    raise PreSendUncertain('physical_request_changed')
                session.check()
                admission.check(wire, self, physical=True)
                response = await client.send(request, stream=True)
                try:
                    raw = bytearray()
                    async for chunk in response.aiter_bytes():
                        if len(raw)+len(chunk) > max_response_bytes:
                            return ProviderResponse(response.status_code, None, 'response_limit_exceeded')
                        raw.extend(chunk)
                    try:
                        decoded = json.loads(raw)
                    except (ValueError, RecursionError):
                        return ProviderResponse(response.status_code, None, 'invalid_json_response')
                    if response.status_code != 200:
                        # Do not expose provider error text, headers or redirects.
                        safe = {'usage': decoded['usage']} if type(decoded) is dict and type(decoded.get('usage')) is dict else {}
                        return ProviderResponse(response.status_code, safe, 'provider_http_'+str(response.status_code))
                    if type(decoded) is not dict or not response_model_allowed(c, decoded.get('model')):
                        return ProviderResponse(200, decoded, 'response_model_version_mismatch')
                    # Existing parser expects registry ID; validate the complete
                    # observed version above, then normalize only this field.
                    observed = decoded['model']
                    if c.version_mode in ('DISCOVER_GIGACHAT_2', 'DISCOVER_FAMILY'):
                        try:
                            session.pin_discovered_version(observed, self.model_id)
                        except Exception:
                            raise PreSendUncertain('first_version_pin_failed') from None
                    decoded['model'] = get_model_spec(self.model_id).provider_model_id
                    return ProviderResponse(200, decoded, observed_model=observed)
                finally:
                    await response.aclose()
        except PreSendDenied:
            # After reserve/SENT a control failure is uncertain, never a false
            # NOT_STARTED. A missing terminal preserves the committed reserve.
            if admission.used:
                raise PreSendUncertain('provider_control_failed_after_reserve') from None
            raise
        except httpx.TimeoutException:
            raise TimeoutError('provider_timeout') from None
        finally:
            with _LOCK:
                _ACTIVE.discard(key)
