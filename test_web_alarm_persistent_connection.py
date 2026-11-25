"""STANDARD lifecycle against the existing protocol over MockTransport only."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import platform
import tempfile
import time
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

import context_storage as core
import gigachat_transport as oauth
from gigachat_runtime import MODELS_URL, ProviderSession
from model_registry import list_model_specs
from ultra_budget_ledger import BudgetLedger
from web_alarm.ordinary_provider import OrdinaryApplicationChatService, OrdinaryProviderFactory
from web_alarm.server import WebAlarmApi
from web_alarm.standard_live import OBSERVED_MODEL, prepare_personal_chat
from web_alarm.turn_service import TurnService
from web_alarm.ultra_chat import UltraChatError


@pytest.fixture
def studio(tmp_path, monkeypatch):
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    monkeypatch.setenv("GIGACHAT_CREDENTIALS", "SYNTHETIC")
    monkeypatch.setenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")
    monkeypatch.setattr(oauth, "_access_token", None)
    trace, owners = [], []
    fault = {"catalog": False, "inference": False, "usage": True}

    async def handle(request):
        url = str(request.url)
        trace.append(url)
        if url == oauth.OAUTH_URL:
            return httpx.Response(200, json={
                "access_token": "SYNTHETIC-TOKEN", "expires_at": int((time.time() + 120) * 1000),
            })
        if url == MODELS_URL:
            if fault["catalog"]:
                raise httpx.ConnectError("synthetic outage")
            return httpx.Response(200, json={"data": [{"id": m.provider_model_id} for m in list_model_specs()]})
        assert url == oauth.CHAT_URL
        if fault["inference"]:
            raise httpx.ReadTimeout("synthetic lost response")
        model = json.loads(request.content)["model"]
        result = {"model": OBSERVED_MODEL if model == "GigaChat-2" else model,
                  "choices": [{"message": {"role": "assistant", "content": "Synthetic answer"}}]}
        if fault["usage"]:
            result["usage"] = {"prompt_tokens": 8, "completion_tokens": 4, "total_tokens": 12}
        return httpx.Response(200, json=result)

    def synthetic_init(self, root, wid, approval):
        self._setup(root, wid, approval, transport=httpx.MockTransport(handle),
                    credentials=("SYNTHETIC", "GIGACHAT_API_PERS"))
        owners.append(self)

    monkeypatch.setattr(ProviderSession, "__init__", synthetic_init)
    recover = TurnService.recover_existing_ordinary

    def recover_mock_turn(self, *args, provider_mode):
        # The HTTP fixture lives entirely in the PROTOCOL_TEST namespace,
        # including after it simulates a process restart with no sender.
        return recover(self, *args, provider_mode="PROTOCOL_TEST")

    monkeypatch.setattr(TurnService, "recover_existing_ordinary", recover_mock_turn)

    def boot():
        api = WebAlarmApi(tmp_path / "registry")
        return api, OrdinaryApplicationChatService(api.registry, OrdinaryProviderFactory(), api=api)

    try:
        yield boot, trace, fault
    finally:
        # A simulated process death releases its lease without writing CLOSED.
        for owner in reversed(owners):
            if owner._owner_lock.handle is not None:
                owner.close()


def personal(api):
    record, root, wid = prepare_personal_chat(api)
    return record.workspace_id, root, wid, core.list_chats_bounded(root)["chats"][0]["chat_id"]


def message(text="Hello", model="gigachat_2_pro"):
    return {"idempotency_key": uuid4().hex, "model_ref": model, "text": text}


def allow(app):
    assert app.start_live({"confirmation": "GIGACHAT 6"})[1]["state"] == "ACTIVE"


def test_restart_expiry_and_oauth_refresh_do_not_repeat_inference(studio, monkeypatch):
    boot, trace, _ = studio
    api, first = boot()
    ws, root, wid, cid = personal(api)
    assert first.capability()["provider_state"] == "INACTIVE"
    assert trace == []
    allow(first)
    assert trace == [oauth.OAUTH_URL, MODELS_URL]
    old = first._factory._session
    old.close()

    api, next_app = boot()
    assert next_app.capability()["provider_state"] == "RESTORE_REQUIRED"
    assert next_app.capability()["available"]
    assert trace.count(MODELS_URL) == 1
    request = message()
    assert next_app.submit_turn(ws, cid, request)["state"] == "SUCCEEDED"
    assert trace.count(oauth.CHAT_URL) == 1
    assert len(BudgetLedger(root, wid).recover().attempts) == 1
    old = next_app._factory._session
    old.approval = replace(old.approval, expires_at=time.time() - 1)
    monkeypatch.setattr(oauth, "_access_token_valid_until", time.time() - 1)
    assert next_app.capability()["provider_state"] == "RESTORE_REQUIRED"
    assert next_app.submit_turn(ws, cid, request)["state"] == "SUCCEEDED"
    assert trace.count(oauth.CHAT_URL) == 1
    assert next_app.submit_turn(ws, cid, message("Second"))["state"] == "SUCCEEDED"
    assert trace.count(oauth.CHAT_URL) == 2
    assert trace.count(oauth.OAUTH_URL) == 2
    assert len(BudgetLedger(root, wid).recover().attempts) == 2


def test_crash_owner_fencing_outage_and_unfinished_turn(studio):
    boot, trace, fault = studio
    api, first = boot()
    ws, root, wid, cid = personal(api)
    allow(first)
    api, second = boot()
    assert second.capability()["provider_state"] == "RESTORE_REQUIRED"
    with pytest.raises(UltraChatError, match="account_owner_live"):
        second.submit_turn(ws, cid, message())
    assert oauth.CHAT_URL not in trace
    fault["inference"] = True
    request = message("Physical outcome unknown")
    assert first.submit_turn(ws, cid, request)["state"] == "UNKNOWN"
    assert trace.count(oauth.CHAT_URL) == 1
    crashed = first._factory._session
    crashed._owner_lock.release()
    assert second.submit_turn(ws, cid, request)["state"] == "UNKNOWN"
    assert trace.count(MODELS_URL) == 1

    fault["catalog"] = True
    fresh = message("After recovery")
    with pytest.raises(UltraChatError, match="provider_control_request_failed"):
        second.submit_turn(ws, cid, fresh)
    assert trace.count(oauth.CHAT_URL) == 1
    assert second.capability()["provider_state"] == "RESTORE_REQUIRED"
    assert (root / ".ultra/provider_sessions" / f"recovery_{crashed.approval.grant_id}.json").is_file()
    fault.update(catalog=False, inference=False)
    assert second.submit_turn(ws, cid, fresh)["state"] == "SUCCEEDED"
    assert trace.count(oauth.CHAT_URL) == 2
    assert len(BudgetLedger(root, wid).recover().attempts) == 2


def test_key_change_and_revoke_while_stopped(studio, monkeypatch):
    boot, trace, _ = studio
    api, app = boot()
    ws, _, _, cid = personal(api)
    allow(app)
    app._factory._session.close()
    api, app = boot()
    monkeypatch.setenv("GIGACHAT_CREDENTIALS", "NEW-SYNTHETIC")
    assert app.capability()["provider_reason"] == "consent_credentials_changed"
    with pytest.raises(UltraChatError, match="consent_credentials_changed"):
        app.submit_turn(ws, cid, message())
    assert trace == [oauth.OAUTH_URL, MODELS_URL]
    assert app.stop_live({}) == (200, {"state": "INACTIVE"})
    monkeypatch.setenv("GIGACHAT_CREDENTIALS", "SYNTHETIC")
    api, app = boot()
    assert app.capability()["provider_state"] == "INACTIVE"
    with pytest.raises(UltraChatError, match="user_permission_required"):
        app.submit_turn(ws, cid, message())
    assert trace == [oauth.OAUTH_URL, MODELS_URL]


def test_copied_consent_cannot_activate_on_another_host(studio, monkeypatch):
    boot, trace, _ = studio
    api, app = boot()
    ws, _, _, cid = personal(api)
    allow(app)
    app._factory._session.close()
    monkeypatch.setattr(platform, "node", lambda: "another-fixture-host.invalid")
    _, reopened = boot()
    assert reopened.capability()["provider_reason"] == "consent_policy_changed"
    with pytest.raises(UltraChatError, match="consent_policy_changed"):
        reopened.submit_turn(ws, cid, message())
    assert trace == [oauth.OAUTH_URL, MODELS_URL]


def test_first_workspace_turn_preserves_selection_usage_and_activity(studio):
    boot, trace, fault = studio
    api, app = boot()
    personal(api)
    allow(app)
    folder = Path(api.registry.storage_root).parent / "project"
    folder.mkdir()
    ws = api.registry.register("Synthetic workspace", folder).workspace_id
    cid = "chat_" + uuid4().hex
    app.create_chat(ws, {"chat_id": cid, "initialize_workspace": True})
    assert not app.chat_model(ws, cid)["enrolled"]
    assert app.messages(ws, cid, None, 50)["usage_summary"]["attempts"] == 0
    assert app.chats(ws)["chats"][0]["last_activity_at"] is None
    assert app.submit_turn(ws, cid, message())["state"] == "SUCCEEDED"
    result = app.chat_model(ws, cid, {"model_ref": "gigachat_ultra"})
    assert result["enrolled"] and result["persisted"]
    fault["usage"] = False
    assert app.submit_turn(ws, cid, message("Without usage", "gigachat_ultra"))["state"] == "SUCCEEDED"
    raw = core.read_chat_history_bounded(folder, cid)["messages"]
    assert len(raw) == 4
    assert app.chats(ws)["chats"][0]["last_activity_at"] == raw[-1]["created_at"]
    summary = app.messages(ws, cid, None, 50)["usage_summary"]
    assert summary["known"]["total_tokens"] == 12
    assert summary["missing"]["total_tokens"] == 1 and not summary["complete"]
    app._factory._session.close()
    _, reopened = boot()
    assert reopened.chat_model(ws, cid)["model_ref"] == "gigachat_ultra"
    assert reopened.messages(ws, cid, None, 50)["usage_summary"]["known"]["total_tokens"] == 12
    assert trace.count(oauth.CHAT_URL) == 2


def test_cards_use_runtime_and_freshness_without_blocking_orange_send(studio):
    boot, trace, _ = studio
    api, app = boot()
    personal(api)
    model = "gigachat_2_pro"
    cards = api.model_cards
    now = datetime(2026, 11, 25, tzinfo=timezone.utc)
    cards.now = lambda: now
    allow(app)
    card = cards.card(model)
    assert card["api"]["color"] == "orange"
    cards.record_chat_success(model, card["settings_version"], turn_id="turn_" + uuid4().hex)
    state = cards.card(model)["api"]
    assert state["color"] == "green"
    now += timedelta(days=30, seconds=1)
    state = cards.card(model)["api"]
    assert (state["color"], state["reason"]) == ("orange", "STALE")
    assert app.capability()["available"]
    cards.record_chat_failure(model, card["settings_version"], code="provider_http_401",
                              turn_id="turn_" + uuid4().hex)
    assert cards.card(model)["api"]["color"] == "red"
    revision = cards.catalog()["settings"]["revision"]
    cards.set_enabled(model, {"base_revision": revision, "enabled": False})
    assert cards.card(model)["api"]["color"] == "gray"
    assert model not in {m["model_id"] for m in app.capability()["models"]}
    assert oauth.CHAT_URL not in trace
