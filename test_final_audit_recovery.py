from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import run_store
import server
import test_final_audit as legacy
import test_task_planner as planner_tests


def read_contract(*, explore=False):
    stage = planner_tests.plan(False)["stages"][0]
    stage.update(
        stage_id="read_stage",
        allowed_capabilities=["READ"],
        completion_mode="server_evidence",
        evidence_requirements=[{
            "evidence_id": "readback",
            "tool": "read_file",
            "arguments": {"path": "result.md"},
        }],
    )
    stages = [stage]
    if explore:
        first = planner_tests.plan(False)["stages"][0]
        first.update(stage_id="explore", allowed_capabilities=["READ"])
        stages.insert(0, first)
    return {"stages": stages, "obligation_changes": []}


def read_response(path="result.md"):
    return planner_tests.tool({"name": "read_file", "arguments": {"path": path}})


class FinalAuditByteBudgetTests(unittest.TestCase):
    def test_clipping_respects_every_small_budget_and_utf8_boundary(self):
        for text in ("x" * 200, "я" * 200, "🐍" * 200):
            for limit in range(100):
                with self.subTest(text=text[:1], limit=limit):
                    clipped, truncated, original = server._clip_final_audit_text(text, limit)
                    self.assertTrue(truncated)
                    self.assertEqual(original, len(text.encode("utf-8")))
                    self.assertLessEqual(len(clipped.encode("utf-8")), limit)
                    self.assertNotIn("\ufffd", clipped)

    def test_exact_budget_preserves_the_original_text(self):
        text = "данные 🐍"
        clipped, truncated, original = server._clip_final_audit_text(
            text, len(text.encode("utf-8"))
        )
        self.assertEqual(clipped, text)
        self.assertFalse(truncated)
        self.assertEqual(original, len(text.encode("utf-8")))


class FinalAuditGitScopeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True, capture_output=True)
        self.policy = server._prepare_policy_for_workspace(
            self.root, server._normalize_permissions({
                "allow_read": True, "allow_verify": True, "read_scope": ".",
            })
        )

    def test_literal_filename_does_not_include_matching_neighbor(self):
        for name in ("target[1].txt", "target1.txt"):
            (self.root / name).write_text(name, encoding="utf-8")
        result = server._agent_git_status(self.root, self.policy, ["target[1].txt"])
        self.assertTrue(result["ok"])
        self.assertIn("target[1].txt", result["stdout"])
        self.assertNotIn("target1.txt", result["stdout"])

    def test_directory_scope_is_recursive_and_literal(self):
        for name in ("dir[1]", "dir1"):
            directory = self.root / name / "nested"
            directory.mkdir(parents=True)
            (directory / "result.txt").write_text(name, encoding="utf-8")
        result = server._agent_git_status(self.root, self.policy, ["dir[1]"])
        self.assertTrue(result["ok"])
        self.assertIn("dir[1]/nested/result.txt", result["stdout"])
        self.assertNotIn("dir1/", result["stdout"])

    def test_deleted_literal_target_is_valid_for_status_and_diff(self):
        path = self.root / "target[1].txt"
        path.write_text("tracked in fixture index", encoding="utf-8")
        subprocess.run(
            ["git", "--literal-pathspecs", "add", "--", path.name],
            cwd=self.root, check=True, capture_output=True,
        )
        path.unlink()
        result = server._agent_git_status(self.root, self.policy, [path.name])
        self.assertTrue(result["ok"])
        self.assertIn(path.name, result["stdout"])
        fake = {"ok": True, "stdout": "", "stderr": "", "truncated": False}
        with patch.object(server, "_run_verify_process", return_value=fake) as process:
            server._agent_git_diff(self.root, [path.name], self.policy, allow_missing=True)
        command = process.call_args.args[0]
        self.assertIn("--literal-pathspecs", command)
        self.assertEqual(command[command.index("--") + 1:], [path.name])

    def test_no_paths_is_not_applicable_without_running_git(self):
        with patch.object(server, "_run_verify_process") as process:
            result = server._agent_git_status(self.root, self.policy, [])
        process.assert_not_called()
        self.assertTrue(result["not_applicable"])
        self.assertEqual(result["reason"], "no_task_scoped_paths")


