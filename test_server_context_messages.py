import tempfile
import unittest
from pathlib import Path

from server_context_messages import (
    delete_server_context_message,
    list_server_context_messages,
    resolve_server_context_message,
    upsert_server_context_message,
)


class ServerContextMessagesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / "server_context_messages.json"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_fallback_custom_and_delete(self) -> None:
        default_text = "Default for {capability}"
        variables = {"capability": "WRITE"}

        self.assertEqual(
            resolve_server_context_message(
                "permission.denied",
                default_text,
                variables,
                path=self.path,
            ),
            "Default for WRITE",
        )

        upsert_server_context_message(
            "permission.denied",
            "Permission отказан.",
            "Custom for {capability}",
            path=self.path,
        )
        self.assertEqual(
            resolve_server_context_message(
                "permission.denied",
                default_text,
                variables,
                path=self.path,
            ),
            "Custom for WRITE",
        )

        self.assertTrue(
            delete_server_context_message(
                "permission.denied", path=self.path
            )
        )
        self.assertEqual(
            resolve_server_context_message(
                "permission.denied",
                default_text,
                variables,
                path=self.path,
            ),
            "Default for WRITE",
        )

    def test_unknown_placeholder_and_corrupt_file_fall_back(self) -> None:
        diagnostics = []
        upsert_server_context_message(
            "tool.error",
            "Ошибка tool.",
            "Unknown {missing}",
            path=self.path,
        )
        with self.assertWarns(RuntimeWarning):
            text = resolve_server_context_message(
                "tool.error",
                "Safe {tool_name}",
                {"tool_name": "read_file"},
                path=self.path,
                on_warning=diagnostics.append,
            )
        self.assertEqual(text, "Safe read_file")
        self.assertEqual(diagnostics[-1]["fallback"], "default_text")

        self.path.write_text("{broken", encoding="utf-8")
        with self.assertWarns(RuntimeWarning):
            text = resolve_server_context_message(
                "tool.error",
                "Still safe",
                path=self.path,
                on_warning=diagnostics.append,
            )
        self.assertEqual(text, "Still safe")

    def test_arbitrary_event_id_is_visible_through_generic_api(self) -> None:
        event_id = "final_report.facts"
        upsert_server_context_message(
            event_id,
            "Будущее событие.",
            "Future {value}",
            path=self.path,
        )
        records = list_server_context_messages(path=self.path)
        self.assertEqual([item["event_id"] for item in records], [event_id])
        self.assertEqual(
            resolve_server_context_message(
                event_id,
                "Fallback",
                {"value": 42},
                path=self.path,
            ),
            "Future 42",
        )

    def test_default_text_preserves_structured_braces(self) -> None:
        default_text = 'State: {"decision": "DENIED"}; tool={tool_name}'
        self.assertEqual(
            resolve_server_context_message(
                "tool.error",
                default_text,
                {"tool_name": "write_file"},
                path=self.path,
            ),
            'State: {"decision": "DENIED"}; tool=write_file',
        )


if __name__ == "__main__":
    unittest.main()
