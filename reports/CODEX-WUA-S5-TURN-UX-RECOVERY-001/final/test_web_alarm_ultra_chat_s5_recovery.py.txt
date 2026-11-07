"""Bounded Stage5 recovery cases; disposable fixtures, fake transport only."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import threading
import unittest
from unittest.mock import patch

import test_web_alarm_ultra_chat_s5 as fixtures
from web_alarm.ordinary_chat_test_adapter import _FixtureTransport
from web_alarm.server import WebAlarmApi
from web_alarm.turn_service import TurnService
from web_alarm.ultra_chat import OfflineUltraChatService


class RecoveryTests(fixtures.Fixture):
    serve = fixtures.HttpAndTkTests.serve
    http = fixtures.HttpAndTkTests.http
    tokens = fixtures.HttpAndTkTests.tokens

    def setUp(self):
        super().setUp()
        self.api = WebAlarmApi(self.root / "registry")
        self.service = OfflineUltraChatService(self.api.registry, self.root)

    def record(self, name, evidence):
        target = os.environ.get("S5_RECOVERY_EVIDENCE_DIR")
        if target:
            output = Path(target).resolve()
            expected = Path(__file__).resolve().parent / "reports/CODEX-WUA-S5-TURN-UX-RECOVERY-001"
            if not output.is_relative_to(expected):
                raise ValueError("Evidence must stay in this task package")
            output.mkdir(parents=True, exist_ok=True)
            (output / (name + ".json")).write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def raw_path(self, ws, chat, message):
        return Path(self.api.registry.get(ws).workspace_root) / ".ultra/chats" / chat / "messages" / (message + ".json")

    def test_active_user_uses_authoritative_turn_state(self):
        ws, chat = self.create_chat("S5 UX active")
        body = self.body("S5_ACTIVE_SYNTHETIC")
        entered, release = threading.Event(), threading.Event()

        async def delayed(fake, payload, **kwargs):
            entered.set()
            if not release.wait(5):
                raise TimeoutError("fixture release")
            return {"choices": [{"message": {"role": "assistant", "content": "S5_DONE"}}]}

        with patch.object(_FixtureTransport, "send", delayed), ThreadPoolExecutor() as pool:
            future = pool.submit(self.service.submit_turn, ws, chat, body)
            try:
                self.assertTrue(entered.wait(3))
                active = self.service.latest_turn(ws, chat)["turn"]
                self.assertEqual(active["state"], "ATTEMPTING")
                page = self.service.messages(ws, chat, None, 50)
                self.assertEqual(page["messages"][0]["outcome"], "running")
                self.assertEqual(page["messages"][0]["turn_state"], "ATTEMPTING")
                disconnected_reader = OfflineUltraChatService(self.api.registry, self.root)
                uncertain = disconnected_reader.messages(ws, chat, None, 50)["messages"][0]
                self.assertEqual((uncertain["turn_state"], uncertain["outcome"]), ("UNKNOWN", "unknown"))
                self.assertEqual(self.service.messages(ws, chat, None, 50)["messages"][0]["outcome"], "running")
            finally:
                release.set()
            done = future.result(timeout=6)
        self.assertEqual(done["state"], "SUCCEEDED")
        self.assertEqual([m["outcome"] for m in self.service.messages(ws, chat, None, 50)["messages"]], ["request", "completed"])
        self.record("active", {"workspace_id": ws, "chat_id": chat, "active": active, "active_history": page, "done": done})

    def cancel_case(self, before_start):
        ws, chat = self.create_chat("S5 cancel isolated")
        server = self.serve(offline_chat=self.service)
        _, read, write = self.tokens(server)
        path = f"/ultra/chat/workspaces/{ws}/chats/{chat}"
        base = path + "/turns"
        body = self.body("S5_CANCEL_BEFORE" if before_start else "S5_CANCEL_AFTER")
        entered, release = threading.Event(), threading.Event()
        wires = []
        original = TurnService._execute

        def gated(turns, *args):
            if before_start:
                entered.set()
                if not release.wait(6):
                    raise TimeoutError("before execution barrier")
            return original(turns, *args)

        async def delayed(fake, payload, **kwargs):
            wires.append(payload)
            if not before_start:
                entered.set()
                if not release.wait(6):
                    raise TimeoutError("after execution barrier")
            return {"choices": [{"message": {"role": "assistant", "content": "SYNTHETIC_ANSWER"}}]}

        with patch.object(TurnService, "_execute", gated), patch.object(_FixtureTransport, "send", delayed), ThreadPoolExecutor() as pool:
            future = pool.submit(self.http, server, "POST", base, body, write)
            try:
                self.assertTrue(entered.wait(4))
                status, latest = self.http(server, "GET", base + "/latest", headers=read)
                self.assertEqual(status, 200)
                turn = latest["turn"]
                self.assertEqual(turn["state"], "READY" if before_start else "ATTEMPTING")
                raw = self.raw_path(ws, chat, turn["user_message_id"])
                original_hash = hashlib.sha256(raw.read_bytes()).hexdigest()
                status, before_page = self.http(server, "GET", path + "/messages?limit=50", headers=read)
                self.assertEqual(status, 200)
                self.assertEqual(before_page["messages"][0]["outcome"], "pending" if before_start else "running")
                status, cancelled = self.http(server, "POST", base + "/" + turn["turn_id"] + "/cancel", {}, write)
                expected = "CANCELLED" if before_start else "UNKNOWN"
                self.assertEqual((status, cancelled["state"]), (200, expected))
            finally:
                release.set()
            self.assertEqual(future.result(timeout=8)[1]["state"], expected)
        self.assertEqual(len(wires), 0 if before_start else 1)
        reopened_service = OfflineUltraChatService(self.api.registry, self.root)
        reopened = self.serve(offline_chat=reopened_service)
        _, read2, write2 = self.tokens(reopened)
        status, after_page = self.http(reopened, "GET", path + "/messages?limit=50", headers=read2)
        self.assertEqual(status, 200)
        self.assertEqual([m["message_id"] for m in after_page["messages"]], [turn["user_message_id"]])
        self.assertEqual(after_page["messages"][0]["outcome"], "cancelled" if before_start else "unknown")
        self.assertEqual(hashlib.sha256(raw.read_bytes()).hexdigest(), original_hash)
        self.assertEqual(self.http(reopened, "GET", base + "/latest", headers=read2)[1]["turn"]["turn_id"], turn["turn_id"])
        self.assertEqual(self.http(reopened, "POST", base, body, write2)[1]["state"], expected)
        following_payloads = []

        async def following(fake, payload, **kwargs):
            following_payloads.append(payload)
            return {"choices": [{"message": {"role": "assistant", "content": "NEXT_ANSWER"}}]}

        with patch.object(_FixtureTransport, "send", following):
            status, next_turn = self.http(reopened, "POST", base, self.body("S5_NEXT_ONLY"), write2)
        self.assertEqual((status, next_turn["state"]), (200, "SUCCEEDED"))
        context = following_payloads[0]["messages"]
        self.assertEqual([m["role"] for m in context], ["system", "user"])
        self.assertNotIn(body["text"], repr(context))
        self.assertEqual(hashlib.sha256(raw.read_bytes()).hexdigest(), original_hash)
        status, small = self.http(reopened, "GET", path + "/messages?limit=1", headers=read2)
        self.assertEqual((status, small["page"]["has_more"]), (200, True))
        status, older = self.http(reopened, "GET", path + "/messages?limit=50&before=" + small["messages"][0]["message_id"], headers=read2)
        self.assertEqual(status, 200)
        self.assertIn(turn["user_message_id"], [m["message_id"] for m in older["messages"]])
        self.record("cancel_before" if before_start else "cancel_after", {
            "workspace_id": ws, "chat_id": chat, "turn_id": turn["turn_id"], "message_id": turn["user_message_id"],
            "raw_sha256_before": original_hash, "raw_sha256_after": hashlib.sha256(raw.read_bytes()).hexdigest(),
            "raw_utf8": raw.read_bytes().decode("utf-8"),
            "before_history": before_page, "after_reopen_history": after_page, "cancel_state": expected,
            "replay_started_no_new_transport": True, "physical_fake_sends_for_cancelled_turn": len(wires),
            "next_context": context, "paginated_older_history": older,
            "historical_user_raw_loss": "NOT REPRODUCED in this controlled same-Chat scenario"})

    def test_cancel_before_execution_preserves_raw_http_history_and_context_policy(self):
        self.cancel_case(True)

    def test_cancel_after_start_preserves_unknown_raw_http_history_and_context_policy(self):
        self.cancel_case(False)


if __name__ == "__main__":
    unittest.main()
