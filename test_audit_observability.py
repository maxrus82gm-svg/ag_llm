import asyncio
import copy
import json
import queue
import threading
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import audit_storage
import context_storage
import server
import ui_state
import ultra_ui


class AuditStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name) / "workspace"
        self.workspace.mkdir()
        self.workspace_id = "ws_test"
        self.chat_id = "chat_test"
        self.run_id = "run_test"
        self.recorder = audit_storage.AuditThreadRecorder(
            self.workspace, self.workspace_id, self.chat_id, self.run_id
        )

    def issue(self, attempt=1):
        self.recorder.observe({
            "event": "final_audit_failed", "audit_attempt": attempt,
            "verifier_run_id": f"ver_{attempt}", "reason": "Wrong result",
            "violations": ["Missing file", "Incorrect line"],
            "required_action": "Correct the file",
        })

    def load(self):
        return audit_storage.load_audit_thread(
            self.workspace, self.workspace_id, self.chat_id, self.run_id
        )

    def test_list_chat_threads_links_task_id_and_keeps_legacy_readable(self):
        task_id = context_storage.new_task_block_id()
        linked = audit_storage.AuditThreadRecorder(
            self.workspace, self.workspace_id, self.chat_id, "run_linked", task_id
        )
        threads = audit_storage.list_chat_audit_threads(
            self.workspace, self.workspace_id, self.chat_id
        )
        self.assertEqual([item["run_id"] for item in threads], ["run_linked", "run_test"])
        self.assertEqual(threads[0]["task_block_id"], task_id)
        self.assertIsNone(threads[1]["task_block_id"])
        self.assertNotEqual(task_id, linked.thread["run_id"])
        other_chat = "chat_other"
        self.assertEqual(audit_storage.list_chat_audit_threads(
            self.workspace, self.workspace_id, other_chat
        ), [])
        self.assertFalse((self.workspace / ".ultra" / "audit" / other_chat).exists())
        with self.assertRaises(ValueError):
            audit_storage.list_chat_audit_threads(self.workspace, "wrong_workspace", self.chat_id)
        # Older records without this key remain readable and are not rewritten.
        legacy_path = audit_storage.audit_thread_path(self.workspace, self.chat_id, self.run_id)
        legacy = json.loads(legacy_path.read_text(encoding="utf-8"))
        legacy.pop("task_block_id")
        legacy_path.write_text(json.dumps(legacy), encoding="utf-8")
        self.assertNotIn("task_block_id", audit_storage.load_audit_thread(
            self.workspace, self.workspace_id, self.chat_id, self.run_id
        ))

    def test_issue_diagnostic_tool_activity_pass_and_reload(self):
        self.issue()
        self.recorder.observe({"event": "audit_diagnostic_question", "text": "Why?"})
        self.recorder.observe({"event": "audit_diagnostic_answer", "text": "I assumed the file existed."})
        self.recorder.observe({
            "event": "tool_finished", "tool_sequence": 3,
            "function": "replace_text", "arguments": {
                "path": "notes.txt", "old_text": "SECRET" * 500,
            },
        })
        self.recorder.observe({"event": "final_audit_passed"})
        self.recorder.observe({"event": "run_finished", "status": "SUCCESS"})
        saved = self.load()
        issue = saved["issues"][0]
        self.assertEqual(issue["reason"], "Wrong result")
        self.assertEqual(issue["violations"], ["Missing file", "Incorrect line"])
        self.assertEqual(issue["required_action"], "Correct the file")
        self.assertEqual(issue["diagnostic_answer"], "I assumed the file existed.")
        self.assertEqual(issue["correction_activity"], [{
            "tool_sequence": 3, "tool_name": "replace_text",
            "path": "notes.txt", "status": "OK",
        }])
        self.assertEqual(issue["result"], "RESOLVED")
        self.assertEqual(saved["final_audit"], "PASS")
        self.assertNotIn("SECRET", json.dumps(saved))
        # A fresh loader after the recorder is gone reads the portable file.
        self.assertTrue(audit_storage.audit_thread_path(self.workspace, self.chat_id, self.run_id).is_file())

    def test_consistency_lifecycle_persists_and_renders_without_changing_final_issues(self):
        self.recorder.observe({"event": "execution_consistency_detected", "attempt": 1,
                               "mutation_intent": {"mutation_intent": "LIKELY_MUTATION", "reasons": ["action:update"]},
                               "reason": "likely_mutation_without_run_mutation"})
        self.recorder.observe({"event": "execution_consistency_feedback_delivered", "attempt": 1})
        self.recorder.observe({"event": "execution_consistency_verifier_started", "attempt": 2})
        self.recorder.observe({"event": "execution_consistency_verifier_failed", "attempt": 2,
                               "verifier_run_id": "ver_consistency", "reason": "No observed work",
                               "violations": ["No tool calls"], "required_action": "Read target"})
        self.recorder.observe({"event": "execution_consistency_correction_started", "attempt": 2})
        self.recorder.observe({"event": "tool_finished", "tool_sequence": 1,
                               "function": "write_file", "arguments": {"path": "notes.txt"}})
        self.recorder.observe({"event": "execution_consistency_resolved", "decision": "MUTATION_OBSERVED"})
        self.recorder.observe({"event": "final_audit_passed"})
        saved = self.load()
        self.assertEqual(saved["execution_consistency"]["status"], "RESOLVED")
        self.assertEqual(saved["execution_consistency"]["correction_activity"][0]["tool_name"], "write_file")
        self.assertEqual(saved["issues"], [])
        rendered = "".join(text for _tag, text in ultra_ui.UltraApp._audit_segments(saved, self.run_id))
        self.assertIn("EXECUTION CONSISTENCY", rendered)
        self.assertIn("повторная попытка", rendered)
        self.assertIn("DREDD CONSISTENCY", rendered)
        self.assertIn("No observed work", rendered)
        self.assertIn("CONSISTENCY: RESOLVED", rendered)

    def test_consistency_terminal_is_unresolved_and_legacy_panel_stays_clean(self):
        legacy = self.load()
        self.assertNotIn("EXECUTION CONSISTENCY", "".join(
            text for _tag, text in ultra_ui.UltraApp._audit_segments(legacy, self.run_id)))
        self.recorder.observe({"event": "execution_consistency_detected"})
        self.recorder.observe({"event": "execution_consistency_terminal",
                               "reason": "execution_consistency_unresolved"})
        self.recorder.observe({"event": "run_failed", "reason": "execution_consistency_unresolved"})
        saved = self.load()
        self.assertEqual(saved["execution_consistency"]["status"], "UNRESOLVED")
        self.assertEqual(saved["final_audit"], "NOT_RUN")

    def test_permission_lifecycle_is_persisted_and_rendered(self):
        for number, tool in ((1, "replace_text"), (2, "insert_after")):
            self.recorder.observe({"event": "permission_denied", "capability": "WRITE",
                                   "attempt": number, "function": tool,
                                   "arguments": {"path": "notes.txt"}})
        self.recorder.observe({"event": "permission_review_started", "capability": "WRITE",
                               "scope": "."})
        self.recorder.observe({"event": "permission_review_passed", "capability": "WRITE",
                               "verifier_run_id": "ver_permission", "verifier_reason": "Edit required",
                               "required_action": "Ask user"})
        self.recorder.observe({"event": "permission_user_prompted", "capability": "WRITE"})
        self.recorder.observe({"event": "permission_user_denied", "capability": "WRITE",
                               "user_decision": "DENIED"})
        self.recorder.observe({"event": "permission_escalation_terminal",
                               "capability": "WRITE", "reason": "permission_not_granted"})
        self.recorder.observe({"event": "run_finished", "status": "BLOCKED"})
        saved = self.load()
        permission = saved["permission_escalation"]
        self.assertEqual(permission["status"], "BLOCKED")
        self.assertEqual(permission["user_decision"], "DENIED")
        self.assertEqual([a["tool"] for a in permission["attempts"]],
                         ["replace_text", "insert_after"])
        segments = ultra_ui.UltraApp._audit_segments(saved, self.run_id)
        rendered = "".join(text for _, text in segments)
        self.assertIn("SERVER PERMISSION CONTROL", rendered)
        self.assertIn("DREDD PERMISSION REVIEW", rendered)
        self.assertIn("РЕШЕНИЕ ПОЛЬЗОВАТЕЛЯ", rendered)
        self.assertTrue(any(tag == "dredd_fail" and "PERMISSION: BLOCKED" in text
                            for tag, text in segments))

    def test_write_and_delete_permission_sections_remain_separate(self):
        for capability, tool in (("WRITE", "replace_text"), ("DELETE", "delete_file")):
            self.recorder.observe({"event": "permission_denied", "capability": capability,
                                   "attempt": 1, "function": tool,
                                   "arguments": {"path": "notes.txt"}})
        saved = self.load()
        self.assertEqual(set(saved["permission_escalations"]), {"WRITE", "DELETE"})
        rendered = "".join(text for _, text in
                           ultra_ui.UltraApp._audit_segments(saved, self.run_id))
        self.assertIn("replace_text", rendered)
        self.assertIn("delete_file", rendered)

    def test_terminal_fail_keeps_open_issues_unresolved(self):
        self.issue()
        self.recorder.observe({"event": "run_failed", "reason": "final_audit_retry_no_progress"})
        saved = self.load()
        self.assertEqual(saved["issues"][0]["result"], "UNRESOLVED")
        self.assertEqual(saved["final_audit"], "FAIL")
        self.assertEqual(saved["run_status"], "FAILED")

    def test_no_issue_and_absent_thread_are_neutral(self):
        self.assertEqual(self.load()["issues"], [])
        self.assertIsNone(audit_storage.load_audit_thread(
            self.workspace, self.workspace_id, self.chat_id, "other_run"
        ))
        with self.assertRaises(ValueError):
            audit_storage.audit_thread_path(self.workspace, "../escape", self.run_id)
        policy = server._prepare_policy_for_workspace(
            self.workspace,
            server._normalize_permissions({"allow_read": True, "allow_verify": True}),
        )
        relative = f".ultra/audit/{self.chat_id}/{self.run_id}.json"
        with self.assertRaises(PermissionError):
            server._agent_read_file(self.workspace, relative, policy)


