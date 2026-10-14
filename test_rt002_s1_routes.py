"""RT-002 S1 baseline-and-routes offline probes (CLAUDE-RT002-S1-001, repaired by CLAUDE-RT002-S1-REPAIR-001).

Production code is never patched on disk. Acceptance command (the only one):
    .venv/Scripts/python.exe -B test_rt002_s1_routes.py
Exit codes: 0 = full MANIFEST passed through the gate; 1 = FAIL (any failure, error,
skip, missing/mismatched RAW evidence, collection mismatch, zero tests, unresolved
selector or isolation violation); 3 = PARTIAL_SELECTION (positional selectors were
given; never an acceptance result). RT002_S1_EVIDENCE_ROOT may point the RAW evidence
snapshot at another root (used only for negative gate checks).

The standalone runner (1) snapshots pinned read-only RAW Run Store evidence (R-031,
R-026) into a disposable sandbox after verifying SHA-256, then (2) redirects
LOCALAPPDATA/APPDATA/TEMP into the sandbox and installs process-wide audit guards
BEFORE runtime imports: no network, no child processes, no writes outside the
sandbox, no access to .git or to any .ultra outside the sandbox.
All LLM traffic is captured at the httpx transport layer (the exact request bytes
httpx would put on the socket) and answered by a fake provider.
Ordinary unittest discovery skips this module; such a run is NOT an S1 acceptance result.
"""
from __future__ import annotations

import ast
import asyncio
import copy
import hashlib
import json
import os
from pathlib import Path
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

# Static send-site inventory: (module, owner function, send kind, traffic class) -> multiplicity.
# Established by CLAUDE-RT002-S1-RECON-001 / S1-001; multiplicity is part of the contract.
EXPECTED_SEND_SITES = {
    ("server.py", "ask_gigachat", "client.post", "LLM"): 1,
    ("server.py", "_request_audit_diagnostic", "client.post", "LLM"): 1,
    ("server.py", "_run_agent_task_impl", "client.post", "LLM"): 1,
    ("planner_runtime.py", "PlannerSession.call", "client.post", "LLM"): 1,
    ("planner_runtime.py", "run_planner", "client.post", "LLM"): 1,
    ("verifier_runtime.py", "_request_gigachat", "client.post", "LLM"): 1,
    ("compressor_runtime.py", "_request_gigachat", "client.post", "LLM"): 1,
    ("gigachat_transport.py", "get_access_token", "client.post", "OAUTH"): 1,
}
# Modules outside the Ultra production send set; production modules must not import them.
NON_PRODUCTION_MODULES = {
    "apply_context_step1.py", "apply_ultra_ui_visual_patch.py", "fix_chat_raw_display.py",
    "patch_allow_py.py", "probe_gigachat_models.py", "live_test_context_bridge.py",
    "wa4a_acceptance.py", "wa4o_ui_demo.py", "wa4o_ui_launcher.py",
}
EXPECTED_NON_PRODUCTION_SITES = {
    ("probe_gigachat_models.py", "main", "client.get", "UNKNOWN"): 1,  # manual GET /models probe
    ("wa4o_ui_launcher.py", "verify_response", "urlopen", "UNKNOWN"): 2,  # local Web Alarm UI launcher
}
# Exact acceptance collection (Class.method). Any missing, extra, skipped or unstarted test fails the gate.
MANIFEST = (
    "AccountingSemanticsTests.test_duplicate_terminal_via_api_is_flagged_and_not_double_counted",
    "AccountingSemanticsTests.test_negative_control_api_terminal_does_change_summary",
    "AccountingSemanticsTests.test_out_of_band_stream_append_does_not_reach_summary",
    "AccountingSemanticsTests.test_precached_tokens_are_not_aggregated",
    "AccountingSemanticsTests.test_unknown_usage_is_not_zero",
    "EvidenceGateTests.test_manifest_matches_the_loaded_collection",
    "EvidenceGateTests.test_pinned_evidence_snapshot_is_complete_and_verified",
    "EvidenceGateTests.test_require_evidence_raises_failure_not_skip",
    "EvidenceGateTests.test_snapshot_reports_missing_and_mismatched_sources",
    "GateLogicTests.test_any_skip_fails",
    "GateLogicTests.test_failures_errors_expected_failures_and_unexpected_successes_fail",
    "GateLogicTests.test_incomplete_or_unexpected_collection_fails",
    "GateLogicTests.test_isolation_violation_fails",
    "GateLogicTests.test_missing_or_mismatched_evidence_fails",
    "GateLogicTests.test_nominal_full_run_is_the_only_pass",
    "GateLogicTests.test_selector_runs_are_never_acceptance",
    "GateLogicTests.test_tests_that_never_started_fail",
    "GateLogicTests.test_zero_tests_and_empty_manifest_fail",
    "GuardNegativeControlTests.test_child_process_is_rejected",
    "GuardNegativeControlTests.test_git_and_production_run_store_reads_are_rejected",
    "GuardNegativeControlTests.test_network_connect_is_rejected",
    "GuardNegativeControlTests.test_write_outside_sandbox_is_rejected",
    "R026RawAccountingTests.test_raw_stream_has_two_terminals_for_one_attempt",
    "R026RawAccountingTests.test_second_terminal_outcome_cannot_be_produced_by_current_builder",
    "R026RawAccountingTests.test_summary_diverges_from_raw_stream",
    "R031RawMatrixTests.test_fifteen_executor_calls_with_exact_request_sizes_in_one_stage",
    "R031RawMatrixTests.test_large_blocks_bind_to_the_two_full_reads_of_root_ultra_ui",
    "R031RawMatrixTests.test_large_blocks_follow_eight_plus_three",
    "R031RawMatrixTests.test_negative_control_oracle_detects_a_missing_resend",
    "R031RawMatrixTests.test_tokens_from_raw_terminals_without_summary",
    "RouteTransportTests.test_accounting_storage_failure_does_not_stop_a_paid_send",
    "RouteTransportTests.test_executor_transport_failures_are_recorded_as_unknown_not_zero",
    "RouteTransportTests.test_negative_control_synchronous_transport_is_rejected",
    "RouteTransportTests.test_negative_control_unexpected_destination_is_rejected",
    "RouteTransportTests.test_oauth_token_traffic_is_distinct_from_llm_traffic",
    "RouteTransportTests.test_route1_mcp_ask_gigachat_sends_without_any_accounting",
    "RouteTransportTests.test_route2_audit_diagnostic_forks_full_executor_context",
    "RouteTransportTests.test_route3_executor_direct_accumulates_tool_results_without_reset",
    "RouteTransportTests.test_route3_route4_planner_on_resets_executor_context_at_stage_boundary",
    "RouteTransportTests.test_route5_direct_run_planner_is_accounted_but_has_no_production_caller",
    "RouteTransportTests.test_route6_verifier_final_and_permission_and_planner_review",
    "RouteTransportTests.test_route6_verifier_protocol_error_discards_returned_usage",
    "RouteTransportTests.test_route7_compressor_is_accounted_outside_run_store",
    "StaticRouteInventoryTests.test_ask_gigachat_is_reached_only_from_mcp_tools",
    "StaticRouteInventoryTests.test_canonical_url_constants_are_defined_once_and_never_rebound",
    "StaticRouteInventoryTests.test_direct_mode_stage_context_returns_without_lifecycle",
    "StaticRouteInventoryTests.test_direct_run_planner_has_no_production_caller",
    "StaticRouteInventoryTests.test_httpx_is_imported_only_by_known_modules",
    "StaticRouteInventoryTests.test_negative_control_aliases_send_stream_and_wrappers_are_detected",
    "StaticRouteInventoryTests.test_negative_control_baseline_synthetic_route",
    "StaticRouteInventoryTests.test_negative_control_inventory_comparison_fails_on_any_drift",
    "StaticRouteInventoryTests.test_negative_control_module_level_httpx_other_stacks_and_unknown_urls",
    "StaticRouteInventoryTests.test_negative_control_real_source_mutations_are_detected",
    "StaticRouteInventoryTests.test_negative_control_endpoint_read_through_unknown_receiver_is_unexplained",
    "StaticRouteInventoryTests.test_every_endpoint_constant_read_is_an_inventoried_send_url",
    "StaticRouteInventoryTests.test_negative_control_second_post_in_same_function_changes_multiplicity",
    "StaticRouteInventoryTests.test_non_production_send_sites_are_known_and_isolated",
    "StaticRouteInventoryTests.test_production_send_sites_match_inventory_with_multiplicity",
    "StaticRouteInventoryTests.test_provider_attempt_events_are_not_mandatory_durable_events",
    "WireEvidenceTests.test_canonical_snapshot_length_matches_wire_but_hash_does_not",
    "WireEvidenceTests.test_content_length_header_equals_body_bytes",
    "WireEvidenceTests.test_negative_control_different_body_breaks_binding",
    "WireEvidenceTests.test_sorted_key_body_is_the_only_case_where_hashes_match",
)

