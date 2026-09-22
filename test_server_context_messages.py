import tempfile
import unittest
from pathlib import Path

from server_context_messages import (
    delete_server_context_message,
    list_registered_server_context_events,
    list_server_context_event_records,
    register_server_context_event,
    resolve_server_context_message,
    upsert_server_context_message,
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
        self.path = Path(self.temp_dir.name) / "server_context_messages.json"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def records(self) -> dict[str, dict]:
        payload = list_server_context_event_records(path=self.path)
        return {item["event_id"]: item for item in payload["records"]}

    def test_01_registry_exposes_real_active_events_without_json(self) -> None:
        registered = {
            item["event_id"]
            for item in list_registered_server_context_events()
        }
        self.assertTrue(ACTIVE_EVENT_IDS.issubset(registered))
        self.assertNotIn("tool_budget.low", registered)
        self.assertFalse(self.path.exists())

        records = self.records()
        for event_id in ACTIVE_EVENT_IDS:
            self.assertEqual(records[event_id]["status"], "ACTIVE")
            self.assertFalse(records[event_id]["has_override"])
            self.assertTrue(records[event_id]["default_template"])
        self.assertFalse(self.path.exists())

    def test_02_active_default_override_and_reset(self) -> None:
        variables = {"capability": "WRITE", "tool_name": "write_file"}
        default_text = resolve_server_context_message(
            "permission.denied", variables, path=self.path
        )
        self.assertIn("WRITE", default_text)
        self.assertEqual(
            self.records()["permission.denied"]["status"], "ACTIVE"
        )

        upsert_server_context_message(
            "permission.denied",
            "Пользовательское описание.",
            "Custom {capability} for {tool_name}",
            path=self.path,
        )
        overridden = self.records()["permission.denied"]
        self.assertEqual(overridden["status"], "ACTIVE + OVERRIDE")
        self.assertEqual(
            resolve_server_context_message(
                "permission.denied", variables, path=self.path
            ),
            "Custom WRITE for write_file",
        )

        self.assertTrue(
            delete_server_context_message(
                "permission.denied", path=self.path
            )
        )
        reset = self.records()["permission.denied"]
        self.assertEqual(reset["status"], "ACTIVE")
        self.assertEqual(
            resolve_server_context_message(
                "permission.denied", variables, path=self.path
            ),
            default_text,
        )

    def test_03_draft_can_be_created_and_deleted(self) -> None:
        event_id = "final_report.facts"
        upsert_server_context_message(
            event_id,
            "Будущее событие.",
            "Future {value}",
            path=self.path,
        )
        record = self.records()[event_id]
        self.assertEqual(record["status"], "DRAFT")
        self.assertFalse(record["is_active"])

        self.assertTrue(
            delete_server_context_message(event_id, path=self.path)
        )
        self.assertNotIn(event_id, self.records())

    def test_04_generic_registration_automatically_becomes_active(self) -> None:
        event_id = "test.dynamic_event"
        upsert_server_context_message(
            event_id,
            "Заранее созданный draft.",
            "Draft override {value}",
            path=self.path,
        )
        self.assertEqual(self.records()[event_id]["status"], "DRAFT")

        register_server_context_event(
            event_id,
            "Динамически зарегистрированное событие.",
            "Dynamic {value}",
        )
        record = self.records()[event_id]
        self.assertEqual(record["status"], "ACTIVE + OVERRIDE")
        self.assertEqual(
            resolve_server_context_message(
                event_id, {"value": 42}, path=self.path
            ),
            "Draft override 42",
        )

    def test_05_corrupt_json_keeps_registry_and_default_available(self) -> None:
        self.path.write_text("{broken", encoding="utf-8")
        payload = list_server_context_event_records(path=self.path)
        records = {item["event_id"]: item for item in payload["records"]}
        self.assertTrue(payload["diagnostics"])
        self.assertEqual(records["permission.denied"]["status"], "ACTIVE")

        diagnostics = []
        with self.assertWarns(RuntimeWarning):
            text = resolve_server_context_message(
                "permission.denied",
                {"capability": "READ", "tool_name": "read_file"},
                path=self.path,
                on_warning=diagnostics.append,
            )
        self.assertIn("READ", text)
        self.assertEqual(diagnostics[-1]["fallback"], "default_text")

    def test_06_invalid_override_template_falls_back_to_registry_default(self) -> None:
        upsert_server_context_message(
            "tool.error",
            "Ошибка tool.",
            "Unknown {missing}",
            path=self.path,
        )
        diagnostics = []
        with self.assertWarns(RuntimeWarning):
            text = resolve_server_context_message(
                "tool.error",
                {
                    "tool_name": "read_file",
                    "error_type": "ValueError",
                    "error_message": "bad path",
                },
                path=self.path,
                on_warning=diagnostics.append,
            )
        self.assertIn("read_file", text)
        self.assertIn("ValueError", text)
        self.assertEqual(diagnostics[-1]["fallback"], "default_text")

    def test_07_final_audit_feedback_default_is_russian_and_resolves(self) -> None:
        variables = {
            "verdict": "FAIL",
            "reason": "Недостаточно доказательств.",
            "violations_lines": "- Не выполнена проверка.",
            "required_action": "Выполнить проверку.",
            "verifier_run_id": "ver-1",
            "check_type": "FINAL",
            "correction_cycle": 1,
            "correction_limit": 2,
            "remaining_corrections": 1,
        }
        text = resolve_server_context_message(
            "final_audit.feedback", variables, path=self.path
        )
        self.assertIn("SERVER FINAL VERIFIER FEEDBACK", text)
        self.assertIn("РЕЗУЛЬТАТ:\nFAIL", text)
        self.assertIn("Недостаточно доказательств", text)
        self.assertIn("Не выполнена проверка", text)
        self.assertIn("Выполнить проверку", text)
        self.assertIn("1 из 2", text)
        self.assertIn("ОСТАЛОСЬ КОРРЕКЦИЙ: 1", text)
        self.assertIn("НЕ новая пользовательская задача", text)
        self.assertNotIn("{verdict}", text)
        self.assertEqual(
            self.records()["final_audit.feedback"]["status"], "ACTIVE"
        )

    def test_08_final_audit_feedback_override_and_invalid_fallback(self) -> None:
        variables = {
            "verdict": "FAIL",
            "reason": "Причина",
            "violations_lines": "- Нарушение",
            "required_action": "Исправить",
            "verifier_run_id": "ver-1",
            "check_type": "FINAL",
            "correction_cycle": 1,
            "correction_limit": 2,
            "remaining_corrections": 1,
        }
        upsert_server_context_message(
            "final_audit.feedback",
            "Пользовательская подача feedback.",
            "CUSTOM {verdict}: {reason} / {required_action}",
            path=self.path,
        )
        self.assertEqual(
            resolve_server_context_message(
                "final_audit.feedback", variables, path=self.path
            ),
            "CUSTOM FAIL: Причина / Исправить",
        )

        upsert_server_context_message(
            "final_audit.feedback",
            "Некорректный override.",
            "BROKEN {unknown}",
            path=self.path,
        )
        diagnostics = []
        with self.assertWarns(RuntimeWarning):
            fallback = resolve_server_context_message(
                "final_audit.feedback",
                variables,
                path=self.path,
                on_warning=diagnostics.append,
            )
        self.assertIn("SERVER FINAL VERIFIER FEEDBACK", fallback)
        self.assertIn("Причина", fallback)
        self.assertEqual(diagnostics[-1]["fallback"], "default_text")

    def test_09_final_audit_template_does_not_own_server_facts(self) -> None:
        record = self.records()["final_audit.feedback"]
        editable_template = record["default_template"]
        self.assertNotIn("SERVER FACTS — NOT TEMPLATE CONTROLLED", editable_template)
        self.assertNotIn("SUCCESS_BLOCKED_CORRECTION_REQUESTED", editable_template)
        self.assertNotIn('"run_id"', editable_template)


if __name__ == "__main__":
    unittest.main()
