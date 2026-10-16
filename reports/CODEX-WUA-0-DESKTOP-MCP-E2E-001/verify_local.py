"""Only this TASK's package/contract/adversarial tests. Never Desktop E2E evidence."""
from __future__ import annotations

import argparse
import asyncio
from contextlib import contextmanager
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.metadata
import json
from pathlib import Path
import platform
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PLUGIN = HERE / "plugin"
sys.path.insert(0, str(PLUGIN))
sys.path.insert(0, str(PLUGIN / "vendor"))
from runtime import BridgeError, FIXTURE_ID, Fixture, HttpBridge, MAX_EVENTS, ReadTools, TOOLS, canonical, sha
from web_alarm.server import WebAlarmApi
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Implementation

DETAILS = {"wire_results": [], "proofs": [], "negative_controls": []}


@contextmanager
def fake_http(body=b"{}", status=200, headers=None, delay=0):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if delay:
                time.sleep(delay)
            self.send_response(status)
            for name, value in (headers or {}).items():
                self.send_header(name, value)
            self.end_headers()
            try:
                self.wfile.write(body)
            except OSError:
                pass

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wua-desktop-tests-")
        self.root = Path(self.tmp.name)
        self.fixture = Fixture(self.root / "fixture", self.root / "evidence", WebAlarmApi)
        self.tools = ReadTools(self.fixture)

    def tearDown(self):
        self.fixture.close()
        self.tmp.cleanup()

    def test_three_reads_match_server_bytes_and_durable_receipts(self):
        ping = self.tools.ping()
        caps = self.tools.list_capabilities()
        result = self.tools.read_synthetic_context()
        proof = json.loads(self.fixture.proof_path.read_bytes())
        self.assertEqual(ping["service"], "web_alarm_server")
        self.assertEqual(caps["tools"], list(TOOLS))
        self.assertEqual({r["nonce"] for r in (ping, caps, result)}, {proof["nonce"]})
        self.assertEqual(sha(result["context"]), proof["expected_context_sha256"])
        self.assertEqual(result["context"], proof["expected_context"])
        self.assertEqual(proof["baseline_state_sha256"], proof["current_state_sha256"])
        self.assertTrue(proof["storage_unchanged"])
        self.assertEqual([e["tool"] for e in proof["events"] if e["kind"] == "tool_finished"], list(TOOLS))
        self.assertEqual(len([e for e in proof["events"] if e["kind"] == "http"]), 3)
        self.assertNotIn("WORKSPACE", result["context"])
        DETAILS["proofs"].append(proof)

    def test_other_task_traversal_absolute_and_invalid_type_fail_before_http(self):
        for value in ("other_task", "../../.ultra", "M:/GitHub/ag_llm/.ultra", {"bad": "type"}):
            with self.subTest(value=value), self.assertRaisesRegex(BridgeError, "^TASK_ID_DENIED$"):
                self.tools.read_synthetic_context(value)
        proof = json.loads(self.fixture.proof_path.read_bytes())
        self.assertFalse(any(e["kind"] == "http" for e in proof["events"]))
        self.assertTrue(proof["storage_unchanged"])

    def test_http_write_requests_are_rejected_without_dispatch(self):
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with patch.object(self.fixture.api, "dispatch", wraps=self.fixture.api.dispatch) as dispatch:
            for method in ("POST", "PUT", "PATCH", "DELETE"):
                req = urllib.request.Request(f"http://127.0.0.1:{self.fixture.port}/tasks", data=b"{}", method=method)
                with self.assertRaises(urllib.error.HTTPError) as error:
                    opener.open(req, timeout=2)
                self.assertEqual(error.exception.code, 405)
            self.assertEqual(dispatch.call_count, 0)
        self.assertEqual(self.fixture.state_hash(), self.fixture.baseline)

    def test_unavailable_api_blocks_health_capabilities_and_context(self):
        self.fixture.stop_http()
        for action in (self.tools.ping, self.tools.list_capabilities, self.tools.read_synthetic_context):
            # A closed loopback port may time out under the host's network policy.
            # Both outcomes must be deliberate transport errors, never a ready result.
            start = time.monotonic()
            with self.assertRaises(BridgeError) as error:
                action()
            self.assertIn(str(error.exception), {"HTTP_UNAVAILABLE", "HTTP_TIMEOUT"})
            self.assertLess(time.monotonic() - start, 3)
        self.assertEqual(self.fixture.state_hash(), self.fixture.baseline)

    def test_unexpected_synthetic_storage_change_fails_closed(self):
        (self.fixture.root / "project" / "synthetic-tamper.txt").write_text("test", encoding="utf-8")
        for action in (self.tools.ping, self.tools.list_capabilities, self.tools.read_synthetic_context):
            with self.assertRaisesRegex(BridgeError, "^FIXTURE_STORAGE_CHANGED$"):
                action()
        self.assertFalse(self.fixture.proof()["storage_unchanged"])
        self.assertFalse(any(e["kind"] == "http" for e in self.fixture.events))

    def test_unknown_http_route_is_refused(self):
        for path in ("/tasks/other/context", "/status?path=..", "http://203.0.113.1/", "/../.ultra"):
            with self.assertRaisesRegex(BridgeError, "^HTTP_ROUTE_DENIED$"):
                self.tools.bridge.get(path)
        self.assertFalse(any(e["kind"] == "http" for e in self.fixture.events))

    def test_bounded_receipts_survive_fixture_shutdown(self):
        for i in range(MAX_EVENTS + 7):
            self.fixture.add_event({"kind": "retention_probe", "value": i})
        self.fixture.close()
        proof = json.loads(self.fixture.proof_path.read_bytes())
        self.assertEqual(proof["state"], "closed")
        self.assertEqual(proof["event_total"], MAX_EVENTS + 7)
        self.assertEqual(len(proof["events"]), MAX_EVENTS)
        self.assertTrue(proof["storage_unchanged"])
        self.assertLess(self.fixture.proof_path.stat().st_size, 65536)