def setUpModule():
    if not _ISOLATED:
        raise unittest.SkipTest("NOT AN S1 ACCEPTANCE RUN: use the guarded standalone runner")


# --------------------------------------------------------------------------- helpers

def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _require_evidence(*names: str) -> dict[str, Path]:
    """Mandatory RAW evidence: absence or mismatch is a FAILURE, never a skip."""
    if _EVIDENCE_PROBLEMS:
        raise AssertionError("RAW evidence REQUIRED: " + "; ".join(_EVIDENCE_PROBLEMS))
    missing = [name for name in names if name not in _EVIDENCE]
    if missing:
        raise AssertionError("RAW evidence REQUIRED: missing " + ", ".join(missing))
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

    def __init__(self, responder, *, oauth_responder=None):
        self.responder = responder
        self.oauth_responder = oauth_responder
        self.requests: list[dict] = []
        self.violations: list[str] = []

    async def handle(self, request):
        import httpx
        import gigachat_transport
        await request.aread()
        content = bytes(request.content)
        url = str(request.url)
        traffic = {gigachat_transport.CHAT_URL: "LLM", gigachat_transport.OAUTH_URL: "OAUTH"}.get(url, "UNKNOWN")
        record = {
            "method": request.method, "url": url, "traffic": traffic,
            "content": content, "content_length": request.headers.get("content-length"),
            "content_type": request.headers.get("content-type"),
        }
        self.requests.append(record)
        responder = {"LLM": self.responder, "OAUTH": self.oauth_responder}.get(traffic)
        if request.method != "POST" or responder is None:
            self.violations.append(f"unexpected {request.method} {request.url}")
            raise httpx.ConnectError("S1 fake transport: unexpected destination", request=request)
        if traffic == "OAUTH":
            from urllib.parse import parse_qs
            body = {k: v[0] for k, v in parse_qs(content.decode("utf-8")).items()}
        else:
            body = json.loads(content.decode("utf-8"))
        status, payload = responder(body, len(self.requests))
        if status == "timeout":
            raise httpx.ReadTimeout("S1 fake provider timeout", request=request)
        return httpx.Response(status, json=payload, request=request)

    def patch(self):
        import httpx
        capture = self

        async def handle_async_request(_transport, request):
            return await capture.handle(request)

        def handle_request(_transport, request):
            capture.violations.append(f"synchronous transport used for {request.method} {request.url}")
            raise httpx.ConnectError("S1 fake transport: synchronous transport is not inventoried", request=request)

        return _Patches([patch.object(httpx.AsyncHTTPTransport, "handle_async_request", handle_async_request),
                         patch.object(httpx.HTTPTransport, "handle_request", handle_request)])

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

    async def test_oauth_token_traffic_is_distinct_from_llm_traffic(self):
        import gigachat_transport
        capture = WireCapture(lambda _b, _n: (200, chat_response()),
                              oauth_responder=lambda body, _n: (200, {"access_token": "s1-oauth-token",
                                                                      "expires_at": 0}))
        with _Patches([capture.patch(),
                       patch.dict(os.environ, {"GIGACHAT_CREDENTIALS": "s1-dummy-credentials"}),
                       patch.object(gigachat_transport, "_access_token", None),
                       patch.object(gigachat_transport, "_access_token_valid_until", 0.0)]):
            first = await gigachat_transport.get_access_token()
            second = await gigachat_transport.get_access_token()  # cached: no second physical request
        self.assertEqual((first, second), ("s1-oauth-token", "s1-oauth-token"))
        self.assertEqual(capture.violations, [])
        self.assertEqual([(r["method"], r["traffic"]) for r in capture.requests], [("POST", "OAUTH")])
        self.assertEqual(capture.requests[0]["url"], gigachat_transport.OAUTH_URL)
        self.assertNotEqual(capture.requests[0]["url"], gigachat_transport.CHAT_URL)
        self.assertEqual(capture.requests[0]["content"], b"scope=GIGACHAT_API_PERS")

    async def test_negative_control_synchronous_transport_is_rejected(self):
        import httpx
        import gigachat_transport
        capture = WireCapture(lambda _b, _n: (200, chat_response()))
        with capture.patch():
            with httpx.Client(timeout=5.0) as client:
                with self.assertRaises(httpx.ConnectError):
                    client.post(gigachat_transport.CHAT_URL, json={"x": 1})
        self.assertEqual(len(capture.violations), 1)

    async def test_negative_control_unexpected_destination_is_rejected(self):
        import httpx
        capture = WireCapture(lambda _b, _n: (200, chat_response()))
        with capture.patch():
            async with httpx.AsyncClient(timeout=5.0) as client:
                with self.assertRaises(httpx.ConnectError):
                    await client.post("https://example.invalid/v1/chat/completions", json={"x": 1})
        self.assertEqual(len(capture.violations), 1)


