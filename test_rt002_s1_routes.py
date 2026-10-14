"""RT-002 S1 (CLAUDE-RT002-S1-001) baseline-and-routes offline probes.

Production code is never patched on disk. Run only as:
    .venv/Scripts/python.exe -B test_rt002_s1_routes.py
Optional positional arguments select exact test IDs from this module.

The standalone runner (1) snapshots pinned read-only RAW Run Store evidence (R-031,
R-026) into a disposable sandbox after verifying SHA-256, then (2) redirects
LOCALAPPDATA/APPDATA/TEMP into the sandbox and installs process-wide audit guards
BEFORE runtime imports: no network, no child processes, no writes outside the
sandbox, no access to .git or to any .ultra outside the sandbox.
All LLM traffic is captured at the httpx transport layer (the exact request bytes
httpx would put on the socket) and answered by a fake provider.
Ordinary unittest discovery skips this module.
"""
from __future__ import annotations

import ast
import asyncio
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parent
_ISOLATED = False
_SANDBOX: Path | None = None
_EVIDENCE: dict[str, Path] = {}
_EVIDENCE_PROBLEMS: list[str] = []
_OBSERVATIONS: dict = {}
_GUARD_VIOLATIONS: list[dict] = []

R031_DIR = ".ultra/audit/chat_b36a4eba7fdf47f98b1d71507bc2938d/20261001_182057_e90f93"
R026_DIR = ".ultra/audit/chat_b36a4eba7fdf47f98b1d71507bc2938d/20260930_233733_1f2fee"
# Pinned read-only RAW evidence (SHA-256, bytes). Content is never embedded here.
EVIDENCE_PINS = {
    "r031/executor.jsonl": (R031_DIR + "/executor.jsonl",
                            "a9f8f6112e54e845790fc441241f92199c63e598cfbfff77b260f49853af8f3b", 723052),
    "r031/server.jsonl": (R031_DIR + "/server.jsonl",
                          "f23146df6a356cca2bce23e76592b81a4bc373b62f57bf56fda636ac8b840f25", 563926),
    "r031/executor_base.json": (R031_DIR + "/executor_base.json",
                                "f3b431ff88215f62c2149e5b69b2b73fdf77d17445c432c97ecec693f767af53", 35568),
    "r031/summary.json": (R031_DIR + "/summary.json",
                          "de1f26cabcb5051fa5163b947e73077b630f5c545f0c830b1dc8038668c65afa", 3468),
    "r026/executor.jsonl": (R026_DIR + "/executor.jsonl",
                            "2cd207327044f476b87e12a70c206e0c91be2632e34ba7a1ffbb8892cc8b066c", 735033),
    "r026/summary.json": (R026_DIR + "/summary.json",
                          "210849cd30793c1e01b63c344a7c7a730a98e6076f4b98dab7e37165e6bb1b89", 3551),
}
LARGE_BLOCK_BYTES = 200_000

# Static route inventory established by CLAUDE-RT002-S1-RECON-001 and re-derived here.
EXPECTED_HTTP_SENDS = {
    ("server.py", "ask_gigachat", "client.post"),
    ("server.py", "_request_audit_diagnostic", "client.post"),
    ("server.py", "_run_agent_task_impl", "client.post"),
    ("planner_runtime.py", "PlannerSession.call", "client.post"),
    ("planner_runtime.py", "run_planner", "client.post"),
    ("verifier_runtime.py", "_request_gigachat", "client.post"),
    ("compressor_runtime.py", "_request_gigachat", "client.post"),
    ("gigachat_transport.py", "get_access_token", "client.post"),  # OAuth, not an LLM call
}
TOOLING_MODULES = {
    "apply_context_step1.py", "apply_ultra_ui_visual_patch.py", "fix_chat_raw_display.py",
    "patch_allow_py.py", "probe_gigachat_models.py", "live_test_context_bridge.py",
    "wa4a_acceptance.py", "wa4o_ui_demo.py", "wa4o_ui_launcher.py",
}


def setUpModule():
    if not _ISOLATED:
        raise unittest.SkipTest("Use the guarded standalone S1 runner")


# --------------------------------------------------------------------------- helpers

def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _require_evidence(*names: str) -> dict[str, Path]:
    if _EVIDENCE_PROBLEMS:
        raise unittest.SkipTest("RAW evidence NOT RUN: " + "; ".join(_EVIDENCE_PROBLEMS))
    missing = [name for name in names if name not in _EVIDENCE]
    if missing:
        raise unittest.SkipTest("RAW evidence NOT RUN: missing " + ", ".join(missing))
    return {name: _EVIDENCE[name] for name in names}