class HttpBoundaryTests(unittest.TestCase):
    def test_oversized_http_response_is_rejected(self):
        with fake_http(b"x" * 65537) as port, self.assertRaisesRegex(BridgeError, "^HTTP_RESPONSE_TOO_LARGE$"):
            HttpBridge(port).get("/status")

    def test_invalid_json_and_wrong_shape_are_rejected(self):
        for body, code in ((b"not-json", "HTTP_INVALID_JSON"), (b"[]", "HTTP_INVALID_JSON_OBJECT")):
            with fake_http(body) as port, self.assertRaisesRegex(BridgeError, "^" + code + "$"):
                HttpBridge(port).get("/status")

    def test_redirect_cannot_create_outbound_connection(self):
        destinations = []
        original = socket.socket.connect

        def capture(sock, address):
            destinations.append(address)
            return original(sock, address)

        with fake_http(status=302, headers={"Location": "http://203.0.113.1:443/outside"}) as port:
            with patch.object(socket.socket, "connect", capture), self.assertRaisesRegex(BridgeError, "^HTTP_REDIRECT_DENIED$"):
                HttpBridge(port).get("/status")
            self.assertTrue(destinations)
            self.assertEqual(set(destinations), {("127.0.0.1", port)})
        DETAILS["negative_controls"].append({"redirect_destinations": destinations})

    def test_http_timeout_is_bounded(self):
        with fake_http(delay=0.15) as port:
            start = time.monotonic()
            with self.assertRaisesRegex(BridgeError, "^HTTP_TIMEOUT$"):
                HttpBridge(port, timeout=0.02).get("/status")
            self.assertLess(time.monotonic() - start, 1)

    def test_http_error_status_is_not_success(self):
        with fake_http(status=503) as port, self.assertRaisesRegex(BridgeError, "^HTTP_ERROR_STATUS$"):
            HttpBridge(port).get("/status")


