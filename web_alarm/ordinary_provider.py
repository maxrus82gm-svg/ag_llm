"""STANDARD Ordinary Chat integration and closed one-model provider preflight.

No REAL authority is minted by this revision. The only executable factory is an
explicit TEMP-bound HTTP fixture used by author/independent application tests.
All execution, persistence and accounting remain in the accepted H32/H33 core.
"""
from pathlib import Path
import tempfile
import threading

from model_registry import get_model_spec, list_model_specs
from ordinary_gigachat_transport import OfflineHTTPFixture
from ordinary_chat_service import PreSendDenied
from .ultra_chat import OrdinaryCoreChatService, UltraChatError, UltraChatService, _core


MODEL_ID = "gigachat_2_pro"  # Reference to the existing registry, not a second catalog.
RELEASE_HOLDS = ("provider_caps_unverified", "account_scope_availability_unverified",
                 "usage_cost_tls_contract_unverified", "S3b_open", "S3c_open",
                 "S9_open", "S13a_open", "independent_acceptance_pending", "owner_go_required")


class OrdinaryProviderFactory:
    """Closed server construction boundary. No JSON/env/URL/client argument for REAL.

    Completion of REAL construction is intentionally deferred until the mandatory
    admission decisions exist. A verified-looking model dictionary cannot open it.
    """
    def __init__(self):
        self._registry = self._root = self._fixture = None
        self._session = None

    @classmethod
    def for_session(cls, registry, session):
        from gigachat_runtime import ProviderSession
        if cls is not OrdinaryProviderFactory or type(session) is not ProviderSession:
            raise PreSendDenied('server_provider_session_required')
        session.check()
        factory = cls()
        factory._registry, factory._session = registry, session
        return factory

    @classmethod
    def offline_application(cls, registry, root, fixture):
        root = Path(root).absolute()
        if (cls is not OrdinaryProviderFactory or type(fixture) is not OfflineHTTPFixture
                or root.resolve() != root or Path(tempfile.gettempdir()).resolve() not in root.parents
                or registry.storage_root != root / "registry"):
            raise ValueError("Expected the isolated application fixture registry")
        # Reuse the accepted disposable-root/link checks before constructing a server.
        OrdinaryCoreChatService(registry, root, http_fixture=fixture)
        factory = cls()
        factory._registry, factory._root, factory._fixture = registry, root, fixture
        return factory

    def preflight(self):
        model = get_model_spec(MODEL_ID)
        return {"model_id": model.model_id, "provider_model_id": model.provider_model_id,
                "contract": "PARTIAL", "context_tokens": None, "output_tokens": None,
                "account_availability": "UNVERIFIED", "real_available": False,
                "real_factory": "BLOCKED", "release_holds": list(RELEASE_HOLDS)}

    def require_real(self):
        # Existing gate remains the sole OAuth authority, before token cache/env/I/O.
        from gigachat_admission import require_real_authority
        require_real_authority(self._session)

    def validate_server(self, registry):
        if type(self) is not OrdinaryProviderFactory:
            raise ValueError("Expected the exact server factory")
        if self._session is not None:
            if registry is not self._registry:
                raise ValueError('Provider registry changed')
        if self._fixture is not None:
            if registry is not self._registry or type(self._fixture) is not OfflineHTTPFixture:
                raise ValueError("Application fixture scope changed")
            OrdinaryCoreChatService(registry, self._root, http_fixture=self._fixture)

    def fixture_for(self, registry, root):
        self.validate_server(registry)
        if self._session is not None:
            if Path(root).absolute() != self._session.root:
                raise UltraChatError(403, 'provider_workspace_scope', 'Workspace is outside the provider approval')
            return None
        if self._fixture is None:
            return None
        # Same registry and same disposable workspace allocator as the accepted TEST
        # service. Registration alone cannot enroll arbitrary normal workspaces.
        scoped = OrdinaryCoreChatService(registry, self._root, http_fixture=self._fixture)
        if Path(root).absolute().parent != scoped.projects:
            raise UltraChatError(403, "ordinary_fixture_scope", "Workspace is outside the application fixture")
        scoped._check_scope()
        return self._fixture