# --------------------------------------------------------------------------- B. static inventory and reachability

HTTP_VERBS = frozenset({"get", "post", "put", "patch", "delete", "head", "options", "request", "send", "stream"})
HTTPX_MODULE_FUNCTIONS = frozenset({"get", "post", "put", "patch", "delete", "head", "options", "request", "stream"})
TRANSPORT_METHODS = frozenset({"handle_async_request", "handle_request"})
CLIENT_FACTORIES = frozenset({"AsyncClient", "Client"})
OTHER_NETWORK_CALLS = frozenset({"urlopen", "create_connection", "HTTPConnection", "HTTPSConnection",
                                 "ClientSession", "build_opener"})
OTHER_NETWORK_MODULES = frozenset({"requests", "aiohttp", "urllib3", "websockets", "http.client",
                                   "urllib.request", "pycurl", "grpc"})
URL_CLASSES = {"CHAT_URL": "LLM", "OAUTH_URL": "OAUTH"}
URL_ORIGINS = {"gigachat_transport", "server"}  # server re-exports the gigachat_transport constants


def _production_modules() -> list[Path]:
    modules = [p for p in ROOT.glob("*.py") if not p.name.startswith("test_") and p.name != "conftest.py"]
    modules += sorted((ROOT / "web_alarm").glob("*.py"))
    return sorted(modules)


def _owners(tree: ast.Module):
    """Yield (owner name, node). Nested defs belong to their outermost owner; module code is '<module>'."""
    module_body = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node.name, node
        elif isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    yield f"{node.name}.{item.name}", item
                else:
                    module_body.append(item)
        else:
            module_body.append(node)
    yield "<module>", ast.Module(body=module_body, type_ignores=[])