def executor_call_matrix(executor_records: list[dict]) -> list[dict]:
    """Independent oracle over RAW executor stream (summary is never consulted)."""
    stage_by_api = {
        r["payload"].get("api_request_number"): r["payload"]
        for r in executor_records if r["event"] == "executor_diagnostic_context"
    }
    terminals = {
        r["payload"]["provider_attempt_id"]: r["payload"]
        for r in executor_records if r["event"] == "provider_attempt_terminal"
    }
    rows = []
    for record in executor_records:
        if record["event"] != "provider_attempt_started" or record["payload"]["role"] != "executor":
            continue
        payload = record["payload"]
        number = len(rows) + 1
        diag = stage_by_api.get(number, {})
        usage = ((terminals.get(payload["provider_attempt_id"]) or {}).get("provider_usage") or {}).get("raw") or {}
        rows.append({
            "call": number,
            "stage_id": diag.get("stage_id"),
            "message_count": diag.get("message_count"),
            "request_utf8_bytes": payload["request_utf8_bytes"],
            "function_messages": sum(1 for b in payload["request_blocks"]
                                     if str(b.get("source_ref", "")).startswith("tool_result:")),
            "large_blocks": [(b["name"], b["sha256"]) for b in payload["request_blocks"]
                             if b["utf8_bytes"] > LARGE_BLOCK_BYTES],
            "prompt_tokens": usage.get("prompt_tokens"),
            "precached_prompt_tokens": usage.get("precached_prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
        })
    return rows


def large_block_occurrences(rows: list[dict]) -> dict[str, list[int]]:
    seen: dict[str, list[int]] = {}
    for row in rows:
        for _name, digest in row["large_blocks"]:
            seen.setdefault(digest, []).append(row["call"])
    return seen


def reconstruct_contexts(base: dict, executor_records: list[dict]) -> dict[int, list[dict]]:
    """Independent re-implementation of base + context_delta replay."""
    messages = copy.deepcopy(base["messages"])
    contexts = {int(base.get("api_request_number", 1)): copy.deepcopy(messages)}
    for record in executor_records:
        delta = (record.get("payload") or {}).get("context_delta")
        if isinstance(delta, dict):
            messages = messages[:int(delta["common_prefix"])] + copy.deepcopy(delta["added_messages"])
            contexts[int(delta["api_request_number"])] = copy.deepcopy(messages)
    return contexts


def chat_response(content: str | None = "ok", *, function_call: dict | None = None,
                  finish_reason: str = "stop", usage: dict | None = None) -> dict:
    message = {"role": "assistant", "content": content or ""}
    if function_call is not None:
        message["function_call"] = function_call
        finish_reason = "function_call"
    data = {"choices": [{"message": message, "finish_reason": finish_reason}]}
    data["usage"] = usage if usage is not None else {
        "prompt_tokens": 11, "completion_tokens": 3, "total_tokens": 14, "precached_prompt_tokens": 0}
    return data


class WireCapture:
    """Fake provider at the httpx transport layer; records the exact request bytes."""

    def __init__(self, responder):
        self.responder = responder
        self.requests: list[dict] = []
        self.violations: list[str] = []

    async def handle(self, request):
        import httpx
        import gigachat_transport
        await request.aread()
        content = bytes(request.content)
        record = {
            "method": request.method, "url": str(request.url),
            "content": content, "content_length": request.headers.get("content-length"),
            "content_type": request.headers.get("content-type"),
        }
        self.requests.append(record)
        if request.method != "POST" or str(request.url) != gigachat_transport.CHAT_URL:
            self.violations.append(f"unexpected {request.method} {request.url}")
            raise httpx.ConnectError("S1 fake transport: unexpected destination", request=request)
        body = json.loads(content.decode("utf-8"))
        status, payload = self.responder(body, len(self.requests))
        if status == "timeout":
            raise httpx.ReadTimeout("S1 fake provider timeout", request=request)
        return httpx.Response(status, json=payload, request=request)

    def patch(self):
        import httpx
        capture = self

        async def handle_async_request(_transport, request):
            return await capture.handle(request)

        return patch.object(httpx.AsyncHTTPTransport, "handle_async_request", handle_async_request)


def token_patches():
    import compressor_runtime
    import planner_runtime
    import server
    import verifier_runtime
    return [patch.object(module, "get_access_token", AsyncMock(return_value="s1-test-token"))
            for module in (server, planner_runtime, verifier_runtime, compressor_runtime)]


class _Patches:
    def __init__(self, items):
        self.items = list(items)

    def __enter__(self):
        for item in self.items:
            item.__enter__()
        return self

    def __exit__(self, *exc):
        for item in reversed(self.items):
            item.__exit__(*exc)
        return False


def wire_binding(started: dict, wire: bytes):
    """Return (length_equal, canonical_sha_equal, wire_sha_equal)."""
    import provider_accounting
    canonical = provider_accounting.canonical_json_text(json.loads(wire.decode("utf-8"))).encode("utf-8")
    return (started["request_utf8_bytes"] == len(wire),
            started["request_snapshot_sha256"] == _sha256(canonical),
            started["request_snapshot_sha256"] == _sha256(wire))


def attempt_pairs(events: list[dict]) -> tuple[list[dict], list[dict]]:
    started = [e for e in events if e.get("event") == "provider_attempt_started"]
    terminal = [e for e in events if e.get("event") == "provider_attempt_terminal"]
    return started, terminal


# --------------------------------------------------------------------------- A. R-031

class R031RawMatrixTests(unittest.TestCase):
    """A: R-031 reproduced from RAW streams only."""

    @classmethod
    def setUpClass(cls):
        files = _require_evidence("r031/executor.jsonl", "r031/server.jsonl", "r031/executor_base.json")
        cls.executor = _jsonl(files["r031/executor.jsonl"])
        cls.server = _jsonl(files["r031/server.jsonl"])
        cls.base = json.loads(files["r031/executor_base.json"].read_text(encoding="utf-8"))
        cls.rows = executor_call_matrix(cls.executor)
        _OBSERVATIONS["r031_matrix"] = [{k: (v if k != "large_blocks" else [(n, d[:12]) for n, d in v])
                                         for k, v in row.items()} for row in cls.rows]

    def test_fifteen_executor_calls_with_exact_request_sizes_in_one_stage(self):
        self.assertEqual([r["request_utf8_bytes"] for r in self.rows], [
            40352, 42743, 48325, 49622, 50830, 52158, 53580,
            341415, 342743, 343951, 345224, 346646, 634481, 635809, 635066])
        self.assertEqual({r["stage_id"] for r in self.rows}, {"stage_1"})
        self.assertEqual([r["message_count"] for r in self.rows], list(range(3, 33, 2)))
        # every tool result stays: one more function message per executor call, never reset
        self.assertEqual([r["function_messages"] for r in self.rows], list(range(0, 15)))

    def test_large_blocks_follow_eight_plus_three(self):
        occurrences = large_block_occurrences(self.rows)
        self.assertEqual(len(occurrences), 2)
        patterns = sorted(occurrences.values(), key=len, reverse=True)
        self.assertEqual(patterns, [[8, 9, 10, 11, 12, 13, 14, 15], [13, 14, 15]])
        self.assertEqual(sum(len(v) for v in occurrences.values()), 11)
        _OBSERVATIONS["r031_large_block_calls"] = {k[:12]: v for k, v in occurrences.items()}

    def test_large_blocks_bind_to_the_two_full_reads_of_root_ultra_ui(self):
        import provider_accounting
        contexts = reconstruct_contexts(self.base, self.executor)
        self.assertEqual(sorted(contexts), list(range(1, 16)))
        reads = [r["payload"] for r in self.server
                 if r["event"] == "tool_finished" and r["payload"]["function"] == "read_file"
                 and r["payload"]["arguments"]["path"] == "ultra_ui.py"]
        self.assertEqual([p["tool_sequence"] for p in reads], [7, 12])
        self.assertEqual(len({p["result"]["content_sha256"] for p in reads}), 1)
        self.assertEqual({len(p["result"]["content"]) for p in reads}, {238540})
        bound = []
        for row in self.rows:
            for name, digest in row["large_blocks"]:
                index = int(name.split("_")[1])
                message = contexts[row["call"]][index]
                block = provider_accounting.measure_json_block(name, message)
                self.assertEqual(block["sha256"], digest, (row["call"], name))
                result = json.loads(message["content"])
                self.assertEqual(message["role"], "function")
                self.assertEqual(result["path"], "ultra_ui.py")
                self.assertEqual(result["content_sha256"], reads[0]["result"]["content_sha256"])
                bound.append((row["call"], index, result["_tool_budget"]["used"]))
        self.assertEqual({(i, used) for _c, i, used in bound}, {(16, 7), (26, 12)})
        # identical file content, yet different function-message bytes (budget/verification fields)
        self.assertEqual(len({d for r in self.rows for _n, d in r["large_blocks"]}), 2)

    def test_tokens_from_raw_terminals_without_summary(self):
        totals = {"prompt": 0, "completion": 0, "precached": 0}
        for record in self.executor:
            if record["event"] != "provider_attempt_terminal":
                continue
            raw = (record["payload"].get("provider_usage") or {}).get("raw") or {}
            totals["prompt"] += raw["prompt_tokens"]
            totals["completion"] += raw["completion_tokens"]
            totals["precached"] += raw.get("precached_prompt_tokens") or 0
        # executor role only (planner 3 393 lives in planner stream)
        self.assertEqual(totals, {"prompt": 664439, "completion": 1066, "precached": 179456})
        _OBSERVATIONS["r031_executor_raw_tokens"] = totals

    def test_negative_control_oracle_detects_a_missing_resend(self):
        mutated = copy.deepcopy(self.executor)
        removed = False
        for record in mutated:
            if (record["event"] == "provider_attempt_started" and record["payload"]["role"] == "executor"
                    and any(b["utf8_bytes"] > LARGE_BLOCK_BYTES for b in record["payload"]["request_blocks"])):
                record["payload"]["request_blocks"] = [b for b in record["payload"]["request_blocks"]
                                                      if b["utf8_bytes"] <= LARGE_BLOCK_BYTES]
                removed = True
                break
        self.assertTrue(removed)
        patterns = sorted(large_block_occurrences(executor_call_matrix(mutated)).values(), key=len, reverse=True)
        self.assertNotEqual(patterns, [[8, 9, 10, 11, 12, 13, 14, 15], [13, 14, 15]])


# --------------------------------------------------------------------------- E. R-026 / accounting anomalies

class R026RawAccountingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        files = _require_evidence("r026/executor.jsonl", "r026/summary.json")
        cls.executor = _jsonl(files["r026/executor.jsonl"])
        cls.summary = json.loads(files["r026/summary.json"].read_text(encoding="utf-8"))

    def test_raw_stream_has_two_terminals_for_one_attempt(self):
        started = [r for r in self.executor if r["event"] == "provider_attempt_started"]
        terminal = [r for r in self.executor if r["event"] == "provider_attempt_terminal"]
        ids = [r["payload"]["provider_attempt_id"] for r in terminal]
        duplicates = sorted({i for i in ids if ids.count(i) > 1})
        # executor stream only; the two planner attempts live in planner.jsonl (summary: 15 + 2 = 17)
        self.assertEqual((len(started), len(terminal), len(set(ids))), (15, 16, 15))
        self.assertEqual(self.summary["usage"]["planner"]["attempts_started"]
                         + self.summary["usage"]["executor"]["attempts_started"], 17)
        self.assertEqual(len(duplicates), 1)
        pair = [r for r in terminal if r["payload"]["provider_attempt_id"] == duplicates[0]]
        self.assertEqual([(r["sequence"], r["payload"]["outcome"], r["payload"]["mode"]) for r in pair], [
            (146, "timeout", pair[0]["payload"]["mode"]),
            (147, "aborted_external_recovery", "EXTERNAL_INTERRUPTION_RECOVERY")])
        self.assertTrue(all(r["payload"]["provider_usage"] is None for r in pair))
        _OBSERVATIONS["r026_duplicate_attempt_suffix"] = duplicates[0][-6:]

    def test_second_terminal_outcome_cannot_be_produced_by_current_builder(self):
        import provider_accounting
        self.assertNotIn("aborted_external_recovery", provider_accounting.TERMINAL_OUTCOMES)
        started = next(r["payload"] for r in self.executor if r["event"] == "provider_attempt_started")
        with self.assertRaises(ValueError):
            provider_accounting.build_provider_attempt_terminal(
                started, outcome="aborted_external_recovery", provider_usage=None, duration=0.0)

    def test_summary_diverges_from_raw_stream(self):
        accounting = self.summary["provider_accounting"]
        self.assertTrue(accounting["complete"])
        self.assertEqual(accounting["duplicate_terminal_ids"], [])
        self.assertEqual((len(accounting["started_ids"]), len(accounting["terminal_ids"])), (17, 17))
        self.assertFalse(self.summary["usage"]["total"]["complete"])
        self.assertEqual(self.summary["usage"]["executor"]["unknown_usage_calls"], 1)


class AccountingSemanticsTests(unittest.TestCase):
    """C/E on current run_store code with disposable workspaces only."""

    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(dir=_SANDBOX))
        self.workspace = self.temp / "workspace"
        self.workspace.mkdir()

    def make_summary(self, run_id="20261014_000000_s1test"):
        import run_store
        return run_store.create_run_summary(self.workspace, "ws_s1", "chat_s1", "tb_s1", run_id)

    def test_unknown_usage_is_not_zero(self):
        import run_store
        summary = self.make_summary()
        run_store.record_provider_attempt_started(summary, "executor", "pa_1")
        run_store.record_provider_attempt_terminal(summary, "executor", "pa_1", None)
        bucket = summary["usage"]["executor"]
        self.assertEqual((bucket["unknown_usage_calls"], bucket["complete"], bucket["total_tokens"]), (1, False, None))
        self.assertIsNone(summary["usage"]["total"]["total_tokens"])

    def test_duplicate_terminal_via_api_is_flagged_and_not_double_counted(self):
        import run_store
        summary = self.make_summary()
        usage = {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12}
        run_store.record_provider_attempt_started(summary, "executor", "pa_1")
        run_store.record_provider_attempt_terminal(summary, "executor", "pa_1", usage)
        run_store.record_provider_attempt_terminal(summary, "executor", "pa_1", usage)
        self.assertEqual(summary["provider_accounting"]["duplicate_terminal_ids"], ["pa_1"])
        self.assertFalse(summary["provider_accounting"]["complete"])
        self.assertEqual(summary["usage"]["executor"]["known_total_tokens"], 12)

    def test_out_of_band_stream_append_does_not_reach_summary(self):
        import run_store
        self.make_summary()
        run_id = "20261014_000000_s1test"
        before = run_store.load_run_summary(self.workspace, run_id)
        run_store.append_run_record(self.workspace, run_id, source="EXECUTOR",
                                    event="provider_attempt_terminal",
                                    payload={"provider_attempt_id": "pa_x", "outcome": "aborted_external_recovery",
                                             "provider_usage": None}, timestamp=time.time())
        after = run_store.load_run_summary(self.workspace, run_id)
        self.assertEqual(before, after)
        self.assertEqual(len(run_store.load_stream_records(self.workspace, run_id, "EXECUTOR")), 1)

    def test_precached_tokens_are_not_aggregated(self):
        import run_store
        summary = self.make_summary()
        usage = {"raw": {"prompt_tokens": 400, "completion_tokens": 58, "total_tokens": 458,
                         "precached_prompt_tokens": 73920},
                 "prompt_tokens": 400, "completion_tokens": 58, "total_tokens": 458}
        run_store.record_provider_attempt_started(summary, "executor", "pa_1")
        run_store.record_provider_attempt_terminal(summary, "executor", "pa_1", usage)
        self.assertEqual(summary["usage"]["executor"]["total_tokens"], 458)
        self.assertNotIn("73920", json.dumps(summary["usage"]))

    def test_negative_control_api_terminal_does_change_summary(self):
        import run_store
        summary = self.make_summary()
        before = copy.deepcopy(summary)
        run_store.record_provider_attempt_started(summary, "executor", "pa_1")
        self.assertNotEqual(before, summary)