class DiagnosticForkTests(unittest.IsolatedAsyncioTestCase):
    async def test_tool_free_fork_does_not_mutate_executor_messages(self):
        messages = [{"role": "system", "content": "Context"},
                    {"role": "user", "content": "Task"}]
        original = copy.deepcopy(messages)
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"choices": [{"message": {"content": "I used an outdated assumption."}}]}
        client = SimpleNamespace(post=AsyncMock(return_value=response))
        answer = await server._request_audit_diagnostic(
            client, {"Authorization": "token"}, "GigaChat", messages,
            "Rejected candidate", "Why was it wrong?",
        )
        self.assertEqual(answer, "I used an outdated assumption.")
        self.assertEqual(messages, original)
        body = client.post.await_args.kwargs["json"]
        self.assertNotIn("functions", body)
        self.assertNotIn("function_call", body)
        self.assertEqual(body["max_tokens"], server.MAX_AUDIT_DIAGNOSTIC_TOKENS)
        self.assertEqual(body["messages"][-2:], [
            {"role": "assistant", "content": "Rejected candidate"},
            {"role": "user", "content": "Why was it wrong?"},
        ])

    async def test_provider_failure_is_exposed_to_caller_without_mutation(self):
        messages = [{"role": "user", "content": "Task"}]
        client = SimpleNamespace(post=AsyncMock(side_effect=TimeoutError("down")))
        with self.assertRaises(TimeoutError):
            await server._request_audit_diagnostic(client, {}, "GigaChat", messages, "Candidate", "Why?")
        self.assertEqual(messages, [{"role": "user", "content": "Task"}])


