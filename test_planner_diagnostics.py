import json
import queue
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import audit_storage
import planner_runtime
import ui_state
import ultra_ui


def valid_plan() -> dict:
    return {
        "stages": [{
            "stage_id": "stage_1",
            "goal": "Inspect the workspace",
            "stage_type": "analysis",
            "persistence_required": False,
            "allowed_capabilities": ["READ"],
            "artifacts": [],
            "completion_criteria": ["Workspace inspected"],
        }],
        "obligation_changes": [],
    }


class FakeResponse:
    def __init__(self, content: str) -> None:
        self.content = content

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return {
            "choices": [{
                "finish_reason": "stop",
                "message": {"content": self.content},
            }],
        }


class FakeClient:
    def __init__(self, content: str) -> None:
        self.response = FakeResponse(content)
        self.body = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def post(self, _url, *, headers, json):
        self.body = json
        self.headers = headers
        return self.response


class FailingClient(FakeClient):
    async def post(self, _url, *, headers, json):
        raise RuntimeError("provider-sensitive-detail")


class PlannerRuntimeDiagnosticTests(unittest.IsolatedAsyncioTestCase):
    async def test_normal_response_reports_request_context_response_in_order(self):
        content = json.dumps(valid_plan(), ensure_ascii=False)
        client = FakeClient(content)
        diagnostics = []
        with patch.object(
            planner_runtime, "get_access_token", AsyncMock(return_value="secret")
        ), patch.object(
            planner_runtime.httpx, "AsyncClient", return_value=client
        ):
            result = await planner_runtime.run_planner(
                mode="INITIAL",
                raw_task="Inspect",
                context={"server_fact": "value"},
                diagnostic_callback=lambda kind, payload: diagnostics.append(
                    (kind, payload)
                ),
            )

        self.assertEqual(result, valid_plan())
        self.assertEqual([kind for kind, _payload in diagnostics], [
            "request", "context", "response",
        ])
        request = diagnostics[0][1]
        self.assertEqual(request["mode"], "INITIAL")
        self.assertEqual(request["planner_model_id"], "gigachat_ultra")
        self.assertEqual(request["provider_model_id"], client.body["model"])
        self.assertEqual(request["temperature"], client.body["temperature"])
        self.assertEqual(request["max_tokens"], client.body["max_tokens"])
        self.assertEqual(request["function_call"], client.body["function_call"])
        context = diagnostics[1][1]
        self.assertEqual(context["system"], client.body["messages"][0]["content"])
        self.assertEqual(context["user"], client.body["messages"][1]["content"])
        self.assertEqual(diagnostics[2][1]["content"], content)
        self.assertNotIn("Authorization", request)
        self.assertNotIn("secret", json.dumps(diagnostics, ensure_ascii=False))

    async def test_invalid_json_preserves_raw_response_before_real_error(self):
        content = 'Here is the plan:\n{"stages": [], "obligation_changes": []}'
        client = FakeClient(content)
        diagnostics = []
        with patch.object(
            planner_runtime, "get_access_token", AsyncMock(return_value="secret")
        ), patch.object(
            planner_runtime.httpx, "AsyncClient", return_value=client
        ):
            with self.assertRaisesRegex(
                planner_runtime.PlannerError,
                "Planner must return one JSON object without prose",
            ):
                await planner_runtime.run_planner(
                    mode="INITIAL",
                    raw_task="Inspect",
                    context={},
                    diagnostic_callback=lambda kind, payload: diagnostics.append(
                        (kind, payload)
                    ),
                )

        self.assertEqual([kind for kind, _payload in diagnostics], [
            "request", "context", "response", "error",
        ])
        self.assertEqual(diagnostics[2][1]["content"], content)
        self.assertEqual(diagnostics[3][1]["error_type"], "PlannerError")
        self.assertEqual(
            diagnostics[3][1]["error_message"],
            "Planner must return one JSON object without prose",
        )

    async def test_diagnostic_callback_failure_does_not_change_planner_result(self):
        client = FakeClient(json.dumps(valid_plan()))

        def broken_callback(_kind, _payload):
            raise RuntimeError("diagnostics unavailable")

        with patch.object(
            planner_runtime, "get_access_token", AsyncMock(return_value="secret")
        ), patch.object(
            planner_runtime.httpx, "AsyncClient", return_value=client
        ):
            result = await planner_runtime.run_planner(
                mode="INITIAL",
                raw_task="Inspect",
                context={},
                diagnostic_callback=broken_callback,
            )
        self.assertEqual(result, valid_plan())

    async def test_runtime_error_diagnostic_uses_safe_message(self):
        diagnostics = []
        with patch.object(
            planner_runtime, "get_access_token", AsyncMock(return_value="secret")
        ), patch.object(
            planner_runtime.httpx,
            "AsyncClient",
            return_value=FailingClient("unused"),
        ):
            with self.assertRaisesRegex(
                planner_runtime.PlannerError,
                "Planner call failed: RuntimeError",
            ):
                await planner_runtime.run_planner(
                    mode="INITIAL",
                    raw_task="Inspect",
                    context={},
                    diagnostic_callback=lambda kind, payload: diagnostics.append(
                        (kind, payload)
                    ),
                )
        self.assertEqual([kind for kind, _payload in diagnostics], [
            "request", "context", "error",
        ])
        self.assertEqual(diagnostics[-1][1], {
            "mode": "INITIAL",
            "error_type": "PlannerError",
            "error_message": "Planner call failed: RuntimeError",
        })
        self.assertNotIn("provider-sensitive-detail", json.dumps(diagnostics))


