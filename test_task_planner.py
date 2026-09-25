from __future__ import annotations

import copy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

import audit_storage
import planner_runtime
import server
import task_planner
import test_final_audit as legacy
import ultra_ui
import verifier_runtime


def plan(persistence=True, *, operation="create", already=False, path="result.md", value="done"):
    return {"stages": [{"stage_id": "main", "goal": "requested result",
        "stage_type": "produce_artifact" if persistence else "analysis",
        "persistence_required": persistence,
        "allowed_capabilities": ["READ", "WRITE"], "completion_criteria": ["requested outcome"],
        "artifacts": [{"artifact_id": "result", "path": path, "operation": operation,
                       "allow_already_satisfied": already,
                       "postcondition": {"kind": "equals", "value": value}}] if persistence else []}],
        "obligation_changes": []}


def ready(context):
    return {"status": "READY_TO_PERSIST", "reason": "material ready",
            "unresolved_requirements": [], "next_action": ""}


def continuation():
    return {"status": "CONTINUE", "reason": "payload missing",
            "unresolved_requirements": ["material candidate"], "next_action": "prepare content for result.md",
            "candidate_ids": []}


def write(path="result.md", content="done"):
    return {"name": "write_file", "arguments": {"path": path, "content": content}}


def tool(call):
    return legacy.FakeResponse("", finish_reason="function_call", function_call=call)