def scan_send_sites(module_name: str, source: str) -> list[dict]:
    """Conservative static inventory of every physical network send construction.

    Every site is kept (multiplicity preserved). A site is LLM/OAUTH only when its URL is the
    canonical CHAT_URL/OAUTH_URL constant imported from gigachat_transport (or server) and not
    rebound in the module; everything else is UNKNOWN and must be explicitly inventoried.
    """
    tree = ast.parse(source)
    httpx_names, factory_names, url_imports, url_assigned = set(), set(), {}, set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "httpx":
                    httpx_names.add(alias.asname or "httpx")
        elif isinstance(node, ast.ImportFrom):
            if node.module == "httpx":
                factory_names |= {a.asname or a.name for a in node.names if a.name in CLIENT_FACTORIES}
            if node.module in URL_ORIGINS:
                for alias in node.names:
                    if alias.name in URL_CLASSES:
                        url_imports[alias.asname or alias.name] = alias.name
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store) and node.id in URL_CLASSES:
            url_assigned.add(node.id)

    def classify(url):
        if not isinstance(url, ast.Name):
            return "UNKNOWN"
        if module_name == "gigachat_transport.py" and url.id in URL_CLASSES:
            return URL_CLASSES[url.id]  # the canonical definitions live here
        if url.id in url_imports and url.id not in url_assigned:
            return URL_CLASSES[url_imports[url.id]]
        return "UNKNOWN"

    def url_argument(call, verb):
        keyword = next((k.value for k in call.keywords if k.arg == "url"), None)
        if verb == "send":
            return None
        position = 1 if verb in {"request", "stream"} else 0
        return call.args[position] if len(call.args) > position else keyword

    def is_factory_call(expr):
        return isinstance(expr, ast.Call) and (
            (isinstance(expr.func, ast.Attribute) and isinstance(expr.func.value, ast.Name)
             and expr.func.value.id in httpx_names and expr.func.attr in CLIENT_FACTORIES)
            or (isinstance(expr.func, ast.Name) and expr.func.id in factory_names))

    def callee_name(func):
        return func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else None

    sites = []
    for owner, node in _owners(tree):
        clients: set[str] = set()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for arg in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]:
                annotation = ast.unparse(arg.annotation) if arg.annotation is not None else ""
                if arg.arg == "client" or any(f in annotation for f in CLIENT_FACTORIES):
                    clients.add(arg.arg)
        method_aliases: dict[str, str] = {}
        alias_value_nodes: set[int] = set()

        def is_client(expr):
            return (isinstance(expr, ast.Name) and expr.id in clients) or is_factory_call(expr)

        changed = True
        while changed:  # fixpoint over client bindings and aliases inside the owner
            changed = False
            for sub in ast.walk(node):
                if isinstance(sub, (ast.With, ast.AsyncWith)):
                    for item in sub.items:
                        if isinstance(item.optional_vars, ast.Name) and is_client(item.context_expr) \
                                and item.optional_vars.id not in clients:
                            clients.add(item.optional_vars.id)
                            changed = True
                elif isinstance(sub, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
                    targets = sub.targets if isinstance(sub, ast.Assign) else [sub.target]
                    value = sub.value
                    for target in targets:
                        if not isinstance(target, ast.Name) or value is None:
                            continue
                        if is_client(value) and target.id not in clients:
                            clients.add(target.id)
                            changed = True
                        elif (isinstance(value, ast.Attribute) and value.attr in HTTP_VERBS
                              and is_client(value.value) and target.id not in method_aliases):
                            method_aliases[target.id] = value.attr
                            alias_value_nodes.add(id(value))
                            changed = True
                        elif (isinstance(value, ast.Name) and value.id in method_aliases
                              and target.id not in method_aliases):
                            method_aliases[target.id] = method_aliases[value.id]
                            changed = True

        call_funcs = {id(sub.func) for sub in ast.walk(node) if isinstance(sub, ast.Call)}
        for sub in ast.walk(node):
            kind = url = None
            if isinstance(sub, ast.Call):
                func = sub.func
                if isinstance(func, ast.Attribute) and func.attr in HTTP_VERBS and is_client(func.value):
                    kind, url = "client." + func.attr, url_argument(sub, func.attr)
                elif isinstance(func, ast.Name) and func.id in method_aliases:
                    verb = method_aliases[func.id]
                    kind, url = "alias." + verb, url_argument(sub, verb)
                elif (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name)
                      and func.value.id in httpx_names and func.attr in HTTPX_MODULE_FUNCTIONS):
                    kind, url = "httpx." + func.attr, url_argument(sub, func.attr)
                elif isinstance(func, ast.Attribute) and func.attr in TRANSPORT_METHODS:
                    kind = "transport." + func.attr
                elif (isinstance(func, ast.Name) and func.id == "getattr" and len(sub.args) >= 2
                      and isinstance(sub.args[1], ast.Constant) and sub.args[1].value in HTTP_VERBS):
                    kind = "getattr." + sub.args[1].value
                elif callee_name(func) in OTHER_NETWORK_CALLS:
                    kind, url = callee_name(func), (sub.args[0] if sub.args else None)
            elif (isinstance(sub, ast.Attribute) and sub.attr in HTTP_VERBS and is_client(sub.value)
                  and id(sub) not in call_funcs and id(sub) not in alias_value_nodes):
                kind = "method-ref." + sub.attr  # e.g. functools.partial(client.post, ...)
            if kind is not None:
                sites.append({"module": module_name, "owner": owner, "kind": kind,
                              "traffic": classify(url) if url is not None else "UNKNOWN",
                              "line": getattr(sub, "lineno", 0)})
    for node in ast.walk(tree):  # importing another network stack is itself an inventory event
        names = []
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names = [node.module]
        for name in names:
            if name in OTHER_NETWORK_MODULES or name.split(".")[0] in {"requests", "aiohttp", "urllib3",
                                                                          "websockets", "pycurl", "grpc"}:
                sites.append({"module": module_name, "owner": "<import>", "kind": "import:" + name,
                              "traffic": "UNKNOWN", "line": node.lineno})
    return sites


def unexplained_endpoint_reads(module_name: str, source: str) -> list[tuple]:
    """Every read of CHAT_URL/OAUTH_URL must be the URL argument of an inventoried LLM/OAuth send."""
    tree = ast.parse(source)
    send_lines = {s["line"] for s in scan_send_sites(module_name, source) if s["traffic"] in {"LLM", "OAUTH"}}
    found, arguments = [], set()
    for call in ast.walk(tree):
        if isinstance(call, ast.Call):
            for arg in [*call.args, *(k.value for k in call.keywords)]:
                arguments.add(id(arg))
                if isinstance(arg, ast.Name) and arg.id in URL_CLASSES and call.lineno not in send_lines:
                    found.append((module_name, call.lineno, "argument of " + ast.unparse(call.func)))
    for node in ast.walk(tree):
        if (isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id in URL_CLASSES
                and id(node) not in arguments):
            found.append((module_name, node.lineno, "non-argument read of " + node.id))
    return sorted(found)


def site_multiset(sites: list[dict]) -> dict[tuple, int]:
    counts: dict[tuple, int] = {}
    for site in sites:
        key = (site["module"], site["owner"], site["kind"], site["traffic"])
        counts[key] = counts.get(key, 0) + 1
    return counts


def _module_sites(modules) -> list[dict]:
    sites = []
    for module in modules:
        sites += scan_send_sites(module.name, module.read_text(encoding="utf-8"))
    return sites


