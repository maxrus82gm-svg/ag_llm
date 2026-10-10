"""Additional S0 repair probes, loaded only by the guarded S0 runner.

No discovery-time runtime import, subprocess, network or production storage.
"""
import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch


def build_suite(h):
    server, store, planner = h.server, h.run_store, h.planner_tests
    import audit_storage

    class RepairBoundaryTests(unittest.IsolatedAsyncioTestCase):
        setUp = h.KernelBoundaryTests.setUp
        tearDown = h.KernelBoundaryTests.tearDown
        run_v6 = h.KernelBoundaryTests.run_v6
        read_case = h.KernelBoundaryTests.read_case
        policy = h.KernelBoundaryTests.policy
        capture = h.KernelBoundaryTests.capture
        success_events = h.KernelBoundaryTests.success_events

        def blocked(self, result, audit, sends=0):
            self.capture(result, audit)
            self.assertIn("BLOCKED", result)
            self.assertFalse(self.success_events())
            self.assertEqual(audit.await_count, sends)

        def watch(self, callback):
            callback_errors = []
            self.addCleanup(lambda: self.assertEqual(callback_errors, [], "fault injection failed"))
            class Events(list):
                def append(events, event):
                    super().append(copy.deepcopy(event))
                    try:
                        callback(event)
                    except Exception as exc:
                        callback_errors.append(repr(exc))
                def __deepcopy__(events, memo):
                    return copy.deepcopy(list(events), memo)
            self.events = Events()

        def contract(self, call):
            contract = h.recovery.read_contract()
            stage = contract["stages"][0]
            capability = server.CAPABILITY_BY_TOOL[call["name"]]
            stage["allowed_capabilities"] = [capability]
            stage["stage_type"] = "verification" if capability == "VERIFY" else "analysis"
            stage["evidence_requirements"][0].update(tool=call["name"], arguments=call["arguments"])
            return contract

        async def run_call(self, call, **kwargs):
            return await self.run_v6(self.contract(call), responses=[
                planner.tool(call), h.legacy.FakeResponse("Finished")], **kwargs)

        def outcome(self, run_id):
            return next(r for r in store.list_run_records(self.workspace, run_id)
                        if r["event"] == "tool_finished")

        def damage(self, run_id, kind):
            item = self.outcome(run_id)
            index = store.run_component_path(self.workspace, run_id, "records.idx.jsonl")
            stream = store.run_component_path(self.workspace, run_id, item["stream"])
            if kind in {"missing", "duplicate", "locator", "wrong_event", "wrong_source"}:
                entries = store.list_run_records(self.workspace, run_id)
                entry = next(e for e in entries if e["record_id"] == item["record_id"])
                if kind == "missing":
                    entries.remove(entry)
                elif kind == "duplicate":
                    entries.append(copy.deepcopy(entry))
                elif kind == "locator":
                    entry["offset"] = -1
                elif kind == "wrong_event":
                    entry["event"] = "tool_started"
                else:
                    entry["source"] = "EXECUTOR"
                index.write_text("".join(json.dumps(e) + "\n" for e in entries), encoding="utf-8")
            elif kind == "partial":
                stream.write_bytes(stream.read_bytes()[:item["offset"] + item["length"] - 1])
            elif kind == "corrupt":
                raw = stream.read_bytes()
                self.assertIn(b"complete", raw[item["offset"]:])
                stream.write_bytes(raw[:item["offset"]] + raw[item["offset"]:].replace(b"complete", b"tampered"))
            elif kind == "deleted":
                stream.unlink()

        def damage_terminal_record(self, run_id, event_type, kind):
            entries = store.list_run_records(self.workspace, run_id)
            item = next(r for r in reversed(entries) if r["event"] == event_type)
            index = store.run_component_path(self.workspace, run_id, "records.idx.jsonl")
            if kind == "missing":
                entries.remove(item)
                index.write_text("".join(json.dumps(e) + "\n" for e in entries), encoding="utf-8")
            else:
                stream = store.run_component_path(self.workspace, run_id, item["stream"])
                raw = stream.read_bytes()
                start, end = item["offset"], item["offset"] + item["length"]
                # Still parseable JSON, still the same length: the original ack
                # must detect corruption independently of optional projections.
                changed = raw[start:end].replace(b'"event":', b'"Event":', 1)
                self.assertNotEqual(changed, raw[start:end])
                stream.write_bytes(raw[:start] + changed + raw[end:])

        def terminal_observation(self, label, result, audit, client, injections):
            self.capture(result, audit)
            h._OBSERVATIONS[self.id() + ":" + label] = h._OBSERVATIONS.pop(self.id())
            terminals = [e for e in self.events if e["event"] == "run_finished"]
            return {"case": label, "result": result, "last_status": terminals[-1]["status"],
                    "callbacks": len(injections), "success_events": len(self.success_events()),
                    "dredd": audit.await_count, "executor": client.post_count}

        def assert_terminal_blocked(self, observations):
            for row in observations:
                with self.subTest(case=row["case"]):
                    self.assertEqual(row["callbacks"], 1, "fault must fire once, without retries")
                    self.assertIn("RUN STATUS: BLOCKED", row["result"])
                    self.assertEqual(row["last_status"], "BLOCKED")
                    self.assertEqual(row["success_events"], 1, "callback saw the provisional SUCCESS")
                    self.assertEqual(row["dredd"], int(row["case"].endswith("audit=True")))
                    self.assertEqual(row["executor"], 2, "terminal fault must not replay Executor")

        async def test_terminal_callback_outcome_damage_cannot_return_success(self):
            observations = []
            for enabled in (True, False):
                for kind in ("missing", "duplicate", "locator", "wrong_event", "wrong_source", "partial", "corrupt", "deleted"):
                    (self.workspace / "result.md").write_text("complete", encoding="utf-8")
                    injections = []
                    def fault(event):
                        if event["event"] == "run_finished" and event.get("status") == "SUCCESS":
                            injections.append(kind)
                            self.damage(event["run_id"], kind)
                    self.watch(fault)
                    result, audit, client = await self.run_v6(h.recovery.read_contract(),
                        final_audit_enabled=enabled, responses=[h.recovery.read_response(), h.legacy.FakeResponse("Finished")])
                    observations.append(self.terminal_observation(f"{kind},audit={enabled}", result, audit, client, injections))
            self.assert_terminal_blocked(observations)

        async def test_terminal_callback_certification_damage_cannot_return_success(self):
            observations = []
            for enabled in (True, False):
                for event_type in (("final_audit_passed", "run_finished") if enabled else ("run_finished",)):
                    for kind in ("missing", "corrupt"):
                        (self.workspace / "result.md").write_text("complete", encoding="utf-8")
                        injections = []
                        def fault(event):
                            if event["event"] == "run_finished" and event.get("status") == "SUCCESS":
                                injections.append(kind)
                                self.damage_terminal_record(event["run_id"], event_type, kind)
                        self.watch(fault)
                        result, audit, client = await self.run_v6(h.recovery.read_contract(),
                            final_audit_enabled=enabled, responses=[h.recovery.read_response(), h.legacy.FakeResponse("Finished")])
                        observations.append(self.terminal_observation(f"{event_type}:{kind},audit={enabled}", result, audit, client, injections))
            self.assert_terminal_blocked(observations)

        async def test_terminal_callback_dependency_drift_cannot_return_success(self):
            observations = []
            for enabled in (True, False):
                for kind in ("read", "deleted_read", "verify", "directory", "compile", "compile_secondary", "persistence"):
                    target = self.workspace / "result.md"
                    target.write_text("complete", encoding="utf-8")
                    folder = self.workspace / "folder"
                    folder.mkdir(exist_ok=True)
                    marker = folder / "new.md"
                    marker.unlink(missing_ok=True)
                    dependency = self.workspace / "dependency.py"
                    dependency.write_text("x = 1", encoding="utf-8")
                    if kind == "persistence":
                        target.unlink()
                        initial, call = planner.plan(), planner.write()
                    else:
                        call = {"read": {"name": "read_file", "arguments": {"path": "result.md"}},
                                "deleted_read": {"name": "read_file", "arguments": {"path": "result.md"}},
                                "verify": {"name": "verify_file_content", "arguments": {"path": "result.md", "kind": "equals", "value": "complete"}},
                                "directory": {"name": "list_dir", "arguments": {"path": "folder"}},
                                "compile": {"name": "python_compile", "arguments": {"paths": ["result.md"]}},
                                "compile_secondary": {"name": "python_compile", "arguments": {"paths": ["result.md", "dependency.py"]}}}[kind]
                        initial = self.contract(call)
                    injections = []
                    def fault(event):
                        if event["event"] == "run_finished" and event.get("status") == "SUCCESS":
                            injections.append(kind)
                            if kind == "directory":
                                marker.write_text("appeared", encoding="utf-8")
                            elif kind == "deleted_read":
                                target.unlink()
                            elif kind == "compile_secondary":
                                dependency.write_text("x = (", encoding="utf-8")
                            else:
                                target.write_text("changed-after-validation", encoding="utf-8")
                    self.watch(fault)
                    fake_compile = {"ok": True, "paths": call["arguments"].get("paths", []), "exit_code": 0, "stdout": "", "stderr": ""}
                    patches = (patch.object(server, "_agent_python_compile", return_value=fake_compile),) if kind.startswith("compile") else ()
                    result, audit, client = await self.run_v6(initial, final_audit_enabled=enabled,
                        responses=[planner.tool(call), h.legacy.FakeResponse("Finished")], extra_patches=patches)
                    observations.append(self.terminal_observation(f"{kind},audit={enabled}", result, audit, client, injections))
            self.assert_terminal_blocked(observations)

        async def test_terminal_callback_mutation_then_exception_cannot_return_success(self):
            observations = []
            for enabled in (True, False):
                target = self.workspace / "result.md"
                target.write_text("complete", encoding="utf-8")
                injections = []
                class Events(list):
                    def append(events, event):
                        super().append(copy.deepcopy(event))
                        if event["event"] == "run_finished" and event.get("status") == "SUCCESS":
                            injections.append(True)
                            target.write_text("changed-before-exception", encoding="utf-8")
                            raise RuntimeError("optional observer failed after mutation")
                    def __deepcopy__(events, memo):
                        return copy.deepcopy(list(events), memo)
                self.events = Events()
                result, audit, client = await self.run_v6(h.recovery.read_contract(), final_audit_enabled=enabled,
                    responses=[h.recovery.read_response(), h.legacy.FakeResponse("Finished")])
                observations.append(self.terminal_observation(f"raise,audit={enabled}", result, audit, client, injections))
            self.assert_terminal_blocked(observations)

        async def test_terminal_callback_exception_only_remains_optional(self):
            for enabled in (True, False):
                with self.subTest(audit=enabled):
                    (self.workspace / "result.md").write_text("complete", encoding="utf-8")
                    injections = []
                    class Events(list):
                        def append(events, event):
                            super().append(copy.deepcopy(event))
                            if event["event"] == "run_finished" and event.get("status") == "SUCCESS":
                                injections.append(True)
                                event["status"] = "spoofed"
                                raise RuntimeError("optional observer only")
                        def __deepcopy__(events, memo):
                            return copy.deepcopy(list(events), memo)
                    self.events = Events()
                    result, audit, client = await self.run_v6(h.recovery.read_contract(), final_audit_enabled=enabled,
                        responses=[h.recovery.read_response(), h.legacy.FakeResponse("Finished")])
                    self.terminal_observation(f"optional,audit={enabled}", result, audit, client, injections)
                    self.assertEqual(result, "Finished")
                    self.assertEqual(injections, [True])
                    self.assertEqual(audit.await_count, int(enabled))
                    self.assertEqual(len(self.success_events()), 1)
                    run_id = self.events[-1]["run_id"]
                    terminal = next(r for r in reversed(store.list_run_records(self.workspace, run_id)) if r["event"] == "run_finished")
                    self.assertEqual(store.validate_run_record(self.workspace, run_id, terminal, event="run_finished")["payload"]["status"], "SUCCESS")

        async def test_terminal_callback_interruption_propagates_with_blocked_terminal(self):
            import asyncio
            class TerminalInterrupt(BaseException):
                pass
            for enabled in (True, False):
                for exception in (asyncio.CancelledError("terminal cancelled"), TerminalInterrupt("terminal interrupted")):
                    with self.subTest(audit=enabled, exception=type(exception).__name__):
                        (self.workspace / "result.md").write_text("complete", encoding="utf-8")
                        injections = []
                        def interrupt(event):
                            if event["event"] == "run_finished" and event.get("status") == "SUCCESS":
                                injections.append(True)
                                raise exception
                        self.watch(interrupt)
                        with self.assertRaises(type(exception)) as caught:
                            await self.run_v6(h.recovery.read_contract(), final_audit_enabled=enabled,
                                responses=[h.recovery.read_response(), h.legacy.FakeResponse("Finished")])
                        self.assertIs(caught.exception, exception)
                        self.assertEqual(injections, [True])
                        self.assertEqual(self.last_verifier.await_count, int(enabled))
                        self.assertEqual(self.events[-1]["status"], "BLOCKED")
                        self.assertEqual(self.events[-1]["reason"], "terminal_callback_interrupted")
                        run_id = self.events[-1]["run_id"]
                        terminal = next(r for r in reversed(store.list_run_records(self.workspace, run_id)) if r["event"] == "run_finished")
                        self.assertEqual(store.validate_run_record(self.workspace, run_id, terminal, event="run_finished")["payload"]["status"], "BLOCKED")
                        self.terminal_observation(f"{type(exception).__name__},audit={enabled}", "INTERRUPTED", self.last_verifier, self.last_client, injections)

        async def test_terminal_callback_legacy_file_and_record_damage_cannot_return_success(self):
            observations = []
            for enabled in (True, False):
                for kind in ("source", "outcome", "terminal"):
                    target = self.workspace / "result.md"
                    target.write_text("complete", encoding="utf-8")
                    injections = []
                    def fault(event):
                        if event["event"] == "run_finished" and event.get("status") == "SUCCESS":
                            injections.append(True)
                            if kind == "source":
                                target.write_text("changed", encoding="utf-8")
                            elif kind == "outcome":
                                self.damage(event["run_id"], "missing")
                            else:
                                self.damage_terminal_record(event["run_id"], "run_finished", "missing")
                    self.watch(fault)
                    result, audit, client = await h.legacy.FinalAuditRuntimeTests.run_case(self,
                        h.legacy.verifier_result(), final_audit_enabled=enabled,
                        fake_client=h.legacy.FakeClient([h.recovery.read_response(), h.legacy.FakeResponse("Finished")]))
                    observations.append(self.terminal_observation(f"legacy:{kind},audit={enabled}", result, audit, client, injections))
            self.assert_terminal_blocked(observations)

        async def test_terminal_callback_semantic_and_unrelated_changes_allow_success(self):
            for enabled in (True, False):
                for kind in ("exists", "unrelated"):
                    with self.subTest(audit=enabled, change=kind):
                        target = self.workspace / "result.md"
                        target.write_text("complete", encoding="utf-8")
                        call = ({"name": "verify_file_content", "arguments": {"path": "result.md", "kind": "exists", "value": ""}}
                                if kind == "exists" else {"name": "read_file", "arguments": {"path": "result.md"}})
                        injections = []
                        def fault(event):
                            if event["event"] == "run_finished" and event.get("status") == "SUCCESS":
                                injections.append(True)
                                (target if kind == "exists" else self.workspace / "unrelated.md").write_text("new content", encoding="utf-8")
                        self.watch(fault)
                        result, audit, client = await self.run_call(call, final_audit_enabled=enabled)
                        self.terminal_observation(f"{kind},audit={enabled}", result, audit, client, injections)
                        self.assertEqual(result, "Finished")
                        self.assertEqual(injections, [True])
                        self.assertEqual(audit.await_count, int(enabled))
                        self.assertEqual(len(self.success_events()), 1)

        async def test_terminal_callback_stage_state_damage_cannot_return_success(self):
            observations = []
            lifecycle_class = server.TaskLifecycle
            for enabled in (True, False):
                (self.workspace / "result.md").write_text("complete", encoding="utf-8")
                controllers, injections = [], []
                def controller(*args, **kwargs):
                    instance = lifecycle_class(*args, **kwargs)
                    controllers.append(instance)
                    return instance
                def fault(event):
                    if event["event"] == "run_finished" and event.get("status") == "SUCCESS":
                        injections.append(True)
                        controllers[0].state["stage_states"]["read_stage"]["status"] = "PENDING"
                self.watch(fault)
                result, audit, client = await self.run_v6(h.recovery.read_contract(), final_audit_enabled=enabled,
                    responses=[h.recovery.read_response(), h.legacy.FakeResponse("Finished")],
                    extra_patches=(patch.object(server, "TaskLifecycle", side_effect=controller),))
                observations.append(self.terminal_observation(f"stage,audit={enabled}", result, audit, client, injections))
            self.assert_terminal_blocked(observations)

        async def test_terminal_callback_damage_and_blocked_append_failure_still_fail_closed(self):
            observations = []
            append = audit_storage.append_run_record
            for enabled in (True, False):
                (self.workspace / "result.md").write_text("complete", encoding="utf-8")
                injections, failed_writes = [], []
                def fault(event):
                    if event["event"] == "run_finished" and event.get("status") == "SUCCESS":
                        injections.append(True)
                        self.damage(event["run_id"], "missing")
                def unavailable(*args, **kwargs):
                    if kwargs["event"] == "run_finished" and kwargs["payload"].get("status") == "BLOCKED":
                        failed_writes.append(True)
                        raise OSError("corrective terminal record unavailable")
                    return append(*args, **kwargs)
                self.watch(fault)
                result, audit, client = await self.run_v6(h.recovery.read_contract(), final_audit_enabled=enabled,
                    responses=[h.recovery.read_response(), h.legacy.FakeResponse("Finished")],
                    extra_patches=(patch.object(audit_storage, "append_run_record", side_effect=unavailable),))
                self.assertEqual(failed_writes, [True])
                observations.append(self.terminal_observation(f"blocked_write,audit={enabled}", result, audit, client, injections))
            self.assert_terminal_blocked(observations)

        async def test_terminal_boundary_rechecks_events_after_the_callers_freshness_gate(self):
            for enabled, event_type in ((True, "planner_session_completed"), (False, "planner_session_completed"), (False, "final_audit_skipped")):
                with self.subTest(audit=enabled, event=event_type):
                    target = self.workspace / "result.md"
                    target.write_text("complete", encoding="utf-8")
                    injections = []
                    def fault(event):
                        if event["event"] == event_type:
                            injections.append(True)
                            target.write_text("changed-before-emit", encoding="utf-8")
                    self.watch(fault)
                    result, audit, client = await self.run_v6(h.recovery.read_contract(), final_audit_enabled=enabled,
                        responses=[h.recovery.read_response(), h.legacy.FakeResponse("Finished")])
                    self.terminal_observation(f"{event_type},audit={enabled}", result, audit, client, injections)
                    self.assertEqual(injections, [True])
                    self.assertIn("RUN STATUS: BLOCKED", result)
                    self.assertEqual(self.events[-1]["status"], "BLOCKED")
                    self.assertFalse(self.success_events())
                    self.assertEqual(audit.await_count, int(enabled))
                    self.assertEqual(client.post_count, 2)

        async def test_range_find_and_directory_races_never_relabel_old_observation(self):
            cases = [
                {"name": "read_file_range", "arguments": {"path": "result.md", "start_line": 1, "end_line": 1}},
                {"name": "find_text", "arguments": {"path": "result.md", "text": "old"}},
                {"name": "list_dir", "arguments": {"path": "folder"}},
            ]
            execute = server._execute_agent_function
            for call in cases:
                with self.subTest(tool=call["name"]):
                    self.events.clear()
                    target = self.workspace / "result.md"
                    target.write_text("old\nsecond", encoding="utf-8")
                    folder = self.workspace / "folder"
                    folder.mkdir(exist_ok=True)
                    marker = folder / "new.md"
                    marker.unlink(missing_ok=True)
                    def race(*args, **kwargs):
                        result = execute(*args, **kwargs)
                        if call["name"] == "list_dir":
                            marker.write_text("new", encoding="utf-8")
                        else:
                            target.write_text("new\nsecond", encoding="utf-8")
                        return result
                    result, audit, _ = await self.run_call(call, tool_limit=1,
                        extra_patches=(patch.object(server, "_execute_agent_function", side_effect=race),))
                    self.blocked(result, audit)
                    self.assertTrue(any(e["event"] == "tool_evidence_stale" for e in self.events))

        async def test_exists_and_absent_races_require_a_new_observation(self):
            execute = server._execute_agent_function
            target = self.workspace / "result.md"
            for kind in ("exists", "absent"):
                with self.subTest(kind=kind):
                    self.events.clear()
                    if kind == "exists":
                        target.write_text("present", encoding="utf-8")
                    else:
                        target.unlink(missing_ok=True)
                    call = {"name": "verify_file_content", "arguments": {"path": "result.md", "kind": kind, "value": ""}}
                    def race(*args, **kwargs):
                        result = execute(*args, **kwargs)
                        if kind == "exists":
                            target.unlink()
                        else:
                            target.write_text("appeared", encoding="utf-8")
                        return result
                    result, audit, _ = await self.run_call(call, tool_limit=1,
                        extra_patches=(patch.object(server, "_execute_agent_function", side_effect=race),))
                    self.blocked(result, audit)
                    self.assertTrue(any(e["event"] == "tool_evidence_stale" for e in self.events))

        async def test_exists_predicate_survives_content_only_change(self):
            target = self.workspace / "result.md"
            target.write_text("old", encoding="utf-8")
            execute = server._execute_agent_function
            def change(*args, **kwargs):
                result = execute(*args, **kwargs)
                target.write_text("new", encoding="utf-8")
                return result
            call = {"name": "verify_file_content", "arguments": {"path": "result.md", "kind": "exists", "value": ""}}
            result, audit, _ = await self.run_call(call,
                extra_patches=(patch.object(server, "_execute_agent_function", side_effect=change),))
            self.capture(result, audit)
            self.assertEqual(result, "Finished")
            self.assertEqual(audit.await_count, 1)
            self.assertEqual(len(self.success_events()), 1)

        async def test_stale_read_recovers_only_with_fresh_generation(self):
            target = self.workspace / "result.md"
            target.write_text("old", encoding="utf-8")
            execute = server._execute_agent_function
            calls = []
            def race_once(*args, **kwargs):
                result = execute(*args, **kwargs)
                calls.append(result)
                if len(calls) == 1:
                    target.write_text("fresh", encoding="utf-8")
                return result
            result, audit, _ = await self.run_v6(h.recovery.read_contract(), responses=[
                h.recovery.read_response(), h.recovery.read_response(), h.legacy.FakeResponse("Finished")],
                extra_patches=(patch.object(server, "_execute_agent_function", side_effect=race_once),))
            self.capture(result, audit)
            self.assertEqual(result, "Finished")
            self.assertEqual(len(calls), 2)
            packet = json.loads(audit.await_args.kwargs["verification_context"])
            facts = packet["authoritative_tool_evidence"]
            self.assertEqual([f["material_preview"]["content"] for f in facts], ["old", "fresh"])
            self.assertGreater(facts[1]["evidence_generation"], facts[0]["evidence_generation"])
            self.assertNotEqual(facts[1]["source_record_id"], facts[0]["source_record_id"])
            self.assertEqual(len(self.success_events()), 1)

        async def test_stale_equals_can_recover_without_reusing_old_pass(self):
            target = self.workspace / "result.md"
            target.write_text("done\n", encoding="utf-8", newline="")
            execute = server._execute_agent_function
            attempts = []
            def race(*args, **kwargs):
                if attempts:
                    target.write_text("done\n", encoding="utf-8", newline="")
                result = execute(*args, **kwargs)
                attempts.append(result)
                if len(attempts) == 1:
                    target.write_text("WRONG", encoding="utf-8")
                return result
            call = {"name": "verify_file_content", "arguments": {"path": "result.md", "kind": "equals", "value": "done\n"}}
            result, audit, _ = await self.run_v6(self.contract(call), responses=[
                planner.tool(call), planner.tool(call), h.legacy.FakeResponse("Finished")],
                extra_patches=(patch.object(server, "_execute_agent_function", side_effect=race),))
            self.capture(result, audit)
            self.assertEqual(result, "Finished")
            facts = json.loads(audit.await_args.kwargs["verification_context"])["authoritative_tool_evidence"]
            self.assertEqual(len(facts), 2)
            self.assertEqual(facts[0]["observed_state_sha256"], facts[1]["observed_state_sha256"])
            self.assertGreater(facts[1]["evidence_generation"], facts[0]["evidence_generation"])

        async def test_fake_compile_cannot_certify_changed_dependencies(self):
            target = self.workspace / "sample.py"
            target.write_text("x = 1", encoding="utf-8")
            call = {"name": "python_compile", "arguments": {"paths": ["sample.py"]}}
            def compile_fake(*_args, **_kwargs):
                target.write_text("x = (", encoding="utf-8")
                return {"ok": True, "paths": ["sample.py"], "exit_code": 0, "stdout": "", "stderr": ""}
            result, audit, _ = await self.run_call(call, tool_limit=1,
                extra_patches=(patch.object(server, "_agent_python_compile", side_effect=compile_fake),))
            self.blocked(result, audit)

        async def test_missing_corrupt_partial_or_wrong_record_blocks_before_dredd(self):
            for kind in ("missing", "duplicate", "locator", "wrong_event", "wrong_source", "partial", "corrupt", "deleted"):
                with self.subTest(kind=kind):
                    self.events = []
                    (self.workspace / "result.md").write_text("complete", encoding="utf-8")
                    def damage(event):
                        if event["event"] == "tool_finished":
                            self.damage(event["run_id"], kind)
                    self.watch(damage)
                    result, audit, _ = await self.read_case()
                    self.blocked(result, audit)
                    self.assertIn("mandatory_evidence_unavailable", result)

        async def test_corruption_during_packet_collection_never_reaches_dredd(self):
            (self.workspace / "result.md").write_text("complete", encoding="utf-8")
            collect = server._collect_final_audit_evidence
            def corrupt(**kwargs):
                packet = collect(**kwargs)
                self.damage(kwargs["run_id"], "corrupt")
                return packet
            result, audit, _ = await self.read_case(extra_patches=(
                patch.object(server, "_collect_final_audit_evidence", side_effect=corrupt),))
            self.blocked(result, audit)

        async def test_corruption_during_final_audit_cannot_emit_pass_or_success(self):
            (self.workspace / "result.md").write_text("complete", encoding="utf-8")
            async def corrupt(**kwargs):
                self.damage(kwargs["task_id"], "corrupt")
                return h.legacy.verifier_result()
            result, _, _ = await self.read_case(extra_patches=(
                patch.object(server, "run_verifier_check", side_effect=corrupt),))
            self.assertIn("BLOCKED", result)
            self.assertFalse(self.success_events())
            self.assertFalse(any(e["event"] == "final_audit_passed" for e in self.events))

        async def test_deleted_outcome_after_audit_pass_is_rechecked_before_success(self):
            (self.workspace / "result.md").write_text("complete", encoding="utf-8")
            self.watch(lambda event: self.damage(event["run_id"], "missing")
                       if event["event"] == "final_audit_passed" else None)
            result, audit, _ = await self.read_case()
            self.blocked(result, audit, sends=1)

        async def test_required_intent_append_failure_prevents_physical_mutation(self):
            append = audit_storage.append_run_record
            def fail(*args, **kwargs):
                if kwargs["event"] == "tool_started":
                    raise OSError("intent unavailable")
                return append(*args, **kwargs)
            result, audit, _ = await self.run_v6(responses=[planner.tool(planner.write())],
                extra_patches=(patch.object(audit_storage, "append_run_record", side_effect=fail),))
            self.blocked(result, audit)
            self.assertFalse((self.workspace / "result.md").exists())

        async def test_outcome_failure_after_mutation_records_unknown_without_retry(self):
            append = audit_storage.append_run_record
            write = server._agent_write_file
            writes = []
            def physical_write(*args, **kwargs):
                result = write(*args, **kwargs)
                writes.append(result)
                return result
            def fail(*args, **kwargs):
                if kwargs["event"] == "tool_finished":
                    raise OSError("outcome unavailable")
                return append(*args, **kwargs)
            result, audit, _ = await self.run_v6(responses=[planner.tool(planner.write())] * 3,
                extra_patches=(patch.object(audit_storage, "append_run_record", side_effect=fail),
                               patch.object(server, "_agent_write_file", side_effect=physical_write)))
            self.blocked(result, audit)
            self.assertEqual(len(writes), 1)
            self.assertEqual((self.workspace / "result.md").read_text(encoding="utf-8"), "done")
            state = json.loads(next((self.runtime / "logs" / "task_plans").glob("*.json")).read_text(encoding="utf-8"))
            candidate = next(iter(state["candidates"].values()))
            self.assertEqual(candidate["outcome"], "UNKNOWN")
            self.assertTrue(candidate["executed"])
            self.assertFalse(any(e["event"] == "persistence_satisfied" for e in self.events))
            self.events = []
            with patch.object(server, "_agent_write_file", side_effect=AssertionError("unexpected replay")):
                result2, audit2, _ = await self.read_case()
            self.assertEqual(result2, "Finished")
            self.assertEqual(audit2.await_count, 1)
            self.assertEqual(len(writes), 1)

        async def test_projection_summary_and_diagnostic_failures_do_not_veto_valid_outcomes(self):
            observe = server.AuditThreadRecorder.observe
            for failure in ("projection", "summary", "diagnostic"):
                with self.subTest(failure=failure):
                    self.events = []
                    (self.workspace / "result.md").write_text("complete", encoding="utf-8")
                    if failure == "diagnostic":
                        def diagnostic(recorder, event):
                            if event["event"].startswith("executor_diagnostic"):
                                raise OSError("optional diagnostic")
                            return observe(recorder, event)
                        fault = patch.object(server.AuditThreadRecorder, "observe", diagnostic)
                    else:
                        method = "_project_event" if failure == "projection" else "_update_summary"
                        fault = patch.object(server.AuditThreadRecorder, method, side_effect=OSError("optional projection"))
                    result, audit, _ = await self.read_case(extra_patches=(fault,))
                    self.capture(result, audit)
                    self.assertEqual(result, "Finished")
                    self.assertEqual(audit.await_count, 1)
                    self.assertEqual(len(self.success_events()), 1)

        async def test_final_attestation_and_terminal_write_failures_cannot_publish_success(self):
            append = audit_storage.append_run_record
            for event_type in ("final_audit_passed", "run_finished"):
                with self.subTest(event=event_type):
                    self.events = []
                    (self.workspace / "result.md").write_text("complete", encoding="utf-8")
                    def fail(*args, **kwargs):
                        if kwargs["event"] == event_type and (event_type != "run_finished" or kwargs["payload"].get("status") == "SUCCESS"):
                            raise OSError("terminal proof unavailable")
                        return append(*args, **kwargs)
                    result, audit, _ = await self.read_case(extra_patches=(
                        patch.object(audit_storage, "append_run_record", side_effect=fail),))
                    self.blocked(result, audit, sends=1)

        async def test_partial_writes_index_append_and_fsync_failures_never_replay_mutation(self):
            append = audit_storage.append_run_record
            path_open = Path.open
            fsync = store.os.fsync
            write = server._agent_write_file
            for fault in ("outcome_short", "index_short", "index_open", "outcome_fsync", "index_fsync"):
                with self.subTest(fault=fault):
                    self.events = []
                    (self.workspace / "result.md").unlink(missing_ok=True)
                    armed = False
                    injections, writes, syncs = [], [], []
                    class ShortWriter:
                        def __init__(proxy, stream):
                            proxy.stream = stream
                        def __enter__(proxy):
                            return proxy
                        def __exit__(proxy, *args):
                            return proxy.stream.__exit__(*args)
                        def __getattr__(proxy, name):
                            return getattr(proxy.stream, name)
                        def write(proxy, data):
                            injections.append(fault)
                            return proxy.stream.write(data[:len(data)//2])
                    def opened(path, mode="r", *args, **kwargs):
                        if armed and mode == "ab":
                            if fault == "index_open" and path.name == "records.idx.jsonl":
                                injections.append(fault)
                                raise OSError("index append unavailable")
                            if ((fault == "outcome_short" and path.name == "server.jsonl")
                                    or (fault == "index_short" and path.name == "records.idx.jsonl")):
                                return ShortWriter(path_open(path, mode, *args, **kwargs))
                        return path_open(path, mode, *args, **kwargs)
                    def synced(fd):
                        if armed:
                            syncs.append(fd)
                            if (fault == "outcome_fsync" and len(syncs) == 1
                                    or fault == "index_fsync" and len(syncs) == 2):
                                injections.append(fault)
                                raise OSError("fsync failed")
                        return fsync(fd)
                    def persisted(*args, **kwargs):
                        nonlocal armed
                        armed = kwargs["event"] == "tool_finished"
                        try:
                            return append(*args, **kwargs)
                        finally:
                            armed = False
                    def physical(*args, **kwargs):
                        result = write(*args, **kwargs)
                        writes.append(result)
                        return result
                    result, audit, _ = await self.run_v6(responses=[planner.tool(planner.write())] * 3,
                        extra_patches=(patch.object(Path, "open", opened),
                                       patch.object(store.os, "fsync", side_effect=synced),
                                       patch.object(audit_storage, "append_run_record", side_effect=persisted),
                                       patch.object(server, "_agent_write_file", side_effect=physical)))
                    self.blocked(result, audit)
                    self.assertEqual(injections, [fault])
                    self.assertEqual(len(writes), 1)
                    self.assertEqual((self.workspace / "result.md").read_text(encoding="utf-8"), "done")
                    run_id = next(e["run_id"] for e in self.events if e["event"] == "tool_started")
                    self.assertIn(b'tool_started', store.run_component_path(self.workspace, run_id, "server.jsonl").read_bytes())

        async def test_acknowledgement_binds_every_identity_dimension_even_with_equal_content(self):
            (self.workspace / "result.md").write_text("complete", encoding="utf-8")
            result, audit, _ = await self.read_case()
            fact = json.loads(audit.await_args.kwargs["verification_context"])["authoritative_tool_evidence"][0]
            server._validate_durable_tool_outcome(self.workspace, fact["run_id"], fact)
            changes = {"source_record_id": "other", "source_run_store_record_id": "invented",
                       "source_run_store_sha256": "0" * 64, "task_block_id": "other",
                       "run_id": "other", "plan_id": "other", "plan_version": 8,
                       "stage_id": "other", "candidate_id": "other", "evidence_generation": 9,
                       "requirement_ids": ["other"], "target_identity": ["other.md"],
                       "tool": "find_text", "capability": "VERIFY", "status": "ERROR",
                       "arguments_sha256": "0" * 64, "observed_state_sha256": "0" * 64,
                       "sequence": 100, "result": {"sha256": "0" * 64}}
            for key, value in changes.items():
                with self.subTest(identity=key):
                    different = copy.deepcopy(fact)
                    different[key] = value
                    with self.assertRaises((ValueError, KeyError)):
                        server._validate_durable_tool_outcome(self.workspace, fact["run_id"], different)
            self.capture(result, audit)

        async def test_old_indexes_remain_readable_but_cannot_downgrade_certification(self):
            (self.workspace / "result.md").write_text("complete", encoding="utf-8")
            result, audit, _ = await self.read_case()
            fact = json.loads(audit.await_args.kwargs["verification_context"])["authoritative_tool_evidence"][0]
            run_id = fact["run_id"]
            index = store.run_component_path(self.workspace, run_id, "records.idx.jsonl")
            entries = store.list_run_records(self.workspace, run_id)
            entry = next(e for e in entries if e["record_id"] == fact["source_run_store_record_id"])
            entry.pop("sha256")
            index.write_text("".join(json.dumps(e) + "\n" for e in entries), encoding="utf-8")
            self.assertIsNotNone(store.load_run_record(self.workspace, run_id, entry["record_id"]))
            server._validate_durable_tool_outcome(self.workspace, run_id, fact)
            missing_ack = copy.deepcopy(fact)
            missing_ack["source_run_store_sha256"] = None
            with self.assertRaises(ValueError):
                server._validate_durable_tool_outcome(self.workspace, run_id, missing_ack)
            stream = store.run_component_path(self.workspace, run_id, entry["stream"])
            raw = stream.read_bytes()
            # A checksum-free index must not hide even a semantic-preserving
            # whitespace change against the original byte acknowledgement.
            start, end = entry["offset"], entry["offset"] + entry["length"]
            changed = raw[start:end].replace(b'"payload":{', b'"payload": {', 1)
            entry["length"] = len(changed)
            index.write_text("".join(json.dumps(e) + "\n" for e in entries), encoding="utf-8")
            stream.write_bytes(raw[:start] + changed + raw[end:])
            self.assertIsNotNone(store.load_run_record(self.workspace, run_id, entry["record_id"]))
            with self.assertRaises(ValueError):
                server._validate_durable_tool_outcome(self.workspace, run_id, fact)

        async def test_negative_verify_is_durable_and_never_certifies_success(self):
            (self.workspace / "result.md").write_text("wrong", encoding="utf-8")
            call = {"name": "verify_file_content", "arguments": {"path": "result.md", "kind": "equals", "value": "done\n"}}
            result, audit, _ = await self.run_call(call, tool_limit=1)
            self.blocked(result, audit)
            error = next(e for e in self.events if e["event"] == "tool_error")
            records = store.list_run_records(self.workspace, error["run_id"])
            pointer = next(r for r in records if r["event"] == "tool_error")
            saved = store.validate_run_record(self.workspace, error["run_id"], pointer, event="tool_error")
            self.assertFalse(saved["payload"]["result"]["passed"])
            self.assertFalse(saved["payload"]["evidence_binding"]["result"]["verification"]["passed"])

        async def test_final_attestation_deleted_after_callback_cannot_certify_success(self):
            (self.workspace / "result.md").write_text("complete", encoding="utf-8")
            def delete_pass(event):
                if event["event"] == "final_audit_passed":
                    run_id = event["run_id"]
                    entries = store.list_run_records(self.workspace, run_id)
                    entries = [r for r in entries if r["event"] != "final_audit_passed"]
                    store.run_component_path(self.workspace, run_id, "records.idx.jsonl").write_text(
                        "".join(json.dumps(e) + "\n" for e in entries), encoding="utf-8")
            self.watch(delete_pass)
            result, audit, _ = await self.read_case()
            self.blocked(result, audit, sends=1)
            self.assertIn("mandatory_certification_unavailable", result)

        async def test_runtime_log_failure_is_optional_and_callbacks_cannot_rewrite_evidence(self):
            (self.workspace / "result.md").write_text("complete", encoding="utf-8")
            mkdir = Path.mkdir
            def failed_mkdir(path, *args, **kwargs):
                if path == self.runtime / "logs" / "runs":
                    raise OSError("decorative trace unavailable")
                return mkdir(path, *args, **kwargs)
            def rewrite(event):
                if event["event"] == "tool_finished":
                    event["result"]["content"] = "spoofed"
                    event["evidence_binding"]["stage_id"] = "spoofed"
            self.watch(rewrite)
            result, audit, _ = await self.read_case(extra_patches=(patch.object(Path, "mkdir", failed_mkdir),))
            self.capture(result, audit)
            self.assertEqual(result, "Finished")
            fact = json.loads(audit.await_args.kwargs["verification_context"])["authoritative_tool_evidence"][0]
            self.assertEqual(fact["material_preview"]["content"], "complete")
            server._validate_durable_tool_outcome(self.workspace, fact["run_id"], fact)

        async def test_disabled_audit_does_not_waive_planner_durable_outcomes(self):
            (self.workspace / "result.md").write_text("complete", encoding="utf-8")
            observe = server.AuditThreadRecorder.observe
            def lost(recorder, event):
                if event["event"] == "tool_finished":
                    raise OSError("lost outcome with final audit disabled")
                return observe(recorder, event)
            result, audit, _ = await self.run_v6(h.recovery.read_contract(),
                final_audit_enabled=False, responses=[h.recovery.read_response(), h.legacy.FakeResponse("Finished")],
                extra_patches=(patch.object(server.AuditThreadRecorder, "observe", lost),))
            self.blocked(result, audit)
            self.assertIn("mandatory_evidence_unavailable", result)

        async def test_both_roles_disabled_cannot_bypass_durable_outcomes(self):
            (self.workspace / "result.md").write_text("complete", encoding="utf-8")
            observe = server.AuditThreadRecorder.observe
            for failure in ("recorder", "outcome"):
                with self.subTest(failure=failure):
                    self.events = []
                    def lost(recorder, event):
                        if event["event"] == "tool_finished":
                            raise OSError("lost legacy outcome")
                        return observe(recorder, event)
                    fault = (patch.object(server, "AuditThreadRecorder", side_effect=OSError("legacy recorder unavailable"))
                             if failure == "recorder" else patch.object(server.AuditThreadRecorder, "observe", lost))
                    result, audit, _ = await h.legacy.FinalAuditRuntimeTests.run_case(
                        self, h.legacy.verifier_result(), final_audit_enabled=False,
                        fake_client=h.legacy.FakeClient([h.recovery.read_response(), h.legacy.FakeResponse("Finished")]),
                        extra_patches=(fault,))
                    self.blocked(result, audit)

        async def test_both_roles_disabled_still_allow_success_with_durable_outcome(self):
            (self.workspace / "result.md").write_text("complete", encoding="utf-8")
            result, audit, _ = await h.legacy.FinalAuditRuntimeTests.run_case(
                self, h.legacy.verifier_result(), final_audit_enabled=False,
                fake_client=h.legacy.FakeClient([h.recovery.read_response(), h.legacy.FakeResponse("Finished")]))
            self.capture(result, audit)
            self.assertEqual(result, "Finished")
            audit.assert_not_awaited()
            self.assertEqual(len(self.success_events()), 1)
            outcome = next(e for e in self.events if e["event"] == "tool_finished")
            item = self.outcome(outcome["run_id"])
            saved = store.validate_run_record(self.workspace, outcome["run_id"], item, event="tool_finished")
            self.assertEqual(saved["payload"]["evidence_binding"]["observed_state_sha256"],
                server._tool_observation_fingerprint("read_file", {"path": "result.md"}, saved["payload"]["result"]))

    return unittest.defaultTestLoader.loadTestsFromTestCase(RepairBoundaryTests)