# --------------------------------------------------------------------------- D. HTTP wire evidence

class WireEvidenceTests(unittest.IsolatedAsyncioTestCase):
    BODY = {
        "model": "GigaChat-3-Ultra",
        "messages": [{"role": "system", "content": "Система — проверка UTF-8 ✓"},
                     {"role": "user", "content": "привет"}],
        "temperature": 0.15, "max_tokens": 32768, "stream": False,
        "functions": [{"name": "read_file", "description": "Читает файл",
                       "parameters": {"type": "object", "properties": {"path": {"type": "string"}},
                                      "required": ["path"]}}],
        "function_call": "auto",
    }

    async def send(self, body):
        import httpx
        import gigachat_transport
        capture = WireCapture(lambda _b, _n: (200, chat_response()))
        with capture.patch():
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(gigachat_transport.CHAT_URL, headers={"Authorization": "Bearer x"},
                                             json=body)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(capture.requests), 1)
        return capture.requests[0]

    async def test_canonical_snapshot_length_matches_wire_but_hash_does_not(self):
        import provider_accounting
        wire = (await self.send(self.BODY))["content"]
        started = provider_accounting.build_provider_attempt_started(
            role="executor", mode="DIRECT", provider="gigachat", model_id="m", provider_model_id="m",
            body=self.BODY, blocks=[])
        length_equal, canonical_equal, wire_equal = wire_binding(started, wire)
        self.assertEqual((length_equal, canonical_equal, wire_equal), (True, True, False))
        self.assertIn("привет".encode("utf-8"), wire)  # ensure_ascii=False on the wire
        self.assertEqual(wire, json.dumps(self.BODY, ensure_ascii=False, separators=(",", ":"),
                                          allow_nan=False).encode("utf-8"))
        _OBSERVATIONS["wire_vs_canonical"] = {"wire_bytes": len(wire), "wire_sha256": _sha256(wire),
                                              "snapshot_sha256": started["request_snapshot_sha256"]}

    async def test_sorted_key_body_is_the_only_case_where_hashes_match(self):
        import provider_accounting
        ordered = json.loads(provider_accounting.canonical_json_text(self.BODY))
        wire = (await self.send(ordered))["content"]
        started = provider_accounting.build_provider_attempt_started(
            role="executor", mode="DIRECT", provider="gigachat", model_id="m", provider_model_id="m",
            body=ordered, blocks=[])
        self.assertEqual(wire_binding(started, wire), (True, True, True))

    async def test_negative_control_different_body_breaks_binding(self):
        import provider_accounting
        wire = (await self.send(self.BODY))["content"]
        other = copy.deepcopy(self.BODY)
        other["messages"][1]["content"] = "пока"
        started = provider_accounting.build_provider_attempt_started(
            role="executor", mode="DIRECT", provider="gigachat", model_id="m", provider_model_id="m",
            body=other, blocks=[])
        self.assertEqual(wire_binding(started, wire)[1:], (False, False))

    async def test_content_length_header_equals_body_bytes(self):
        request = await self.send(self.BODY)
        self.assertEqual(int(request["content_length"]), len(request["content"]))
        self.assertEqual(request["content_type"], "application/json")