class StaticRouteInventoryTests(unittest.TestCase):
    def test_production_send_sites_match_inventory_with_multiplicity(self):
        production = [m for m in _production_modules() if m.name not in NON_PRODUCTION_MODULES]
        sites = _module_sites(production)
        _OBSERVATIONS["static_send_sites"] = sorted(
            [s["module"], s["owner"], s["kind"], s["traffic"], s["line"]] for s in sites)
        self.assertEqual(site_multiset(sites), EXPECTED_SEND_SITES)
        self.assertEqual(sum(1 for s in sites if s["traffic"] == "LLM"), 7)
        self.assertEqual(sum(1 for s in sites if s["traffic"] == "OAUTH"), 1)

    def test_non_production_send_sites_are_known_and_isolated(self):
        non_production = [m for m in _production_modules() if m.name in NON_PRODUCTION_MODULES]
        sites = [s for s in _module_sites(non_production) if not s["kind"].startswith("import:")]
        self.assertEqual(site_multiset(sites), EXPECTED_NON_PRODUCTION_SITES)
        stems = {Path(name).stem for name in NON_PRODUCTION_MODULES}
        for module in _production_modules():
            if module.name in NON_PRODUCTION_MODULES:
                continue
            tree = ast.parse(module.read_text(encoding="utf-8"))
            imported = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
            imported |= {(n.module or "").split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
            self.assertFalse(imported & stems, module.name)

    def test_httpx_is_imported_only_by_known_modules(self):
        importers = set()
        for module in _production_modules():
            tree = ast.parse(module.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import) and any(a.name.split(".")[0] == "httpx" for a in node.names):
                    importers.add(module.name)
                if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == "httpx":
                    importers.add(module.name)
        self.assertEqual(importers - NON_PRODUCTION_MODULES, {
            "server.py", "planner_runtime.py", "verifier_runtime.py", "compressor_runtime.py",
            "gigachat_transport.py"})

    def test_every_endpoint_constant_read_is_an_inventoried_send_url(self):
        """Second, receiver-independent net: an LLM/OAuth endpoint read anywhere else is unexplained."""
        unexplained = []
        for module in _production_modules():
            if module.name not in NON_PRODUCTION_MODULES:
                unexplained += unexplained_endpoint_reads(module.name, module.read_text(encoding="utf-8"))
        self.assertEqual(unexplained, [])

    def test_negative_control_endpoint_read_through_unknown_receiver_is_unexplained(self):
        source = ("from gigachat_transport import CHAT_URL\n"
                  "async def f(http):\n    return await http.post(CHAT_URL, json={})\n"
                  "LOG = CHAT_URL\n")
        self.assertEqual(scan_send_sites("synthetic.py", source), [])  # receiver scan cannot see `http`
        self.assertEqual(unexplained_endpoint_reads("synthetic.py", source), [
            ("synthetic.py", 3, "argument of http.post"), ("synthetic.py", 4, "non-argument read of CHAT_URL")])

    def test_canonical_url_constants_are_defined_once_and_never_rebound(self):
        for module in _production_modules():
            tree = ast.parse(module.read_text(encoding="utf-8"))
            stores = [n.id for n in ast.walk(tree)
                      if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store) and n.id in URL_CLASSES]
            expected = sorted(URL_CLASSES) if module.name == "gigachat_transport.py" else []
            self.assertEqual(sorted(stores), expected, module.name)

    # ---- F2 negative controls: each must be detected, counted and classified -------------
    BASE = ("import httpx\nfrom gigachat_transport import CHAT_URL, OAUTH_URL\n"
            "async def call(body):\n    async with httpx.AsyncClient() as client:\n"
            "        return await client.post(CHAT_URL, json=body)\n")

    def scan(self, source):
        return site_multiset(scan_send_sites("synthetic.py", source))

    def test_negative_control_baseline_synthetic_route(self):
        self.assertEqual(self.scan(self.BASE), {("synthetic.py", "call", "client.post", "LLM"): 1})

    def test_negative_control_second_post_in_same_function_changes_multiplicity(self):
        source = self.BASE.replace("        return await client.post(CHAT_URL, json=body)\n",
                                   "        await client.post(CHAT_URL, json=body)\n"
                                   "        return await client.post(CHAT_URL, json=body)\n")
        self.assertEqual(self.scan(source), {("synthetic.py", "call", "client.post", "LLM"): 2})

    def test_negative_control_aliases_send_stream_and_wrappers_are_detected(self):
        cases = {
            "c = client\n        return await c.post(CHAT_URL)\n": ("client.post", "LLM"),
            "p = client.post\n        return await p(CHAT_URL)\n": ("alias.post", "LLM"),
            "q = client.post\n        r = q\n        return await r(CHAT_URL)\n": ("alias.post", "LLM"),
            "return await client.send(client.build_request('POST', CHAT_URL))\n": ("client.send", "UNKNOWN"),
            "async with client.stream('POST', CHAT_URL) as r:\n            return r\n": ("client.stream", "LLM"),
            "return await client.request('POST', url=CHAT_URL)\n": ("client.request", "LLM"),
            "return await getattr(client, 'post')(CHAT_URL)\n": ("getattr.post", "UNKNOWN"),
            "import functools\n        return functools.partial(client.post, CHAT_URL)\n": ("method-ref.post", "UNKNOWN"),
            "return await client._transport.handle_async_request(None)\n": ("transport.handle_async_request", "UNKNOWN"),
            "return await client.get(CHAT_URL)\n": ("client.get", "LLM"),
        }
        for snippet, (kind, traffic) in cases.items():
            with self.subTest(kind=kind):
                source = self.BASE.replace("return await client.post(CHAT_URL, json=body)\n", snippet)
                self.assertEqual(self.scan(source), {("synthetic.py", "call", kind, traffic): 1}, snippet)

    def test_negative_control_module_level_httpx_other_stacks_and_unknown_urls(self):
        cases = [
            ("import httpx\nfrom gigachat_transport import CHAT_URL\ndef f():\n    return httpx.post(CHAT_URL)\n",
             {("synthetic.py", "f", "httpx.post", "LLM"): 1}),
            ("import httpx\ndef f():\n    with httpx.Client() as c:\n        return c.post('https://example.invalid')\n",
             {("synthetic.py", "f", "client.post", "UNKNOWN"): 1}),
            ("from httpx import AsyncClient as AC\nfrom server import CHAT_URL\nasync def f():\n"
             "    async with AC() as c:\n        return await c.post(CHAT_URL)\n",
             {("synthetic.py", "f", "client.post", "LLM"): 1}),
            ("from urllib.request import urlopen\ndef f(u):\n    return urlopen(u)\n",
             {("synthetic.py", "<import>", "import:urllib.request", "UNKNOWN"): 1,
              ("synthetic.py", "f", "urlopen", "UNKNOWN"): 1}),
            ("import requests\ndef f(u):\n    return requests.post(u)\n",
             {("synthetic.py", "<import>", "import:requests", "UNKNOWN"): 1}),
            ("import httpx\nfrom gigachat_transport import CHAT_URL\nCHAT_URL = 'https://evil.invalid'\n"
             "async def f():\n    async with httpx.AsyncClient() as c:\n        return await c.post(CHAT_URL)\n",
             {("synthetic.py", "f", "client.post", "UNKNOWN"): 1}),
            ("import httpx\nfrom gigachat_transport import OAUTH_URL\nasync def f():\n"
             "    async with httpx.AsyncClient() as c:\n        return await c.post(OAUTH_URL)\n",
             {("synthetic.py", "f", "client.post", "OAUTH"): 1}),
            ("import httpx\nclass K:\n    async def m(self):\n        async with httpx.AsyncClient() as c:\n"
             "            async def inner():\n                return await c.post('x')\n            return await inner()\n",
             {("synthetic.py", "K.m", "client.post", "UNKNOWN"): 1}),
        ]
        for source, expected in cases:
            with self.subTest(source=source.splitlines()[-1]):
                self.assertEqual(self.scan(source), expected)

    def test_negative_control_real_source_mutations_are_detected(self):
        import server
        source = Path(server.__file__).read_text(encoding="utf-8")
        opener = "    async with httpx.AsyncClient(timeout=180.0) as client:\n"
        self.assertGreaterEqual(source.count(opener), 2)  # first occurrence is ask_gigachat
        baseline = site_multiset(scan_send_sites("server.py", source))
        mutations = {
            "second_post_in_ask_gigachat": (
                source.replace(opener, opener + "        await client.post(CHAT_URL, json={})\n", 1),
                ("server.py", "ask_gigachat", "client.post", "LLM"), 2),
            "send_wrapper_in_ask_gigachat": (
                source.replace(opener, opener + "        await client.send(client.build_request('POST', CHAT_URL))\n", 1),
                ("server.py", "ask_gigachat", "client.send", "UNKNOWN"), 1),
            "alias_in_ask_gigachat": (
                source.replace(opener, opener + "        _send = client.post\n        await _send(CHAT_URL)\n", 1),
                ("server.py", "ask_gigachat", "alias.post", "LLM"), 1),
            "rebound_chat_url": (
                source.replace("\nmcp = MCPServer(", "\nCHAT_URL = 'https://evil.invalid'\nmcp = MCPServer(", 1),
                ("server.py", "ask_gigachat", "client.post", "UNKNOWN"), 1),
        }
        for name, (mutated, key, count) in mutations.items():
            with self.subTest(mutation=name):
                self.assertNotEqual(mutated, source)
                observed = site_multiset(scan_send_sites("server.py", mutated))
                self.assertEqual(observed.get(key), count)
                self.assertNotEqual(observed, baseline)

    def test_negative_control_inventory_comparison_fails_on_any_drift(self):
        drifted = dict(EXPECTED_SEND_SITES)
        drifted[("server.py", "ask_gigachat", "client.post", "LLM")] = 2
        self.assertNotEqual(drifted, EXPECTED_SEND_SITES)
        extra = dict(EXPECTED_SEND_SITES)
        extra[("server.py", "ask_gigachat", "alias.post", "LLM")] = 1
        self.assertNotEqual(extra, EXPECTED_SEND_SITES)

    def test_direct_run_planner_has_no_production_caller(self):
        references = []
        for module in _production_modules():
            tree = ast.parse(module.read_text(encoding="utf-8"))
            calls = {id(n.func): n for n in ast.walk(tree) if isinstance(n, ast.Call)}
            for node in ast.walk(tree):
                name = node.id if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) else (
                    node.attr if isinstance(node, ast.Attribute) else None)
                if name != "run_planner":
                    continue
                call = calls.get(id(node))
                session = next((k.value for k in call.keywords if k.arg == "session"), None) if call else None
                references.append((module.name, node.lineno, call is not None,
                                   ast.unparse(session) if session is not None else None))
        # the only reference anywhere in production is a call that always passes a session object
        self.assertEqual([(m, c, s) for m, _l, c, s in references], [("server.py", True, "planner_session")])
        _OBSERVATIONS["run_planner_references"] = references

    def test_ask_gigachat_is_reached_only_from_mcp_tools(self):
        import server
        tree = ast.parse(Path(server.__file__).read_text(encoding="utf-8"))
        owners = []
        for owner, node in _owners(tree):
            loads = [n for n in ast.walk(node) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)
                     and n.id == "ask_gigachat"]
            if loads:
                decorators = [ast.unparse(d) for d in getattr(node, "decorator_list", [])]
                owners.append((owner, len(loads), decorators))
        self.assertEqual(owners, [("gigachat_ask", 1, ["mcp.tool()"]), ("gigachat_file_task", 1, ["mcp.tool()"])])
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