class PackageTests(unittest.TestCase):
    def copied_package(self, root):
        cached = root / "cache/wua-desktop-e2e-local/wua-desktop-readonly/local"
        shutil.copytree(PLUGIN, cached)
        target = root / "CODEX-WUA-0-DESKTOP-MCP-E2E-001-local-tests/evidence"
        target.parent.mkdir(parents=True)
        (cached / "local_config.json").write_bytes(canonical({"evidence_root": str(target)}))
        return cached, target

    def test_real_mcp_from_relocated_package(self):
        async def wire(cached, evidence):
            config = json.loads((cached / "mcp.json").read_bytes())["mcpServers"]["wua_desktop_readonly"]
            args = [a.replace("${PLUGIN_ROOT}", str(cached)) for a in config["args"]]
            params = StdioServerParameters(command=config["command"], args=args, cwd=str(cached))
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write, read_timeout_seconds=8,
                                         client_info=Implementation(name="WUA Local SDK Regression", version="0.2.0")) as session:
                    init = await session.initialize()
                    self.assertEqual(init.server_info.name, "WUA Desktop Read-only")
                    listed = await session.list_tools()
                    self.assertEqual({t.name for t in listed.tools}, set(TOOLS))
                    self.assertTrue(all(t.annotations.read_only_hint and not t.annotations.destructive_hint for t in listed.tools))
                    self.assertTrue(all("ctx" not in t.input_schema.get("properties", {}) for t in listed.tools))
                    values = []
                    for name in TOOLS:
                        result = await session.call_tool(name)
                        DETAILS["wire_results"].append({"tool": name, "result": result.model_dump(mode="json", by_alias=True, exclude_none=True)})
                        self.assertFalse(result.is_error)
                        values.append(result.structured_content or json.loads(result.content[0].text))
                    self.assertEqual(len({v["nonce"] for v in values}), 1)
                    self.assertEqual(sha(values[-1]["context"]), values[1]["expected_context_sha256"])
                    for name, args in (("read_synthetic_context", {"fixture_id": "other_task"}),
                                       ("read_synthetic_context", {"fixture_id": "../../.ultra"}),
                                       ("read_synthetic_context", {"fixture_id": {"bad": "type"}}),
                                       ("execute_mutation", {})):
                        result = await session.call_tool(name, args)
                        DETAILS["wire_results"].append({"tool": name, "arguments": args, "result": result.model_dump(mode="json", by_alias=True, exclude_none=True)})
                        self.assertTrue(result.is_error)
                        if isinstance(args.get("fixture_id"), str):
                            self.assertIn("TASK_ID_DENIED", result.content[0].text)
                    self.assertTrue(Path(values[0]["proof_path"]).is_relative_to(evidence))
                    return init.protocol_version

        with tempfile.TemporaryDirectory(prefix="wua-desktop-relocation-") as raw:
            cached, evidence = self.copied_package(Path(raw))
            protocol = asyncio.run(wire(cached, evidence))
            proof = json.loads(next(evidence.glob("*/session.json")).read_bytes())
            self.assertEqual(proof["state"], "closed")
            self.assertTrue(proof["storage_unchanged"])
            self.assertTrue(all(v == 0 for v in proof["guard_denials"].values()))
            peers = [e["peer_claim"] for e in proof["events"] if e["kind"] == "tool_started"]
            self.assertTrue(all(p["client_name"] == "WUA Local SDK Regression" for p in peers))
            self.assertEqual(protocol, "2025-11-25")
            DETAILS["proofs"].append(proof)

    def test_vendor_drift_refuses_startup(self):
        with tempfile.TemporaryDirectory(prefix="wua-desktop-vendor-drift-") as raw:
            cached, evidence = self.copied_package(Path(raw))
            with (cached / "vendor/web_alarm/server.py").open("ab") as f:
                f.write(b"\n# isolated vendor tamper negative control\n")
            result = subprocess.run([sys.executable, "-I", "-X", "utf8", "-B", str(cached / "server.py")],
                                    cwd=cached, input="", capture_output=True, text=True, encoding="utf-8", timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("VENDOR_SOURCE_HASH_MISMATCH", result.stderr)
            self.assertFalse(evidence.exists())
            DETAILS["negative_controls"].append({"vendor_drift_exit": result.returncode, "stderr": result.stderr})

    def test_actual_audit_hook_blocks_external_network_write_and_process(self):
        script = '''
import json,pathlib,socket,subprocess,sys,tempfile
sys.path.insert(0,sys.argv[1])
from runtime import IsolationPolicy
with tempfile.TemporaryDirectory(prefix="wua-desktop-guard-") as raw:
    root=pathlib.Path(raw)
    outside=root.parent/(root.name+"-denied.txt")
    policy=IsolationPolicy([root])
    policy.port=1
    sys.addaudithook(policy.audit)
    codes=[]
    for action in [lambda:socket.socket().connect(("203.0.113.1",443)),lambda:outside.write_text("blocked"),lambda:subprocess.run(["must-not-launch"])]:
        try:action()
        except PermissionError as error:codes.append(str(error))
    print(json.dumps({"codes":codes,"denials":policy.denials,"outside_file_exists":outside.exists()}))
'''
        result = subprocess.run([sys.executable, "-I", "-X", "utf8", "-B", "-c", script, str(PLUGIN)],
                                capture_output=True, text=True, encoding="utf-8", timeout=10)
        # The deliberate external-file denial is observed before stdlib temporary cleanup.
        observed = json.loads(result.stdout.strip())
        self.assertEqual(observed["codes"], ["WUA_ISOLATION_NETWORK", "WUA_ISOLATION_FILE_WRITE", "WUA_ISOLATION_SUBPROCESS"])
        self.assertFalse(observed["outside_file_exists"])
        self.assertEqual(observed["denials"], {"network": 1, "file_write": 1, "subprocess": 1})
        DETAILS["negative_controls"].append({"audit_probe": observed, "exit": result.returncode, "stderr": result.stderr})
        self.assertEqual(result.returncode, 0)


class JsonResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.records.append({"id": test.id(), "status": "PASS"})

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.records.append({"id": test.id(), "status": "FAIL", "error": self._exc_info_to_string(err, test)})

    def addError(self, test, err):
        super().addError(test, err)
        self.records.append({"id": test.id(), "status": "ERROR", "error": self._exc_info_to_string(err, test)})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    options = parser.parse_args()
    if options.output.exists():
        raise SystemExit("Refusing to overwrite original attempt evidence")
    files = [p for p in PLUGIN.rglob("*") if p.is_file()]
    before = {p.relative_to(PLUGIN).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    started = time.monotonic()
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=1, resultclass=JsonResult).run(suite)
    after = {p.relative_to(PLUGIN).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    counts = {"collected": result.testsRun, "PASS": len([x for x in result.records if x["status"] == "PASS"]),
              "FAIL": len(result.failures), "ERROR": len(result.errors), "SKIP": len(result.skipped)}
    record = {"task_id": "CODEX-WUA-0-DESKTOP-MCP-E2E-001", "test_kind": "LOCAL SDK/HTTP; NOT DESKTOP E2E",
              "python": sys.version, "platform": platform.platform(), "mcp": importlib.metadata.version("mcp"),
              "counts": counts, "tests": result.records, "details": DETAILS,
              "package_before": before, "package_after": after, "package_unchanged": before == after,
              "seconds": round(time.monotonic() - started, 3)}
    record["exit_code"] = 0 if result.wasSuccessful() and counts["collected"] > 0 and before == after else 1
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"counts": counts, "exit_code": record["exit_code"], "seconds": record["seconds"], "evidence": str(options.output)}, ensure_ascii=False))
    raise SystemExit(record["exit_code"])