# --------------------------------------------------------------------------- B/C. physical routes on fake transport

class RouteTransportTests(unittest.IsolatedAsyncioTestCase):
    def assert_single_chat_post(self, capture, count=1):
        import gigachat_transport
        self.assertEqual(capture.violations, [])
        self.assertEqual(len(capture.requests), count)
        self.assertTrue(all(r["url"] == gigachat_transport.CHAT_URL and r["method"] == "POST"
                            for r in capture.requests))

    def assert_bound(self, started_payload, wire):
        self.assertEqual(wire_binding(started_payload, wire), (True, True, False))

    async def test_route1_mcp_ask_gigachat_sends_without_any_accounting(self):
        import server
        capture = WireCapture(lambda _b, _n: (200, chat_response("answer")))
        with _Patches([capture.patch(), *token_patches()]):
            answer = await server.ask_gigachat("привет")
        self.assertEqual(answer, "answer")
        self.assert_single_chat_post(capture)
        body = json.loads(capture.requests[0]["content"])
        self.assertEqual(list(body), ["model", "messages", "temperature", "max_tokens", "stream"])
        self.assertEqual(body["max_tokens"], server.MAX_TOKENS)
        source = Path(server.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef) and n.name == "ask_gigachat")
        names = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)} | {
            n.attr for n in ast.walk(fn) if isinstance(n, ast.Attribute)}
        self.assertFalse({"build_provider_attempt_started", "build_provider_attempt_terminal",
                          "extract_usage", "_emit"} & names)
        _OBSERVATIONS["route1_unaccounted_wire_bytes"] = len(capture.requests[0]["content"])

    async def test_route2_audit_diagnostic_forks_full_executor_context(self):
        import httpx
        import server
        marker = "BIGMARK-" + "Ж" * 5000
        messages = [{"role": "system", "content": "sys"}, {"role": "user", "content": "task"},
                    {"role": "function", "name": "read_file",
                     "content": json.dumps({"content": marker}, ensure_ascii=False)}]
        events = []
        capture = WireCapture(lambda _b, _n: (200, chat_response("because")))
        with _Patches([capture.patch()]):
            async with httpx.AsyncClient(timeout=5.0) as client:
                answer = await server._request_audit_diagnostic(
                    client, {"Authorization": "Bearer x"}, "GigaChat-3-Ultra", messages, "CANDIDATE", "Why?",
                    model_id="gigachat_ultra", diagnostic_callback=lambda k, p: events.append({"event": k, **p}))
        self.assertEqual(answer, "because")
        self.assert_single_chat_post(capture)
        wire = capture.requests[0]["content"]
        self.assertIn(marker.encode("utf-8"), wire)
        body = json.loads(wire)
        self.assertEqual(body["max_tokens"], server.MAX_AUDIT_DIAGNOSTIC_TOKENS)
        self.assertEqual([m["role"] for m in body["messages"]], ["system", "user", "function", "assistant", "user"])
        started, terminal = attempt_pairs(events)
        self.assertEqual((len(started), len(terminal)), (1, 1))
        self.assertEqual((started[0]["role"], started[0]["mode"]), ("executor", "AUDIT_DIAGNOSTIC"))
        self.assertEqual(started[0]["provider_attempt_id"], terminal[0]["provider_attempt_id"])
        self.assert_bound(started[0], wire)

    async def run_executor(self, workspace: Path, responder, *, planner_enabled: bool, task: str, tool_limit=6):
        import agent_global_context
        import server
        # sandbox APP_DATA_ROOT starts empty; provision the mandatory global context the supported way
        agent_global_context.save_agent_global_context("S1 TEST GLOBAL CONTEXT", "ultra")
        events: list[dict] = []
        capture = WireCapture(responder)
        permissions = {"allow_read": True, "allow_write": False, "allow_delete": False, "allow_verify": False,
                       "allow_guard_p1": True, "read_scope": ".", "write_scope": ".", "delete_scope": ".",
                       "tool_limit": tool_limit, "auto_backup": True}
        guards = [patch.object(server, name, side_effect=AssertionError(name + " must not run in S1 probe"))
                  for name in ("_agent_git_status", "_agent_git_diff", "run_verifier_check",
                               "_request_audit_diagnostic", "run_planner_dredd_review")]
        with _Patches([capture.patch(), *token_patches(), *guards]):
            result = await server.run_agent_task(
                task, str(workspace), on_event=lambda e: events.append(copy.deepcopy(e)),
                permissions=permissions, planner_enabled=planner_enabled, final_audit_enabled=False)
        return result, events, capture

    async def test_route3_executor_direct_accumulates_tool_results_without_reset(self):
        workspace = Path(tempfile.mkdtemp(dir=_SANDBOX)) / "ws"
        workspace.mkdir()
        big = "S1BIG-" + ("строка данных " * 8000)
        (workspace / "big.txt").write_text(big, encoding="utf-8", newline="\n")
        (workspace / "small.txt").write_text("small", encoding="utf-8", newline="\n")
        script = [
            chat_response(None, function_call={"name": "read_file", "arguments": {"path": "big.txt"}}),
            chat_response(None, function_call={"name": "read_file", "arguments": {"path": "small.txt"}}),
            chat_response("done"),
        ]
        result, events, capture = await self.run_executor(
            workspace, lambda _b, n: (200, script[n - 1]), planner_enabled=False, task="прочитай файлы")
        self.assert_single_chat_post(capture, 3)
        wires = [r["content"] for r in capture.requests]
        marker = "S1BIG-".encode("utf-8")
        self.assertEqual([marker in w for w in wires], [False, True, True])
        sizes = [len(w) for w in wires]
        self.assertGreater(sizes[1] - sizes[0], len(big.encode("utf-8")))
        self.assertGreater(sizes[2], sizes[1])
        started, terminal = attempt_pairs(events)
        executor_started = [e for e in started if e["role"] == "executor"]
        self.assertEqual([e["mode"] for e in executor_started], ["DIRECT"] * 3)
        self.assertEqual(len(terminal), 3)
        for payload, wire in zip(executor_started, wires):
            self.assert_bound(payload, wire)
        self.assertFalse(any(e.get("event") == "executor_diagnostic_reset" for e in events))
        self.assertIn("done", result)
        _OBSERVATIONS["route3_direct_request_bytes"] = sizes

    async def test_route3_route4_planner_on_resets_executor_context_at_stage_boundary(self):
        workspace = Path(tempfile.mkdtemp(dir=_SANDBOX)) / "ws"
        workspace.mkdir()
        (workspace / "big.txt").write_text("S1STAGE-" + ("контекст " * 6000), encoding="utf-8", newline="\n")
        plan = {"stages": [
            {"stage_id": "stage_1", "goal": "Прочитать big.txt", "stage_type": "analysis",
             "persistence_required": False, "allowed_capabilities": ["READ"], "artifacts": [],
             "completion_mode": "model_result", "evidence_requirements": [],
             "completion_criteria": ["Файл прочитан"]},
            {"stage_id": "stage_2", "goal": "Сформулировать ответ", "stage_type": "analysis",
             "persistence_required": False, "allowed_capabilities": [], "artifacts": [],
             "completion_mode": "model_result", "evidence_requirements": [],
             "completion_criteria": ["Ответ сформулирован"]}],
            "obligation_changes": []}
        ready = {"status": "READY_TO_PERSIST", "reason": "готово", "unresolved_requirements": [],
                 "next_action": "дальше"}
        executor_script = [
            chat_response(None, function_call={"name": "read_file", "arguments": {"path": "big.txt"}}),
            chat_response("итог стадии 1"),
            chat_response("итог стадии 2"),
        ]
        counters = {"planner": 0, "executor": 0}

        def responder(body, _n):
            if body.get("function_call") == "none":
                counters["planner"] += 1
                payload = json.loads(body["messages"][-1]["content"])
                return 200, chat_response(json.dumps(plan if payload.get("mode") == "INITIAL" else ready,
                                                     ensure_ascii=False))
            counters["executor"] += 1
            if counters["executor"] > len(executor_script):
                return 200, chat_response("незапланированный вызов")
            return 200, executor_script[counters["executor"] - 1]

        result, events, capture = await self.run_executor(
            workspace, responder, planner_enabled=True, task="прочитай big.txt и ответь")
        self.assertEqual(capture.violations, [])
        bodies = [json.loads(r["content"]) for r in capture.requests]
        executor_wires = [r["content"] for r, b in zip(capture.requests, bodies) if b.get("function_call") != "none"]
        self.assertEqual(len(executor_wires), 3, counters)
        marker = "S1STAGE-".encode("utf-8")
        self.assertEqual([marker in w for w in executor_wires], [False, True, False])
        resets = [e for e in events if e.get("event") == "executor_diagnostic_reset"]
        self.assertEqual(len(resets), 1)
        self.assertEqual(resets[0]["removed_function_messages"], ["read_file"])
        started, terminal = attempt_pairs(events)
        modes = [(e["role"], e["mode"]) for e in started]
        self.assertEqual(modes, [("planner", "INITIAL"), ("executor", "STAGE:stage_1"),
                                 ("executor", "STAGE:stage_1"), ("planner", "READINESS"),
                                 ("executor", "STAGE:stage_2"), ("planner", "READINESS")])
        self.assertEqual(len(terminal), len(started))
        for payload, request in zip(started, capture.requests):
            self.assert_bound(payload, request["content"])
        self.assertIn("итог стадии 2", result)
        _OBSERVATIONS["route4_planner_on_request_bytes"] = [len(r["content"]) for r in capture.requests]

    async def test_executor_transport_failures_are_recorded_as_unknown_not_zero(self):
        import run_store
        for status, outcome in (("timeout", "timeout"), (500, "provider_error")):
            with self.subTest(status=status):
                workspace = Path(tempfile.mkdtemp(dir=_SANDBOX)) / "ws"
                workspace.mkdir()
                events: list[dict] = []
                capture = WireCapture(lambda _b, _n, s=status: (s, {"error": "fake"}))
                import agent_global_context
                import server
                agent_global_context.save_agent_global_context("S1 TEST GLOBAL CONTEXT", "ultra")
                permissions = {"allow_read": True, "allow_write": False, "allow_delete": False,
                               "allow_verify": False, "allow_guard_p1": True, "read_scope": ".",
                               "write_scope": ".", "delete_scope": ".", "tool_limit": 3, "auto_backup": True}
                with _Patches([capture.patch(), *token_patches()]):
                    with self.assertRaises(Exception):
                        await server.run_agent_task("привет", str(workspace),
                                                    on_event=lambda e: events.append(copy.deepcopy(e)),
                                                    permissions=permissions, final_audit_enabled=False)
                self.assert_single_chat_post(capture)
                started, terminal = attempt_pairs(events)
                self.assertEqual([t["outcome"] for t in terminal], [outcome])
                self.assertIsNone(terminal[0]["provider_usage"])
                self.assertFalse(any(e.get("event") == "run_finished" and e.get("status") == "SUCCESS"
                                     for e in events))
                run_id = next(e["run_id"] for e in events if e.get("event") == "run_started")
                summary = run_store.load_run_summary(workspace, run_id)
                bucket = summary["usage"]["executor"]
                self.assertEqual((bucket["attempts_started"], bucket["unknown_usage_calls"], bucket["complete"]),
                                 (1, 1, False))
                self.assertIsNone(summary["usage"]["total"]["total_tokens"])

    async def test_accounting_storage_failure_does_not_stop_a_paid_send(self):
        import audit_storage
        import run_store
        original = audit_storage.AuditThreadRecorder.observe

        def failing_observe(recorder, event, *args, **kwargs):
            if str(event.get("event", "")).startswith("provider_attempt_"):
                raise OSError("S1 simulated accounting storage failure")
            return original(recorder, event, *args, **kwargs)

        workspace = Path(tempfile.mkdtemp(dir=_SANDBOX)) / "ws"
        workspace.mkdir()
        with patch.object(audit_storage.AuditThreadRecorder, "observe", failing_observe):
            result, events, capture = await self.run_executor(
                workspace, lambda _b, _n: (200, chat_response("готово")), planner_enabled=False, task="привет")
        self.assert_single_chat_post(capture)
        self.assertTrue(any(e.get("event") == "run_finished" and e.get("status") == "SUCCESS" for e in events))
        flagged = [e for e in events if e.get("event", "").startswith("provider_attempt_")]
        self.assertEqual({e.get("audit_storage_error") for e in flagged}, {"OSError"})
        run_id = next(e["run_id"] for e in events if e.get("event") == "run_started")
        summary = run_store.load_run_summary(workspace, run_id)
        # one physical paid request happened, yet the durable summary records no attempt at all
        self.assertEqual(summary["usage"]["executor"]["attempts_started"], 0)
        self.assertEqual(summary["usage"]["total"]["calls"], 0)
        self.assertEqual(summary["provider_accounting"]["started_ids"], [])
        self.assertIn("готово", result)

    async def test_route5_direct_run_planner_is_accounted_but_has_no_production_caller(self):
        import planner_runtime
        events = []
        plan = {"stages": [{"stage_id": "stage_1", "goal": "ответить", "stage_type": "analysis",
                            "persistence_required": False, "allowed_capabilities": [], "artifacts": [],
                            "completion_mode": "model_result", "evidence_requirements": [],
                            "completion_criteria": ["Ответ"]}], "obligation_changes": []}
        capture = WireCapture(lambda _b, _n: (200, chat_response(json.dumps(plan, ensure_ascii=False))))
        with _Patches([capture.patch(), *token_patches()]):
            result = await planner_runtime.run_planner(
                mode="INITIAL", raw_task="привет", context={},
                diagnostic_callback=lambda k, p: events.append({"event": k, **p}))
        self.assertEqual(result["stages"][0]["stage_id"], "stage_1")
        self.assert_single_chat_post(capture)
        started, terminal = attempt_pairs(events)
        self.assertEqual((len(started), len(terminal)), (1, 1))
        self.assertIn("planner_direct_call", started[0]["source_references"])
        self.assert_bound(started[0], capture.requests[0]["content"])

    async def test_route6_verifier_final_and_permission_and_planner_review(self):
        import verifier_runtime
        for check_type in ("FINAL", "PERMISSION"):
            with self.subTest(check_type=check_type):
                events = []
                verdict = {"result": "PASS", "check_type": check_type, "violations": [], "reason": "ok",
                           "required_action": ""}
                capture = WireCapture(lambda _b, _n: (200, chat_response(json.dumps(verdict))))
                with _Patches([capture.patch(), *token_patches()]):
                    result = await verifier_runtime.run_verifier_check(
                        check_type=check_type, raw_task="привет", verification_context="{}",
                        diagnostic_callback=lambda k, p: events.append({"event": k, **p}))
                self.assertEqual(result.verdict, "PASS")
                self.assert_single_chat_post(capture)
                started, terminal = attempt_pairs(events)
                self.assertEqual((len(started), len(terminal), started[0]["role"]), (1, 1, "dredd"))
                self.assert_bound(started[0], capture.requests[0]["content"])
        events = []
        review = {"diagnosis": "план неполон", "required_action": "исправить"}
        capture = WireCapture(lambda _b, _n: (200, chat_response(json.dumps(review, ensure_ascii=False))))
        with _Patches([capture.patch(), *token_patches()]):
            await verifier_runtime.run_planner_dredd_review(
                raw_task="привет", planner_session_transcript=[{"role": "user", "content": "x"}],
                mode="INITIAL", validation_error="bad plan", task_block_id=None,
                diagnostic_callback=lambda k, p: events.append({"event": k, **p}))
        self.assert_single_chat_post(capture)
        started, terminal = attempt_pairs(events)
        self.assertEqual((len(started), len(terminal), started[0]["role"]), (1, 1, "dredd"))

    async def test_route6_verifier_protocol_error_discards_returned_usage(self):
        import verifier_runtime
        events = []
        usage = {"prompt_tokens": 2203, "completion_tokens": 90, "total_tokens": 2293, "precached_prompt_tokens": 0}
        capture = WireCapture(lambda _b, _n: (200, chat_response("{}", finish_reason="length", usage=usage)))
        with _Patches([capture.patch(), *token_patches()]):
            with self.assertRaises(verifier_runtime.VerifierRuntimeError):
                await verifier_runtime.run_verifier_check(
                    check_type="FINAL", raw_task="привет", verification_context="{}",
                    diagnostic_callback=lambda k, p: events.append({"event": k, **p}))
        self.assert_single_chat_post(capture)
        _started, terminal = attempt_pairs(events)
        self.assertEqual(len(terminal), 1)
        self.assertEqual(terminal[0]["outcome"], "parse_error")
        self.assertIsNone(terminal[0]["provider_usage"])  # usage was in the HTTP response but is lost

    async def test_route7_compressor_is_accounted_outside_run_store(self):
        import compressor_runtime
        events = []
        body = compressor_runtime.build_compressor_request_body("gigachat_3_pro", "Сожми текст")
        capture = WireCapture(lambda _b, _n: (200, chat_response("сжато")))
        with _Patches([capture.patch(), *token_patches()]):
            result = await compressor_runtime._request_gigachat(
                body, model_id="gigachat_3_pro", diagnostic_callback=lambda k, p: events.append({"event": k, **p}))
        self.assertEqual(result, "сжато")
        self.assert_single_chat_post(capture)
        started, terminal = attempt_pairs(events)
        self.assertEqual((len(started), len(terminal), started[0]["role"]), (1, 1, "compressor"))
        self.assert_bound(started[0], capture.requests[0]["content"])
        import run_store
        self.assertNotIn("compressor", run_store.USAGE_ROLES)
        with self.assertRaises(ValueError):
            run_store.record_provider_attempt_started(run_store.empty_usage_summary() | {
                "provider_accounting": run_store.empty_provider_accounting_summary()}, "compressor", "pa_c")

    async def test_negative_control_unexpected_destination_is_rejected(self):
        import httpx
        capture = WireCapture(lambda _b, _n: (200, chat_response()))
        with capture.patch():
            async with httpx.AsyncClient(timeout=5.0) as client:
                with self.assertRaises(httpx.ConnectError):
                    await client.post("https://example.invalid/v1/chat/completions", json={"x": 1})
        self.assertEqual(len(capture.violations), 1)


