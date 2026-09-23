import asyncio
import copy
import json
import queue
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import audit_storage
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


class TraceAndUiStateTests(unittest.TestCase):
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
        for kind in ("run_started", "final_audit_failed", "audit_diagnostic_answer", "final_audit_passed"):
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
        self.assertEqual(len(refreshed), 4)

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
        self.assertIn("нет событий", neutral[0][1])
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