class PlannerIntegrationTests(unittest.IsolatedAsyncioTestCase):
    setUp = legacy.FinalAuditRuntimeTests.setUp
    tearDown = legacy.FinalAuditRuntimeTests.tearDown

    async def run_v6(self, initial=None, responses=None, *, planner_effect=None, audits=None,
                     callback=None, extra_patches=(), allow_write=True):
        self.permissions.update(allow_write=allow_write, allow_verify=True, tool_limit=12)
        initial = initial or plan()
        async def planner(**kwargs):
            if planner_effect:
                return await planner_effect(**kwargs)
            if kwargs["mode"] == "INITIAL":
                return copy.deepcopy(initial)
            return ready(kwargs["context"])
        self.planner = AsyncMock(side_effect=planner)
        original = server.run_agent_task
        async def enabled(*args, **kwargs):
            return await original(*args, **kwargs, planner_enabled=True)
        with patch.object(server, "run_agent_task", enabled), patch.object(server, "run_planner", self.planner):
            return await legacy.FinalAuditRuntimeTests.run_case(
                self, audits or legacy.verifier_result(), fake_client=legacy.FakeClient(responses),
                permission_request_callback=callback, extra_patches=extra_patches,
            )

    def stored(self):
        files = list((self.runtime / "logs" / "task_plans").glob("*.json"))
        self.assertEqual(len(files), 1)
        self.assertNotIn(self.workspace, files[0].parents)
        return json.loads(files[0].read_text(encoding="utf-8"))

    def event_names(self):
        return [e["event"] for e in self.events]

    async def test_readonly_stop_reaches_audit_without_mutation(self):
        result, audit, _ = await self.run_v6(plan(False))
        self.assertEqual(result, "CANDIDATE FINAL")
        self.assertEqual(audit.await_count, 1)
        self.assertNotIn("persistence_required", self.event_names())
        self.assertFalse((self.workspace / "result.md").exists())
        self.assertEqual(self.stored()["stage_states"]["main"]["status"], "SATISFIED")

    async def test_required_create_normal_tool_then_audit(self):
        result, audit, client = await self.run_v6(responses=[tool(write()), legacy.FakeResponse("Finished")])
        self.assertEqual(result, "Finished")
        self.assertEqual((self.workspace / "result.md").read_text(), "done")
        names = self.event_names()
        self.assertLess(names.index("persistence_satisfied"), names.index("final_audit_started"))
        evidence = json.loads(audit.await_args.kwargs["verification_context"])["task_plan"]
        self.assertEqual(evidence["stage_states"]["main"]["obligations"]["result"]["status"], "SATISFIED")
        self.assertEqual(client.bodies[0]["function_call"], "auto")
        self.assertIsNone(self.stored()["active_stage_id"])

    async def test_live_readiness_ready_without_uuid_executes_concrete_write(self):
        async def nonideal_planner(**kw):
            if kw["mode"] == "INITIAL":
                return plan()
            return {"status": "READY_TO_PERSIST", "reason": "document material is ready",
                    "unresolved_requirements": [], "next_action": "WRITE_FILE", "candidate_ids": []}
        real_dispatch = server._execute_agent_function
        with patch.object(server, "_execute_agent_function", wraps=real_dispatch) as dispatch:
            result, audit, _ = await self.run_v6(planner_effect=nonideal_planner,
                responses=[tool(write()), legacy.FakeResponse("Finished")])
        self.assertGreater(dispatch.call_count, 0)
        self.assertEqual(result, "Finished")
        self.assertEqual((self.workspace / "result.md").read_text(), "done")
        self.assertTrue(any(c.args[1]["name"] == "write_file" for c in dispatch.call_args_list))
        events = self.event_names()
        self.assertLess(events.index("persistence_required"), events.index("tool_started"))
        self.assertLess(events.index("persistence_satisfied"), events.index("final_audit_started"))
        self.assertEqual(audit.await_count, 1)

    async def test_invented_legacy_uuid_cannot_redirect_single_candidate(self):
        async def invented(**kw):
            if kw["mode"] == "INITIAL":
                return plan()
            return {**ready(kw["context"]), "candidate_ids": ["candidate_invented_other_target"]}
        result, audit, _ = await self.run_v6(planner_effect=invented,
            responses=[tool(write()), legacy.FakeResponse("Finished")])
        self.assertEqual(result, "Finished")
        self.assertEqual((self.workspace / "result.md").read_text(), "done")
        self.assertEqual(self.stored()["receipts"][0]["path"], "result.md")
        self.assertEqual(audit.await_count, 1)

    async def test_readiness_without_legacy_uuid_field(self):
        result, audit, _ = await self.run_v6(responses=[tool(write()), legacy.FakeResponse("Finished")])
        self.assertEqual(result, "Finished")
        self.assertEqual(audit.await_count, 1)
        self.assertTrue(all("candidate_id" not in candidate
                            for c in self.planner.await_args_list if c.kwargs["mode"] == "READINESS"
                            for candidate in c.kwargs["context"]["candidates"]))

    async def test_legacy_correct_uuid_is_advisory(self):
        async def legacy_echo(**kw):
            if kw["mode"] == "INITIAL":
                return plan()
            return {**ready(kw["context"]), "candidate_ids": [
                next(iter(self.stored()["candidates"]))]}
        result, audit, _ = await self.run_v6(planner_effect=legacy_echo,
            responses=[tool(write()), legacy.FakeResponse("Finished")])
        self.assertEqual(result, "Finished")
        self.assertEqual(audit.await_count, 1)

    async def test_zero_tools_false_completion_never_reaches_audit(self):
        result, audit, _ = await self.run_v6(responses=[legacy.FakeResponse("Файл создан, git diff выполнен.")] * 4)
        self.assertIn("BLOCKED", result)
        audit.assert_not_awaited()
        self.assertIn("persistence_recovery_exhausted", self.event_names())
        self.assertFalse((self.workspace / "result.md").exists())

    async def test_material_stop_uses_existing_dispatcher(self):
        result, audit, client = await self.run_v6(responses=[
            legacy.FakeResponse(json.dumps({"candidates": [write()]})), legacy.FakeResponse("Finished")])
        self.assertEqual(result, "Finished")
        self.assertIn("persistence_dispatch", self.event_names())
        self.assertEqual(client.post_count, 2)
        self.assertEqual(audit.await_count, 1)
        self.assertEqual((self.workspace / "result.md").read_text(), "done")

    async def test_other_file_cannot_satisfy_obligation(self):
        result, audit, _ = await self.run_v6(responses=[tool(write("other.md"))] + [legacy.FakeResponse("done")] * 4)
        self.assertIn("BLOCKED", result)
        audit.assert_not_awaited()
        self.assertEqual(self.stored()["stage_states"]["main"]["obligations"]["result"]["status"], "OPEN")

    async def test_already_satisfied_has_no_fake_receipt(self):
        (self.workspace / "result.md").write_text("done")
        result, audit, _ = await self.run_v6(plan(already=True))
        self.assertEqual(audit.await_count, 1)
        state = self.stored()
        self.assertEqual(state["receipts"], [])
        self.assertEqual(state["stage_states"]["main"]["obligations"]["result"]["status"], "ALREADY_SATISFIED")

    async def test_write_off_uses_existing_permission_escalation(self):
        callback = lambda request: False
        result, audits, _ = await self.run_v6(responses=[tool(write()), tool(write())],
            audits=legacy.verifier_result(check_type="PERMISSION"), callback=callback,
            allow_write=False)
        self.assertIn("BLOCKED", result)
        self.assertFalse((self.workspace / "result.md").exists())
        self.assertTrue(all(c.kwargs["check_type"] == "PERMISSION" for c in audits.await_args_list))
        self.assertIn("permission_review_started", self.event_names())
        self.assertNotIn("persistence_required", self.event_names())

    async def test_explicit_permission_grant_allows_same_contract_to_continue(self):
        decisions = []
        def granted(request):
            decisions.append(request)
            return True
        result, audit, _ = await self.run_v6(allow_write=False, callback=granted,
            responses=[tool(write()), tool(write()), tool(write()), legacy.FakeResponse("Finished")],
            audits=[legacy.verifier_result(check_type="PERMISSION"), legacy.verifier_result()])
        self.assertEqual(result, "Finished")
        self.assertEqual(len(decisions), 1)
        self.assertEqual((self.workspace / "result.md").read_text(), "done")
        names = self.event_names()
        self.assertLess(names.index("permission_granted"), names.index("persistence_required"))

    async def test_scope_violation_does_not_reach_audit_or_force(self):
        (self.workspace / "allowed").mkdir()
        self.permissions["write_scope"] = "allowed"
        result, audit, client = await self.run_v6(responses=[tool(write())])
        self.assertIn("BLOCKED", result)
        audit.assert_not_awaited()
        self.assertFalse((self.workspace / "result.md").exists())
        self.assertTrue(all(b["function_call"] == "auto" for b in client.bodies))
        rejected = [e for e in self.events if e["event"] == "mutation_preflight_rejected"]
        self.assertTrue(rejected)
        self.assertTrue(all(e["executed"] is False for e in rejected))
        self.assertNotIn("tool_started", self.event_names())

    async def test_ready_with_unresolved_requirements_is_rejected(self):
        async def premature(**kw):
            if kw["mode"] == "INITIAL":
                return plan()
            result = ready(kw["context"])
            result["unresolved_requirements"] = ["unknown content"]
            return result
        result, audit, _ = await self.run_v6(planner_effect=premature,
            responses=[legacy.FakeResponse(json.dumps({"candidates": [write()]}))] * 4)
        self.assertIn("BLOCKED", result)
        self.assertNotIn("persistence_required", self.event_names())
        self.assertFalse((self.workspace / "result.md").exists())
        audit.assert_not_awaited()

    async def test_existing_create_target_replans_and_preserves_v1(self):
        (self.workspace / "result.md").write_text("before")
        async def replanner(**kw):
            if kw["mode"] == "INITIAL":
                return plan()
            if kw["mode"] == "REPLAN":
                new = plan(operation="update")
                new["obligation_changes"] = [{"old_artifact_id": "result", "action": "replace",
                    "replacement_ids": ["result"], "reason": "target exists",
                    "fact_id": kw["context"]["authoritative_facts"][0]["fact_id"]}]
                return new
            return ready(kw["context"])
        result, audit, _ = await self.run_v6(planner_effect=replanner,
            responses=[tool(write()), tool(write()), legacy.FakeResponse("Finished")])
        self.assertEqual(result, "Finished")
        state = self.stored()
        self.assertEqual([p["plan_version"] for p in state["plans"]], [1, 2])
        self.assertEqual(state["plans"][0]["stages"][0]["artifacts"][0]["operation"], "create")
        self.assertIn("plan_revised", self.event_names())

    async def test_dredd_execution_defect_does_not_call_planner_again(self):
        failed = replace(legacy.fail_result("A"), route="EXECUTION_DEFECT", affected_stage_ids=("main",))
        result, audit, _ = await self.run_v6(plan(False), audits=[failed, legacy.verifier_result()],
            responses=[legacy.FakeResponse("Candidate A"), legacy.FakeResponse("Candidate B")])
        self.assertEqual(result, "Candidate B")
        self.assertEqual([c.kwargs["mode"] for c in self.planner.await_args_list], ["INITIAL", "READINESS"])
        self.assertEqual(audit.await_count, 2)

    async def test_dredd_plan_defect_runs_new_repair_stage(self):
        async def replanner(**kw):
            if kw["mode"] == "INITIAL":
                return plan(False)
            if kw["mode"] == "REPLAN":
                return plan()
            return ready(kw["context"])
        failed = replace(legacy.fail_result("A"), route="PLAN_DEFECT")
        result, audit, _ = await self.run_v6(planner_effect=replanner,
            audits=[failed, legacy.verifier_result()], responses=[legacy.FakeResponse("Candidate A"),
            tool(write()), legacy.FakeResponse("Candidate B")])
        self.assertEqual(result, "Candidate B")
        self.assertEqual(self.stored()["plan_version"], 2)
        self.assertIn("final_audit_routed_plan_defect", self.event_names())
        self.assertEqual(audit.await_count, 2)

    async def test_unknown_route_uses_bounded_execution_correction(self):
        failed = replace(legacy.fail_result("A"), route="UNKNOWN")
        result, audit, _ = await self.run_v6(plan(False), audits=[failed, legacy.verifier_result()],
            responses=[legacy.FakeResponse("Candidate A"), legacy.FakeResponse("Candidate B")])
        self.assertEqual(result, "Candidate B")
        self.assertNotIn("replan_started", self.event_names())

    async def test_continue_loop_terminates(self):
        async def never_ready(**kw):
            return plan(False) if kw["mode"] == "INITIAL" else continuation()
        result, audit, _ = await self.run_v6(planner_effect=never_ready,
            responses=[legacy.FakeResponse("Need more analysis")] * 5)
        self.assertIn("readiness_no_progress", result)
        audit.assert_not_awaited()

    async def test_role_isolation_and_safe_request_trace(self):
        result, audit, client = await self.run_v6(plan(False))
        planner_context = json.dumps([c.kwargs for c in self.planner.await_args_list])
        self.assertNotIn("audit_diagnostic", planner_context)
        self.assertNotIn("Independent Final", planner_context)
        request = next(e for e in self.events if e["event"] == "api_request")
        self.assertEqual(request["exposed_tool_count"], len(client.bodies[0]["functions"]))
        self.assertEqual(request["exposed_tool_names"], [f["name"] for f in client.bodies[0]["functions"]])
        self.assertEqual(request["function_call_mode"], "auto")
        self.assertNotIn("messages", request)
        self.assertNotIn("Authorization", request)
        self.assertNotIn("planner_context", json.dumps(client.bodies))
        state = self.stored()
        thread = audit_storage.load_audit_thread(self.workspace, "ws_test", None, state["run_id"])
        self.assertIn("task_lifecycle", thread)
        rendered = ultra_ui.UltraApp._audit_segments(thread, state["run_id"])
        self.assertIn("TASK PLAN", "".join(t for _, t in rendered))

    async def test_planner_failure_never_falls_back(self):
        async def broken(**kw):
            raise planner_runtime.PlannerError("bad JSON")
        result, audit, client = await self.run_v6(planner_effect=broken)
        self.assertIn("BLOCKED", result)
        self.assertEqual(client.post_count, 0)
        audit.assert_not_awaited()

    async def test_previous_stage_mutation_does_not_close_later_obligation(self):
        first = plan(path="other.md")["stages"][0]
        first["stage_id"], first["artifacts"][0]["artifact_id"] = "first", "other"
        multi = plan()
        multi["stages"].insert(0, first)
        result, audit, _ = await self.run_v6(multi, responses=[tool(write("other.md")),
            legacy.FakeResponse("First stage finished")] + [legacy.FakeResponse("Finished")] * 4)
        self.assertIn("BLOCKED", result)
        self.assertEqual((self.workspace / "other.md").read_text(), "done")
        self.assertFalse((self.workspace / "result.md").exists())
        state = self.stored()
        self.assertEqual(state["stage_states"]["first"]["status"], "SATISFIED")
        self.assertEqual(state["stage_states"]["main"]["obligations"]["result"]["status"], "OPEN")
        self.assertTrue(state["receipts"][0]["executed"])
        audit.assert_not_awaited()

    async def test_created_file_can_be_completed_by_precise_edit(self):
        insertion = {"name": "insert_after", "arguments": {"path": "result.md", "marker": "do",
            "content": "ne", "expected_content_sha256": server._sha256_utf8("do")}}
        result, audit, _ = await self.run_v6(responses=[tool(write(content="do")), tool(insertion),
                                                          legacy.FakeResponse("Finished")])
        self.assertEqual(result, "Finished")
        self.assertEqual((self.workspace / "result.md").read_text(), "done")
        self.assertEqual(len(self.stored()["receipts"]), 2)

    async def test_execution_repair_mutates_without_new_planner_call(self):
        contract = plan()
        contract["stages"][0]["artifacts"][0]["postcondition"] = {"kind": "contains", "value": "done"}
        failed = replace(legacy.fail_result("A"), route="EXECUTION_DEFECT", affected_stage_ids=("main",))
        result, audit, _ = await self.run_v6(contract, audits=[failed, legacy.verifier_result()],
            responses=[tool(write()), legacy.FakeResponse("Candidate A"), tool(write(content="done with detail")),
                       legacy.FakeResponse("Candidate B")])
        self.assertEqual(result, "Candidate B")
        self.assertEqual((self.workspace / "result.md").read_text(), "done with detail")
        self.assertEqual([c.kwargs["mode"] for c in self.planner.await_args_list], ["INITIAL", "READINESS"])

    async def test_delete_contract_observes_absence(self):
        (self.workspace / "result.md").write_text("delete me")
        self.permissions["allow_delete"] = True
        contract = plan(operation="delete")
        contract["stages"][0]["allowed_capabilities"].append("DELETE")
        contract["stages"][0]["artifacts"][0]["postcondition"] = {"kind": "absent", "value": ""}
        result, audit, _ = await self.run_v6(contract, responses=[
            tool({"name": "delete_file", "arguments": {"path": "result.md"}}), legacy.FakeResponse("Finished")])
        self.assertEqual(result, "Finished")
        self.assertFalse((self.workspace / "result.md").exists())
        self.assertEqual(self.stored()["receipts"][0]["after"], {"exists": False, "sha256": None})

    async def test_execution_repair_preserves_other_artifact_receipt(self):
        contract = plan()
        artifact = contract["stages"][0]["artifacts"][0]
        artifact["postcondition"] = {"kind": "contains", "value": "done"}
        contract["stages"][0]["artifacts"].append({
            **copy.deepcopy(artifact), "artifact_id": "other", "path": "other.md"})
        failed = replace(legacy.fail_result("A"), route="EXECUTION_DEFECT", affected_stage_ids=("main",))
        result, audit, _ = await self.run_v6(contract, audits=[failed, legacy.verifier_result()],
            responses=[tool(write()), tool(write("other.md")), legacy.FakeResponse("Candidate A"),
                       tool(write(content="done with detail")), legacy.FakeResponse("Candidate B")])
        self.assertEqual(result, "Candidate B")
        state = self.stored()
        self.assertEqual(len(state["receipts"]), 3)
        self.assertEqual(len([r for r in state["receipts"] if r["path"] == "other.md"]), 1)
        self.assertEqual((self.workspace / "other.md").read_text(), "done")
        self.assertEqual(audit.await_count, 2)
        self.assertEqual([c.kwargs["mode"] for c in self.planner.await_args_list],
                         ["INITIAL", "READINESS", "READINESS"])

    async def test_batch_prepared_artifacts_dispatch_without_replanning_each_write(self):
        contract = plan()
        artifact = contract["stages"][0]["artifacts"][0]
        contract["stages"][0]["artifacts"] = [
            {**copy.deepcopy(artifact), "artifact_id": f"a{i}", "path": f"file{i}.md"} for i in range(4)]
        candidate = json.dumps({"candidates": [write(f"file{i}.md") for i in range(4)]})
        result, audit, client = await self.run_v6(contract,
            responses=[legacy.FakeResponse(candidate), legacy.FakeResponse("Finished")])
        self.assertEqual(result, "Finished")
        self.assertEqual(client.post_count, 2)
        self.assertEqual(self.planner.await_count, 2)
        self.assertEqual(len(self.stored()["receipts"]), 4)
        self.assertEqual(audit.await_count, 1)

    async def test_ambiguous_operations_same_artifact_never_dispatch(self):
        proposals = json.dumps({"candidates": [write(content="done"), write(content="different")]})
        real_dispatch = server._execute_agent_function
        with patch.object(server, "_execute_agent_function", wraps=real_dispatch) as dispatch:
            result, audit, _ = await self.run_v6(responses=[legacy.FakeResponse(proposals)]
                + [legacy.FakeResponse("Still ready") for _ in range(4)])
        self.assertIn("BLOCKED", result)
        self.assertEqual(dispatch.call_count, 0)
        self.assertFalse((self.workspace / "result.md").exists())
        self.assertNotIn("persistence_required", self.event_names())
        self.assertIn("candidate_ambiguous", [e.get("reason_code") for e in self.events])
        audit.assert_not_awaited()

    async def test_preflight_continuation_has_no_tool_runtime_events(self):
        async def not_ready(**kw):
            return plan() if kw["mode"] == "INITIAL" else continuation()
        real_dispatch = server._execute_agent_function
        with patch.object(server, "_execute_agent_function", wraps=real_dispatch) as dispatch:
            result, audit, _ = await self.run_v6(planner_effect=not_ready,
                responses=[tool(write())] + [legacy.FakeResponse("Later") for _ in range(4)])
        self.assertIn("BLOCKED", result)
        self.assertEqual(dispatch.call_count, 0)
        self.assertNotIn("tool_started", self.event_names())
        self.assertNotIn("tool_error", self.event_names())
        rejected = next(e for e in self.events if e["event"] == "mutation_preflight_rejected")
        self.assertEqual(rejected["reason_code"], "planner_continue")
        self.assertIs(rejected["executed"], False)
        self.assertEqual(rejected["stage_id"], "main")
        self.assertEqual(rejected["plan_version"], 1)
        state = self.stored()
        thread = audit_storage.load_audit_thread(self.workspace, "ws_test", None, state["run_id"])
        stored_event = next(e for e in thread["task_lifecycle"]["events"]
                            if e["event"] == "mutation_preflight_rejected")
        self.assertIs(stored_event["executed"], False)
        self.assertEqual(stored_event["reason_code"], "planner_continue")
        audit.assert_not_awaited()

    async def test_real_dispatch_error_has_tool_started_then_tool_error(self):
        real_dispatch = server._execute_agent_function
        calls = 0
        def first_write_fails(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise ValueError("real dispatcher failure")
            return real_dispatch(*args, **kwargs)
        with patch.object(server, "_execute_agent_function", side_effect=first_write_fails):
            result, audit, _ = await self.run_v6(responses=[tool(write()),
                legacy.FakeResponse("Retry"), legacy.FakeResponse("Finished")])
        self.assertEqual(result, "Finished")
        self.assertEqual(calls, 2)
        names = self.event_names()
        self.assertLess(names.index("tool_started"), names.index("tool_error"))
        self.assertNotIn("mutation_preflight_rejected", names)
        self.assertEqual(audit.await_count, 1)


class PersistenceStateTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "workspace"
        self.root.mkdir()
        self.events = []
        self.policy = server._prepare_policy_for_workspace(self.root, server._normalize_permissions({
            "allow_read": True, "allow_write": True, "allow_verify": True, "auto_backup": False}))

    def controller(self, contract, effect=None):
        async def planner(**kw):
            if effect:
                return await effect(**kw)
            return copy.deepcopy(contract) if kw["mode"] != "READINESS" else ready(kw["context"])
        return task_planner.TaskLifecycle(path=Path(self.temp.name) / "state.json", run_id="run1",
            task_block_id=None, raw_task="TASK", planner_call=planner,
            emit=lambda name, data: self.events.append({"event": name, **data}),
            snapshot=lambda p: server._planner_target_snapshot(self.root, p, self.policy),
            prepare=lambda c, a, repair: server._prepare_persistence_candidate(self.root, c, a, self.policy, repair))

    async def test_noop_write_is_not_mutation_evidence(self):
        (self.root / "result.md").write_text("done")
        lc = self.controller(plan(operation="update"))
        await lc.initialize({})
        with self.assertRaisesRegex(ValueError, "No logical mutation"):
            await lc.before_mutation(write())
        self.assertFalse(lc.check_obligations())
        self.assertEqual(lc.state["receipts"], [])

    async def test_external_change_after_stage_start_is_not_already_satisfied(self):
        (self.root / "result.md").write_text("before")
        lc = self.controller(plan(operation="update", already=True))
        await lc.initialize({})
        (self.root / "result.md").write_text("done")
        self.assertFalse(lc.check_obligations())
        self.assertEqual(lc.state["stage_states"]["main"]["obligations"]["result"]["status"], "OPEN")

    async def test_stale_candidate_after_planner_does_not_acquire_latch(self):
        (self.root / "result.md").write_text("before")
        async def effect(**kw):
            if kw["mode"] == "INITIAL":
                return plan(operation="update")
            (self.root / "result.md").write_text("external")
            return ready(kw["context"])
        lc = self.controller(plan(), effect)
        await lc.initialize({})
        with self.assertRaises(task_planner.PlanInvalidated):
            await lc.before_mutation(write())
        self.assertEqual(lc.state["stage_states"]["main"]["status"], "WORKING")
        self.assertEqual((self.root / "result.md").read_text(), "external")

    async def test_server_binding_rejects_candidate_from_other_plan_version(self):
        lc = self.controller(plan())
        await lc.initialize({})
        candidate = lc.new_candidate(write())
        candidate["plan_version"] = 999
        decision = await lc.readiness("material ready", [candidate])
        self.assertEqual(decision["reason_code"], "candidate_binding_invalid")
        self.assertEqual(lc.state["stage_states"]["main"]["status"], "WORKING")
        self.assertEqual(lc.state["receipts"], [])

    async def test_replan_cannot_silently_drop_obligation(self):
        async def effect(**kw):
            return plan() if kw["mode"] == "INITIAL" else plan(False)
        lc = self.controller(plan(), effect)
        await lc.initialize({})
        with self.assertRaisesRegex(task_planner.LifecycleBlocked, "dropped_obligation"):
            await lc.replan({"reason": "target_changed"})
        self.assertEqual(lc.state["plan_version"], 1)

    async def test_shared_call_budget_applies_across_roles(self):
        lc = self.controller(plan(False))
        await lc.initialize({})
        with patch.object(task_planner, "RUN_LIFECYCLE_CALL_LIMIT", 2):
            lc.tick("EXECUTOR")
            with self.assertRaisesRegex(task_planner.LifecycleBlocked, "run_lifecycle_budget"):
                lc.tick("FINAL_VERIFIER")

    async def test_atomic_storage_failure_preserves_last_state(self):
        lc = self.controller(plan(False))
        await lc.initialize({})
        original = lc.path.read_bytes()
        with patch.object(task_planner.os, "replace", side_effect=OSError("disk problem")):
            with self.assertRaises(OSError):
                lc.save()
        self.assertEqual(lc.path.read_bytes(), original)
        self.assertEqual(list(lc.path.parent.glob(".*.tmp")), [])

    async def test_satisfied_receipt_invalidated_by_external_change(self):
        lc = self.controller(plan())
        await lc.initialize({})
        cid = await lc.before_mutation(write())
        (self.root / "result.md").write_text("done")
        lc.after_mutation(cid, {"path": "result.md", "content_sha256": server._sha256_utf8("done")})
        (self.root / "result.md").write_text("external")
        with self.assertRaises(task_planner.PlanInvalidated):
            lc.check_obligations()

    async def test_latched_stop_reuses_material_without_readiness_call(self):
        lc = self.controller(plan())
        await lc.initialize({})
        await lc.before_mutation(write())
        lc.planner_call = AsyncMock(side_effect=AssertionError("Planner must not redecide a latched operation"))
        decision = await lc.on_stop("Finished")
        self.assertEqual(decision, {"action": "dispatch", "call": write()})
        lc.planner_call.assert_not_awaited()

    async def test_replan_budget_does_not_reset_shared_run_budget(self):
        lc = self.controller(plan(False))
        await lc.initialize({})
        await lc.replan({"reason": "new_fact"})
        await lc.replan({"reason": "another_fact"})
        with self.assertRaisesRegex(task_planner.LifecycleBlocked, "replan_budget"):
            await lc.replan({"reason": "third_fact"})
        self.assertEqual(lc.state["plan_version"], 3)
        self.assertEqual(lc.state["calls"], 3)


class PlannerProtocolTests(unittest.IsolatedAsyncioTestCase):
    def test_schema_rejects_untyped_or_empty_contract(self):
        for mutation in [lambda p: p["stages"][0].update(persistence_required="true"),
                         lambda p: p["stages"][0].update(artifacts=[]),
                         lambda p: p["stages"][0]["artifacts"][0].update(path="../escape.md")]:
            value = plan()
            mutation(value)
            with self.assertRaises(planner_runtime.PlannerError):
                planner_runtime.validate_plan(value)

    def test_tool_free_role_body_and_context_bound(self):
        body = planner_runtime.build_planner_body("INITIAL", "TASK", {"permissions": {}}, "gigachat_ultra")
        self.assertNotIn("functions", body)
        self.assertEqual(body["function_call"], "none")
        with self.assertRaises(planner_runtime.PlannerError):
            planner_runtime.build_planner_body("INITIAL", "x" * 150000, {}, "gigachat_ultra")

    def test_strict_json(self):
        for text in ['```json\n{}\n```', '{"a":1,"a":2}', '[]', '{"a":NaN}']:
            with self.assertRaises(planner_runtime.PlannerError):
                planner_runtime.strict_json(text)

    def test_backward_compatible_final_route(self):
        old = {"result": "FAIL", "check_type": "FINAL", "reason": "x", "violations": [], "required_action": "y"}
        self.assertNotIn("route", verifier_runtime._parse_verifier_response(json.dumps(old), "FINAL"))
        for route in ("UNKNOWN", "EXECUTION_DEFECT", "PLAN_DEFECT"):
            parsed = verifier_runtime._parse_verifier_response(json.dumps({**old, "route": route}), "FINAL")
            self.assertEqual(parsed["route"], route)
        with self.assertRaises(verifier_runtime.VerifierProtocolError):
            verifier_runtime._parse_verifier_response(json.dumps({**old, "route": "GUESS_FROM_REASON"}), "FINAL")

    async def test_runtime_parses_one_shot_without_executor_session(self):
        client = legacy.FakeClient([legacy.FakeResponse(json.dumps(plan(False)))])
        with patch.object(planner_runtime, "get_access_token", AsyncMock(return_value="secret")), \
                patch.object(planner_runtime.httpx, "AsyncClient", return_value=client):
            result = await planner_runtime.run_planner(mode="INITIAL", raw_task="Explain", context={})
        self.assertEqual(result, plan(False))
        self.assertEqual(client.post_count, 1)
        self.assertEqual(len(client.bodies[0]["messages"]), 2)


if __name__ == "__main__":
    unittest.main()