# --------------------------------------------------------------------------- F1. acceptance gate

def _short_id(test) -> str:
    """'Class.method' independent of whether the module runs as __main__ or is imported."""
    return ".".join(test.id().split(".")[-2:])


def evaluate_gate(*, manifest, collected, selected, unresolved_selectors, started, counts,
                  evidence_problems, violations) -> dict:
    """Pure acceptance decision. Exit 0 only for a complete, clean run of the full MANIFEST."""
    reasons = []
    manifest, collected, started = list(manifest), list(collected), list(started)
    if not manifest:
        reasons.append("EMPTY_MANIFEST")
    missing = sorted(set(manifest) - set(collected))
    unexpected = sorted(set(collected) - set(manifest))
    if missing:
        reasons.append("COLLECTION_MISSING:" + ",".join(missing))
    if unexpected:
        reasons.append("COLLECTION_UNEXPECTED:" + ",".join(unexpected))
    if len(collected) != len(set(collected)):
        reasons.append("COLLECTION_DUPLICATE_IDS")
    if unresolved_selectors:
        reasons.append("SELECTOR_UNRESOLVED:" + ",".join(sorted(unresolved_selectors)))
    target = manifest if selected is None else list(selected)
    if not target or counts.get("run", 0) == 0:
        reasons.append("ZERO_TESTS")
    not_run = sorted(set(target) - set(started))
    if not_run:
        reasons.append("NOT_RUN:" + ",".join(not_run))
    for key, code in (("failures", "FAILURES"), ("errors", "ERRORS"), ("skipped", "UNEXPECTED_SKIP"),
                      ("expected_failures", "EXPECTED_FAILURE_FORBIDDEN"),
                      ("unexpected_successes", "UNEXPECTED_SUCCESS")):
        if counts.get(key, 0):
            reasons.append(f"{code}:{counts[key]}")
    if evidence_problems:
        reasons.append("EVIDENCE:" + "; ".join(evidence_problems))
    if violations:
        reasons.append(f"ISOLATION_VIOLATIONS:{len(violations)}")
    if reasons:
        return {"status": "FAIL", "exit_code": 1, "reasons": reasons}
    if selected is not None:
        return {"status": "PARTIAL_SELECTION", "exit_code": 3,
                "reasons": ["NOT_ACCEPTANCE: positional selectors restrict the MANIFEST"]}
    return {"status": "PASS", "exit_code": 0, "reasons": []}