class FinalAuditRecoveryIntegrationTests(unittest.IsolatedAsyncioTestCase):
    setUp = legacy.FinalAuditRuntimeTests.setUp
    tearDown = legacy.FinalAuditRuntimeTests.tearDown
    run_v6 = planner_tests.PlannerIntegrationTests.run_v6

    async def test_deduplicated_required_large_read_blocks_before_dredd(self):
        material = "x" * 9000
        (self.workspace / "result.md").write_text(material, encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "FINAL AUDIT ERROR"):
            await self.run_v6(read_contract(explore=True), responses=[
                read_response(), legacy.FakeResponse("Inspected"),
                read_response(), legacy.FakeResponse("Finished"),
            ])
        self.last_verifier.assert_not_awaited()
        failure = next(e for e in self.events if e["event"] == "final_audit_error")
        self.assertIn("requirement_material_truncated:read_stage:readback", failure["reason"])
        started = next(e for e in self.events if e["event"] == "run_started")
        records = run_store.load_stream_records(self.workspace, started["run_id"], "SERVER")
        reads = [r for r in records if r["event"] == "tool_finished"]
        self.assertEqual(len(reads), 2)
        self.assertTrue(all(r["payload"]["result"]["content"] == material for r in reads))

    async def test_complete_deduplicated_material_keeps_an_explicit_source(self):
        (self.workspace / "result.md").write_text("small complete material", encoding="utf-8")
        result, audit, _ = await self.run_v6(read_contract(explore=True), responses=[
            read_response(), legacy.FakeResponse("Inspected"),
            read_response(), legacy.FakeResponse("Finished"),
        ])
        self.assertEqual(result, "Finished")
        packet = json.loads(audit.await_args.kwargs["verification_context"])
        facts = packet["authoritative_tool_evidence"]
        self.assertEqual([f["sequence"] for f in facts], [1, 2])
        source = next(f for f in facts if "material_preview" in f)
        duplicate = next(f for f in facts if f.get("material_deduplicated"))
        self.assertEqual(duplicate["material_source_record_id"], source["source_record_id"])
        self.assertFalse(packet["evidence_completeness"]["critical_for_success"])
        self.assertEqual(audit.await_args.kwargs["raw_task"], "ORIGINAL RAW TASK")

    async def test_current_required_material_gets_budget_before_exploration(self):
        (self.workspace / "result.md").write_text("needed", encoding="utf-8")
        (self.workspace / "unrelated.md").write_text("x" * 9000, encoding="utf-8")
        with patch.object(server, "MAX_FINAL_AUDIT_TOOL_MATERIAL_BYTES", 64):
            result, audit, _ = await self.run_v6(read_contract(explore=True), responses=[
                read_response("unrelated.md"), legacy.FakeResponse("Inspected"),
                read_response(), legacy.FakeResponse("Finished"),
            ])
        self.assertEqual(result, "Finished")
        packet = json.loads(audit.await_args.kwargs["verification_context"])
        self.assertEqual(packet["task_scope"]["paths"], ["result.md"])
        required = packet["authoritative_tool_evidence"][1]
        self.assertEqual(required["material_preview"]["content"], "needed")
        self.assertLessEqual(packet["task_material"]["included_bytes"], 64)
        self.assertFalse(packet["evidence_completeness"]["critical_for_success"])

    async def test_old_truncated_material_cannot_block_fresh_generation(self):
        path = self.workspace / "result.md"
        path.write_text("x" * 9000, encoding="utf-8")

        class ChangedResponse(legacy.FakeResponse):
            def json(self):
                path.write_text("fresh small value", encoding="utf-8")
                return super().json()

        result, audit, _ = await self.run_v6(read_contract(), responses=[
            read_response(), ChangedResponse("Finished"),
            read_response(), legacy.FakeResponse("Finished"),
        ])
        self.assertEqual(result, "Finished")
        self.assertTrue(any(e["event"] == "evidence_invalidated" for e in self.events))
        packet = json.loads(audit.await_args.kwargs["verification_context"])
        self.assertTrue(packet["requirement_coverage"]["complete"])
        self.assertFalse(packet["evidence_completeness"]["critical_for_success"])
        current = packet["authoritative_tool_evidence"][1]
        self.assertEqual(current["evidence_generation"], 1)
        self.assertEqual(current["material_preview"]["content"], "fresh small value")

    async def test_missing_required_material_blocks_before_dredd(self):
        (self.workspace / "result.md").write_text("required", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "FINAL AUDIT ERROR"):
            await self.run_v6(read_contract(), responses=[
                read_response(), legacy.FakeResponse("Finished"),
            ], extra_patches=(
                patch.object(server, "_final_audit_tool_material_preview", return_value=None),
            ))
        self.last_verifier.assert_not_awaited()
        failure = next(e for e in self.events if e["event"] == "final_audit_error")
        self.assertIn("requirement_material_missing:read_stage:readback", failure["reason"])

    async def test_required_material_budget_exhaustion_blocks_before_dredd(self):
        (self.workspace / "result.md").write_text("required", encoding="utf-8")
        with patch.object(server, "MAX_FINAL_AUDIT_TOOL_MATERIAL_BYTES", 0):
            with self.assertRaisesRegex(RuntimeError, "FINAL AUDIT ERROR"):
                await self.run_v6(read_contract(), responses=[
                    read_response(), legacy.FakeResponse("Finished"),
                ])
        self.last_verifier.assert_not_awaited()

    async def test_failed_exact_check_keeps_details_and_its_outcome_record(self):
        (self.workspace / "result.md").write_text("done", encoding="utf-8")
        contract = planner_tests.plan(False)
        contract["stages"][0]["allowed_capabilities"] = ["READ", "VERIFY"]
        result, audit, _ = await self.run_v6(contract, responses=[
            planner_tests.tool({"name": "verify_file_content", "arguments": {
                "path": "result.md", "kind": "equals", "value": "wrong",
            }}),
            planner_tests.tool({"name": "verify_file_content", "arguments": {
                "path": "result.md", "kind": "sha256", "value": server._sha256_utf8("done"),
            }}),
            legacy.FakeResponse("Finished"),
        ])
        self.assertEqual(result, "Finished")
        packet = json.loads(audit.await_args.kwargs["verification_context"])
        failed, passed = packet["authoritative_tool_evidence"]
        self.assertEqual(failed["status"], "ERROR")
        self.assertEqual(passed["status"], "OK")
        detail = json.loads(failed["material_preview"]["content"])
        self.assertEqual(detail["kind"], "equals")
        self.assertFalse(detail["matched"])
        self.assertEqual(detail["expected_sha256"], server._sha256_utf8("wrong"))
        self.assertEqual(detail["actual_sha256"], server._sha256_utf8("done"))
        record = run_store.load_run_record(
            self.workspace, packet["run_facts"]["run_id"], failed["source_run_store_record_id"],
        )
        self.assertEqual(record["event"], "tool_error")
        self.assertEqual(record["payload"]["result"], detail)
        self.assertEqual(record["payload"]["evidence_record_id"], failed["source_record_id"])
        self.assertEqual(server._sha256_utf8(json.dumps(
            detail, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        )), failed["result"]["sha256"])

    async def test_empty_search_negative_fact_survives_no_preview_budget(self):
        (self.workspace / "result.md").write_text("nothing relevant", encoding="utf-8")
        with patch.object(server, "MAX_FINAL_AUDIT_TOOL_MATERIAL_BYTES", 0):
            result, audit, _ = await self.run_v6(planner_tests.plan(False), responses=[
                planner_tests.tool({"name": "find_text", "arguments": {
                    "path": "result.md", "text": "missing needle",
                }}),
                legacy.FakeResponse("Nothing found"),
            ])
        self.assertEqual(result, "Nothing found")
        packet = json.loads(audit.await_args.kwargs["verification_context"])
        fact = packet["authoritative_tool_evidence"][0]
        self.assertEqual(fact["status"], "OK")
        self.assertTrue(fact["material_omitted_due_to_budget"])
        self.assertIn("count=0", fact.get("summary", ""))

    async def test_ignored_file_material_remains_available_without_git_diff(self):
        subprocess.run(["git", "init", "-q", str(self.workspace)], check=True, capture_output=True)
        (self.workspace / ".gitignore").write_text("result.md\n", encoding="utf-8")
        (self.workspace / "result.md").write_text("ignored but required", encoding="utf-8")
        status, diff = server._agent_git_status, server._agent_git_diff
        result, audit, _ = await self.run_v6(read_contract(), responses=[
            read_response(), legacy.FakeResponse("Finished"),
        ], extra_patches=(
            patch.object(server, "_agent_git_status", side_effect=status),
            patch.object(server, "_agent_git_diff", side_effect=diff),
        ))
        self.assertEqual(result, "Finished")
        packet = json.loads(audit.await_args.kwargs["verification_context"])
        self.assertEqual(packet["fresh_git_status"]["stdout"], "")
        self.assertFalse(packet["fresh_git_diff"]["available"])
        self.assertEqual(packet["authoritative_tool_evidence"][0]["material_preview"]["content"],
                         "ignored but required")
        self.assertFalse(packet["evidence_completeness"]["critical_for_success"])

    async def test_tool_level_truncated_find_text_blocks_before_dredd(self):
        (self.workspace / "result.md").write_text("x x", encoding="utf-8")
        contract = read_contract()
        contract["stages"][0]["evidence_requirements"] = [{
            "evidence_id": "matches", "tool": "find_text",
            "arguments": {"path": "result.md", "text": "x"},
        }]
        with patch.object(server, "MAX_FIND_TEXT_MATCHES", 1):
            with self.assertRaisesRegex(RuntimeError, "FINAL AUDIT ERROR"):
                await self.run_v6(contract, responses=[
                    planner_tests.tool({"name": "find_text", "arguments": {
                        "path": "result.md", "text": "x",
                    }}), legacy.FakeResponse("Finished"),
                ])
        self.last_verifier.assert_not_awaited()
        failure = next(e for e in self.events if e["event"] == "final_audit_error")
        self.assertIn("requirement_material_truncated:read_stage:matches", failure["reason"])

    async def test_failed_exact_metadata_survives_zero_material_budget(self):
        (self.workspace / "result.md").write_text("done", encoding="utf-8")
        contract = planner_tests.plan(False)
        contract["stages"][0]["allowed_capabilities"] = ["READ", "VERIFY"]
        with patch.object(server, "MAX_FINAL_AUDIT_TOOL_MATERIAL_BYTES", 0):
            result, audit, _ = await self.run_v6(contract, responses=[
                planner_tests.tool({"name": "verify_file_content", "arguments": {
                    "path": "result.md", "kind": "equals", "value": "wrong",
                }}), legacy.FakeResponse("Finished"),
            ])
        self.assertEqual(result, "Finished")
        packet = json.loads(audit.await_args.kwargs["verification_context"])
        failed = packet["authoritative_tool_evidence"][0]
        self.assertTrue(failed["material_omitted_due_to_budget"])
        exact = failed["result"]["verification"]
        self.assertEqual(exact["kind"], "equals")
        self.assertFalse(exact["matched"])
        self.assertEqual(exact["expected_sha256"], server._sha256_utf8("wrong"))
        self.assertEqual(exact["actual_sha256"], server._sha256_utf8("done"))

    async def test_directory_listing_requirement_reaches_audit_with_freshness(self):
        directory = self.workspace / "pkg"
        directory.mkdir()
        (directory / "a.txt").write_text("a", encoding="utf-8")
        contract = read_contract()
        contract["stages"][0]["evidence_requirements"] = [{
            "evidence_id": "listing", "tool": "list_dir", "arguments": {"path": "pkg"},
        }]
        result, audit, _ = await self.run_v6(contract, responses=[
            planner_tests.tool({"name": "list_dir", "arguments": {"path": "pkg"}}),
            legacy.FakeResponse("Finished"),
        ])
        self.assertEqual(result, "Finished")
        packet = json.loads(audit.await_args.kwargs["verification_context"])
        self.assertEqual(packet["task_scope"]["paths"], ["pkg"])
        coverage = packet["requirement_coverage"]["requirements"][1]
        self.assertTrue(coverage["covered"])
        self.assertIsNotNone(coverage["target_state_sha256"])
        policy = server._prepare_policy_for_workspace(
            self.workspace, server._normalize_permissions(self.permissions)
        )
        with self.assertRaisesRegex(ValueError, "not a regular file"):
            server._planner_target_snapshot(self.workspace, "pkg", policy)

    async def test_directory_listing_drift_after_pass_requires_fresh_audit(self):
        directory = self.workspace / "pkg"
        directory.mkdir()
        (directory / "a.txt").write_text("a", encoding="utf-8")
        contract = read_contract()
        contract["stages"][0]["evidence_requirements"] = [{
            "evidence_id": "listing", "tool": "list_dir", "arguments": {"path": "pkg"},
        }]
        calls = 0

        async def audit(**_kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                (directory / "b.txt").write_text("b", encoding="utf-8")
            return legacy.verifier_result()

        result, verifier, _ = await self.run_v6(contract, responses=[
            planner_tests.tool({"name": "list_dir", "arguments": {"path": "pkg"}}),
            legacy.FakeResponse("Finished"),
            planner_tests.tool({"name": "list_dir", "arguments": {"path": "pkg"}}),
            legacy.FakeResponse("Finished"),
        ], extra_patches=(patch.object(server, "run_verifier_check", side_effect=audit),))
        self.assertEqual(result, "Finished")
        self.assertEqual(calls, 2)
        self.assertTrue(any(e["event"] == "evidence_invalidated" for e in self.events))

    async def test_git_diff_state_drift_requires_new_source_evidence(self):
        (self.workspace / "result.md").write_text("unchanged filesystem", encoding="utf-8")
        contract = read_contract()
        contract["stages"][0]["allowed_capabilities"] = ["VERIFY"]
        contract["stages"][0]["evidence_requirements"] = [{
            "evidence_id": "diff", "tool": "git_diff", "arguments": {"paths": ["result.md"]},
        }]
        state = {"stdout": "initial diff"}

        real_diff = server._agent_git_diff

        def diff_process(*_args, **_kwargs):
            return {"ok": True, "exit_code": 0, "stdout": state["stdout"], "stderr": "",
                    "truncated": False}

        calls = 0

        async def audit(**_kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                state["stdout"] = "externally changed Git diff"
            return legacy.verifier_result()

        response = lambda: planner_tests.tool({"name": "git_diff", "arguments": {"paths": ["result.md"]}})
        result, _, _ = await self.run_v6(contract, responses=[
            response(), legacy.FakeResponse("Finished"),
            response(), legacy.FakeResponse("Finished"),
        ], extra_patches=(
            patch.object(server, "_agent_git_diff", side_effect=real_diff),
            patch.object(server, "_run_verify_process", side_effect=diff_process),
            patch.object(server, "run_verifier_check", side_effect=audit),
        ))
        self.assertEqual(result, "Finished")
        self.assertEqual(calls, 2)
        self.assertTrue(any(e["event"] == "evidence_invalidated" for e in self.events))

    async def test_truncated_directory_observation_is_unresolved(self):
        directory = self.workspace / "pkg"
        directory.mkdir()
        for name in ("a.txt", "b.txt"):
            (directory / name).write_text(name, encoding="utf-8")
        policy = server._prepare_policy_for_workspace(
            self.workspace, server._normalize_permissions(self.permissions)
        )
        with patch.object(server, "MAX_AGENT_LIST_ENTRIES", 1):
            with self.assertRaisesRegex(ValueError, "truncated"):
                server._planner_dependency_fingerprint(self.workspace, "list_dir", {"path": "pkg"}, policy)

    async def test_model_result_stage_keeps_semantic_tail_beyond_2000_chars(self):
        text = "x" * 2500 + "REQUIRED_TAIL"
        first = planner_tests.plan(False)["stages"][0]
        second = {**first, "stage_id": "finish"}
        contract = {"stages": [first, second], "obligation_changes": []}
        result, audit, _ = await self.run_v6(contract, responses=[
            legacy.FakeResponse(text), legacy.FakeResponse("Finished"),
        ])
        self.assertEqual(result, "Finished")
        packet = json.loads(audit.await_args.kwargs["verification_context"])
        state = packet["task_plan"]["stage_states"]["main"]
        self.assertEqual(state["result"], text)
        self.assertFalse(state["result_truncated"])
        self.assertEqual(state["result_original_bytes"], len(text.encode("utf-8")))

    async def test_truncated_model_result_stage_blocks_before_dredd(self):
        text = "x" * 9000 + "REQUIRED_TAIL"
        first = planner_tests.plan(False)["stages"][0]
        second = {**first, "stage_id": "finish"}
        contract = {"stages": [first, second], "obligation_changes": []}
        with self.assertRaisesRegex(RuntimeError, "FINAL AUDIT ERROR"):
            await self.run_v6(contract, responses=[
                legacy.FakeResponse(text), legacy.FakeResponse("Finished"),
            ])
        self.last_verifier.assert_not_awaited()
        failure = next(e for e in self.events if e["event"] == "final_audit_error")
        self.assertIn("stage_result_truncated:main", failure["reason"])
        stored = list((self.runtime / "logs" / "task_plans").glob("*.json"))
        self.assertEqual(json.loads(stored[0].read_text(encoding="utf-8"))["stage_states"]["main"]["result"], text)

    async def test_truncated_fresh_git_is_declared_in_packet_metadata(self):
        contract, freshness = legacy.FinalAuditRuntimeTests._task_scoped_packet_fixture(self)
        policy = server._prepare_policy_for_workspace(
            self.workspace, server._normalize_permissions(self.permissions)
        )
        good = {"ok": True, "stdout": "", "stderr": "", "truncated": False}
        with patch.object(server, "_agent_git_status", return_value={**good, "truncated": True}), \
                patch.object(server, "_agent_git_diff", return_value=good):
            _, metadata = server._collect_final_audit_evidence(
                root=self.workspace, candidate_final="Finished", policy=policy,
                run_id="run-test", api_request_count=1, tool_call_count=0,
                verification_state={"write_revision": 0}, backup_session=None,
                task_plan_evidence=contract, freshness_snapshot=freshness,
            )
        self.assertTrue(metadata["critical_for_success"])
        self.assertTrue(metadata["truncated"])


if __name__ == "__main__":
    unittest.main()