class PlannerDiagnosticPersistenceTests(unittest.TestCase):
    def test_audit_persists_order_full_content_and_bounded_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            recorder = audit_storage.AuditThreadRecorder(
                workspace, "ws_test", "chat_test", "run_test"
            )
            long_content = "RAW:" + "x" * 5000
            events = [
                {"event": "planner_diagnostic_request", "mode": "INITIAL",
                 "planner_model_id": "gigachat_ultra", "provider_model_id": "GigaChat-3-Ultra",
                 "temperature": 0.0, "max_tokens": 8192, "function_call": "none",
                 "Authorization": "must-not-persist"},
                {"event": "planner_diagnostic_context", "mode": "INITIAL",
                 "system": "SYSTEM:" + "s" * 3000, "user": "USER:" + "u" * 3000},
                {"event": "planner_diagnostic_response", "mode": "INITIAL",
                 "finish_reason": "stop", "content": long_content, "function_call": None},
                {"event": "planner_diagnostic_error", "mode": "INITIAL",
                 "error_type": "PlannerError", "error_message": "Invalid JSON"},
            ]
            for event in events:
                recorder.observe(event)
            saved = audit_storage.load_audit_thread(
                workspace, "ws_test", "chat_test", "run_test"
            )

            diagnostics = saved["planner_diagnostics"]
            self.assertEqual(
                [item["kind"] for item in diagnostics],
                ["request", "context", "response", "error"],
            )
            self.assertEqual(diagnostics[2]["content"], long_content)
            self.assertEqual(len(diagnostics[1]["system"]), 3007)
            self.assertEqual(len(diagnostics[1]["user"]), 3005)
            self.assertNotIn("Authorization", diagnostics[0])

            for index in range(70):
                recorder.observe({
                    "event": "planner_diagnostic_error",
                    "mode": "READINESS",
                    "error_type": "PlannerError",
                    "error_message": str(index),
                })
            self.assertEqual(len(recorder.thread["planner_diagnostics"]), 64)
            self.assertEqual(
                recorder.thread["planner_diagnostics"][-1]["error_message"],
                "69",
            )


