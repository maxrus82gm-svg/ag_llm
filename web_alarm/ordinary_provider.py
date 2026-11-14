"""STANDARD Ordinary Chat integration and closed one-model provider preflight.

No REAL authority is minted by this revision. The only executable factory is an
explicit TEMP-bound HTTP fixture used by author/independent application tests.
All execution, persistence and accounting remain in the accepted H32/H33 core.
"""
from pathlib import Path
import tempfile
import threading

from model_registry import get_model_spec
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
        require_real_authority()
        raise PreSendDenied("real_provider_authority_unavailable")

    def validate_server(self, registry):
        if type(self) is not OrdinaryProviderFactory:
            raise ValueError("Expected the exact server factory")
        if self._fixture is not None:
            if registry is not self._registry or type(self._fixture) is not OfflineHTTPFixture:
                raise ValueError("Application fixture scope changed")
            OrdinaryCoreChatService(registry, self._root, http_fixture=self._fixture)

    def fixture_for(self, registry, root):
        self.validate_server(registry)
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
    def __init__(self, registry, factory):
        if type(factory) is not OrdinaryProviderFactory:
            raise ValueError("Expected the exact server factory")
        factory.validate_server(registry)
        UltraChatService.__init__(self, registry)
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
        model = get_model_spec(MODEL_ID)
        fixture = self._factory._fixture is not None
        return {**contract, "available": fixture, "mode": "ORDINARY", "core_bridge": True,
                "execution_mode": "OFFLINE_APPLICATION" if fixture else "HOLD",
                "chat_preferences": True, "models": [{"model_id": model.model_id,
                    "display_name": model.display_name, "provider_model_id": model.provider_model_id}]}

    @staticmethod
    def _model_path(path):
        return OrdinaryCoreChatService._settings_path(path.removesuffix("/model") + "/settings") if path.endswith("/model") else False

    @staticmethod
    def is_write_path(path):
        return (OrdinaryApplicationChatService._model_path(path)
                or OrdinaryCoreChatService._settings_path(path) or UltraChatService.is_write_path(path))

    def create_workspace(self, body):
        raise UltraChatError(405, "method_not_allowed", "Use normal Workspace registration")

    def route(self, path, raw_query):
        if self._model_path(path):
            ws, cid = self._settings_route(path, raw_query)
            return lambda: self.chat_model(ws, cid)
        return super().route(path, raw_query)

    def write_route(self, path, raw_query):
        if path == "/ultra/chat/workspaces":
            raise UltraChatError(405, "method_not_allowed", "Use normal Workspace registration")
        if self._model_path(path):
            ws, cid = self._settings_route(path, raw_query)
            return lambda body: (200, self.chat_model(ws, cid, body))
        return super().write_route(path, raw_query)

    def chat_model(self, wa_workspace_id, chat_id, update=...):
        if update is not ... and (type(update) is not dict or update != {"model_ref": MODEL_ID}):
            raise UltraChatError(400, "ordinary_model_not_allowed", "Select the admitted model")
        core = _core()
        root, wid = self._writable_workspace(core, wa_workspace_id)
        try:
            with core._existing_workspace_writer(root, wid) as writer:
                parts, metadata = core._require_chat_for_write(writer, chat_id)
                selected = metadata.get("ordinary_chat_model", MODEL_ID)
                if selected != MODEL_ID:
                    raise UltraChatError(409, "ordinary_model_invalid", "Saved model requires review")
                if update is not ... and "ordinary_chat_model" not in metadata:
                    core._replace_verified(writer.anchor, parts + ("metadata.json",),
                        core._json_bytes({**metadata, "ordinary_chat_model": MODEL_ID}))
                return {"model_ref": selected, "persisted": "ordinary_chat_model" in metadata or update is not ...}
        except (core.StorageWriteError, core.ChatNotFoundError, OSError, ValueError):
            raise UltraChatError(503, "ordinary_model_unavailable", "Chat model could not be verified") from None

    def submit_turn(self, wa_workspace_id, chat_id, body):
        if type(body) is not dict or set(body) != {"idempotency_key", "model_ref", "text"}:
            raise UltraChatError(400, "invalid_turn_request", "Expected model, text and retry key")
        if type(body) is dict and body.get("model_ref") != MODEL_ID:
            raise UltraChatError(400, "ordinary_model_not_allowed", "Select the admitted model")
        if self._factory._fixture is None:
            try:
                self._factory.require_real()
            except PreSendDenied:
                raise UltraChatError(403, "ordinary_real_hold", "GigaChat sending awaits provider and safety acceptance") from None
        root, _ = self._writable_workspace(_core(), wa_workspace_id)
        self._factory.fixture_for(self.registry, root)
        result = super().submit_turn(wa_workspace_id, chat_id, body)
        return self._application_view(result)

    @staticmethod
    def _application_view(result):
        # Durable TEST_OFFLINE provenance is retained; only the browser envelope
        # names its actual application route. No synthetic result is called REAL.
        return {**result, "mode": "ORDINARY", "execution_mode": "OFFLINE_APPLICATION"}

    def _turn_request(self, action, wa_workspace_id, chat_id, value, body=None):
        result = super()._turn_request(action, wa_workspace_id, chat_id, value, body)
        return result if action == "submit" else self._application_view(result)

    def latest_turn(self, wa_workspace_id, chat_id):
        if self._factory._fixture is None:
            raise UltraChatError(403, "ordinary_real_hold", "Provider Turn recovery awaits safety acceptance")
        result = super().latest_turn(wa_workspace_id, chat_id)
        return {**result, "turn": self._application_view(result["turn"]) if result["turn"] else None}

    def messages(self, wa_workspace_id, chat_id, before, limit):
        if self._factory._fixture is not None:
            return super().messages(wa_workspace_id, chat_id, before, limit)
        page = UltraChatService.messages(self, wa_workspace_id, chat_id, before, limit)
        page["usage_summary"] = {"available": False, "synthetic": False}
        return page
