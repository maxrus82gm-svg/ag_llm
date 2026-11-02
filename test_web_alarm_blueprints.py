"""Blueprint design contract, persistence and protected HTTP on disposable storage."""
from __future__ import annotations

import copy
import http.client
import json
import os
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from web_alarm.blueprints import (BlueprintError, BlueprintService, DEFAULT_PORTS, CAPABILITY_PATH,
                                  TOKEN_HEADER, definition, validate_graph, preview)
from web_alarm.server import WebAlarmApi, create_server
from web_alarm.ultra_connections import UltraConnections


def graph():
    def node(nid, role):
        return {"id": nid, "kind": "llm", "title": nid, "position": {"x": 0, "y": 0},
                "executor_ref": "api:gigachat:gigachat_ultra", "role": role,
                "instruction": "", "input_text": "", "context_text": "", "context_refs": [],
                "parameters": {"temperature": .7, "max_output_tokens": 2048}, "ports": copy.deepcopy(DEFAULT_PORTS)}
    return {"schema_version": 1, "blueprint_id": "bp_" + "a" * 32, "name": "Решение и проверка",
            "nodes": [node("node_a", "Планировщик"), node("node_b", "Проверяющий")],
            "edges": [{"id": "edge_ab", "source": "node_a", "source_port": "result", "target": "node_b", "target_port": "prior"}],
            "output_node_id": "node_b"}


class BlueprintContractTests(unittest.TestCase):
    def test_one_type_custom_roles_independent_settings_and_arbitrary_named_ports(self):
        g = graph(); g["nodes"][0]["role"] = "Историк со своим заданием"
        g["nodes"][0]["ports"].append({"id": "assessment", "label": "Оценка", "direction": "output", "type": "json", "multiple": False, "required": False})
        checked = definition(g); checked["nodes"][0]["role"] = "Редактор"
        self.assertEqual(g["nodes"][0]["role"], "Историк со своим заданием")
        self.assertEqual(checked["nodes"][1]["role"], "Проверяющий")
        self.assertTrue(validate_graph(checked, {})["valid"])

    def test_cycles_dangling_type_direction_duplicate_and_cardinality_are_rejected(self):
        cases = []
        g = graph(); g["edges"].append({"id": "edge_back", "source": "node_b", "source_port": "result", "target": "node_a", "target_port": "task"}); cases.append((g, "cycle"))
        g = graph(); g["edges"][0]["target_port"] = "absent"; cases.append((g, "dangling_edge"))
        g = graph(); g["edges"][0]["target_port"] = "data"; cases.append((g, "incompatible_ports"))
        g = graph(); g["edges"][0]["source_port"] = "task"; cases.append((g, "incompatible_ports"))
        g = graph(); g["edges"].append(dict(g["edges"][0], id="edge_duplicate")); cases.append((g, "duplicate_edge"))
        g = graph(); g["edges"][0]["target_port"] = "task"; g["edges"].append(dict(g["edges"][0], id="edge_duplicate")); cases.append((g, "input_cardinality"))
        for value, expected in cases:
            with self.subTest(expected=expected):
                result = validate_graph(definition(value), {})
                self.assertFalse(result["valid"])
                self.assertIn(expected, [e["code"] for e in result["errors"]])

    def test_unknown_version_unknown_fields_duplicates_nonfinite_and_endpoint_rejected(self):
        cases = []
        g = graph(); g["schema_version"] = 2; cases.append(g)
        g = graph(); g["nodes"][0]["server_url"] = "http://localhost"; cases.append(g)
        g = graph(); g["nodes"][1]["id"] = "node_a"; cases.append(g)
        g = graph(); g["nodes"][0]["parameters"]["temperature"] = float("nan"); cases.append(g)
        g = graph(); g["nodes"][0]["executor_ref"] = "http://server/v1"; cases.append(g)
        g = graph(); g["nodes"][0]["context_refs"] = ["C:\\private.txt"]; cases.append(g)
        for value in cases:
            with self.subTest(value=value):
                with self.assertRaises(BlueprintError): definition(value)

    def test_fanout_and_multi_input_accept_multiple_sources(self):
        g = graph(); c = copy.deepcopy(g["nodes"][0]); c["id"] = "node_c"; g["nodes"].append(c)
        g["edges"].extend([
            {"id": "edge_ac", "source": "node_a", "source_port": "result", "target": "node_c", "target_port": "prior"},
            {"id": "edge_cb", "source": "node_c", "source_port": "result", "target": "node_b", "target_port": "prior"},
        ])
        result = validate_graph(definition(g), {})
        self.assertTrue(result["valid"]); self.assertEqual(result["order"], ["node_a", "node_c", "node_b"])

    def test_mock_preview_passes_only_wired_context_and_never_reads_sources(self):
        g = graph(); g["nodes"][0]["context_text"] = "Only when wired"
        g["nodes"][0]["context_refs"] = ["artifact:private"]
        with patch("builtins.open", side_effect=AssertionError("preview must not open files")):
            first = preview(definition(g), "Вопрос пользователя", {})
        self.assertEqual(first["mode"], "simulation"); self.assertFalse(first["execution"])
        self.assertEqual(first["network_calls"], 0); self.assertFalse(first["persisted"])
        self.assertNotIn("Only when wired", json.dumps(first["trace"][1], ensure_ascii=False))
        g["edges"].append({"id": "edge_context", "source": "node_a", "source_port": "context_out", "target": "node_b", "target_port": "context"})
        second = preview(definition(g), "Вопрос пользователя", {})
        context = next(i for i in second["trace"][1]["inputs"] if i["pin"] == "context")
        self.assertEqual(context["sample"]["text"], "Only when wired")
        self.assertEqual(context["source_node_id"], "node_a")
        self.assertFalse(second["trace"][0]["context_refs_resolved"])
        self.assertEqual(second["trace"][0]["task"], "Вопрос пользователя")

    def test_required_custom_input_and_missing_output_cannot_preview(self):
        g = graph(); g["nodes"][0]["ports"][3]["required"] = True
        with self.assertRaises(BlueprintError): preview(definition(g), "test", {})
        g = graph(); g["output_node_id"] = None
        with self.assertRaises(BlueprintError): preview(definition(g), "test", {})


class BlueprintStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="wua_blueprint_")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "store"
        self.service = BlueprintService(self.root, UltraConnections(self.root))

    def test_catalog_and_list_are_readonly_and_do_not_select_global_model(self):
        self.assertEqual(self.service.list()["items"], [])
        catalog = self.service.catalog()
        self.assertEqual(catalog["source"], "model_registry")
        self.assertGreater(len(catalog["targets"]), 0)
        self.assertFalse(self.root.exists())

    def test_save_reopen_duplicate_request_and_revision_conflict(self):
        g = graph(); bid = g["blueprint_id"]
        first = self.service.save(bid, {"expected_revision": 0, "definition": g})
        self.assertEqual(first["revision"], 1)
        reopened = BlueprintService(self.root, UltraConnections(self.root))
        self.assertEqual(reopened.request("GET", "/ultra/blueprints/" + bid), first)
        self.assertEqual(reopened.save(bid, {"expected_revision": 0, "definition": g}), first)
        update = copy.deepcopy(g); update["nodes"][0]["role"] = "Редактор"
        self.assertEqual(reopened.save(bid, {"expected_revision": 1, "definition": update})["revision"], 2)
        with self.assertRaises(BlueprintError) as ctx:
            self.service.save(bid, {"expected_revision": 1, "definition": g})
        self.assertEqual(ctx.exception.code, "blueprint_revision_conflict")
        self.assertFalse((self.root / "ultra" / "connections.json").exists())

    def test_two_concurrent_edits_have_one_winner_and_one_visible_conflict(self):
        g = graph(); bid = g["blueprint_id"]
        self.service.save(bid, {"expected_revision": 0, "definition": g})
        barrier = threading.Barrier(2)
        def save(name):
            value = copy.deepcopy(g); value["name"] = name
            service = BlueprintService(self.root, UltraConnections(self.root)); barrier.wait(timeout=5)
            try: return service.save(bid, {"expected_revision": 1, "definition": value})["revision"]
            except BlueprintError as exc: return exc.code
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(save, name) for name in ("One", "Two")]
            results = [future.result(timeout=15) for future in futures]
        self.assertCountEqual(results, [2, "blueprint_revision_conflict"])

    def test_corrupt_file_is_reported_without_overwrite(self):
        g = graph(); bid = g["blueprint_id"]
        self.service.save(bid, {"expected_revision": 0, "definition": g})
        path = self.root / "ultra" / "blueprints" / (bid + ".json"); path.write_bytes(b"broken")
        self.assertEqual(self.service.list()["damaged"][0]["code"], "blueprint_storage_corrupt")
        with self.assertRaises(BlueprintError): self.service.save(bid, {"expected_revision": 1, "definition": g})
        self.assertEqual(path.read_bytes(), b"broken")

    def test_invalid_connections_do_not_write_anything(self):
        g = graph(); g["edges"][0]["target_port"] = "data"
        with self.assertRaises(BlueprintError): self.service.save(g["blueprint_id"], {"expected_revision": 0, "definition": g})
        self.assertFalse(self.root.exists())

    def test_storage_directory_link_is_refused(self):
        self.root.mkdir(); destination = Path(self.temp.name) / "outside"; destination.mkdir()
        link = self.root / "ultra"
        if os.name == "nt":
            import _winapi
            _winapi.CreateJunction(str(destination), str(link))
        else: link.symlink_to(destination, target_is_directory=True)
        try:
            with self.assertRaises(BlueprintError): self.service.list()
            self.assertEqual(list(destination.iterdir()), [])
        finally: os.rmdir(link) if os.name == "nt" else link.unlink()


class BlueprintHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="wua_blueprint_http_"); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "store"
        self.api = WebAlarmApi(self.root)
        self.server = create_server(self.api, port=0)
        self.thread = threading.Thread(target=lambda: self.server.serve_forever(poll_interval=.02), daemon=True); self.thread.start()
        self.addCleanup(self.stop)
        self.host = f"127.0.0.1:{self.server.server_port}"
        self.token = self.api.blueprints.token

    def stop(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(3)

    def request(self, method, path, data=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        body = json.dumps(data).encode() if data is not None else None
        sent = {"Host": self.host, TOKEN_HEADER: self.token}
        if body is not None: sent.update({"Content-Type": "application/json", "Origin": "http://" + self.host})
        sent.update(headers or {})
        try:
            conn.request(method, path, body=body, headers=sent); response = conn.getresponse(); raw = response.read()
            return response.status, json.loads(raw) if response.getheader("Content-Type", "").startswith("application/json") else raw.decode()
        finally: conn.close()

    def test_page_catalog_save_reopen_validate_and_preview(self):
        status, page = self.request("GET", "/")
        self.assertEqual(status, 200); self.assertIn('id="viewBlueprint"', page); self.assertIn('id="bpCanvas"', page)
        self.assertIn('id="bpReload"', page); self.assertNotIn('<!-- BLUEPRINT_CONTENT -->', page)
        self.assertEqual(self.request("GET", "/ultra/blueprints/catalog")[0], 200)
        g = graph(); path = "/ultra/blueprints/" + g["blueprint_id"]
        self.assertEqual(self.request("PUT", path, {"expected_revision": 0, "definition": g})[0], 200)
        self.assertEqual(self.request("GET", path)[1]["definition"], g)
        self.assertTrue(self.request("POST", "/ultra/blueprints/validate", {"definition": g})[1]["valid"])
        preview_response = self.request("POST", "/ultra/blueprints/preview", {"definition": g, "prompt": "Test"})
        self.assertEqual(preview_response[0], 200); self.assertFalse(preview_response[1]["execution"])
        self.assertFalse((self.root / "ultra" / "connections.json").exists())

    def test_wrong_origin_host_token_and_chat_token_cannot_read_or_write(self):
        for headers in ({"Host": "attacker.test"}, {"Origin": "https://attacker.test"}, {"Sec-Fetch-Site": "cross-site"},
                        {TOKEN_HEADER: "invalid"}, {TOKEN_HEADER: self.server.web_alarm_ultra_chat_access.capability()["token"]}):
            with self.subTest(headers=headers):
                self.assertEqual(self.request("GET", "/ultra/blueprints", headers=headers)[0], 403)
        self.assertEqual(self.request("GET", CAPABILITY_PATH, headers={"Host": "attacker.test"})[0], 403)

    def test_bad_methods_schema_paths_and_queries_are_refused(self):
        self.assertEqual(self.request("DELETE", "/ultra/blueprints")[0], 405)
        self.assertEqual(self.request("GET", "/ultra/blueprints?path=outside")[0], 400)
        self.assertEqual(self.request("GET", "/ultra/blueprints/../../outside")[0], 405)
        g = graph(); g["schema_version"] = 2
        self.assertEqual(self.request("POST", "/ultra/blueprints/validate", {"definition": g})[0], 400)


if __name__ == "__main__":
    unittest.main()
