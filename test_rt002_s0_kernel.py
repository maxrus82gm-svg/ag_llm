"""RT-002 S0 offline acceptance probes; production code is never patched on disk.

Run only as: .venv/Scripts/python.exe -B test_rt002_s0_kernel.py
Optional positional arguments select exact unittest IDs from this manifest.
The standalone runner installs process-wide safety guards BEFORE runtime imports.
Ordinary unittest discovery skips this module rather than installing global guards.
Failing safety assertions are findings, deliberately not expectedFailure markers.
"""
from __future__ import annotations

import copy
import hashlib
import json
import inspect
import logging
import os
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

_ISOLATED = False
_OBSERVATIONS = {}


def setUpModule():
    if not _ISOLATED:
        raise unittest.SkipTest("Use the guarded standalone S0 runner")


class KernelBoundaryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        legacy.FinalAuditRuntimeTests.setUp(self)

    def tearDown(self):
        legacy.FinalAuditRuntimeTests.tearDown(self)

    async def run_v6(self, *args, **kwargs):
        return await planner_tests.PlannerIntegrationTests.run_v6(self, *args, **kwargs)

    def policy(self, **changes):
        return server._prepare_policy_for_workspace(
            self.workspace, server._normalize_permissions({**self.permissions, **changes})
        )

    def success_events(self):
        return [e for e in self.events if e["event"] == "run_finished" and e.get("status") == "SUCCESS"]

    def capture(self, result, audit):
        _OBSERVATIONS[self.id()] = {
            "result": result, "events": copy.deepcopy(self.events),
            "dredd_sends": audit.await_count,
            "packet": json.loads(audit.await_args.kwargs["verification_context"]) if audit.await_args else None,
        }

    async def read_case(self, *, extra_patches=()):
        return await self.run_v6(recovery.read_contract(), responses=[
            recovery.read_response(), legacy.FakeResponse("Finished")
        ], extra_patches=extra_patches)

    def test_read_and_verify_denied_scopes_and_traversal(self):
        (self.workspace / "allowed").mkdir()
        (self.workspace / "secret.md").write_text("secret", encoding="utf-8")
        policy = self.policy(allow_verify=True, read_scope="allowed")
        for path in ("secret.md", "../outside.md", str(self.workspace.parent / "outside.md")):
            with self.subTest(path=path):
                with self.assertRaises((PermissionError, ValueError)):
                    server._agent_read_file(self.workspace, path, policy)
                with self.assertRaises((PermissionError, ValueError)):
                    server._agent_verify_file_content(self.workspace, path, "exists", "", policy)
        with self.assertRaises(PermissionError):
            server._agent_read_file(self.workspace, "secret.md", self.policy(allow_read=False))
        with self.assertRaises(PermissionError):
            server._agent_verify_file_content(self.workspace, "secret.md", "exists", "", self.policy(allow_verify=False))

    def test_exact_equality_is_not_contains_and_false_block_is_explicit(self):
        (self.workspace / "result.md").write_text("prefix done suffix", encoding="utf-8")
        p = self.policy(allow_verify=True)
        contains = server._agent_verify_file_content(self.workspace, "result.md", "contains", "done", p)
        equals = server._agent_verify_file_content(self.workspace, "result.md", "equals", "done", p)
        self.assertTrue(contains["ok"])
        self.assertFalse(equals["ok"])
        self.assertFalse(equals["matched"])
        self.assertNotEqual(equals["actual_sha256"], equals["expected_sha256"])

    def test_missing_oversized_unsupported_and_invalid_predicate_fail_closed(self):
        p = self.policy(allow_verify=True)
        (self.workspace / "binary.exe").write_bytes(b"abc")
        (self.workspace / "large.md").write_text("x" * 33, encoding="utf-8")
        (self.workspace / "result.md").write_text("done", encoding="utf-8")
        with self.assertRaises(FileNotFoundError):
            server._agent_read_file(self.workspace, "missing.md", p)
        with self.assertRaises(ValueError):
            server._agent_read_file(self.workspace, "binary.exe", p)
        with patch.object(server, "MAX_AGENT_FILE_BYTES", 32):
            with self.assertRaises(ValueError):
                server._agent_read_file(self.workspace, "large.md", p)
        for kind, value in (("regex", "x"), ("sha256", "not-hash"), ("exists", "unexpected")):
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                server._agent_verify_file_content(self.workspace, "result.md", kind, value, p)

    async def test_positive_read_has_durable_source_and_exact_packet_identity(self):
        (self.workspace / "result.md").write_text("complete evidence", encoding="utf-8")
        result, audit, _ = await self.read_case()
        self.assertEqual(result, "Finished")
        self.assertEqual(len(self.success_events()), 1)
        packet = json.loads(audit.await_args.kwargs["verification_context"])
        fact = packet["authoritative_tool_evidence"][0]
        self.assertEqual(fact["requirement_ids"], ["readback"])
        self.assertEqual(fact["stage_id"], "read_stage")
        self.assertEqual(fact["material_preview"]["content"], "complete evidence")
        self.assertTrue(fact["source_run_store_record_id"])
        record = run_store.load_run_record(self.workspace, fact["run_id"], fact["source_run_store_record_id"])
        self.assertIsNotNone(record)

    async def test_positive_exact_verify_control_for_fingerprint_race(self):
        (self.workspace / "result.md").write_text("done\n", encoding="utf-8", newline="")
        call = {"name": "verify_file_content", "arguments": {"path": "result.md", "kind": "equals", "value": "done\n"}}
        result, audit, _ = await self.run_v6(stage_tests.verify_evidence_plan(), responses=[
            planner_tests.tool(call), legacy.FakeResponse("Finished")])
        self.assertEqual(result, "Finished")
        self.assertEqual(audit.await_count, 1)
        self.assertEqual(len(self.success_events()), 1)

    async def test_denied_read_never_satisfies_requirement_or_calls_dredd(self):
        (self.workspace / "allowed").mkdir()
        (self.workspace / "result.md").write_text("not permitted", encoding="utf-8")
        self.permissions["read_scope"] = "allowed"
        with self.assertRaisesRegex(RuntimeError, "LOOP DETECTED"):
            await self.run_v6(recovery.read_contract(), responses=[recovery.read_response()] * 6, allow_write=False)
        self.last_verifier.assert_not_awaited()
        self.assertFalse(self.success_events())

    async def test_required_false_equals_blocks_without_dredd(self):
        (self.workspace / "result.md").write_text("prefix done suffix", encoding="utf-8")
        contract = stage_tests.verify_evidence_plan()
        call = {"name": "verify_file_content", "arguments": {"path": "result.md", "kind": "equals", "value": "done\n"}}
        with self.assertRaisesRegex(RuntimeError, "LOOP DETECTED"):
            await self.run_v6(contract, responses=[planner_tests.tool(call)] * 6)
        self.last_verifier.assert_not_awaited()
        self.assertFalse(self.success_events())

    async def test_read_change_before_fingerprint_cannot_certify_old_content(self):
        """S0-F01: inject the external change after READ, before evidence binding."""
        target = self.workspace / "result.md"
        target.write_text("OLD MATERIAL", encoding="utf-8")
        read = server._agent_read_file
        changed = False
        def racing_read(*args, **kwargs):
            nonlocal changed
            result = read(*args, **kwargs)
            if not changed:
                target.write_text("NEW MATERIAL", encoding="utf-8")
                changed = True
            return result
        result, audit, _ = await self.read_case(extra_patches=(patch.object(server, "_agent_read_file", side_effect=racing_read),))
        outcome = next(e for e in self.events if e["event"] == "tool_finished")
        fact = outcome["evidence_binding"]
        self.assertEqual(target.read_text(encoding="utf-8"), "NEW MATERIAL")
        self.assertEqual(outcome["result"]["content"], "OLD MATERIAL")
        self.assertNotEqual(fact["observed_state_sha256"], server._planner_dependency_fingerprint(
            self.workspace, "read_file", {"path": "result.md"}, self.policy(allow_verify=True)))
        self.capture(result, audit)
        self.assertTrue(any(e["event"] == "tool_evidence_stale" for e in self.events))
        self.assertIn("BLOCKED", result)
        audit.assert_not_awaited()
        self.assertFalse(self.success_events(), "S0-F01: stale READ material certified against a later filesystem fingerprint; returned " + result)

    async def test_verify_change_before_fingerprint_cannot_certify_old_predicate(self):
        """S0-F02: an exact predicate passed only before the injected change."""
        target = self.workspace / "result.md"
        target.write_text("done\n", encoding="utf-8", newline="")
        verify = server._agent_verify_file_content
        changed = False
        def racing_verify(*args, **kwargs):
            nonlocal changed
            result = verify(*args, **kwargs)
            if not changed:
                target.write_text("WRONG", encoding="utf-8")
                changed = True
            return result
        contract = stage_tests.verify_evidence_plan()
        call = {"name": "verify_file_content", "arguments": {"path": "result.md", "kind": "equals", "value": "done\n"}}
        result, audit, _ = await self.run_v6(contract, responses=[planner_tests.tool(call), legacy.FakeResponse("Finished")],
            extra_patches=(patch.object(server, "_agent_verify_file_content", side_effect=racing_verify),))
        self.assertEqual(target.read_text(encoding="utf-8"), "WRONG")
        fact = next(e for e in self.events if e["event"] == "tool_finished")["evidence_binding"]
        self.assertTrue(fact["result"]["verification"]["passed"])
        self.assertEqual(fact["result"]["verification"]["actual_sha256"], server._sha256_utf8("done\n"))
        self.assertNotEqual(fact["observed_state_sha256"], server._planner_dependency_fingerprint(
            self.workspace, "verify_file_content", call["arguments"], self.policy(allow_verify=True)))
        self.capture(result, audit)
        self.assertTrue(any(e["event"] == "tool_evidence_stale" for e in self.events))
        self.assertIn("BLOCKED", result)
        self.assertFalse(self.success_events(), "S0-F02: false current equals after observation/fingerprint race; returned " + result)
        self.assertEqual(audit.await_count, 0)

    async def test_missing_recorder_cannot_return_certified_success(self):
        """S0-F03: a packet must retain durable evidence, not just RAM IDs."""
        (self.workspace / "result.md").write_text("complete", encoding="utf-8")
        result, audit, _ = await self.read_case(extra_patches=(
            patch.object(server, "AuditThreadRecorder", side_effect=OSError("S0 simulated storage unavailable")),))
        self.assertTrue(any(e["event"] == "audit_storage_error" for e in self.events))
        audit.assert_not_awaited()
        self.assertIn("mandatory_evidence_store_unavailable", result)
        self.assertFalse(any(e["event"] == "tool_started" for e in self.events))
        self.capture(result, audit)
        self.assertFalse(self.success_events(), "S0-F03: SUCCESS despite unavailable RunStore; returned " + result)

    async def test_lost_tool_outcome_cannot_return_certified_success(self):
        """S0-F04: tool_started being durable does not prove a durable outcome."""
        (self.workspace / "result.md").write_text("complete", encoding="utf-8")
        observe = server.AuditThreadRecorder.observe
        failures = []
        def fail_outcome(recorder, event):
            if event["event"] == "tool_finished":
                failures.append(event["event"])
                raise OSError("S0 simulated outcome append failure")
            return observe(recorder, event)
        result, audit, _ = await self.read_case(extra_patches=(
            patch.object(server.AuditThreadRecorder, "observe", fail_outcome),))
        self.assertEqual(failures, ["tool_finished"])
        audit.assert_not_awaited()
        self.assertIn("mandatory_evidence_unavailable", result)
        self.assertEqual(len([e for e in self.events if e["event"] == "tool_started"]), 1)
        self.capture(result, audit)
        self.assertFalse(self.success_events(), "S0-F04: SUCCESS with missing durable tool outcome; returned " + result)

    async def test_plan_storage_failure_does_not_reach_executor_or_success(self):
        with self.assertRaises(OSError):
            await self.run_v6(extra_patches=(patch.object(task_planner, "atomic_state", side_effect=OSError("S0 disk full")),))
        self.last_verifier.assert_not_awaited()
        self.assertEqual(self.last_client.post_count, 0)
        self.assertFalse(self.success_events())

    async def test_abort_after_write_records_no_success_and_does_not_auto_replay(self):
        import asyncio
        original_write = server._agent_write_file
        writes = []
        def abort_after_write(*args, **kwargs):
            result = original_write(*args, **kwargs)
            writes.append(result)
            raise asyncio.CancelledError("S0 interruption after physical write")
        with self.assertRaises(asyncio.CancelledError):
            await self.run_v6(responses=[planner_tests.tool(planner_tests.write())], extra_patches=(
                patch.object(server, "_agent_write_file", side_effect=abort_after_write),))
        self.assertEqual(len(writes), 1)
        self.assertEqual((self.workspace / "result.md").read_text(encoding="utf-8"), "done")
        self.last_verifier.assert_not_awaited()
        self.assertFalse(self.success_events())
        files = list((self.runtime / "logs" / "task_plans").glob("*.json"))
        self.assertEqual(len(files), 1)
        saved = json.loads(files[0].read_text(encoding="utf-8"))
        self.assertFalse(saved["receipts"])
        # Reconstructing a fresh controller never loads/replays the interrupted latch.
        fresh = task_planner.TaskLifecycle(path=files[0], run_id="new_run", task_block_id="new_task",
            raw_task="new task", planner_call=None, emit=lambda *_: None,
            snapshot=lambda *_: {}, prepare=lambda *_: {})
        self.assertEqual(fresh.state["receipts"], [])
        self.assertEqual(fresh.state["candidates"], {})
        self.assertEqual(len(writes), 1)

    async def test_mutation_after_audit_pass_before_terminal_gate_requires_new_read(self):
        target = self.workspace / "result.md"
        target.write_text("old", encoding="utf-8")
        changed = False
        class Events(list):
            def append(inner, event):
                nonlocal changed
                super().append(event)
                if event["event"] == "final_audit_passed" and not changed:
                    target.write_text("changed after PASS", encoding="utf-8")
                    changed = True
        # The callback is synchronous and runs strictly before terminal_success_gate.
        self.events = Events()
        result, audit, _ = await self.run_v6(recovery.read_contract(), responses=[
            recovery.read_response(), legacy.FakeResponse("Finished"),
            recovery.read_response(), legacy.FakeResponse("Finished"),
        ])
        self.assertEqual(result, "Finished")
        self.assertEqual(audit.await_count, 2)
        events = self.events
        self.assertTrue(any(e["event"] == "terminal_evidence_freshness_blocked" for e in events))
        self.assertEqual(sum(e["event"] == "run_finished" and e.get("status") == "SUCCESS" for e in events), 1)


class IdentityBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_identity_dimensions_and_same_hash_other_target_are_rejected(self):
        fixture = stage_tests.StageEvidenceContractTests()
        self.addCleanup(fixture.doCleanups)
        life, _, tools = fixture.lifecycle(stage_tests.read_evidence_plan(), ["read_file"],
            snapshot=lambda _: {"exists": True, "sha256": "a" * 64, "content": "same"})
        await life.initialize({"tools": tools})
        fact = fixture.evidence_fact(life, stage_id="read_stage", tool="read_file", arguments={"path": "result.md"})
        for key, value in {"task_block_id": "other_task", "run_id": "other_run", "plan_version": 99,
                           "stage_id": "other_stage", "evidence_generation": 99,
                           "requirement_ids": ["other_requirement"], "source_record_id": "",
                           "status": "ERROR", "executed": False}.items():
            with self.subTest(dimension=key):
                self.assertFalse(life.non_persistence_evidence_satisfied([{**fact, key: value}]))
        other = fixture.evidence_fact(life, stage_id="read_stage", tool="read_file", arguments={"path": "other.md"})
        other["requirement_ids"] = ["readback"]
        self.assertFalse(life.non_persistence_evidence_satisfied([other]))
        self.assertTrue(life.non_persistence_evidence_satisfied([fact]))

    def test_unknown_provider_usage_remains_unknown_and_replay_is_not_double_counted(self):
        summary = {"usage": run_store.empty_usage_summary(), "provider_accounting": run_store.empty_provider_accounting_summary()}
        role = "EXECUTOR"
        # Use the module's canonical role spelling instead of assuming UI capitalization.
        role = next(r for r in run_store.USAGE_ROLES if r.lower() == "executor")
        run_store.record_provider_attempt_started(summary, role, "attempt_s0")
        run_store.record_provider_attempt_terminal(summary, role, "attempt_s0", None)
        before = copy.deepcopy(summary["usage"])
        self.assertFalse(summary["usage"][role]["complete"])
        run_store.record_provider_attempt_terminal(summary, role, "attempt_s0", None)
        self.assertEqual(summary["usage"], before)
        self.assertFalse(summary["provider_accounting"]["complete"])