class PlannerDiagnosticUiTests(unittest.TestCase):
    def test_ui_state_defaults_saved_values_and_legacy_default(self):
        expected = {
            "request": True,
            "context": True,
            "response": True,
            "stages": True,
            "errors": True,
        }
        self.assertEqual(ui_state.default_ui_state()["planner_diagnostics"], expected)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ui_state.json"
            state = ui_state.default_ui_state()
            state["planner_diagnostics"] = {
                "request": False,
                "context": True,
                "response": False,
                "stages": True,
                "errors": False,
            }
            with patch.object(ui_state, "STATE_PATH", path):
                ui_state.save_ui_state(state)
                loaded = ui_state.load_ui_state()
                legacy = dict(state)
                legacy.pop("planner_diagnostics")
                ui_state.save_ui_state(legacy)
                legacy_loaded = ui_state.load_ui_state()
        self.assertEqual(loaded["planner_diagnostics"], state["planner_diagnostics"])
        self.assertEqual(legacy_loaded["planner_diagnostics"], expected)

    def test_filters_tooltips_and_existing_audit_layout(self):
        with patch.object(
            ultra_ui, "load_ui_state", return_value=ui_state.default_ui_state()
        ), patch.object(
            ultra_ui.UltraApp, "_initialize_workspace_registry"
        ):
            app = ultra_ui.UltraApp()
        self.addCleanup(app.destroy)
        app.withdraw()
        app.update_idletasks()

        controls = app.audit_section.winfo_children()[0]
        self.assertIn(
            str(app.audit_text.master),
            [str(child) for child in app.audit_section.winfo_children()],
        )
        self.assertIsInstance(app.audit_records, ultra_ui.ttk.Treeview)
        self.assertEqual(app.audit_text.pack_info()["fill"], "both")
        self.assertEqual(int(app.audit_text.pack_info()["expand"]), 1)
        checks = [
            child for child in controls.winfo_children()
            if isinstance(child, ultra_ui.ttk.Checkbutton)
        ]
        self.assertEqual(
            [check.cget("text") for check in checks],
            ["Запрос", "Контекст", "Ответ", "Стадии", "Ошибки"],
        )
        self.assertTrue(all(variable.get() for variable in (
            app.planner_diag_request_var,
            app.planner_diag_context_var,
            app.planner_diag_response_var,
            app.planner_diag_stages_var,
            app.planner_diag_errors_var,
        )))
        self.assertEqual(set(app._planner_diag_tooltips), {
            "request", "context", "response", "stages", "errors",
        })
        for key, tooltip in app._planner_diag_tooltips.items():
            self.assertEqual(tooltip.text, ultra_ui.PLANNER_DIAGNOSTIC_TOOLTIPS[key])
            self.assertTrue(tooltip.widget.bind("<Enter>"))

        with patch.object(app, "_save_ui_state") as save, patch.object(
            app, "_render_audit_thread"
        ) as render:
            app._on_planner_diagnostic_filter_changed()
        save.assert_called_once_with(silent=True)
        render.assert_called_once_with()

        app.planner_diag_request_var.set(False)
        app.planner_diag_errors_var.set(False)
        with patch.object(ultra_ui, "save_ui_state") as save_state:
            app._save_ui_state(silent=True)
        persisted = save_state.call_args.args[0]["planner_diagnostics"]
        self.assertEqual(persisted, {
            "request": False,
            "context": True,
            "response": True,
            "stages": True,
            "errors": False,
        })

    def test_render_filters_are_reversible_and_plan_failure_is_explicit(self):
        raw = 'Here is the plan:\n{"stages": []}'
        thread = {
            "run_status": "BLOCKED",
            "final_audit": "NOT_RUN",
            "task_lifecycle": {"events": [
                {"event": "planner_started", "mode": "INITIAL"},
                {"event": "planner_failed", "mode": "INITIAL",
                 "reason": "PlannerError", "error_type": "PlannerError",
                 "error_message": "Planner must return one JSON object without prose"},
                {"event": "stage_blocked", "reason": "planner_protocol_or_runtime_error"},
            ]},
            "planner_diagnostics": [
                {"kind": "request", "mode": "INITIAL", "planner_model_id": "gigachat_ultra",
                 "provider_model_id": "GigaChat-3-Ultra", "temperature": 0.0,
                 "max_tokens": 8192, "function_call": "none"},
                {"kind": "context", "mode": "INITIAL", "system": "FULL SYSTEM",
                 "user": "FULL USER"},
                {"kind": "response", "mode": "INITIAL", "finish_reason": "stop",
                 "content": raw, "function_call": None},
                {"kind": "error", "mode": "INITIAL", "error_type": "PlannerError",
                 "error_message": "Planner must return one JSON object without prose"},
            ],
            "issues": [],
        }
        shown = "".join(
            text for _tag, text in ultra_ui.UltraApp._audit_segments(
                thread, "run_test"
            )
        )
        self.assertIn("ПЛАН НЕ СОЗДАН", shown)
        self.assertIn("Режим: INITIAL", shown)
        self.assertIn("PLANNER / RAW RESPONSE", shown)
        self.assertIn(raw, shown)
        self.assertIn("PLANNER / LIFECYCLE", shown)
        self.assertIn("Planner must return one JSON object without prose", shown)

        hidden = "".join(
            text for _tag, text in ultra_ui.UltraApp._audit_segments(
                thread,
                "run_test",
                planner_filters={key: False for key in (
                    "request", "context", "response", "stages", "errors",
                )},
            )
        )
        self.assertIn("ПЛАН НЕ СОЗДАН\nПричина: PlannerError", hidden)
        self.assertNotIn("PLANNER /", hidden)
        self.assertNotIn(raw, hidden)
        self.assertNotIn("planner_failed", hidden)

        shown_again = "".join(
            text for _tag, text in ultra_ui.UltraApp._audit_segments(
                thread, "run_test"
            )
        )
        self.assertEqual(shown_again, shown)
        legacy = {"run_status": "SUCCESS", "final_audit": "PASS", "issues": []}
        legacy_text = "".join(
            text for _tag, text in ultra_ui.UltraApp._audit_segments(
                legacy, "old_run"
            )
        )
        self.assertIn("RUN: old_run", legacy_text)

    def test_diagnostics_refresh_audit_without_entering_action_log(self):
        events = queue.Queue()
        events.put({
            "event": "planner_diagnostic_response",
            "run_id": "run_test",
            "content": "FULL RAW RESPONSE",
        })
        appended = []
        rendered = []
        fake = type("FakeUi", (), {})()
        fake.trace_events = events
        fake._run_started_once = False
        fake._selected_audit_run_id = "run_test"
        fake._active_audit_run_id = None
        fake.current_chat_id = None
        fake._append_trace = lambda *args: appended.append(args)
        fake._format_event = lambda event: event["event"]
        fake._render_audit_thread = lambda: rendered.append(True)
        fake._refresh_selected_run_index = lambda: rendered.append("index")
        fake._poll_trace_events = lambda: None
        fake.after = lambda *_args: None

        ultra_ui.UltraApp._poll_trace_events(fake)

        self.assertEqual(appended, [])
        self.assertEqual(rendered, ["index"])


if __name__ == "__main__":
    unittest.main()