def snapshot_evidence(evidence_root: Path, base: Path, pins: dict) -> tuple[dict[str, Path], list[str]]:
    """Copy pinned RAW evidence into the sandbox; every absence or mismatch is reported."""
    evidence, problems = {}, []
    for name, (relative, digest, size) in pins.items():
        source = evidence_root / relative
        if not source.is_file():
            problems.append(f"{name}: source missing")
            continue
        data = source.read_bytes()
        if len(data) != size or _sha256(data) != digest:
            problems.append(f"{name}: pinned SHA-256/size mismatch (DRIFT)")
            continue
        target = base / "evidence" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        evidence[name] = target
    return evidence, problems


class GateLogicTests(unittest.TestCase):
    """F1: the gate cannot report PASS for an incomplete or degraded run."""

    M = ["A.t1", "A.t2", "B.t3"]

    def gate(self, **changes):
        arguments = {"manifest": self.M, "collected": self.M, "selected": None, "unresolved_selectors": [],
                     "started": self.M, "counts": {"run": 3}, "evidence_problems": [], "violations": []}
        arguments.update(changes)
        return evaluate_gate(**arguments)

    def assert_fail(self, prefix, **changes):
        decision = self.gate(**changes)
        self.assertEqual((decision["status"], decision["exit_code"]), ("FAIL", 1), decision)
        self.assertTrue(any(r.startswith(prefix) for r in decision["reasons"]), decision)

    def test_nominal_full_run_is_the_only_pass(self):
        self.assertEqual(self.gate(), {"status": "PASS", "exit_code": 0, "reasons": []})

    def test_missing_or_mismatched_evidence_fails(self):
        self.assert_fail("EVIDENCE", evidence_problems=["r031/executor.jsonl: source missing"])
        self.assert_fail("EVIDENCE", evidence_problems=["r026/summary.json: pinned SHA-256/size mismatch (DRIFT)"])

    def test_any_skip_fails(self):
        self.assert_fail("UNEXPECTED_SKIP", counts={"run": 3, "skipped": 1})

    def test_failures_errors_expected_failures_and_unexpected_successes_fail(self):
        self.assert_fail("FAILURES", counts={"run": 3, "failures": 1})
        self.assert_fail("ERRORS", counts={"run": 3, "errors": 1})
        self.assert_fail("EXPECTED_FAILURE_FORBIDDEN", counts={"run": 3, "expected_failures": 1})
        self.assert_fail("UNEXPECTED_SUCCESS", counts={"run": 3, "unexpected_successes": 1})

    def test_incomplete_or_unexpected_collection_fails(self):
        self.assert_fail("COLLECTION_MISSING", collected=self.M[:2], started=self.M[:2], counts={"run": 2})
        self.assert_fail("COLLECTION_UNEXPECTED", collected=self.M + ["C.t4"], started=self.M + ["C.t4"],
                         counts={"run": 4})
        self.assert_fail("COLLECTION_DUPLICATE_IDS", collected=self.M + ["A.t1"])

    def test_zero_tests_and_empty_manifest_fail(self):
        self.assert_fail("ZERO_TESTS", started=[], counts={"run": 0})
        self.assert_fail("EMPTY_MANIFEST", manifest=[], collected=[], started=[], counts={"run": 0})
        self.assert_fail("ZERO_TESTS", selected=[], started=[], counts={"run": 0})

    def test_tests_that_never_started_fail(self):
        self.assert_fail("NOT_RUN", started=self.M[:2], counts={"run": 2})

    def test_isolation_violation_fails(self):
        self.assert_fail("ISOLATION_VIOLATIONS", violations=[{"event": "socket.connect"}])

    def test_selector_runs_are_never_acceptance(self):
        decision = self.gate(selected=["A.t1"], started=["A.t1"], counts={"run": 1})
        self.assertEqual((decision["status"], decision["exit_code"]), ("PARTIAL_SELECTION", 3))
        self.assert_fail("SELECTOR_UNRESOLVED", selected=["A.t1"], started=["A.t1"], counts={"run": 1},
                         unresolved_selectors=["typo"])
        self.assert_fail("EVIDENCE", selected=["A.t1"], started=["A.t1"], counts={"run": 1},
                         evidence_problems=["x: source missing"])