def _install_guards(base: Path):
    """Permit reads of ordinary source; all mutations stay within the sandbox.

    Windows asyncio's socketpair may create loopback sockets internally; only that
    synchronous stdlib housekeeping operation is permitted. No HTTP/DNS/other
    socket connects or child processes are permitted, including localhost.
    """
    violations = []
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
        raise PermissionError("S0 isolation guard: " + event + " " + str(detail))
    def audit(event, args):
        if event.startswith("subprocess.") or event in {"os.system", "os.posix_spawn", "os.posix_spawnp"} or event.startswith("os.spawn"):
            reject(event, "child processes forbidden")
        if event in {"socket.connect", "socket.connect_ex", "socket.bind", "socket.getaddrinfo", "socket.gethostbyname"}:
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
                writable = (isinstance(mode, str) and any(c in mode for c in "wax+")) or (isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
                if writable and not under_root(name):
                    reject(event, name)
        if event in {"os.mkdir", "os.remove", "os.rmdir", "os.rename", "os.link", "os.symlink", "os.chmod", "os.utime", "os.truncate"}:
            targets = args[:2] if event in {"os.rename", "os.link", "os.symlink"} else args[:1]
            for value in targets:
                if path_text(value) and not under_root(value):
                    reject(event, value)
    sys.addaudithook(audit)
    return violations


def _manifest():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for cls in (KernelBoundaryTests, IdentityBoundaryTests, stage_tests.StageEvidenceContractTests,
                recovery.FinalAuditByteBudgetTests, planner_tests.PersistenceStateTests):
        suite.addTests(loader.loadTestsFromTestCase(cls))
    excluded = {"test_ignored_file_material_remains_available_without_git_diff", "test_git_diff_state_drift_requires_new_source_evidence"}
    for name in loader.getTestCaseNames(recovery.FinalAuditRecoveryIntegrationTests):
        if name not in excluded:
            suite.addTest(recovery.FinalAuditRecoveryIntegrationTests(name))
    names = [
        "test_readonly_stop_reaches_audit_without_mutation",
        "test_disabled_final_audit_requires_satisfied_planner_lifecycle",
        "test_required_create_normal_tool_then_audit",
        "test_151c_incomplete_requirement_coverage_blocks_before_dredd",
        "test_successful_persistence_advances_before_executor_can_repeat_write",
        "test_read_stage_completes_from_server_owned_tool_evidence",
        "test_verify_stage_completes_from_successful_verify_evidence",
        "test_151c_state_change_during_packet_collection_blocks_dredd_until_fresh",
        "test_state_change_during_final_audit_reopens_evidence_and_requires_fresh_read",
        "test_wrong_successful_verify_does_not_close_exact_evidence_stage",
        "test_server_evidence_gate_blocks_non_contract_calls_without_tool_budget",
        "test_tool_reserve_preserves_mandatory_write_read_verify_calls",
        "test_tool_reserve_blocks_impossible_plan_before_executor_api",
        "test_write_off_uses_existing_permission_escalation",
        "test_explicit_permission_grant_allows_same_contract_to_continue",
        "test_scope_violation_does_not_reach_audit_or_force",
        "test_dredd_execution_defect_does_not_call_planner_again",
        "test_dredd_plan_defect_runs_new_repair_stage",
        "test_unknown_route_uses_bounded_execution_correction",
        "test_real_dispatch_error_has_tool_started_then_tool_error",
    ]
    suite.addTests(planner_tests.PlannerIntegrationTests(name) for name in names)
    import test_verifier_runtime
    verifier_names = [
        "test_valid_pass_returns_immutable_typed_result", "test_valid_fail_is_semantic_result_not_runtime_error",
        "test_malformed_json_is_protocol_error_and_no_retry", "test_unknown_result_values_are_rejected",
        "test_invalid_response_check_type_is_rejected", "test_mismatched_response_check_type_is_rejected",
        "test_permission_protocol_pass_fail_and_malformed_fail_closed",
        "test_unsupported_provider_is_rejected_without_model_call",
        "test_unknown_model_is_rejected_without_fallback",
        "test_request_body_has_no_tools_or_function_declarations",
    ]
    suite.addTests(test_verifier_runtime.VerifierRuntimeTests(name) for name in verifier_names)
    # Directly affected compatibility and file-tool regressions. Packet builders
    # in these unit tests must receive fake Git observations, never spawn Git.
    import test_audit_observability
    import test_file_editing_toolbox
    suite.addTests(loader.loadTestsFromTestCase(test_audit_observability.AuditStorageTests))
    class IsolatedFileEditingToolboxTests(test_file_editing_toolbox.FileEditingToolboxTests):
        def setUp(self):
            super().setUp()
            unavailable = {"ok": False, "exit_code": None, "stdout": "", "stderr": "offline fake", "truncated": False}
            for helper in ("_agent_git_status", "_agent_git_diff"):
                self.enterContext(patch.object(server, helper, return_value=unavailable))
    suite.addTests(loader.loadTestsFromTestCase(IsolatedFileEditingToolboxTests))
    # Pure pytest-style functions, invoked directly: no pytest plugin discovery.
    import pytest
    import test_run_store_v2
    import test_provider_accounting
    import test_audit_v2_compatibility
    import test_verify_file_content
    for module in (test_run_store_v2, test_provider_accounting, test_audit_v2_compatibility, test_verify_file_content):
        for name, function in inspect.getmembers(module, inspect.isfunction):
            if not name.startswith("test_"):
                continue
            def run_function(function=function):
                with tempfile.TemporaryDirectory() as directory, pytest.MonkeyPatch.context() as monkeypatch:
                    available = {"tmp_path": Path(directory), "monkeypatch": monkeypatch}
                    function(**{p: available[p] for p in inspect.signature(function).parameters})
            run_function.__name__ = module.__name__ + "." + name
            suite.addTest(unittest.FunctionTestCase(run_function))
    import test_rt002_s0_repair
    suite.addTests(test_rt002_s0_repair.build_suite(sys.modules[__name__]))
    return suite


def _flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _flatten(item)
        else:
            yield item


def main():
    global _ISOLATED, server, task_planner, run_store, legacy, planner_tests, stage_tests, recovery
    sys.dont_write_bytecode = True
    base = Path(tempfile.mkdtemp(prefix="codex-rt002-s0-"))
    for key in ("LOCALAPPDATA", "APPDATA", "TEMP", "TMP"):
        location = base / key.lower()
        location.mkdir()
        os.environ[key] = str(location)
    tempfile.tempdir = str(base / "temp")
    violations = _install_guards(base)
    _ISOLATED = True
    import server
    import task_planner
    import run_store
    import test_final_audit as legacy
    import test_task_planner as planner_tests
    import test_stage_evidence_contract as stage_tests
    import test_final_audit_recovery as recovery
    logging.getLogger("asyncio").setLevel(logging.ERROR)
    tests = list(_flatten(_manifest()))
    if sys.argv[1:]:
        requested = set(sys.argv[1:])
        tests = [t for t in tests if t.id() in requested or t.id().split(".")[-1] in requested]
        if not tests or len(tests) != len(requested):
            raise SystemExit("Selectors must resolve exactly to manifest tests")
    started = time.time()
    log_path = base / "unittest.log"
    with log_path.open("w", encoding="utf-8") as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.TestSuite(tests))
    report = {"task": "CODEX-RT002-S0-REPAIR-001", "sandbox": str(base), "tests": result.testsRun,
              "failures": [t.id() for t, _ in result.failures], "errors": [t.id() for t, _ in result.errors],
              "skipped": [(t.id(), reason) for t, reason in result.skipped], "isolation_violations": violations,
              "manifest": [t.id() for t in tests], "elapsed_seconds": round(time.time() - started, 3),
              "observations": _OBSERVATIONS,
              "log": str(log_path), "log_sha256": hashlib.sha256(log_path.read_bytes()).hexdigest()}
    (base / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in {"manifest", "observations"}}, ensure_ascii=False, indent=2))
    if result.failures or result.errors:
        print(log_path.read_text(encoding="utf-8").split("======================================================================", 1)[-1])
    return 0 if result.wasSuccessful() and not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