class OrdinaryApplicationChatService(OrdinaryCoreChatService):
    """Normal application routes, using existing Ordinary/Turn/RAW/usage methods.

    Explicit base delegates remove the disposable registry/allocator behavior.
    The factory supplies execution only in isolated tests. Normal installation
    reads history and preferences, but accepts no provider Turn while HOLD is open.
    """
    def __init__(self, registry, factory, *, api=None):
        if type(factory) is not OrdinaryProviderFactory:
            raise ValueError("Expected the exact server factory")
        factory.validate_server(registry)
        UltraChatService.__init__(self, registry)
        if api is not None and api.registry is not registry:
            raise ValueError('Personal chat API must use the same registry')
        self._api = api
        if api is not None:
            from .model_cards import LiveCheckNotAuthorized
            if type(api.model_cards.checker) is LiveCheckNotAuthorized:
                api.model_cards.checker = _OrdinaryTurnChecker(self)
        self._personal_lock = threading.Lock()
        self._factory = factory
        self._http_fixture = factory._fixture
        self._owners = {}
        self._owner_lock = threading.Lock()

    _registration = UltraChatService._registration
    workspaces = UltraChatService.workspaces
    rename_workspace = UltraChatService.rename_workspace

    def _writable_workspace(self, core, wa_workspace_id, *, initialize=False):
        root, wid = UltraChatService._writable_workspace(self, core, wa_workspace_id, initialize=initialize)
        fixture = self._factory.fixture_for(self.registry, root)
        if initialize and fixture is not None:
            # Same explicit first-chat enrollment as H32; never bootstrap on send/read.
            from ultra_budget_ledger import BudgetLedger, LedgerDenied
            try:
                if wid is None:
                    wid = core.ensure_workspace_storage(root)["workspace_id"]
                with core._existing_workspace_writer(root, wid):
                    BudgetLedger(root, wid).initialize()
            except (LedgerDenied, OSError, ValueError):
                raise UltraChatError(503, "ordinary_enrollment_required", "Audit enrollment requires review") from None
        return root, wid

    def capability(self):
        contract = self._factory.preflight()
        fixture = self._factory._fixture is not None
        session = self._factory._session
        active = False
        if session is not None:
            try:
                session.check()
                active = bool(session._available)
            except PreSendDenied:
                pass
        from .standard_live import personal_chat_registration
        personal = personal_chat_registration(self.registry)
        selected_root = None
        if active and session is not None and not session.synthetic:
            try:
                selected_root = self.registry.find_by_root(session.root)
            except Exception:
                pass
        admitted = {c.model_id for c in session.approval.contracts} if session is not None else set()
        models = [dict(model_id=m.model_id, display_name=m.display_name, provider_model_id=m.provider_model_id,
            availability=(('UNAVAILABLE' if m.provider_model_id not in session._available else
                           'AVAILABLE' if m.model_id in admitted else 'NOT_APPROVED')
                         if session is not None else 'UNVERIFIED'))
            for m in list_model_specs() if m.enabled and m.provider == 'gigachat' and not m.is_local]
        return {**contract, 'available': fixture or active, 'real_available': active and not session.synthetic if session else False,
                'mode': 'ORDINARY', 'core_bridge': True, 'chat_preferences': True,
                'execution_mode': ('PROTOCOL_TEST' if session.synthetic else 'REAL') if active else 'OFFLINE_APPLICATION' if fixture else 'HOLD',
                'models': models,
                'personal_workspace_id': personal.workspace_id if personal else None,
                'live_workspace_id': selected_root.workspace_id if selected_root else None}

    @staticmethod
    def _model_path(path):
        return OrdinaryCoreChatService._settings_path(path.removesuffix("/model") + "/settings") if path.endswith("/model") else False

    @staticmethod
    def is_write_path(path):
        return (path in ('/ultra/chat/personal', '/ultra/chat/live/start', '/ultra/chat/live/stop')
                or OrdinaryApplicationChatService._model_path(path)
                or OrdinaryCoreChatService._settings_path(path) or UltraChatService.is_write_path(path))

    def create_personal_chat(self, body):
        """Browser-only local registration; never creates OAuth or model grants."""
        if type(body) is not dict or body:
            raise UltraChatError(400, 'invalid_ultra_chat_request', 'Expected empty personal chat request')
        if self._api is None:
            raise UltraChatError(403, 'personal_creation_unavailable', 'Personal creation is unavailable here')
        from .standard_live import prepare_personal_chat, personal_chat_registration
        with self._personal_lock:
            existed = personal_chat_registration(self.registry) is not None
            try:
                record, _, _ = prepare_personal_chat(self._api)
            except Exception:
                raise UltraChatError(409, 'personal_storage_unavailable',
                                     'Personal history needs storage review; no existing data changed') from None
        return (200 if existed else 201), {'wa_workspace_id': record.workspace_id, 'created': not existed}


    def start_live(self, body):
        """Explicit local-user action opens a finite six-model session.

        The existing profile/environment owns credentials and OAuth. Never accept
        a grant, model cap, endpoint, root or credentials from browser JSON.
        """
        if type(body) is not dict or body != {'confirmation': 'GIGACHAT 6'}:
            raise UltraChatError(400, 'live_confirmation_required', 'Confirm the six-model bounded session')
        if self._api is None or self._factory._fixture is not None:
            raise UltraChatError(403, 'live_unavailable', 'Only normal local STANDARD can start GigaChat')
        import os
        import secrets
        import time
        import asyncio
        from .live_bootstrap import _verified_workspace
        from .standard_live import personal_chat_registration, OBSERVED_MODEL
        from gigachat_runtime import LiveApproval, ModelContract, ProviderSession
        if (not os.environ.get('GIGACHAT_CREDENTIALS')
                or os.environ.get('GIGACHAT_SCOPE', 'GIGACHAT_API_PERS') != 'GIGACHAT_API_PERS'):
            raise UltraChatError(409, 'live_credentials_missing',
                                 'Configure the existing GIGACHAT_CREDENTIALS and PERS profile, then restart STANDARD')
        with self._personal_lock:
            current = self._factory._session
            if current is not None:
                try:
                    current.check()
                except PreSendDenied:
                    try:
                        current.close()
                    except PreSendDenied:
                        raise UltraChatError(409, 'live_session_unresolved', 'Previous provider session requires review') from None
                    self._factory._session = None
                else:
                    raise UltraChatError(409, 'live_already_active', 'Stop the active GigaChat session first')
            record = personal_chat_registration(self.registry)
            if record is None:
                raise UltraChatError(409, 'personal_chat_required', 'Create Личные чаты first')
            try:
                root, wid = _verified_workspace(self._api, record.workspace_id)
            except Exception:
                raise UltraChatError(409, 'personal_storage_unavailable', 'Personal storage needs review') from None
            contracts = tuple(
                    ModelContract(m.model_id, 128000 if m.model_id.startswith('gigachat_2') or m.model_id == 'gigachat_ultra' else 32768, 20000,
                    (OBSERVED_MODEL,) if m.model_id == 'gigachat_2' else (),
                    'Operator output preference ceiling 20000; 2-series and 3-Ultra context 128000 from official docs, '
                    'other 3-series context admission ceiling 32768, provider context/output maximum UNKNOWN; '
                    'exact GigaChat-2 previously observed; other versions pinned on first bounded response',
                    version_mode='EXACT' if m.model_id == 'gigachat_2' else 'DISCOVER_FAMILY')
                for m in list_model_specs()
                if m.enabled and m.provider == 'gigachat' and not m.is_local
            )
            if len(contracts) != 6:
                raise UltraChatError(409, 'live_registry_changed', 'Six-model registry requires review')
            approval = LiveApproval(
                grant_id='InAppGigaChat' + secrets.token_hex(16),
                user_go='in-app authenticated same-origin GIGACHAT 6 consent; 2026-11-16',
                independent_review='Bounded offline verification required before owner merge; general release HOLD',
                account_id='existing-windows-gigachat-pers-account', scope='GIGACHAT_API_PERS',
                expires_at=time.time() + 86400, contracts=contracts,
                max_oauth=None, max_catalog=1, max_inference=None,
                max_liability_tokens=None, max_request_bytes=4096, max_answer_tokens=20000,
                user_turn_mode=True)
            try:
                session = ProviderSession(root, wid, approval)
            except PreSendDenied as exc:
                raise UltraChatError(409, 'live_session_denied',
                                     'Provider session requires review: ' + str(exc)) from None
            try:
                available = asyncio.run(session.discover_models())
                if not any(m.provider_model_id in available for m in list_model_specs()):
                    raise PreSendDenied('no_gigachat_models_in_catalog')
            except Exception:
                try:
                    session.close()
                except Exception:
                    raise UltraChatError(503, 'live_session_unresolved',
                                         'Provider control call uncertain; review before retry') from None
                raise UltraChatError(503, 'live_catalog_unavailable',
                                     'Provider catalog could not be verified; no chat Turn was sent') from None
            self._factory._registry = self.registry
            self._factory._session = session
            return 200, {'state': 'ACTIVE', 'limits': {'sends': 'PER_USER_TURN', 'output_tokens': 20000,
                                                       'request_bytes': 4096, 'hours': 24},
                         'models': self.capability()['models']}

    def stop_live(self, body):
        """An explicit stop closes the durable grant without clearing any history."""
        if type(body) is not dict or body:
            raise UltraChatError(400, 'invalid_ultra_chat_request', 'Expected empty stop request')
        if self._api is None or self._factory._fixture is not None:
            raise UltraChatError(403, 'live_unavailable', 'Only normal local STANDARD can stop GigaChat')
        with self._personal_lock:
            session = self._factory._session
            if session is None:
                return 200, {'state': 'INACTIVE'}
            try:
                session.close()
            except PreSendDenied:
                raise UltraChatError(409, 'live_session_busy', 'A provider request is still active') from None
            self._factory._session = None
            return 200, {'state': 'INACTIVE'}

    def create_workspace(self, body):
        raise UltraChatError(405, "method_not_allowed", "Use normal Workspace registration")

    def route(self, path, raw_query):
        if self._model_path(path):
            ws, cid = self._settings_route(path, raw_query)
            return lambda: self.chat_model(ws, cid)
        return super().route(path, raw_query)

    def write_route(self, path, raw_query):
        if path in ('/ultra/chat/live/start', '/ultra/chat/live/stop'):
            if raw_query:
                raise UltraChatError(400, 'invalid_ultra_chat_request', 'Query parameters are not supported')
            return self.start_live if path.endswith('/start') else self.stop_live
        if path == '/ultra/chat/personal':
            if raw_query:
                raise UltraChatError(400, 'invalid_ultra_chat_request', 'Query parameters are not supported')
            return self.create_personal_chat
        if path == "/ultra/chat/workspaces":
            raise UltraChatError(405, "method_not_allowed", "Use normal Workspace registration")
        if self._model_path(path):
            ws, cid = self._settings_route(path, raw_query)
            return lambda body: (200, self.chat_model(ws, cid, body))
        return super().write_route(path, raw_query)

    def chat_model(self, wa_workspace_id, chat_id, update=...):
        allowed = {m.model_id for m in list_model_specs() if m.enabled and m.provider == 'gigachat' and not m.is_local}
        if update is not ... and (type(update) is not dict or set(update) != {'model_ref'}
                or type(update['model_ref']) is not str or update['model_ref'] not in allowed):
            raise UltraChatError(400, "ordinary_model_not_allowed", "Select the admitted model")
        core = _core()
        root, wid = self._writable_workspace(core, wa_workspace_id)
        try:
            with core._existing_workspace_writer(root, wid) as writer:
                parts, metadata = core._require_chat_for_write(writer, chat_id)
                fallback = (self._factory._session.approval.contracts[0].model_id
                            if self._factory._session is not None and not self._factory._session.synthetic else MODEL_ID)
                selected = metadata.get("ordinary_chat_model", fallback) if update is ... else update['model_ref']
                if selected not in allowed:
                    raise UltraChatError(409, "ordinary_model_invalid", "Saved model requires review")
                if update is not ... and metadata.get('ordinary_chat_model') != selected:
                    core._replace_verified(writer.anchor, parts + ("metadata.json",),
                        core._json_bytes({**metadata, "ordinary_chat_model": selected}))
                return {"model_ref": selected, "persisted": "ordinary_chat_model" in metadata or update is not ...}
        except (core.StorageWriteError, core.ChatNotFoundError, OSError, ValueError):
            raise UltraChatError(503, "ordinary_model_unavailable", "Chat model could not be verified") from None

    def submit_turn(self, wa_workspace_id, chat_id, body):
        if type(body) is not dict or set(body) != {"idempotency_key", "model_ref", "text"}:
            raise UltraChatError(400, "invalid_turn_request", "Expected model, text and retry key")
        allowed = {m['model_id'] for m in self.capability()['models']}
        if type(body.get('model_ref')) is not str or body['model_ref'] not in allowed:
            raise UltraChatError(400, "ordinary_model_not_allowed", "Select the admitted model")
        if self._factory._fixture is None:
            try:
                self._factory.require_real()
            except PreSendDenied:
                raise UltraChatError(403, "ordinary_real_hold", "GigaChat sending awaits provider and safety acceptance") from None
        # Preserve the existing Turn/error contract: the immutable admitted wire
        # is refused by session.validate_wire before physical POST for an absent
        # catalog model; UI availability alone must not change stored outcomes.
        root, _ = self._writable_workspace(_core(), wa_workspace_id)
        self._factory.fixture_for(self.registry, root)
        result = super().submit_turn(wa_workspace_id, chat_id, body)
        if (self._api is not None and result.get('execution_mode') == 'REAL'
                and type(result.get('evm_profile')) is dict):
            try:
                if result.get('state') == 'SUCCEEDED':
                    synced = self._api.model_cards.record_chat_success(body['model_ref'],
                        result['evm_profile']['settings_version'], turn_id=result['turn_id'])
                elif result.get('state') in ('FAILED', 'UNKNOWN'):
                    synced = self._api.model_cards.record_chat_failure(body['model_ref'],
                        result['evm_profile']['settings_version'],
                        code=result.get('diagnostic_code') or result['state'].lower(), turn_id=result['turn_id'])
                else:
                    synced = False
                result = {**result, 'evm_status_sync': 'UPDATED' if synced else 'NO_CHANGE'}
            except Exception:
                # The committed Turn/RAW/ledger must remain readable even if
                # the secondary EVM indicator store needs repair.
                result = {**result, 'evm_status_sync': 'UNAVAILABLE'}
        return self._application_view(result)

    def _application_view(self, result):
        # Durable TEST_OFFLINE provenance is retained; only the browser envelope
        # names its actual application route. No synthetic result is called REAL.
        session = self._factory._session
        return {**result, "mode": "ORDINARY", "execution_mode":
                result.get('execution_mode') or (('PROTOCOL_TEST' if session.synthetic else 'REAL') if session else "OFFLINE_APPLICATION")}

    def _turn_request(self, action, wa_workspace_id, chat_id, value, body=None):
        result = super()._turn_request(action, wa_workspace_id, chat_id, value, body)
        return result if action == "submit" else self._application_view(result)

    def latest_turn(self, wa_workspace_id, chat_id):
        result = super().latest_turn(wa_workspace_id, chat_id)
        return {**result, "turn": self._application_view(result["turn"]) if result["turn"] else None}

    def messages(self, wa_workspace_id, chat_id, before, limit):
        if self._factory._fixture is not None:
            # Synthetic application tests retain Stage 5's strict TEST Turn/RAW checks.
            page = super().messages(wa_workspace_id, chat_id, before, limit)
        else:
            # STANDARD must read historical Tk/Ultra RAW without requiring a
            # TEST_OFFLINE Turn. The shared bounded reader still verifies the
            # workspace identity, message ownership, limits and damaged records.
            page = UltraChatService.messages(self, wa_workspace_id, chat_id, before, limit)
            try:
                # Usage is optional display data; missing historical Turn/ledger
                # enrollment cannot make otherwise readable RAW disappear.
                page['usage_summary'] = self.chat_usage(wa_workspace_id, chat_id)
            except (UltraChatError, OSError, ValueError, KeyError, TypeError):
                page['usage_summary'] = {'available': False, 'synthetic': False}
        page['usage_summary']['synthetic'] = bool(self._factory._fixture is not None
            or self._factory._session and self._factory._session.synthetic)
        if not self._factory._fixture and not self._factory._session and not page['usage_summary'].get('attempts'):
            page['usage_summary']['available'] = False
        return page

    def chat_preferences(self, wa_workspace_id, chat_id, update=...):
        result = super().chat_preferences(wa_workspace_id, chat_id, update)
        session = self._factory._session
        if session is not None:
            selected = self.chat_model(wa_workspace_id, chat_id)['model_ref']
            contract = next((c for c in session.approval.contracts if c.model_id == selected), None)
            result['effective_answer_tokens'] = min(result['settings']['answer_tokens'],
                session.approval.max_answer_tokens, contract.output_tokens) if contract else None
            result['applied_to_provider'] = self.capability()['available'] and contract is not None
        return result

    def _fixture_turns(self, root, context=(), context_ref='offline-read:v1', response_text='TEST'):
        from .turn_service import TurnService
        from .ordinary_chat_bridge import OrdinaryCoreAdapter
        session = self._factory._session
        if session is None:
            if self._factory._fixture is not None:
                return super()._fixture_turns(root, context, context_ref, response_text)
            return TurnService(test_roots=[root])  # Read-only recovery; no sender.
        chat_id = context_ref.removeprefix('stage5:') if context_ref.startswith('stage5:') else None
        model_id = session.approval.contracts[0].model_id if not session.synthetic else MODEL_ID
        answer = session.approval.max_answer_tokens
        if chat_id:
            with _core()._existing_workspace_writer(root, session.workspace_id) as writer:
                _, metadata = _core()._require_chat_for_write(writer, chat_id)
                model_id = metadata.get('ordinary_chat_model', session.approval.contracts[0].model_id if not session.synthetic else MODEL_ID)
                answer = metadata.get('ordinary_chat_settings', {}).get('answer_tokens', answer)
        if not chat_id:
            return TurnService(test_roots=[root])
        evm_profile = None
        if self._api is not None and not session.synthetic:
            from .model_cards import ModelCardsError
            try:
                evm_profile = self._api.model_cards.execution_snapshot(model_id)
            except ModelCardsError:
                raise PreSendDenied('evm_profile_unavailable') from None
        adapter = OrdinaryCoreAdapter.for_provider(session, context_ref=context_ref, model_id=model_id,
            context_loader=lambda: self._chat_context(root, chat_id), answer_tokens=answer,
            evm_profile=evm_profile)
        return TurnService(test_roots=[root], offline_adapter=adapter, provider_session=session)


