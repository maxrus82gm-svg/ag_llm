import tempfile
import unittest
from pathlib import Path

from context_registry import (
    save_context_variant,
    set_active_variant,
)
from server_context_messages import (
    get_registered_server_context_event,
    list_registered_server_context_events,
    register_server_context_event,
    resolve_server_context_message,
)


ACTIVE_EVENT_IDS = {
    "final_audit.feedback",
    "permission.denied",
    "tool.error",
    "guard.repeat",
    "guard.suspicious_create",
    "verification.required",
}


class ServerContextMessagesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.state_path = Path(self.temp_dir.name) / "contexts.json"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_01_factory_events_are_registered(self) -> None:
        registered = {
            item["event_id"]
            for item in list_registered_server_context_events()
        }
        self.assertTrue(ACTIVE_EVENT_IDS.issubset(registered))
        self.assertNotIn("tool_budget.low", registered)

    def test_02_registry_default_resolves(self) -> None:
        text = resolve_server_context_message(
            "permission.denied",
            {
                "capability": "WRITE",
                "tool_name": "write_file",
            },
            state_path=self.state_path,
        )
        self.assertIn("WRITE", text)
        self.assertIn("write_file", text)

    def test_03_registry_custom_variant_is_used(self) -> None:
        save_context_variant(
            "permission.denied",
            "custom",
            "CUSTOM {capability} / {tool_name}",
            description="Тестовый custom.",
            state_path=self.state_path,
        )
        set_active_variant(
            "permission.denied",
            "custom",
            state_path=self.state_path,
        )

        text = resolve_server_context_message(
            "permission.denied",
            {
                "capability": "WRITE",
                "tool_name": "replace_text",
            },
            state_path=self.state_path,
        )

        self.assertEqual(
            text,
            "CUSTOM WRITE / replace_text",
        )

    def test_04_corrupt_registry_falls_back_to_factory_default(self) -> None:
        self.state_path.write_text(
            "{broken",
            encoding="utf-8",
        )

        diagnostics = []

        with self.assertWarns(RuntimeWarning):
            text = resolve_server_context_message(
                "permission.denied",
                {
                    "capability": "READ",
                    "tool_name": "read_file",
                },
                state_path=self.state_path,
                on_warning=diagnostics.append,
            )

        self.assertIn("READ", text)
        self.assertIn("read_file", text)
        self.assertEqual(
            diagnostics[-1]["fallback"],
            "default_text",
        )

    def test_05_dynamic_event_uses_registered_fallback(self) -> None:
        event_id = "test.dynamic_event"

        register_server_context_event(
            event_id,
            "Динамическое runtime-событие.",
            "Dynamic {value}",
        )

        diagnostics = []

        with self.assertWarns(RuntimeWarning):
            text = resolve_server_context_message(
                event_id,
                {"value": 42},
                state_path=self.state_path,
                on_warning=diagnostics.append,
            )

        self.assertEqual(text, "Dynamic 42")
        self.assertEqual(
            diagnostics[-1]["fallback"],
            "default_text",
        )

    def test_06_final_audit_feedback_resolves(self) -> None:
        variables = {
            "verdict": "FAIL",
            "reason": "Недостаточно доказательств.",
            "violations_lines": "- Не выполнена проверка.",
            "required_action": "Выполнить проверку.",
            "correction_cycle": 1,
            "correction_limit": 2,
            "remaining_corrections": 1,
        }

        text = resolve_server_context_message(
            "final_audit.feedback",
            variables,
            state_path=self.state_path,
        )

        self.assertIn(
            "SERVER FINAL VERIFIER FEEDBACK",
            text,
        )
        self.assertIn(
            "РЕЗУЛЬТАТ:\nFAIL",
            text,
        )
        self.assertIn(
            "Недостаточно доказательств",
            text,
        )
        self.assertNotIn(
            "{verdict}",
            text,
        )

    def test_07_final_audit_template_does_not_own_server_facts(self) -> None:
        record = get_registered_server_context_event(
            "final_audit.feedback"
        )
        self.assertIsNotNone(record)

        editable_template = record["default_template"]

        self.assertNotIn(
            "SERVER FACTS — NOT TEMPLATE CONTROLLED",
            editable_template,
        )
        self.assertNotIn(
            "SUCCESS_BLOCKED_CORRECTION_REQUESTED",
            editable_template,
        )
        self.assertNotIn(
            '"run_id"',
            editable_template,
        )


if __name__ == "__main__":
    unittest.main()
