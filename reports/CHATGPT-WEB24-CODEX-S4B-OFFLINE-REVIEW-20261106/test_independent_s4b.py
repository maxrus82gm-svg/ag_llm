"""WEB24 independent negative controls for Stage4B on synthetic Windows Workspace only."""
from pathlib import Path
import hashlib
import tempfile
import unittest
from unittest.mock import patch

import context_storage as core
from ordinary_chat_service import RequestLimits
from web_alarm.ordinary_chat_test_adapter import OfflineTestAdapter, _FixtureTransport
from web_alarm.turn_service import ANSWER, REFERENCES, TurnService
from web_alarm.ultra_chat import UltraChatError


class IndependentS4BBoundaries(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="web24_review_s4b_")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / "synthetic-workspace"
        self.root.mkdir()
        self.workspace_id = core.ensure_workspace_storage(self.root)["workspace_id"]
        self.chat_id = core.create_chat(self.root)["chat_id"]
        self.adapter = OfflineTestAdapter(
            context=(),
            context_ref="review-only:v1",
            limits=RequestLimits(9, 2048, 8192, 8192, 64, 2),
            response={"choices": [{"message": {"role": "assistant", "content": "REVIEW FAKE"}}]},
        )
        self.body = dict(
            idempotency_key="review_negative_00001",
            text="Reviewer question",
            model_ref="gigachat_2_pro",
            context_ref="review-only:v1",
            config_ref="s4b-offline:v1",
        )

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes()
                for p in self.root.rglob("*") if p.is_file()}

    def test_no_adapter_refuses_offline_before_writing(self):
        ordinary = TurnService(test_roots=[self.root])
        before = self.snapshot()
        with self.assertRaises(UltraChatError) as error:
            ordinary.submit(self.root, self.workspace_id, self.chat_id, self.body)
        self.assertEqual(error.exception.code, "invalid_turn_reference")
        self.assertEqual(self.snapshot(), before)

    def test_legacy_fixture_does_not_invoke_s4a_transport(self):
        service = TurnService(test_roots=[self.root], offline_adapter=self.adapter)
        legacy = dict(idempotency_key="review_legacy_0000001", text="Legacy user", **REFERENCES)
        with patch.object(_FixtureTransport, "send", side_effect=AssertionError("unexpected fake call")) as sender:
            view = service.submit(self.root, self.workspace_id, self.chat_id, legacy)
        sender.assert_not_called()
        self.assertEqual(view["state"], "SUCCEEDED")
        self.assertEqual(view["answer"], ANSWER)
        self.assertEqual(view["mode"], "TEST")

    def test_offline_record_cannot_be_read_using_disabled_adapter(self):
        service = TurnService(test_roots=[self.root], offline_adapter=self.adapter)
        view = service.submit(self.root, self.workspace_id, self.chat_id, self.body)
        self.assertEqual((view["state"], view["answer"]), ("SUCCEEDED", "REVIEW FAKE"))
        before = self.snapshot()
        without_adapter = TurnService(test_roots=[self.root])
        with self.assertRaises(UltraChatError) as error:
            without_adapter.get(self.root, self.workspace_id, self.chat_id, view["turn_id"])
        self.assertEqual(error.exception.code, "test_turn_unavailable")
        self.assertEqual(self.snapshot(), before)

    def test_unallowlisted_sibling_root_is_never_written(self):
        service = TurnService(test_roots=[self.root], offline_adapter=self.adapter)
        sibling = self.root.parent / "unlisted-workspace"
        sibling.mkdir()
        with self.assertRaises(UltraChatError) as error:
            service.submit(sibling, self.workspace_id, self.chat_id, self.body)
        self.assertEqual(error.exception.code, "test_turn_unavailable")
        self.assertEqual(list(sibling.iterdir()), [])

    def test_pinned_product_sources_match_author_manifest(self):
        project = Path(__file__).resolve().parents[2]
        expected = {
            "web_alarm/turn_service.py": "66dbb1c74983efa2bc38aa8c11ddd834a84f009de9eda7e1c24e0a9689294805",
            "web_alarm/ordinary_chat_test_adapter.py": "fa62abf7268e9e60696d5d6ce85fe2ad4031f4ff884e0ecc83f75650024428f0",
            "ordinary_chat_service.py": "509d26c16f05f259520733e00bc2675bb91f2c132af784ce7b605e77c78b9a85",
        }
        for path, digest in expected.items():
            with self.subTest(path=path):
                source = (project / path).read_bytes().replace(b"\r\n", b"\n")
                self.assertEqual(hashlib.sha256(source).hexdigest(), digest)