class _OrdinaryTurnChecker:
    """EVM check uses the visible Ordinary Chat Turn, never a second sender."""
    def __init__(self, service):
        self.service = service

    @property
    def authorized(self):
        session = self.service._factory._session
        if session is None or session.synthetic:
            return False
        try:
            session.check()
            return bool(session._available)
        except PreSendDenied:
            return False

    @property
    def reason(self):
        return "Сначала явно подключите GigaChat в Ultra Chat" if not self.authorized else ""

    def check(self, request):
        from uuid import uuid4
        from .model_cards import CheckRefusedError, CheckResult
        from .standard_live import personal_chat_registration
        session = self.service._factory._session
        if (not self.authorized or session is None or request.provider_id != 'gigachat'
                or request.model_id not in {c.model_id for c in session.approval.contracts}
                or request.provider_model_id not in session._available):
            raise CheckRefusedError('A verified active provider session is required')
        self.service._factory.require_real()
        record = personal_chat_registration(self.service.registry)
        if record is None or Path(record.workspace_root).resolve() != session.root:
            raise CheckRefusedError('Personal chat Workspace is not the approved provider Workspace')
        chat_id = 'chat_' + uuid4().hex
        self.service.create_chat(record.workspace_id,
            {'chat_id': chat_id, 'title': 'Проверка EVM — ' + request.model_id})
        self.service.chat_model(record.workspace_id, chat_id, {'model_ref': request.model_id})
        result = self.service.submit_turn(record.workspace_id, chat_id,
            {'idempotency_key': uuid4().hex, 'model_ref': request.model_id, 'text': request.message})
        if result.get('execution_mode') != 'REAL':
            raise CheckRefusedError('The provider did not execute a real Turn')
        if result.get('state') == 'SUCCEEDED' and result.get('answer'):
            return CheckResult(ok=True, live=True, reply=result['answer'])
        return CheckResult(ok=False, live=True, error_code=result.get('diagnostic_code') or 'turn_not_succeeded',
                           error_message=result.get('state') or 'unknown')
