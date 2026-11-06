"""Offline Turn through the real S4A core, using only synthetic fixtures."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import context_storage as core
import gigachat_transport
import httpx
import model_registry
import ordinary_chat_service as ordinary
import run_store as runs
from ordinary_chat_service import RequestLimits
from web_alarm.ordinary_chat_test_adapter import OfflineTestAdapter, _FixtureTransport
from web_alarm.turn_service import ANSWER, REFERENCES, TurnService, identities
from web_alarm.ultra_chat import UltraChatError


def reply(**fields):
    return {"choices": [{"message": {"role": "assistant", "content": "Fake answer"}}],
            **fields}


CRASH_CHILD = """
import json, os, sys
from ordinary_chat_service import RequestLimits
from web_alarm.ordinary_chat_test_adapter import OfflineTestAdapter, _FixtureTransport
from web_alarm.turn_service import TurnService
root, ws, chat, body, phase = sys.argv[1:]
adapter = OfflineTestAdapter(context=(), context_ref="fixture:v1",
    limits=RequestLimits(9, 2048, 8192, 8192, 64, 2),
    response={"choices":[{"message":{"role":"assistant","content":"Fake answer"}}]})
service = TurnService(test_roots=[root], offline_adapter=adapter)
if phase == "during_send":
    async def send(*args, **kwargs):
        os._exit(71)
    _FixtureTransport.send = send
else:
    commit = service._commit
    def stop(root, turn, role, text):
        if role == "user" and phase == "before_user":
            os._exit(72)
        commit(root, turn, role, text)
        if role == "assistant":
            os._exit(73)
    service._commit = stop