class CompactLayoutTests(unittest.TestCase):
    def test_security_interface_and_bottom_composer_structure(self):
        with patch.object(ultra_ui, "load_ui_state", return_value=ui_state.default_ui_state()), \
             patch.object(ultra_ui.UltraApp, "_initialize_workspace_registry"):
            app = ultra_ui.UltraApp()
        self.addCleanup(app.destroy)
        app.withdraw()
        app.update_idletasks()

        def descendants(widget):
            for child in widget.winfo_children():
                yield child
                yield from descendants(child)

        def titled(name):
            return next(w for w in descendants(app)
                        if isinstance(w, ultra_ui.ttk.LabelFrame) and w.cget("text") == name)

        security = next(w for w in descendants(app)
                        if isinstance(w, ultra_ui.ttk.LabelFrame)
                        and str(w.cget("text")).startswith("БЕЗОПАСНОСТЬ ЗАПУСКА"))
        controls, service = security.winfo_children()
        top = controls.winfo_children()[0]
        self.assertEqual(top.grid_info()["columnspan"], 4)
        self.assertEqual([w.cget("text") for w in top.winfo_children()
                          if isinstance(w, ultra_ui.ttk.Checkbutton)], ["VERIFY", "GUARD P1"])
        scope_rows = [int(w.grid_info()["row"]) for w in controls.winfo_children()
                      if isinstance(w, ultra_ui.ttk.Entry)]
        self.assertEqual(scope_rows, [1, 2, 3])
        self.assertTrue(any(w.cget("text") == "Контекстные сообщения"
                            for w in service.winfo_children()
                            if isinstance(w, ultra_ui.ttk.Button)))

        interface = titled("ИНТЕРФЕЙС")
        labels = {w.cget("text"): (int(w.grid_info()["row"]), int(w.grid_info()["column"]))
                  for w in interface.winfo_children() if isinstance(w, ultra_ui.ttk.Label)}
        self.assertEqual(labels["Лог действий"], (1, 0))
        self.assertEqual(labels["Пользователь"], (1, 2))
        self.assertEqual(labels["Разбор выполнения"], (3, 0))
        self.assertEqual(labels["Workspace / чаты"], (3, 2))
        self.assertEqual(len(app._color_swatches), 6)

        upper, lower = app.central_vertical_paned.panes()
        self.assertEqual(str(app.chat_audit_paned.master), str(upper))
        self.assertEqual(str(titled("КОНТЕКСТ СООБЩЕНИЙ / COMPRESSOR").master), str(upper))
        message = titled("Сообщение")
        self.assertEqual(str(message.master), str(lower))
        self.assertEqual(message.pack_info()["fill"], "both")
        self.assertEqual(int(message.pack_info()["expand"]), 1)
        self.assertEqual(app.input_box.pack_info()["fill"], "both")
        self.assertEqual(int(app.input_box.pack_info()["expand"]), 1)
        self.assertEqual(str(app.send_button.master.master), str(lower))
        self.assertEqual(app.send_button.master.pack_info()["side"], "bottom")


class TaskBlockUiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name) / "workspace"
        self.workspace.mkdir()
        self.workspace_info = context_storage.ensure_workspace_storage(self.workspace)
        self.chat_id = context_storage.create_chat(self.workspace)["chat_id"]
        self.task_a = context_storage.new_task_block_id()
        self.task_b = context_storage.new_task_block_id()
        self.user_a = context_storage.append_raw_message(
            self.workspace, self.chat_id, "user", "TASK A", task_block_id=self.task_a
        )
        self.assistant_a = context_storage.append_raw_message(
            self.workspace, self.chat_id, "assistant", "ANSWER A",
            task_block_id=self.task_a,
            producer={
                "kind": "llm", "role_id": "main_chat", "run_id": "run_a",
                "model_id": "gigachat_ultra", "model_display_name": "Ultra",
                "provider": "gigachat", "provider_model_id": "GigaChat-Ultra",
            },
        )
        self.user_b = context_storage.append_raw_message(
            self.workspace, self.chat_id, "user", "TASK B", task_block_id=self.task_b
        )
        audit_a = audit_storage.AuditThreadRecorder(
            self.workspace, self.workspace_info["workspace_id"], self.chat_id, "run_a", self.task_a
        )
        audit_a.observe({"event": "run_finished", "status": "SUCCESS"})
        audit_b = audit_storage.AuditThreadRecorder(
            self.workspace, self.workspace_info["workspace_id"], self.chat_id, "run_b", self.task_b
        )
        audit_b.observe({"event": "final_audit_failed", "reason": "Wrong", "violations": ["Missing"]})
        audit_b.observe({"event": "run_failed"})
        with patch.object(ultra_ui, "load_ui_state", return_value=ui_state.default_ui_state()), \
             patch.object(ultra_ui.UltraApp, "_initialize_workspace_registry"):
            self.app = ultra_ui.UltraApp()
        self.addCleanup(self.app.destroy)
        self.app.withdraw()
        self.app.current_workspace_id = self.workspace_info["workspace_id"]
        self.app.current_chat_id = self.chat_id
        self.app.workspace_var.set(str(self.workspace))
        self.app._render_current_chat()

    def test_reopen_rebuilds_index_and_failed_run_remains_selected(self):
        app = self.app
        self.assertEqual(list(app._task_block_index), [self.task_a, self.task_b])
        self.assertEqual(app._task_block_order, [self.task_a, self.task_b])
        self.assertEqual(app._task_block_index[self.task_a]["assistant_message_id"], self.assistant_a["message_id"])
        self.assertIsNone(app._task_block_index[self.task_b]["assistant_message_id"])
        self.assertEqual(app._selected_task_block_id, self.task_b)
        self.assertEqual(app._selected_audit_run_id, "run_b")
        self.assertIn("RUN STATUS: FAILED", app.audit_text.get("1.0", "end"))
        self.assertIn(f"TASK BLOCK: {self.task_b}", app.audit_text.get("1.0", "end"))
        self.assertTrue(app.chat.mark_names().count(f"task_block_{self.task_a}"))
        self.assertTrue(app.chat.mark_names().count(f"task_block_{self.task_b}"))
        app._render_current_chat()
        self.assertEqual((app._selected_task_block_id, app._selected_audit_run_id), (self.task_b, "run_b"))
        for reference, expected_id, expected_run in (
            (f"task_block_{self.task_a}", self.task_a, "run_a"),
            (f"task_block_{self.task_b}", self.task_b, "run_b"),
        ):
            selected = app._task_block_for_viewport(
                app._task_block_order, app._task_block_index,
                lambda mark: app.chat.compare(mark, "<=", reference),
            )
            app._select_task_block(selected)
            self.assertEqual((app._selected_task_block_id, app._selected_audit_run_id),
                             (expected_id, expected_run))
        app._selected_task_block_id = None
        app._task_block_index = {}
        app._task_block_order = []
        app._render_current_chat()
        self.assertEqual((app._selected_task_block_id, app._selected_audit_run_id), (self.task_b, "run_b"))

    def test_user_assistant_buttons_and_explicit_selection_resolve_same_audit(self):
        message_dir = self.workspace / ".ultra" / "chats" / self.chat_id / "messages"
        before = {path.name: path.read_bytes() for path in message_dir.glob("*.json")}
        frames = self.app._message_action_widgets
        def audit_button(frame):
            return next(w for w in frame.winfo_children()
                        if isinstance(w, ultra_ui.ttk.Button) and w.cget("text") == "Разбор")
        audit_button(frames[0]).invoke()
        self.assertEqual(self.app._selected_audit_run_id, "run_a")
        audit_button(frames[1]).invoke()
        self.assertEqual(self.app._selected_audit_run_id, "run_a")
        audit_button(frames[2]).invoke()
        self.assertEqual(self.app._selected_audit_run_id, "run_b")
        self.app._select_message(self.user_a["message_id"])
        self.assertEqual(self.app._selected_audit_run_id, "run_a")
        self.app._select_message(self.user_b["message_id"])
        self.assertEqual(self.app._selected_audit_run_id, "run_b")
        self.assertEqual(before, {path.name: path.read_bytes() for path in message_dir.glob("*.json")})

    def test_explicit_audit_button_rereads_same_selected_run_from_disk(self):
        self.assertEqual((self.app._selected_task_block_id, self.app._selected_audit_run_id),
                         (self.task_b, "run_b"))
        self.assertIn("Wrong", self.app.audit_text.get("1.0", "end"))
        thread = audit_storage.load_audit_thread(
            self.workspace, self.workspace_info["workspace_id"], self.chat_id, "run_b"
        )
        thread["issues"][0]["reason"] = "FRESH DISK REASON"
        audit_storage._save_audit_thread(
            audit_storage.audit_thread_path(self.workspace, self.chat_id, "run_b"), thread
        )
        self.assertNotIn("FRESH DISK REASON", self.app.audit_text.get("1.0", "end"))
        frame = self.app._message_action_widgets[2]
        button = next(widget for widget in frame.winfo_children()
                      if isinstance(widget, ultra_ui.ttk.Button)
                      and widget.cget("text") == "Разбор")
        button.invoke()
        self.assertEqual((self.app._selected_task_block_id, self.app._selected_audit_run_id),
                         (self.task_b, "run_b"))
        self.assertIn("FRESH DISK REASON", self.app.audit_text.get("1.0", "end"))

    def test_send_creates_one_id_and_worker_persists_it_on_assistant(self):
        captured = {}
        class FakeThread:
            def __init__(self, *, target, args, daemon):
                captured["args"] = args
            def start(self): pass
        self.app.input_box.insert("1.0", "TASK C")
        with patch.object(self.app, "_ensure_workspace_ui_current"), \
             patch.object(ultra_ui.threading, "Thread", FakeThread):
            self.app._send()
        task_id = captured["args"][-1]
        user_c = context_storage.load_chat_messages(self.workspace, self.chat_id)[-1]
        self.assertEqual(user_c["task_block_id"], task_id)
        self.assertEqual(user_c["original_text"], "TASK C")
        self.assertNotIn(task_id, user_c["original_text"])
        self.assertNotEqual(task_id, user_c["message_id"])
        async def fake_run(_task, _workspace, **kwargs):
            self.assertEqual(kwargs["task_block_id"], task_id)
            kwargs["on_event"]({
                "event": "run_started", "run_id": "run_c", "task_block_id": task_id,
                "model_id": kwargs["model_id"], "model_display_name": "Ultra",
                "provider": "gigachat", "provider_model_id": "GigaChat-Ultra",
            })
            return "ANSWER C"
        with patch.object(ultra_ui, "run_agent_task", fake_run):
            self.app._worker(*captured["args"])
        assistant_c = context_storage.load_chat_messages(self.workspace, self.chat_id)[-1]
        self.assertEqual(assistant_c["role"], "assistant")
        self.assertEqual(assistant_c["task_block_id"], task_id)
        self.assertEqual(assistant_c["producer"]["run_id"], "run_c")

    def test_legacy_assistant_audit_button_remains_available(self):
        context_storage.append_raw_message(self.workspace, self.chat_id, "user", "legacy task")
        context_storage.append_raw_message(
            self.workspace, self.chat_id, "assistant", "legacy answer",
            producer={
                "kind": "llm", "role_id": "main_chat", "run_id": "run_legacy",
                "model_id": "gigachat_ultra", "model_display_name": "Ultra",
                "provider": "gigachat", "provider_model_id": "GigaChat-Ultra",
            },
        )
        audit_storage.AuditThreadRecorder(
            self.workspace, self.workspace_info["workspace_id"], self.chat_id, "run_legacy"
        )
        self.app._render_current_chat()
        button = next(w for w in self.app._message_action_widgets[-1].winfo_children()
                      if isinstance(w, ultra_ui.ttk.Button) and w.cget("text") == "Разбор")
        button.invoke()
        self.assertEqual(self.app._selected_audit_run_id, "run_legacy")
        self.assertIn("TASK BLOCK: LEGACY", self.app.audit_text.get("1.0", "end"))

    def test_running_task_gets_audit_button_when_run_started_is_observed(self):
        task_id = context_storage.new_task_block_id()
        context_storage.append_raw_message(
            self.workspace, self.chat_id, "user", "running task", task_block_id=task_id
        )
        self.app._render_current_chat()
        frame = self.app._message_action_widgets[-1]
        self.assertFalse(any(w.cget("text") == "Разбор" for w in frame.winfo_children()
                             if isinstance(w, ultra_ui.ttk.Button)))
        audit_storage.AuditThreadRecorder(
            self.workspace, self.workspace_info["workspace_id"], self.chat_id,
            "run_running", task_id,
        )
        self.app.trace_events.put({
            "event": "run_started", "run_id": "run_running",
            "chat_id": self.chat_id, "task_block_id": task_id,
        })
        self.app._poll_trace_events()
        self.assertTrue(any(w.cget("text") == "Разбор" for w in frame.winfo_children()
                            if isinstance(w, ultra_ui.ttk.Button)))
        self.assertEqual((self.app._selected_task_block_id, self.app._selected_audit_run_id),
                         (task_id, "run_running"))
        self.assertIn("RUN STATUS: RUNNING", self.app.audit_text.get("1.0", "end"))

    def test_scroll_resolver_and_debounce_do_not_rerender_same_block(self):
        order = ["A", "B", "C"]
        index = {key: {"ui_start_mark": key, "run_id": f"run_{key}"}
                 for key in order}
        positions = {"A": 0, "B": 100, "C": 200}
        draws = []
        fake = SimpleNamespace(
            _task_block_order=order, _task_block_index=index,
            _selected_task_block_id=None, _selected_audit_run_id=None,
            _chat_audit_sync_after=None,
            _task_block_for_viewport=ultra_ui.UltraApp._task_block_for_viewport,
            _render_audit_thread=lambda: draws.append(True),
            _select_task_block=None,
        )
        fake._select_task_block = lambda tid: ultra_ui.UltraApp._select_task_block(fake, tid)
        viewport = {"position": 0}
        fake.chat = SimpleNamespace(
            index=lambda _pos: viewport["position"],
            compare=lambda mark, _op, ref: positions[mark] <= ref,
        )
        for position, expected in ((0, "A"), (50, "A"), (100, "B"), (200, "C"), (150, "B"), (20, "A")):
            viewport["position"] = position
            ultra_ui.UltraApp._sync_audit_to_viewport(fake)
            self.assertEqual(fake._selected_task_block_id, expected)
        self.assertEqual(len(draws), 5)
        scheduled = []
        fake.chat.vbar = SimpleNamespace(set=lambda *_: None)
        fake.after = lambda delay, callback: scheduled.append((delay, callback)) or "pending"
        fake._sync_audit_to_viewport = lambda: ultra_ui.UltraApp._sync_audit_to_viewport(fake)
        fake._chat_rendering = True
        ultra_ui.UltraApp._on_chat_yview(fake, "0.0", "1.0")
        self.assertEqual(scheduled, [])
        fake._chat_rendering = False
        fake._last_chat_yview_first = 0.0
        ultra_ui.UltraApp._on_chat_yview(fake, "0.0", "1.0")
        self.assertEqual(scheduled, [])
        ultra_ui.UltraApp._on_chat_yview(fake, "0.1", "0.5")
        ultra_ui.UltraApp._on_chat_yview(fake, "0.2", "0.6")
        self.assertEqual(len(scheduled), 1)
        self.assertEqual(scheduled[0][0], 40)