# --------------------------------------------------------------------------- B. static inventory and reachability

def _production_modules() -> list[Path]:
    modules = [p for p in ROOT.glob("*.py") if not p.name.startswith("test_") and p.name != "conftest.py"]
    modules += sorted((ROOT / "web_alarm").glob("*.py"))
    return sorted(modules)


def _qualified_calls(path: Path, source: str | None = None) -> list[tuple[str, str, str, int]]:
    tree = ast.parse(source if source is not None else path.read_text(encoding="utf-8"))
    found = []

    def visit(node, scope, in_function):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                visit(child, (scope + "." if scope else "") + child.name, in_function)
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # nested helpers report their outermost function (the physical send owner)
                visit(child, scope if in_function else (scope + "." if scope else "") + child.name, True)
            else:
                if (isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute)
                        and child.func.attr in {"post", "send", "stream", "request"}):
                    found.append((path.name, scope, ast.unparse(child.func), child.lineno))
                visit(child, scope, in_function)

    visit(tree, "", False)
    return found


class StaticRouteInventoryTests(unittest.TestCase):
    def test_http_send_sites_match_inventory_exactly(self):
        sites = []
        for module in _production_modules():
            sites += [s for s in _qualified_calls(module) if module.name not in TOOLING_MODULES]
        relevant = {(m, f, c) for m, f, c, _ in sites if c.startswith("client.") or "httpx" in c}
        non_client = sorted({(m, f, c) for m, f, c, _ in sites} - relevant)
        _OBSERVATIONS["static_send_sites"] = sorted([list(s) for s in sites])
        self.assertEqual(relevant, EXPECTED_HTTP_SENDS, non_client)

    def test_httpx_is_imported_only_by_known_modules(self):
        importers = set()
        for module in _production_modules():
            tree = ast.parse(module.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import) and any(a.name.split(".")[0] in {"httpx", "requests", "aiohttp"}
                                                        for a in node.names):
                    importers.add(module.name)
                if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] in {
                        "httpx", "requests", "aiohttp"}:
                    importers.add(module.name)
        self.assertEqual(importers - TOOLING_MODULES, {
            "server.py", "planner_runtime.py", "verifier_runtime.py", "compressor_runtime.py",
            "gigachat_transport.py"})

    def test_negative_control_extra_send_is_detected(self):
        source = "async def sneaky(client):\n    return await client.stream('POST', 'x')\n"
        sites = _qualified_calls(ROOT / "synthetic.py", source)
        self.assertEqual([(m, f, c) for m, f, c, _ in sites], [("synthetic.py", "sneaky", "client.stream")])

    def test_direct_run_planner_has_no_production_caller(self):
        callers = []
        for module in _production_modules():
            tree = ast.parse(module.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "run_planner":
                    session = next((k.value for k in node.keywords if k.arg == "session"), None)
                    callers.append((module.name, node.lineno, ast.unparse(session) if session is not None else None))
        self.assertEqual([(m, s) for m, _l, s in callers], [("server.py", "planner_session")])
        _OBSERVATIONS["run_planner_callers"] = callers

    def test_ask_gigachat_is_reached_only_from_mcp_tools(self):
        import server
        tree = ast.parse(Path(server.__file__).read_text(encoding="utf-8"))
        owners = []
        for fn in ast.walk(tree):
            if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if any(isinstance(n, ast.Call) and getattr(n.func, "id", None) == "ask_gigachat" for n in ast.walk(fn)):
                    decorators = [ast.unparse(d) for d in fn.decorator_list]
                    owners.append((fn.name, decorators))
        self.assertEqual(owners, [("gigachat_ask", ["mcp.tool()"]), ("gigachat_file_task", ["mcp.tool()"])])
        for module in _production_modules():
            if module.name == "server.py":
                continue
            self.assertNotIn("ask_gigachat", module.read_text(encoding="utf-8"), module.name)

    def test_direct_mode_stage_context_returns_without_lifecycle(self):
        import server
        tree = ast.parse(Path(server.__file__).read_text(encoding="utf-8"))
        stage_context = next(n for n in ast.walk(tree)
                             if isinstance(n, ast.FunctionDef) and n.name == "stage_context")
        first = stage_context.body[0]
        self.assertIsInstance(first, ast.If)
        self.assertEqual(ast.unparse(first.test), "not lifecycle")
        self.assertIsInstance(first.body[0], ast.Return)

    def test_provider_attempt_events_are_not_mandatory_durable_events(self):
        import server
        tree = ast.parse(Path(server.__file__).read_text(encoding="utf-8"))
        emit = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_emit")
        assign = next(n for n in ast.walk(emit) if isinstance(n, ast.Assign)
                      and any(getattr(t, "id", None) == "required_event" for t in n.targets))
        literal = next(n for n in ast.walk(assign.value) if isinstance(n, ast.Set))
        self.assertEqual({ast.literal_eval(e) for e in literal.elts}, {"tool_started", "final_audit_passed"})


class GuardNegativeControlTests(unittest.TestCase):
    """Prove the process guard actually rejects what the probes claim cannot happen."""

    def expect_violation(self, action, event_prefix):
        before = len(_GUARD_VIOLATIONS)
        with self.assertRaises(PermissionError):
            action()
        new = _GUARD_VIOLATIONS[before:]
        self.assertEqual(len(new), 1, new)
        self.assertTrue(new[0]["event"].startswith(event_prefix), new)
        del _GUARD_VIOLATIONS[before:]  # expected probe, not an isolation failure

    def test_network_connect_is_rejected(self):
        def connect():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.connect(("127.0.0.1", 9))
            finally:
                sock.close()
        self.expect_violation(connect, "socket.connect")

    def test_write_outside_sandbox_is_rejected(self):
        self.expect_violation(lambda: open(ROOT / "s1_guard_probe.tmp", "w"), "open")
        self.assertFalse((ROOT / "s1_guard_probe.tmp").exists())

    def test_git_and_production_run_store_reads_are_rejected(self):
        # non-existent probe paths: the guard must refuse by path before any filesystem access
        self.expect_violation(lambda: open(ROOT / ".git" / "s1-nonexistent-probe", "rb"), "open")
        self.expect_violation(lambda: os.listdir(ROOT / ".ultra" / "s1-nonexistent-probe"), "os.listdir")

    def test_child_process_is_rejected(self):
        import subprocess
        self.expect_violation(lambda: subprocess.run(["cmd", "/c", "echo"], check=False), "subprocess")


# --------------------------------------------------------------------------- guarded standalone runner

def _snapshot_evidence(base: Path) -> None:
    for name, (relative, digest, size) in EVIDENCE_PINS.items():
        source = ROOT / relative
        if not source.is_file():
            _EVIDENCE_PROBLEMS.append(f"{name}: source missing")
            continue
        data = source.read_bytes()
        if len(data) != size or _sha256(data) != digest:
            _EVIDENCE_PROBLEMS.append(f"{name}: pinned SHA-256/size mismatch (DRIFT)")
            continue
        target = base / "evidence" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        _EVIDENCE[name] = target


def _install_guards(base: Path):
    """S0-style process guard: reads of ordinary source allowed; nothing else escapes the sandbox."""
    violations = _GUARD_VIOLATIONS
    local = threading.local()
    original_pair = socket.socketpair

    def isolated_pair(*args, **kwargs):
        local.socketpair = True
        try:
            return original_pair(*args, **kwargs)
        finally:
            local.socketpair = False

    socket.socketpair = isolated_pair
    root = os.path.normcase(os.path.abspath(base))

    def path_text(value):
        if isinstance(value, (str, bytes, os.PathLike)):
            return os.path.normcase(os.path.abspath(os.fsdecode(value)))
        return None

    def under_root(value):
        value = path_text(value)
        return value is not None and (value == root or value.startswith(root + os.sep))

    def reject(event, detail):
        violations.append({"event": event, "detail": str(detail)})
        raise PermissionError("S1 isolation guard: " + event + " " + str(detail))

    def audit(event, args):
        if event.startswith("subprocess.") or event in {"os.system", "os.posix_spawn", "os.posix_spawnp"} \
                or event.startswith("os.spawn") or event.startswith("os.exec"):
            reject(event, "child processes forbidden")
        if event in {"socket.connect", "socket.connect_ex", "socket.bind", "socket.getaddrinfo",
                     "socket.gethostbyname", "socket.sendto"}:
            if not getattr(local, "socketpair", False):
                reject(event, "network forbidden")
        if event in {"open", "os.listdir", "os.scandir"} and args:
            name = path_text(args[0])
            if name:
                parts = Path(name).parts
                if ".git" in parts or (".ultra" in parts and not under_root(name)):
                    reject(event, "Git/production storage access forbidden")
            if event == "open" and name:
                mode = args[1] if len(args) > 1 else "r"
                flags = args[2] if len(args) > 2 else 0
                writable = (isinstance(mode, str) and any(c in mode for c in "wax+")) or (
                    isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
                if writable and not under_root(name):
                    reject(event, name)
        if event in {"os.mkdir", "os.remove", "os.rmdir", "os.rename", "os.link", "os.symlink", "os.chmod",
                     "os.utime", "os.truncate", "shutil.rmtree", "shutil.copyfile", "shutil.copytree",
                     "shutil.move"}:
            targets = args[:2] if event in {"os.rename", "os.link", "os.symlink", "shutil.copyfile",
                                            "shutil.copytree", "shutil.move"} else args[:1]
            for value in targets[-1:] if event.startswith("shutil.copy") or event == "shutil.move" else targets:
                if path_text(value) and not under_root(value):
                    reject(event, value)

    sys.addaudithook(audit)
    return violations


def main() -> int:
    global _ISOLATED, _SANDBOX
    sys.dont_write_bytecode = True
    base = Path(tempfile.mkdtemp(prefix="claude-rt002-s1-"))
    _SANDBOX = base
    _snapshot_evidence(base)  # read-only snapshot of pinned RAW evidence before guards
    for key in ("LOCALAPPDATA", "APPDATA", "TEMP", "TMP"):
        location = base / key.lower()
        location.mkdir()
        os.environ[key] = str(location)
    tempfile.tempdir = str(base / "temp")
    for key in ("GIGACHAT_CREDENTIALS", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
        os.environ.pop(key, None)
    violations = _install_guards(base)
    _ISOLATED = True
    already = sorted(m for m in ("server", "planner_runtime", "verifier_runtime", "compressor_runtime",
                                 "run_store", "workspace_runtime_settings") if m in sys.modules)
    if already:
        raise SystemExit("Runtime modules imported before guards: " + ", ".join(already))
    import server  # noqa: F401  (import only after guards and sandbox redirection)
    import compressor_runtime  # noqa: F401
    import verifier_runtime  # noqa: F401
    loader = unittest.defaultTestLoader
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    tests = []

    def flatten(item):
        if isinstance(item, unittest.TestSuite):
            for child in item:
                flatten(child)
        else:
            tests.append(item)

    flatten(suite)
    if sys.argv[1:]:
        requested = set(sys.argv[1:])
        tests = [t for t in tests if t.id() in requested or t.id().split(".")[-1] in requested]
        if not tests:
            raise SystemExit("Selectors must resolve to tests in this module")
    started = time.time()
    log_path = base / "unittest.log"
    with log_path.open("w", encoding="utf-8") as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.TestSuite(tests))
    report = {
        "task": "CLAUDE-RT002-S1-001", "sandbox": str(base), "python": sys.version.split()[0],
        "tests": result.testsRun, "failures": [t.id() for t, _ in result.failures],
        "errors": [t.id() for t, _ in result.errors],
        "skipped": [(t.id(), reason) for t, reason in result.skipped],
        "isolation_violations": violations, "evidence_problems": _EVIDENCE_PROBLEMS,
        "manifest": [t.id() for t in tests], "elapsed_seconds": round(time.time() - started, 3),
        "observations": _OBSERVATIONS, "log": str(log_path),
        "log_sha256": _sha256(log_path.read_bytes()),
    }
    (base / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in {"manifest", "observations"}},
                     ensure_ascii=False, indent=2))
    if result.failures or result.errors:
        print(log_path.read_text(encoding="utf-8").split("=" * 70, 1)[-1])
    return 0 if result.wasSuccessful() and not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