service.submit(root, ws, chat, json.loads(body))
"""


class OfflineTurnTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="s4b_")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / "workspace"
        self.root.mkdir()
        self.ws = core.ensure_workspace_storage(self.root)["workspace_id"]
        self.chat = core.create_chat(self.root)["chat_id"]
        self.body = dict(idempotency_key="s4b_key_00000000001", text="Вопрос 😀",
                         model_ref="gigachat_2_pro", context_ref="fixture:v1",
                         config_ref="s4b-offline:v1")
        self.service = self.reopen()

    def reopen(self, **options):
        config = dict(context=(), context_ref="fixture:v1", limits=RequestLimits(9, 2048, 8192, 8192, 64, 2),
                      response=reply())
        adapter = OfflineTestAdapter(**{**config, **options})
        return TurnService(test_roots=[self.root], offline_adapter=adapter)

    def submit(self, **body):
        return self.service.submit(self.root, self.ws, self.chat, {**self.body, **body})

    def ids(self):
        return identities(self.ws, self.chat, self.body["idempotency_key"])

    def get(self):
        return self.service.get(self.root, self.ws, self.chat, self.ids()["turn_id"])

    def events(self):
        return runs.load_stream_records(self.root, self.ids()["run_id"], "SERVER")

    def raw(self):
        return {p.name: p.read_bytes() for p in
                (self.root / ".ultra/chats" / self.chat / "messages").glob("*.json")}

    def disk(self):
        return {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}

    def test_fake_answer_survives_reopen(self):
        result = self.submit()
        self.assertEqual((result["state"], result["answer"]), ("SUCCEEDED", "Fake answer"))
        self.service = self.reopen()
        self.assertEqual(self.service.get(self.root, self.ws, self.chat, result["turn_id"]), result)

    def test_s4a_wire_durable_start_and_replay(self):
        self.service = self.reopen(context=[{"role": "system", "content": "Fixture"}],
                                   response=reply(usage={"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7}))
        wires = []
        async def send(_fake, payload, *, timeout_seconds):
            wires.append(payload)
            self.assertEqual(len(self.raw()), 1)
            self.assertEqual([r["event"] for r in self.events()], ["turn_started"])
            return reply(usage={"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7})
        with (patch.object(_FixtureTransport, "send", send),
              patch.object(ordinary, "execute_request", wraps=ordinary.execute_request) as s4a,
              patch.object(self.service, "_imitate", side_effect=AssertionError("legacy path")) as legacy):
            first = self.submit()
            before = self.disk()
            self.assertEqual(self.submit(), first)
            with self.assertRaises(UltraChatError) as conflict:
                self.submit(text="Changed")
            self.assertEqual(conflict.exception.code, "idempotency_conflict")
            self.assertEqual(self.disk(), before)
        s4a.assert_called_once()
        legacy.assert_not_called()
        self.assertEqual(wires, [{"model": "GigaChat-2-Pro", "stream": False, "max_tokens": 64,
                                 "messages": [{"role": "system", "content": "Fixture"},
                                              {"role": "user", "content": self.body["text"]}]}])
        self.assertEqual(first["usage"]["total_tokens"], 7)
        start, result = [record["payload"] for record in self.events()]
        self.assertEqual(start["attempt_id"], first["attempt_id"])
        self.assertEqual(result["request_ref"], first["request_ref"])
        self.assertEqual(result["binding_sha256"], start["binding_sha256"])
        self.assertEqual(json.loads(self.raw()[first["assistant_message_id"] + ".json"])["original_text"], "Fake answer")

    def test_ready_snapshot_survives_adapter_settings_change(self):
        self.service = self.reopen(context=[{"role": "system", "content": "Frozen"}])
        with patch.object(self.service, "_execute", side_effect=lambda *args: self.get()):
            ready = self.submit()
        self.assertEqual(ready["state"], "READY")
        self.service = self.reopen(context=[{"role": "system", "content": "New setting"}],
                                   context_ref="new", limits=RequestLimits(4, 256, 2048, 2048, 8, 1))
        original = _FixtureTransport.send
        with patch.object(_FixtureTransport, "send", autospec=True, side_effect=original) as transport:
            done = self.submit()
        self.assertEqual(done["state"], "SUCCEEDED")
        self.assertEqual(done["request_ref"], ready["request_ref"])
        self.assertEqual(transport.call_args.args[1]["messages"][0]["content"], "Frozen")
        self.assertEqual(transport.call_args.args[1]["max_tokens"], 64)

    def test_invalid_model_context_and_authority_do_not_write(self):
        before = self.disk()
        with patch.object(_FixtureTransport, "send") as transport:
            for changes in (dict(model_ref="unknown"), dict(context_ref="foreign"), dict(text="x"*2049)):
                with self.subTest(changes=changes), self.assertRaises(UltraChatError):
                    self.submit(**changes)
            self.service = self.reopen(context=[{"role": "tool", "content": "invalid"}])
            with self.assertRaises(UltraChatError): self.submit()
            for service in (TurnService(), TurnService(test_roots=[self.root])):
                with self.assertRaises(UltraChatError):
                    service.submit(self.root, self.ws, self.chat, self.body)
            self.service = self.reopen()
            with tempfile.TemporaryDirectory() as foreign:
                with self.assertRaises(UltraChatError):
                    self.service.submit(foreign, self.ws, self.chat, self.body)
                self.assertEqual(list(Path(foreign).iterdir()), [])
        transport.assert_not_called()
        self.assertEqual(self.disk(), before)
        with self.assertRaises(ValueError):
            TurnService(test_roots=[Path.cwd()], offline_adapter=self.service._offline_adapter)

    def test_cancel_ready_has_no_attempt(self):
        with patch.object(self.service, "_execute", side_effect=lambda *args: self.get()):
            self.submit()
        with patch.object(_FixtureTransport, "send") as transport:
            self.service.cancel(self.root, self.ws, self.chat, self.ids()["turn_id"], {})
            self.assertEqual(self.submit()["state"], "CANCELLED")
        transport.assert_not_called()
        self.assertEqual(len(self.raw()), 1)
        self.assertEqual([r["event"] for r in self.events()], ["turn_cancel_requested"])

    def test_two_writers_and_late_cancel(self):
        for cancel in (False, True):
            with self.subTest(cancel=cancel):
                self.body["idempotency_key"] = f"parallel_{int(cancel)}_00000000"
                entered, release = threading.Event(), threading.Event()
                calls = []
                other = self.reopen()
                async def delayed(_fake, payload, **kwargs):
                    calls.append(payload)
                    entered.set()
                    if not release.wait(8):
                        raise TimeoutError()
                    return reply(usage={"total_tokens": 9})
                with patch.object(_FixtureTransport, "send", delayed), ThreadPoolExecutor() as pool:
                    first = pool.submit(self.submit)
                    try:
                        self.assertTrue(entered.wait(8))
                        repeat = other.submit(self.root, self.ws, self.chat, self.body)
                        self.assertEqual(repeat["state"], "UNKNOWN")
                        if cancel:
                            self.assertEqual(other.cancel(self.root, self.ws, self.chat, repeat["turn_id"], {})["state"], "UNKNOWN")
                    finally:
                        release.set()
                    result = first.result(12)
                self.assertEqual(len(calls), 1)
                self.assertEqual(result["state"], "UNKNOWN" if cancel else "SUCCEEDED")
                self.assertEqual(result["usage"]["total_tokens"], 9)
                self.assertEqual(result["assistant_message_id"] + ".json" in self.raw(), not cancel)

    def test_process_crash_at_three_boundaries(self):
        for phase, code, state, calls in (
            ("before_user", 72, "SUCCEEDED", 1),
            ("during_send", 71, "UNKNOWN", 0),
            ("after_assistant", 73, "SUCCEEDED", 0),
        ):
            with self.subTest(phase=phase):
                self.body["idempotency_key"] = f"process_{phase}_00000000"
                child = subprocess.run([sys.executable, "-B", "-c", CRASH_CHILD, str(self.root), self.ws,
                                        self.chat, json.dumps(self.body), phase], capture_output=True, timeout=30)
                self.assertEqual(child.returncode, code, child.stderr.decode(errors="replace"))
                self.service = self.reopen()
                original = _FixtureTransport.send
                with patch.object(_FixtureTransport, "send", autospec=True, side_effect=original) as transport:
                    result = self.submit()
                    self.assertEqual(self.submit(), result)
                self.assertEqual(transport.call_count, calls)
                self.assertEqual(result["state"], state)
                self.assertEqual(self.ids()["assistant_message_id"] + ".json" in self.raw(), state == "SUCCEEDED")
                self.assertEqual(sum(r["event"] == "turn_started" for r in self.events()), 1)
        self.assertEqual(len(self.raw()), 5)

    def test_result_ack_lost_recovers_exact_answer(self):
        clear = runs._clear_pending
        def fail_result(path):
            if json.loads(path.read_bytes())["record"]["event"] == "turn_result":
                raise OSError("synthetic lost acknowledgement")
            return clear(path)
        with patch.object(runs, "_clear_pending", side_effect=fail_result), self.assertRaises(UltraChatError):
            self.submit()
        self.assertEqual(len(self.raw()), 1)
        self.service = self.reopen(response=reply(error="different fixture"))
        with patch.object(_FixtureTransport, "send") as transport:
            result = self.submit()
        transport.assert_not_called()
        self.assertEqual((result["state"], result["answer"]), ("SUCCEEDED", "Fake answer"))
        self.assertEqual(len(self.raw()), 2)

    def test_errors_and_usage_have_durable_classifications(self):
        async def broken(*args, **kwargs):
            raise RuntimeError("SECRET_SENTINEL")
        async def slow(*args, **kwargs):
            await asyncio.Event().wait()
        cases = [
            (dict(refuse=True), None, "FAILED", "rejected", "missing", None),
            (dict(response=reply(error="SECRET_SENTINEL", usage={"total_tokens": 6})), None,
             "FAILED", "invalid_response", "partial", 6),
            ({}, broken, "UNKNOWN", "transport_error", "missing", None),
            (dict(limits=RequestLimits(9, 2048, 8192, 8192, 64, 0.02)), slow,
             "UNKNOWN", "unknown_after_start", "missing", None),
            ({}, None, "SUCCEEDED", "completed", "missing", None),
            (dict(response=reply(usage={"total_tokens": True})), None, "SUCCEEDED", "completed", "invalid", None),
        ]
        original = _FixtureTransport.send
        for n, (options, sender, state, outcome, usage, total) in enumerate(cases):
            with self.subTest(outcome=outcome, usage=usage):
                self.body["idempotency_key"] = f"error_fixture_{n:05}"
                self.service = self.reopen(**options)
                with patch.object(_FixtureTransport, "send", autospec=True, side_effect=sender or original) as transport:
                    result = self.submit()
                    self.assertEqual(self.submit(), result)
                self.assertEqual(transport.call_count, 0 if outcome == "rejected" else 1)
                self.assertEqual(result["state"], state)
                self.assertEqual((result["usage"]["status"], result["usage"]["total_tokens"]), (usage, total))
                self.assertEqual(self.events()[-1]["payload"]["outcome"], outcome)
                self.assertNotIn(b"SECRET_SENTINEL", b"".join(self.disk().values()))

    def test_revoked_model_never_replaced(self):
        with patch.object(self.service, "_execute", side_effect=lambda *args: self.get()):
            self.submit()
        model = model_registry.get_model_spec("gigachat_2_pro")
        with (patch.dict(model_registry._MODEL_REGISTRY, {model.model_id: replace(model, enabled=False)}),
              patch.object(_FixtureTransport, "send") as transport):
            self.assertEqual(self.submit()["state"], "FAILED")
        transport.assert_not_called()
        self.assertEqual(self.events()[-1]["payload"]["execution"], "not_started")

    def test_corrupt_durable_components_refused_without_mutation(self):
        result = self.submit()
        summary = runs.run_component_path(self.root, result["run_id"], "summary.json")
        raw = self.root / ".ultra/chats" / self.chat / "messages" / (result["assistant_message_id"] + ".json")
        stream = runs.run_component_path(self.root, result["run_id"], "server.jsonl")
        alterations = [
            (summary, lambda d: d["turn"]["prepared"]["model"].update(provider_model_id="other")),
            (summary, lambda d: d["turn"]["prepared"].update(request_ref="sha256:"+"0"*64)),
            (summary, lambda d: d.update(task_block_id="tb_"+"0"*32)),
            (summary, lambda d: d["turn"].update(state="READY")),
            (raw, lambda d: d.update(original_text="tampered")),
            (raw, lambda d: d["producer"].update(request_ref="wrong")),
            (stream, None),
        ]
        for path, change in alterations:
            with self.subTest(file=path.name):
                original = path.read_bytes()
                if change:
                    data = json.loads(original)
                    change(data)
                    path.write_text(json.dumps(data), encoding="utf-8")
                else:
                    path.write_bytes(original.replace(b"Fake answer", b"Fake changed"))
                before = self.disk()
                with patch.object(_FixtureTransport, "send") as transport:
                    for action in (self.get, self.submit):
                        with self.assertRaises(UltraChatError):
                            action()
                transport.assert_not_called()
                self.assertEqual(self.disk(), before)
                path.write_bytes(original)

    def test_valid_run_checksum_cannot_bypass_attempt_and_usage_binding(self):
        for change in ({"attempt_id": "wrong"}, {"request_ref": "sha256:"+"0"*64},
                       {"usage": dict(status="missing", total_tokens=0, prompt_tokens=None, completion_tokens=None)}):
            with self.subTest(change=change):
                self.body["idempotency_key"] = f"semantic_binding_{len(self.raw()):04}"
                append = self.service._event
                def append_changed(root, turn, event, payload):
                    return append(root, turn, event, {**payload, **change} if event == "turn_result" else payload)
                with patch.object(self.service, "_event", side_effect=append_changed), self.assertRaises(UltraChatError):
                    self.submit()
                self.assertEqual(self.events()[-1]["event"], "turn_result")  # Run Store hash is valid.
                self.assertNotIn(self.ids()["assistant_message_id"] + ".json", self.raw())
                before = self.disk()
                with patch.object(_FixtureTransport, "send") as transport:
                    for action in (self.get, self.submit):
                        with self.assertRaises(UltraChatError):
                            action()
                transport.assert_not_called()
                self.assertEqual(self.disk(), before)

    def test_legacy_turn_with_adapter_retains_v1(self):
        with patch.object(_FixtureTransport, "send") as transport:
            result = self.submit(**REFERENCES)
        transport.assert_not_called()
        self.assertEqual((result["answer"], result["mode"]), (ANSWER, "TEST"))
        self.service = TurnService(test_roots=[self.root])
        self.assertEqual(self.get(), result)

    def test_no_oauth_http_or_credentials_and_guard_controls(self):
        with (patch.object(gigachat_transport, "get_access_token", side_effect=AssertionError("OAuth blocked")) as oauth,
              patch.object(httpx, "AsyncClient", side_effect=AssertionError("HTTP blocked")) as http):
            self.assertEqual(self.submit()["state"], "SUCCEEDED")
            oauth.assert_not_called()
            http.assert_not_called()
            with self.assertRaises(AssertionError):
                asyncio.run(gigachat_transport.get_access_token())
            with self.assertRaises(AssertionError):
                httpx.AsyncClient()
        if "ORDINARY_GUARD_LOG" not in os.environ:
            self.skipTest("Physical negative controls require the early guard")
        with socket.socket() as sock, self.assertRaises(PermissionError):
            sock.connect(("192.0.2.1", 443))
        with self.assertRaises(PermissionError):
            socket.getaddrinfo("offline.invalid", 443)
        with self.assertRaises(PermissionError):
            os.getenv("GIGACHAT_CREDENTIALS")