class EvidenceGateTests(unittest.TestCase):
    """F1: mandatory RAW evidence is checked as a failure, not a skip."""

    def test_pinned_evidence_snapshot_is_complete_and_verified(self):
        self.assertEqual(_EVIDENCE_PROBLEMS, [])
        self.assertEqual(set(_EVIDENCE), set(EVIDENCE_PINS))
        for name, path in _EVIDENCE.items():
            _relative, digest, size = EVIDENCE_PINS[name]
            data = path.read_bytes()
            self.assertEqual((len(data), _sha256(data)), (size, digest), name)

    def test_snapshot_reports_missing_and_mismatched_sources(self):
        root = Path(tempfile.mkdtemp(dir=_SANDBOX))
        evidence, problems = snapshot_evidence(root / "empty", root / "out1", EVIDENCE_PINS)
        self.assertEqual((evidence, len(problems)), ({}, len(EVIDENCE_PINS)))
        self.assertTrue(all(p.endswith("source missing") for p in problems))
        for _name, (relative, _digest, _size) in EVIDENCE_PINS.items():
            junk = root / "junk" / relative
            junk.parent.mkdir(parents=True, exist_ok=True)
            junk.write_bytes(b"not the pinned evidence")
        evidence, problems = snapshot_evidence(root / "junk", root / "out2", EVIDENCE_PINS)
        self.assertEqual((evidence, len(problems)), ({}, len(EVIDENCE_PINS)))
        self.assertTrue(all("mismatch" in p for p in problems))

    def test_require_evidence_raises_failure_not_skip(self):
        saved = list(_EVIDENCE_PROBLEMS)
        _EVIDENCE_PROBLEMS.append("synthetic: source missing")
        try:
            with self.assertRaises(AssertionError):
                _require_evidence("r031/executor.jsonl")
        finally:
            _EVIDENCE_PROBLEMS[:] = saved

    def test_manifest_matches_the_loaded_collection(self):
        loaded = []

        def flatten(item):
            if isinstance(item, unittest.TestSuite):
                for child in item:
                    flatten(child)
            else:
                loaded.append(_short_id(item))

        flatten(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
        self.assertEqual(sorted(loaded), sorted(MANIFEST))
        self.assertEqual(len(MANIFEST), len(set(MANIFEST)))


# --------------------------------------------------------------------------- guarded standalone runner

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


class _RecordingResult(unittest.TextTestResult):
    started_ids: list[str] = []

    def startTest(self, test):
        type(self).started_ids.append(_short_id(test))
        super().startTest(test)


def main() -> int:
    global _ISOLATED, _SANDBOX, _EVIDENCE, _EVIDENCE_PROBLEMS
    sys.dont_write_bytecode = True
    base = Path(tempfile.mkdtemp(prefix="claude-rt002-s1-"))
    _SANDBOX = base
    evidence_root = Path(os.environ.get("RT002_S1_EVIDENCE_ROOT") or ROOT)
    # read-only snapshot of pinned RAW evidence before guards; problems fail the gate
    evidence, problems = snapshot_evidence(evidence_root, base, EVIDENCE_PINS)
    _EVIDENCE.clear()
    _EVIDENCE.update(evidence)
    _EVIDENCE_PROBLEMS[:] = problems
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
    collected_tests = []

    def flatten(item):
        if isinstance(item, unittest.TestSuite):
            for child in item:
                flatten(child)
        else:
            collected_tests.append(item)

    flatten(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    collected = [_short_id(t) for t in collected_tests]
    selected = unresolved = None
    tests = collected_tests
    if sys.argv[1:]:
        requested = list(dict.fromkeys(sys.argv[1:]))
        resolved = {r: [t for t in collected_tests if _short_id(t) == r or t.id() == r
                        or t.id().split(".")[-1] == r] for r in requested}
        unresolved = [r for r, found in resolved.items() if not found]
        tests = [t for t in collected_tests if any(t in found for found in resolved.values())]
        selected = [_short_id(t) for t in tests]
    started = time.time()
    log_path = base / "unittest.log"
    _RecordingResult.started_ids = []
    with log_path.open("w", encoding="utf-8") as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=_RecordingResult).run(
            unittest.TestSuite(tests))
    counts = {"run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
              "skipped": len(result.skipped), "expected_failures": len(result.expectedFailures),
              "unexpected_successes": len(result.unexpectedSuccesses)}
    gate = evaluate_gate(manifest=MANIFEST, collected=collected, selected=selected,
                         unresolved_selectors=unresolved or [], started=_RecordingResult.started_ids,
                         counts=counts, evidence_problems=_EVIDENCE_PROBLEMS, violations=violations)
    report = {
        "task": "CLAUDE-RT002-S1-REPAIR-001", "sandbox": str(base), "python": sys.version.split()[0],
        "gate": gate, "counts": counts, "manifest_size": len(MANIFEST),
        "failures": [t.id() for t, _ in result.failures], "errors": [t.id() for t, _ in result.errors],
        "skipped": [(t.id(), reason) for t, reason in result.skipped],
        "isolation_violations": violations, "evidence_root": str(evidence_root),
        "evidence_problems": _EVIDENCE_PROBLEMS, "selected": selected,
        "elapsed_seconds": round(time.time() - started, 3), "observations": _OBSERVATIONS,
        "log": str(log_path), "log_sha256": _sha256(log_path.read_bytes()),
    }
    (base / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in {"observations"}}, ensure_ascii=False, indent=2))
    if result.failures or result.errors:
        print(log_path.read_text(encoding="utf-8").split("=" * 70, 1)[-1])
    return gate["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
