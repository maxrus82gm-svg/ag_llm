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


class RegisteredProviderWorkspace:
    """One registered, audited Workspace bound to a shared live provider session.

    The provider grant, account OS lock and TLS authority remain in the original
    personal session. This object only scopes an individual Turn/RAW/ledger.
    """
    def __init__(self, registry, session, root, workspace_id):
        from gigachat_runtime import ProviderSession
        if type(session) is not ProviderSession:
            raise ValueError("A real provider-session object is required")
        self.registry, self.session = registry, session
        self.root = Path(root).absolute()
        self.workspace_id = workspace_id
        self.check()

    def check(self):
        from ultra_budget_ledger import BudgetLedger, LedgerDenied
        from .workspace_registry import WorkspaceRegistryError
        self.session.check()
        try:
            record = self.registry.find_by_root(self.root)
            if (record is None or Path(record.workspace_root) != self.root
                    or self.root.resolve(strict=True) != self.root
                    or _core().read_workspace_identity_bounded(self.root).get('workspace_id') != self.workspace_id):
                raise ValueError("Registered Workspace identity changed")
            BudgetLedger(self.root, self.workspace_id).recover()
        except (OSError, ValueError, LedgerDenied, WorkspaceRegistryError):
            raise UltraChatError(409, 'ordinary_workspace_not_enrolled',
                                 'Workspace identity or audit requires review') from None


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
        self._colibri_transport = None

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
    def offline_application(cls, registry, root, fixture, *, colibri_transport=None):
        root = Path(root).absolute()
        if (cls is not OrdinaryProviderFactory or type(fixture) is not OfflineHTTPFixture
                or root.resolve() != root or Path(tempfile.gettempdir()).resolve() not in root.parents
                or registry.storage_root != root / "registry"):
            raise ValueError("Expected the isolated application fixture registry")
        # Reuse the accepted disposable-root/link checks before constructing a server.
        OrdinaryCoreChatService(registry, root, http_fixture=fixture)
        factory = cls()
        factory._registry, factory._root, factory._fixture = registry, root, fixture
        if colibri_transport is not None:
            from .colibri_bridge_transport import OfflineColibriTransport
            if type(colibri_transport) is not OfflineColibriTransport:
                raise ValueError("Explicit isolated Colibri transport required")
        factory._colibri_transport=colibri_transport
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
            # One GigaChat authority, many independent registered chat stores.
            # Never authorize arbitrary filesystem paths or a browser-provided root.
            from .workspace_registry import WorkspaceRegistryError
            scope = Path(root).absolute()
            try:
                record = registry.find_by_root(scope)
                if (record is None or Path(record.workspace_root) != scope
                        or scope.resolve(strict=True) != scope):
                    raise ValueError('Workspace registration changed')
            except (ValueError, OSError, WorkspaceRegistryError):
                raise UltraChatError(403, 'provider_workspace_scope',
                                     'Only registered Workspace roots may use GigaChat') from None
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
        self._connection_failure = None
        if api is not None and factory._fixture is None:
            api.model_cards.gigachat_runtime = self._connection_state
            if factory._session is not None:
                factory._session._model_enabled = api.model_cards.is_enabled
        self._factory = factory
        self._colibri_transport=factory._colibri_transport
        self._colibri_enabled=None
        if self._colibri_transport is not None:
            if api is None or factory._fixture is None:
                raise ValueError("Colibri requires isolated application and shared EVM")
            api.ultra_connections.bind_offline_colibri(self._colibri_transport)
            self._colibri_enabled=api.ultra_connections.enabled_local_targets
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
        from .standard_live import personal_chat_registration
        contract = self._factory.preflight()
        fixture = self._factory._fixture is not None
        personal = personal_chat_registration(self.registry)
        local_context = self._api.model_cards._context() if self._api is not None else None
        state, reason, session, _ = (local_context.get('gigachat_runtime') if local_context is not None else None) or self._connection_state()
        active = state == 'ACTIVE'
        selected_root = self.registry.find_by_root(session.root) if active and not session.synthetic else None
        models = []
        for m in list_model_specs():
            if not m.enabled or m.provider != 'gigachat' or m.is_local:
                continue
            card = self._api.model_cards._card(local_context, m) if local_context is not None else None
            if card is not None and not card['enabled']:
                continue
            availability = ('UNAVAILABLE' if m.provider_model_id not in session._available else
                            'AVAILABLE' if any(c.model_id == m.model_id for c in session.approval.contracts)
                            else 'NOT_APPROVED') if active else state if state != 'INACTIVE' else 'UNVERIFIED'
            if card is not None:
                availability = card['api'].get('availability', availability)
            models.append(dict(model_id=m.model_id, display_name=m.display_name,
                               provider_model_id=m.provider_model_id, availability=availability,
                               api=card['api'] if card is not None else None))
        if self._colibri_transport is not None:
            registry,targets,_state=local_context["snapshot"]
            local={t["target_id"]:t for t in targets}
            # Same EVM switch, no shadow enabled list.
            models.extend(dict(model_id=s.model_id,display_name=s.display_name,
                provider_model_id=s.provider_model_id,provider_id="colibri",is_local=True,
                api=self._api.model_cards._card(local_context,s)["api"],
                availability="AVAILABLE" if s.enabled else "UNAVAILABLE",
                instance_id=local[s.model_id]["instance_id"],
                manager_name=local[s.model_id]["manager_name"],
                slot_id=local[s.model_id]["slot_id"],
                local_status=local[s.model_id]["status"])
                for s in registry.list_model_specs() if s.is_local
                and self._api.model_cards.is_enabled(s.model_id))
        return {**contract, 'available': fixture or active or state == 'RESTORE_REQUIRED',
                'provider_state': state, 'provider_reason': reason, 'real_available': active and not session.synthetic if session else False,
                'mode': 'ORDINARY', 'core_bridge': True, 'chat_preferences': True, 'compact_sidebar': True,
                'execution_mode': ('PROTOCOL_TEST' if session.synthetic else 'REAL') if active else 'OFFLINE_APPLICATION' if fixture else 'HOLD',
                'models': models,
                **({'colibri_offline':True} if self._colibri_transport is not None else {}),
                'personal_workspace_id': personal.workspace_id if personal else None,
                'live_workspace_id': selected_root.workspace_id if selected_root else None}

    @staticmethod
    def _model_path(path):
        return OrdinaryCoreChatService._settings_path(path.removesuffix("/model") + "/settings") if path.endswith("/model") else False

    @staticmethod
    def is_write_path(path):
        from .chat_sidebar import ChatSidebar
        return (ChatSidebar.is_write_path(path) or path in ('/ultra/chat/personal', '/ultra/chat/live/start', '/ultra/chat/live/stop')
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


    def _consent_workspace(self):
        from .live_bootstrap import _verified_workspace
        from .standard_live import personal_chat_registration
        record = personal_chat_registration(self.registry)
        if record is None:
            return None, None, None
        try:
            root, wid = _verified_workspace(self._api, record.workspace_id)
        except Exception:
            raise PreSendDenied('personal_storage_unavailable') from None
        return record, root, wid

    def _connection_state(self):
        from .standard_live import read_standard_consent, standard_approval
        session = self._factory._session
        if session is not None:
            if getattr(session, '_close_error', False):
                return ('BLOCKED', 'provider_session_close_unverified', None, None)
            try:
                session.check()
                if session._available:
                    return ('ACTIVE', None, session, getattr(session, '_permission_revision', None))
            except PreSendDenied as exc:
                if str(exc) != 'provider_session_inactive':
                    return ('BLOCKED', str(exc), None, None)
            except Exception:
                return ('BLOCKED', 'provider_session_state_unverifiable', None, None)
        if self._api is not None and self._factory._fixture is None:
            try:
                _, root, wid = self._consent_workspace()
                consent = read_standard_consent(root, wid, standard_approval()) if root is not None else None
                if consent is not None:
                    return ('RESTORE_REQUIRED', self._connection_failure, None, consent['salt'])
            except PreSendDenied as exc:
                return ('BLOCKED', str(exc), None, None)
        return ('INACTIVE', None, None, None)

    def _open_standard_session(self, *, explicit=False):
        import asyncio
        from gigachat_runtime import ProviderSession
        from .standard_live import read_standard_consent, save_standard_consent, standard_approval, standard_credentials

        current = self._factory._session
        if current is not None:
            try:
                current.check()
            except PreSendDenied as exc:
                renewable = {'provider_session_inactive'}
                if explicit:
                    renewable |= {'consent_policy_changed', 'consent_credentials_changed',
                                  'credentials_or_scope_invalid', 'consent_revoked_or_replaced'}
                if str(exc) not in renewable:
                    raise
                current.close()
                self._factory._session = None
            else:
                if explicit:
                    raise PreSendDenied('live_already_active')
                return current

        _, root, wid = self._consent_workspace()
        if root is None:
            raise PreSendDenied('personal_chat_required')
        approval = standard_approval()
        credential = standard_credentials()
        consent = None if explicit else read_standard_consent(root, wid, approval)
        if not explicit and consent is None:
            raise PreSendDenied('user_permission_required')
        session = ProviderSession(root, wid, approval)

        try:
            if explicit:
                consent = save_standard_consent(root, wid, approval, credential=credential)

            def check_consent():
                if read_standard_consent(root, wid, approval) != consent:
                    raise PreSendDenied('consent_revoked_or_replaced')

            session._check_user_permission = check_consent
            session._permission_revision = consent['salt']
            session._model_enabled = self._api.model_cards.is_enabled
            # Read again under the account lease before any provider I/O.
            check_consent()
            available = asyncio.run(session.discover_models())
            approved = {get_model_spec(c.model_id).provider_model_id for c in approval.contracts}
            if not available.intersection(approved):
                raise PreSendDenied('no_gigachat_models_in_catalog')
        except Exception as exc:
            try:
                session.close()
            except Exception:
                self._factory._session = session
                raise PreSendDenied('live_session_unresolved') from None
            self._connection_failure = str(exc) if isinstance(exc, PreSendDenied) else 'provider_control_request_failed'
            raise PreSendDenied(self._connection_failure) from None
        self._factory._registry = self.registry
        self._factory._session = session
        self._connection_failure = None
        return session

    def start_live(self, body):
        """Explicit owner approval on the established same-origin write route."""
        if type(body) is not dict or body != {'confirmation': 'GIGACHAT 6'}:
            raise UltraChatError(400, 'live_confirmation_required', 'Confirm persistent GigaChat permission')
        if self._api is None or self._factory._fixture is not None:
            raise UltraChatError(403, 'live_unavailable', 'Only normal local STANDARD can start GigaChat')
        if not any(self._api.model_cards.is_enabled(m.model_id) for m in list_model_specs()
                   if m.enabled and m.provider == 'gigachat' and not m.is_local):
            raise UltraChatError(409, 'no_enabled_models', 'Enable a GigaChat model in EVM first')
        from .standard_live import standard_credentials
        try:
            standard_credentials()
        except PreSendDenied:
            raise UltraChatError(409, 'live_credentials_missing',
                                 'Configure the existing GIGACHAT_CREDENTIALS and PERS profile, then restart STANDARD') from None
        with self._personal_lock:
            try:
                session = self._open_standard_session(explicit=True)
            except PreSendDenied as exc:
                raise UltraChatError(409, str(exc), 'GigaChat: ' + str(exc)) from None
            except Exception:
                raise UltraChatError(503, 'live_storage_unavailable', 'Provider state requires storage review') from None
            return 200, {'state': 'ACTIVE', 'limits': {'sends': 'PER_USER_TURN',
                         'output_tokens': session.approval.max_answer_tokens,
                         'request_bytes': session.approval.max_request_bytes},
                         'models': self.capability()['models']}

    def stop_live(self, body):
        """Revoke consent even when the runtime has already stopped."""
        if type(body) is not dict or body:
            raise UltraChatError(400, 'invalid_ultra_chat_request', 'Expected empty stop request')
        if self._api is None or self._factory._fixture is not None:
            raise UltraChatError(403, 'live_unavailable', 'Only normal local STANDARD can stop GigaChat')
        from gigachat_runtime import account_owner_lock
        from .standard_live import save_standard_consent, standard_approval
        with self._personal_lock:
            session = self._factory._session
            try:
                _, root, wid = self._consent_workspace()

                def revoke():
                    if root is not None:
                        save_standard_consent(root, wid)

                if session is not None:
                    session.close(before_release=revoke)
                elif root is not None:
                    owner = account_owner_lock(standard_approval().account_id)
                    owner.acquire()
                    try:
                        revoke()
                    finally:
                        owner.release()
            except PreSendDenied as exc:
                raise UltraChatError(409, 'live_session_busy', 'GigaChat: ' + str(exc)) from None
            except Exception:
                raise UltraChatError(503, 'live_storage_unavailable', 'Provider state requires storage review') from None
            self._factory._session = None
            self._connection_failure = None
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

    def _default_model(self):
        session = self._factory._session
        if session is not None and not session.synthetic and len(session.approval.contracts) == 1:
            return session.approval.contracts[0].model_id
        return MODEL_ID

    def chat_model(self, wa_workspace_id, chat_id, update=...):
        allowed = {m.model_id for m in list_model_specs() if m.enabled and m.provider == 'gigachat' and not m.is_local}
        local_ids=set()
        if self._colibri_transport is not None:
            reg,_,_=self._api.ultra_connections.registry_snapshot()
            local_ids={s.model_id for s in reg.list_model_specs() if s.is_local and s.enabled}
        if update is not ... and (type(update) is not dict or set(update) != {'model_ref'}
                or type(update['model_ref']) is not str or update['model_ref'] not in allowed|local_ids
                or self._api is not None and not self._api.model_cards.is_enabled(update['model_ref'])):
            raise UltraChatError(400, "ordinary_model_not_allowed", "Select the admitted model")
        core = _core()
        root, wid = self._writable_workspace(core, wa_workspace_id)
        try:
            with core._existing_workspace_writer(root, wid) as writer:
                parts, metadata = core._require_chat_for_write(writer, chat_id)
                enrolled = True
                if self._factory._fixture is None:
                    # Reads never enroll. Explicit model selection is the local
                    # consent point to initialize an empty audit, preserving all
                    # old Run/RAW/UNKNOWN and rejecting a damaged audit.
                    from ultra_budget_ledger import BudgetLedger, LedgerDenied
                    try:
                        ledger = BudgetLedger(root, wid)
                        if update is ...:
                            ledger.recover()
                        else:
                            ledger.initialize()
                    except LedgerDenied:
                        enrolled = False
                fallback = self._default_model()
                selected = metadata.get("ordinary_chat_model", fallback) if update is ... else update['model_ref']
                import re
                saved_local=type(selected) is str and re.fullmatch(r"tgt_[a-f0-9]{64}",selected)
                if selected not in allowed and not saved_local:
                    raise UltraChatError(409, "ordinary_model_invalid", "Saved model requires review")
                if update is not ... and metadata.get('ordinary_chat_model') != selected:
                    core._replace_verified(writer.anchor, parts + ("metadata.json",),
                        core._json_bytes({**metadata, "ordinary_chat_model": selected}))
                return {"model_ref": selected, "persisted": "ordinary_chat_model" in metadata or update is not ...,
                        "enabled": self._api is None or self._api.model_cards.is_enabled(selected),
                        "enrolled": enrolled,
                        **({"availability":"AVAILABLE" if selected in local_ids else "UNAVAILABLE"}
                           if saved_local else {})}
        except (core.StorageWriteError, core.ChatNotFoundError, OSError, ValueError):
            raise UltraChatError(503, "ordinary_model_unavailable", "Chat model could not be verified") from None

    def submit_turn(self, wa_workspace_id, chat_id, body, *, diagnostic=False):
        if type(body) is not dict or set(body) != {"idempotency_key", "model_ref", "text"}:
            raise UltraChatError(400, "invalid_turn_request", "Expected model, text and retry key")
        registry_allowed = {m.model_id for m in list_model_specs() if m.enabled and m.provider == 'gigachat' and not m.is_local}
        import re
        ref=body.get("model_ref")
        local=type(ref) is str and re.fullmatch(r"tgt_[a-f0-9]{64}",ref) is not None
        if type(ref) is not str or (ref not in registry_allowed and not local):
            raise UltraChatError(400, "ordinary_model_not_allowed", "Select the admitted model")
        if local and self._colibri_transport is None:
            # Only a previously accepted local Turn may be replayed read-only.
            from .turn_service import KEY, TurnService, identities
            key=body.get("idempotency_key")
            if type(key) is not str or not KEY.fullmatch(key):
                raise UltraChatError(403,"local_provider_unavailable","Local provider is not enabled")
            root,wid=self._writable_workspace(_core(),wa_workspace_id)
            reader=TurnService(test_roots=[root])
            try:
                with reader._session(root,wid,chat_id):
                    previous=reader._load(root,wid,chat_id,identities(wid,chat_id,key)["turn_id"])
                    if previous["schema_version"]!=3:
                        raise UltraChatError(403,"local_provider_unavailable","Local provider is not enabled")
            except UltraChatError:
                raise UltraChatError(403,"local_provider_unavailable","Local provider is not enabled") from None
        replay = None
        if self._factory._fixture is None and not local:
            replay = self._prepare_standard_turn(wa_workspace_id, chat_id, body)
        elif self._api is not None and not self._api.model_cards.is_enabled(body['model_ref']):
            from .turn_service import KEY, TurnService, identities
            accepted = False
            key = body.get('idempotency_key')
            if type(key) is str and KEY.fullmatch(key):
                root, wid = self._writable_workspace(_core(), wa_workspace_id)
                reader = TurnService(test_roots=[root])
                try:
                    with reader._session(root, wid, chat_id):
                        reader._load(root, wid, chat_id, identities(wid, chat_id, key)['turn_id'])
                    accepted = True
                except UltraChatError as exc:
                    if exc.code not in ('turn_not_found', 'turn_acceptance_incomplete'):
                        raise
            if not accepted:
                raise UltraChatError(403, "ordinary_model_disabled", "Model is disabled in EVM")
        # Preserve the existing Turn/error contract: the immutable admitted wire
        # is refused by session.validate_wire before physical POST for an absent
        # catalog model; UI availability alone must not change stored outcomes.
        root, _ = self._writable_workspace(_core(), wa_workspace_id)
        self._factory.fixture_for(self.registry, root)
        result = replay if replay is not None else super().submit_turn(wa_workspace_id, chat_id, body)
        if (self._api is not None and result.get('execution_mode') == 'REAL'
                and type(result.get('evm_profile')) is dict):
            try:
                if result.get('state') == 'SUCCEEDED':
                    synced = self._api.model_cards.record_chat_success(body['model_ref'],
                        result['evm_profile']['settings_version'], turn_id=result['turn_id'], diagnostic=diagnostic)
                elif result.get('state') == 'UNKNOWN':
                    synced = self._api.model_cards.record_chat_unknown(body['model_ref'],
                        result['evm_profile']['settings_version'], turn_id=result['turn_id'], diagnostic=diagnostic)
                elif result.get('state') == 'FAILED':
                    synced = self._api.model_cards.record_chat_failure(body['model_ref'],
                        result['evm_profile']['settings_version'],
                        code=result.get('diagnostic_code') or result['state'].lower(), turn_id=result['turn_id'],
                        diagnostic=diagnostic)
                else:
                    synced = False
                result = {**result, 'evm_status_sync': 'UPDATED' if synced else 'NO_CHANGE'}
            except Exception:
                # The committed Turn/RAW/ledger must remain readable even if
                # the secondary EVM indicator store needs repair.
                result = {**result, 'evm_status_sync': 'UNAVAILABLE'}
        return self._application_view(result)

    def _prepare_standard_turn(self, wa_workspace_id, chat_id, body):
        from .turn_service import TurnService
        from ultra_budget_ledger import BudgetLedger, LedgerDenied

        root, wid = self._writable_workspace(_core(), wa_workspace_id)
        reader = TurnService(test_roots=[root])
        session = self._factory._session
        provider_mode = 'PROTOCOL_TEST' if session is not None and session.synthetic else 'REAL'
        replay = reader.recover_existing_ordinary(root, wid, chat_id, body, provider_mode=provider_mode)
        if replay is not None:
            return replay
        if self._api is not None and not self._api.model_cards.is_enabled(body['model_ref']):
            raise UltraChatError(403, 'ordinary_model_disabled', 'Model is disabled in EVM')
        connection, reason, _, _ = self._connection_state()
        if connection in ('INACTIVE', 'BLOCKED'):
            raise UltraChatError(403, 'ordinary_real_hold', 'GigaChat: ' + (reason or 'user_permission_required'))
        selected = self.chat_model(wa_workspace_id, chat_id)
        if selected['model_ref'] != body['model_ref']:
            raise UltraChatError(409, 'ordinary_model_selection_changed', 'Chat model changed; reload the saved selection')
        try:
            BudgetLedger(root, wid).initialize()
        except LedgerDenied:
            raise UltraChatError(409, 'ordinary_workspace_not_enrolled',
                                 'Workspace audit needs review before sending') from None
        with self._personal_lock:
            try:
                self._open_standard_session()
                self._factory.require_real()
            except PreSendDenied as exc:
                self._connection_failure = str(exc)
                raise UltraChatError(403, 'ordinary_real_hold', 'GigaChat: ' + str(exc)) from None
            except Exception:
                raise UltraChatError(503, 'live_storage_unavailable', 'Provider state requires storage review') from None
        return None

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

    def chats(self, wa_workspace_id):
        listing = super().chats(wa_workspace_id)
        core = _core()
        root = self._registration(wa_workspace_id).workspace_root
        for item in listing['chats']:
            if item['status'] != 'ok':
                continue
            try:
                history = core.read_chat_history_bounded(root, item['chat_id'])
            except core.StorageReadError:
                continue
            item['last_activity_at'] = max((m['created_at'] for m in history['messages']),
                                           default=None)
        return listing

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
                page['usage_summary'] = self._project_message_usage(wa_workspace_id, chat_id, page)
            except (UltraChatError, OSError, ValueError, KeyError, TypeError):
                page['usage_summary'] = {'available': False, 'synthetic': False}
        page['usage_summary']['synthetic'] = bool(self._factory._fixture is not None
            or self._factory._session and self._factory._session.synthetic)
        if page['usage_summary'].get('attempts') == 0:
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
        model_id = self._default_model()
        answer = session.approval.max_answer_tokens
        if chat_id:
            identity = _core().read_workspace_identity_bounded(root)
            workspace_id = identity.get('workspace_id') if identity.get('status') == 'ok' else None
            if not workspace_id:
                raise UltraChatError(409, 'workspace_unavailable', 'Workspace identity needs review')
            with _core()._existing_workspace_writer(root, workspace_id) as writer:
                _, metadata = _core()._require_chat_for_write(writer, chat_id)
                model_id = metadata.get('ordinary_chat_model', model_id)
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
        scope = (None if Path(root).absolute() == session.root and workspace_id == session.workspace_id
                 else RegisteredProviderWorkspace(self.registry, session, root, workspace_id))
        return TurnService(test_roots=[root], offline_adapter=adapter, provider_session=session,
                           provider_workspace=scope)


class _OrdinaryTurnChecker:
    """EVM check uses the visible Ordinary Chat Turn, never a second sender."""
    def __init__(self, service):
        self.service = service

    @property
    def authorized(self):
        state, _, session, _ = self.service._connection_state()
        return state == 'RESTORE_REQUIRED' or (state == 'ACTIVE' and not session.synthetic)

    @property
    def reason(self):
        state, reason, _, _ = self.service._connection_state()
        if state == 'BLOCKED':
            return 'GigaChat: ' + reason
        return "Провайдер не подключён. Подключите GigaChat в EVM." if state == 'INACTIVE' else ""

    def check(self, request):
        from uuid import uuid4
        from .model_cards import CheckRefusedError, CheckResult
        from .standard_live import personal_chat_registration
        if not self.authorized or request.provider_id != 'gigachat':
            raise CheckRefusedError('A verified provider permission is required')
        try:
            with self.service._personal_lock:
                session = self.service._open_standard_session()
        except PreSendDenied as exc:
            raise CheckRefusedError('GigaChat: ' + str(exc)) from None
        if (session.synthetic
                or request.model_id not in {c.model_id for c in session.approval.contracts}
                or request.provider_model_id not in session._available):
            raise CheckRefusedError('A verified active provider session is required')
        try:
            self.service._factory.require_real()
        except PreSendDenied:
            raise CheckRefusedError('Provider session is not active; no check Turn was submitted') from None
        record = personal_chat_registration(self.service.registry)
        if record is None or Path(record.workspace_root).resolve() != session.root:
            raise CheckRefusedError('Personal chat Workspace is not the approved provider Workspace')
        chat_id = 'chat_' + uuid4().hex
        self.service.create_chat(record.workspace_id,
            {'chat_id': chat_id, 'title': 'Проверка EVM — ' + request.model_id})
        self.service.chat_model(record.workspace_id, chat_id, {'model_ref': request.model_id})
        result = self.service.submit_turn(record.workspace_id, chat_id,
            {'idempotency_key': uuid4().hex, 'model_ref': request.model_id, 'text': request.message}, diagnostic=True)
        if result.get('execution_mode') != 'REAL':
            raise CheckRefusedError('The provider did not execute a real Turn')
        if result.get('state') == 'SUCCEEDED' and result.get('answer'):
            return CheckResult(ok=True, live=True, reply=result['answer'], turn_id=result.get('turn_id'))
        return CheckResult(ok=False, live=True, error_code=result.get('diagnostic_code') or 'turn_not_succeeded',
                           error_message=result.get('state') or 'unknown',
                           uncertain=result.get('state') == 'UNKNOWN', turn_id=result.get('turn_id'))