class TraceAndUiStateTests(unittest.TestCase):
    def test_permission_request_crosses_worker_to_main_event_queue(self):
        events = queue.Queue()
        seen = []
        fake = SimpleNamespace(events=events, trace_events=queue.Queue(),
                               after=lambda *_: None,
                               _finish_run=lambda *_: None,
                               _append_chat=lambda *_: None)
        fake._poll_events = lambda: ultra_ui.UltraApp._poll_events(fake)
        def open_request(item):
            self.assertIs(threading.current_thread(), threading.main_thread())
            seen.append(item["payload"]["capability"])
            item["answer"]["granted"] = True
            item["ready"].set()
        fake._open_permission_request = open_request
        async def run_task(_task, _workspace, *, permission_request_callback, on_event, **_kwargs):
            granted = permission_request_callback({"capability": "WRITE"})
            on_event({"event": "run_finished", "status": "SUCCESS"})
            return "granted" if granted else "denied"
        with (patch.object(ultra_ui, "run_agent_task", side_effect=run_task),
              patch.object(ultra_ui, "append_raw_message", return_value={"producer": None})):
            worker = threading.Thread(target=ultra_ui.UltraApp._worker,
                args=(fake, "task", "workspace", {}, "chat", "gigachat_ultra",
                      "gigachat_3_pro"))
            worker.start()
            for _ in range(100):
                ultra_ui.UltraApp._poll_events(fake)
                if not worker.is_alive():
                    break
                worker.join(0.01)
            worker.join(1)
        self.assertFalse(worker.is_alive())
        self.assertEqual(seen, ["WRITE"])

    def test_permission_dialog_rejects_worker_thread(self):
        errors = []
        def call():
            try:
                ultra_ui.UltraApp._open_permission_request(object(), {})
            except Exception as exc:
                errors.append(exc)
        worker = threading.Thread(target=call)
        worker.start()
        worker.join()
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], RuntimeError)

    def test_mutation_intent_classification_is_visible_in_live_trace(self):
        fake = SimpleNamespace(_compact_event_arguments=ultra_ui.UltraApp._compact_event_arguments)
        line = ultra_ui.UltraApp._format_event(fake, {
            "event": "mutation_intent_classified", "run_id": "run_test",
            "mutation_intent": "LIKELY_MUTATION",
            "reasons": ["action:обнови", "target:Документация/13_Архитектура.md"],
        })
        self.assertIn("MUTATION INTENT | LIKELY_MUTATION", line)
        self.assertIn("13_Архитектура.md", line)

    def test_final_audit_lifecycle_formatting_and_non_error_tags(self):
        samples = (
            ("final_audit_started", {"model_id": "verifier", "write_revision": 2}, "ДРЕДД — START"),
            ("final_audit_retry_evaluated", {"decision": "CONTINUE", "progress_class": "MATERIAL_PROGRESS", "audit_attempt": 1}, "RETRY POLICY → CONTINUE"),
            ("final_audit_feedback_delivered", {"correction_cycle": 1, "correction_limit": 2}, "DREDD FEEDBACK → EXECUTOR"),
            ("final_audit_correction_started", {"correction_cycle": 1, "correction_limit": 2}, "CORRECTION START"),
        )
        formatter = SimpleNamespace(_compact_event_arguments=ultra_ui.UltraApp._compact_event_arguments)
        events = queue.Queue()
        for kind, fields, expected in samples:
            event = {"event": kind, "run_id": "run_test", **fields}
            self.assertIn(expected, ultra_ui.UltraApp._format_event(formatter, event))
            events.put(event)
        events.put({"event": "final_audit_failed", "run_id": "run_test"})
        appended = []
        fake = SimpleNamespace(
            trace_events=events,
            _format_event=lambda event: ultra_ui.UltraApp._format_event(formatter, event),
            _append_trace=lambda line, tag="trace": appended.append((line, tag)),
            _run_started_once=False, _selected_audit_run_id=None,
            _active_audit_run_id=None, current_chat_id=None,
            _poll_trace_events=lambda: None,
            after=lambda *_: None,
        )
        ultra_ui.UltraApp._poll_trace_events(fake)
        self.assertEqual([tag for _line, tag in appended], ["trace"] * 4 + ["trace_error"])

    def test_new_color_swatches_refresh(self):
        class Swatch:
            def __init__(self): self.options = {}
            def configure(self, **options): self.options.update(options)
        class ColorVar:
            def __init__(self, value): self.value = value
            def get(self): return self.value
            def set(self, value): self.value = value
        swatches = {key: Swatch() for key in ("log", "error_log", "audit", "user", "assistant", "workspace")}
        fake = SimpleNamespace(
            _color_swatches=swatches,
            log_text_color_var=ColorVar("#000001"),
            error_log_color_var=ColorVar("#000002"),
            audit_text_color_var=ColorVar("#000003"),
            user_text_color_var=ColorVar("#000004"),
            assistant_text_color_var=ColorVar("#000005"),
            workspace_text_color_var=ColorVar("#000006"),
        )
        ultra_ui.UltraApp._refresh_color_swatches(fake)
        self.assertEqual(swatches["error_log"].options["bg"], "#000002")
        self.assertEqual(swatches["error_log"].options["activebackground"], "#000002")
        self.assertEqual(swatches["audit"].options["bg"], "#000003")
        self.assertEqual(swatches["audit"].options["activebackground"], "#000003")
        fake._apply_text_colors = lambda: ultra_ui.UltraApp._refresh_color_swatches(fake)
        fake._save_ui_state = lambda **_kwargs: None
        with patch.object(ultra_ui.colorchooser, "askcolor", return_value=((255, 0, 0), "#ff0000")):
            ultra_ui.UltraApp._choose_text_color(fake, fake.error_log_color_var, "Ошибки лога")
        self.assertEqual(swatches["error_log"].options["bg"], "#FF0000")

    def test_formatter_failure_cannot_stop_polling_or_next_event(self):
        events = queue.Queue()
        events.put({"event": "broken"})
        events.put({"event": "tool_finished", "function": "replace_text", "tool_sequence": 2})
        appended = []
        scheduled = []
        def formatter(event):
            if event["event"] == "broken":
                raise ValueError("malformed")
            return "OK next event"
        fake = SimpleNamespace(
            trace_events=events, _format_event=formatter,
            _append_trace=lambda line, tag="trace": appended.append((line, tag)),
            _run_started_once=False, _selected_audit_run_id=None,
            _active_audit_run_id=None, current_chat_id=None,
            _poll_trace_events=lambda: None,
            after=lambda delay, callback: scheduled.append((delay, callback)),
        )
        ultra_ui.UltraApp._poll_trace_events(fake)
        self.assertEqual(len(appended), 2)
        self.assertIn("TRACE RENDER ERROR", appended[0][0])
        self.assertEqual(appended[1], ("OK next event", "trace"))
        self.assertEqual(scheduled[0][0], 100)

    def test_append_failure_is_local_and_error_events_are_tagged(self):
        events = queue.Queue()
        events.put({"event": "tool_started", "function": "find_text"})
        events.put({"event": "tool_error", "function": "replace_text"})
        events.put({"event": "tool_finished", "function": "read_file_range"})
        appended = []
        def append(line, tag="trace"):
            if "find_text" in line:
                raise ValueError("widget failed")
            appended.append((line, tag))
        fake = SimpleNamespace(
            trace_events=events,
            _format_event=lambda event: str(event["function"]),
            _append_trace=append, _run_started_once=False,
            _selected_audit_run_id=None, _active_audit_run_id=None,
            _poll_trace_events=lambda: None,
            current_chat_id=None, after=lambda *_: None,
        )
        ultra_ui.UltraApp._poll_trace_events(fake)
        self.assertEqual(appended, [
            ("[TRACE RENDER ERROR] tool_started: ValueError", "trace_error"),
            ("replace_text", "trace_error"),
            ("read_file_range", "trace"),
        ])

    def test_live_audit_events_refresh_current_run_panel(self):
        events = queue.Queue()
        for kind in ("run_started", "execution_consistency_detected",
                     "execution_consistency_verifier_failed", "execution_consistency_resolved",
                     "final_audit_failed", "audit_diagnostic_answer", "final_audit_passed"):
            events.put({"event": kind, "run_id": "run_test", "chat_id": "chat_test"})
        refreshed = []
        fake = SimpleNamespace(
            trace_events=events, _format_event=lambda event: event["event"],
            _append_trace=lambda *_: None, _run_started_once=False,
            _selected_audit_run_id=None, _active_audit_run_id=None,
            current_chat_id="chat_test", _render_audit_thread=lambda: refreshed.append(True),
            _poll_trace_events=lambda: None, after=lambda *_: None,
        )
        ultra_ui.UltraApp._poll_trace_events(fake)
        self.assertEqual(fake._selected_audit_run_id, "run_test")
        self.assertEqual(len(refreshed), 7)

    def test_precise_arguments_are_compact_and_dredd_label_is_ui_only(self):
        compact = ultra_ui.UltraApp._compact_event_arguments({
            "path": "notes.txt", "old_text": "A" * 1000, "new_text": "B" * 1000,
            "marker": "C" * 1000, "text": "D" * 1000,
        })
        self.assertIn("path=notes.txt", compact)
        for key in ("old_text", "new_text", "marker", "text"):
            self.assertIn(f"{key}=<1000 chars>", compact)
        self.assertNotIn("AAAA", compact)
        fake = SimpleNamespace(_compact_event_arguments=ultra_ui.UltraApp._compact_event_arguments)
        line = ultra_ui.UltraApp._format_event(fake, {
            "event": "final_audit_failed", "run_id": "run_test",
            "reason": "Wrong", "violations": ["Missing"],
            "required_action": "Fix", "audit_attempt": 1,
            "verifier_run_id": "ver_test",
        })
        self.assertIn("СУДЬЯ ДРЕДД FAIL", line)
        self.assertIn("ver_test", line)

    def test_audit_render_and_producer_linkage(self):
        self.assertEqual(ultra_ui.get_assistant_audit_run_id({
            "role": "assistant", "producer": {"run_id": "run_test"},
        }), "run_test")
        self.assertIsNone(ultra_ui.get_assistant_audit_run_id({
            "role": "user", "producer": {"run_id": "run_test"},
        }))
        neutral = ultra_ui.UltraApp._audit_segments(None, "run_test")
        self.assertIn("нет событий", "".join(text for _tag, text in neutral))
        thread = {"issues": [{
            "audit_attempt": 1, "verifier_run_id": "ver_test",
            "reason": "Wrong", "violations": ["Missing"],
            "required_action": "Fix", "diagnostic_question": "Why?",
            "diagnostic_answer": "Assumption", "correction_activity": [{
                "tool_sequence": 1, "tool_name": "replace_text",
                "path": "notes.txt", "status": "OK",
            }], "result": "RESOLVED",
        }], "final_audit": "PASS"}
        rendered = "".join(text for _tag, text in ultra_ui.UltraApp._audit_segments(thread, "run_test"))
        self.assertIn("СУДЬЯ ДРЕДД", rendered)
        self.assertIn("ОТВЕТЧИК — ULTRA", rendered)
        self.assertIn("Исправлено: 1", rendered)
        self.assertIn("Final Audit: PASS", rendered)

    def test_audit_panel_widget_renders_read_only_and_absence_is_neutral(self):
        class Widget:
            def __init__(self): self.calls = []; self.state = "disabled"
            def configure(self, **options): self.state = options["state"]
            def delete(self, *_): self.calls.clear()
            def insert(self, _where, text, tag): self.calls.append((text, tag))
            def see(self, *_): pass
        widget = Widget()
        fake = SimpleNamespace(
            audit_text=widget, _selected_audit_run_id="run_test",
            current_workspace_id="ws_test", current_chat_id="chat_test",
            workspace_var=SimpleNamespace(get=lambda: "M:/workspace"),
            _audit_segments=ultra_ui.UltraApp._audit_segments,
        )
        with patch.object(ultra_ui, "load_audit_thread", return_value=None):
            ultra_ui.UltraApp._render_audit_thread(fake)
        self.assertEqual(widget.state, "disabled")
        self.assertIn("нет событий", "".join(text for text, _tag in widget.calls))

    def test_ui_state_persists_colors_ratios_visibility(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "ui_state.json"
            state = ui_state.default_ui_state()
            state["colors"]["error_log"] = "#DD1111"
            state["colors"]["audit"] = "#CCDDEE"
            state["chat_audit_ratios"]["normal"] = 0.61
            state["central_vertical_ratios"]["zoomed"] = 0.72
            state["audit_visible"] = False
            with patch.object(ui_state, "STATE_PATH", state_path):
                ui_state.save_ui_state(state)
                loaded = ui_state.load_ui_state()
        self.assertEqual(loaded["colors"]["error_log"], "#DD1111")
        self.assertEqual(loaded["colors"]["audit"], "#CCDDEE")
        self.assertEqual(loaded["chat_audit_ratios"]["normal"], 0.61)
        self.assertEqual(loaded["central_vertical_ratios"]["zoomed"], 0.72)
        self.assertFalse(loaded["audit_visible"])

    def test_error_and_audit_colors_apply_to_distinct_tags(self):
        class ColorVar:
            def __init__(self, value): self.value = value
            def get(self): return self.value
        class TextWidget:
            def __init__(self): self.tags = {}
            def tag_configure(self, name, **options): self.tags[name] = options
        trace = TextWidget()
        audit = TextWidget()
        chat = TextWidget()
        fake = SimpleNamespace(
            trace_log=trace, audit_text=audit, chat=chat,
            log_text_color_var=ColorVar("#00AA00"),
            error_log_color_var=ColorVar("#DD1111"),
            audit_text_color_var=ColorVar("#CCDDEE"),
            assistant_text_color_var=ColorVar("#1122FF"),
            user_text_color_var=ColorVar("#FFFFFF"),
            _theme_colors={"muted": "#777777"},
            _refresh_color_swatches=lambda: None,
            _apply_workspace_sidebar_theme=lambda: None,
        )
        ultra_ui.UltraApp._apply_text_colors(fake)
        self.assertEqual(trace.tags["trace_error"]["foreground"], "#DD1111")
        self.assertEqual(trace.tags["trace"]["foreground"], "#00AA00")
        self.assertEqual(audit.tags["audit"]["foreground"], "#CCDDEE")
        self.assertEqual(audit.tags["dredd_fail"]["foreground"], "#DD1111")
        self.assertEqual(audit.tags["ultra"]["foreground"], "#1122FF")

    def test_reset_panels_restores_nested_defaults_and_visibility(self):
        class BoolVar:
            def __init__(self, value): self.value = value
            def set(self, value): self.value = value
            def get(self): return self.value
        state = ui_state.default_ui_state()
        state["chat_audit_ratios"]["normal"] = 0.8
        state["central_vertical_ratios"]["normal"] = 0.3
        state["audit_visible"] = False
        visible = BoolVar(False)
        fake = SimpleNamespace(
            _ui_state=state, audit_visible_var=visible,
            _toggle_audit_panel=lambda **_: state.update(audit_visible=visible.get()),
            _apply_panel_ratios=lambda *_: None,
            _window_mode=lambda: "normal",
            _save_ui_state=lambda **_: None,
        )
        ultra_ui.UltraApp._reset_panel_layout(fake)
        self.assertEqual(state["chat_audit_ratios"], ui_state.DEFAULT_CHAT_AUDIT_RATIOS)
        self.assertEqual(state["central_vertical_ratios"], ui_state.DEFAULT_CENTRAL_VERTICAL_RATIOS)
        self.assertTrue(state["audit_visible"])
        self.assertTrue(visible.get())

    def test_nested_sash_ratios_capture_and_apply(self):
        class Paned:
            def __init__(self, width, height, position):
                self.width = width; self.height = height; self.position = position
                self.placed = None
            def winfo_width(self): return self.width
            def winfo_height(self): return self.height
            def sash_coord(self, _index): return self.position
            def panes(self): return ("first", "second")
            def sash_place(self, _index, x, y): self.placed = (x, y)
        chat = Paned(1000, 500, (610, 0))
        vertical = Paned(1000, 600, (0, 360))
        state = ui_state.default_ui_state()
        fake = SimpleNamespace(
            _ui_state=state, chat_audit_paned=chat,
            central_vertical_paned=vertical,
            audit_visible_var=SimpleNamespace(get=lambda: True),
            _capture_panel_ratios=lambda: [0.24, 0.80],
            _window_mode=lambda: "normal",
        )
        ultra_ui.UltraApp._store_current_panel_ratios(fake)
        self.assertEqual(state["chat_audit_ratios"]["normal"], 0.61)
        self.assertEqual(state["central_vertical_ratios"]["normal"], 0.6)
        ultra_ui.UltraApp._apply_inner_panel_ratios(fake, "normal")
        self.assertEqual(chat.placed, (610, 0))
        self.assertEqual(vertical.placed, (0, 360))


if __name__ == "__main__":
    unittest.main()
