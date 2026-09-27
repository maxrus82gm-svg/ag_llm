from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from context_registry import (
    delete_context_variant,
    get_context_record,
    list_context_groups,
    list_context_records,
    resolve_context_text,
    save_context_variant,
    set_active_variant,
)


class ContextRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.state_path = Path(self.temp_dir.name) / "contexts.json"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_01_factory_catalog_loads(self) -> None:
        groups = list_context_groups()
        self.assertIn(
            {"group_id": "server_events", "group_name": "Серверные события"},
            groups,
        )
        self.assertIn(
            {"group_id": "planner", "group_name": "Planner"},
            groups,
        )
        records = list_context_records(state_path=self.state_path)
        ids = {item["context_id"] for item in records}
        self.assertIn("task.stage", ids)
        self.assertIn("permission.denied", ids)
        self.assertTrue({
            "planner.base", "planner.initial", "planner.readiness", "planner.replan",
        }.issubset(ids))

    def test_02_factory_default_resolves(self) -> None:
        text = resolve_context_text(
            "permission.denied",
            {"capability": "WRITE", "tool_name": "write_file"},
            state_path=self.state_path,
        )
        self.assertIn("WRITE", text)
        self.assertIn("write_file", text)
        record = get_context_record(
            "permission.denied",
            state_path=self.state_path,
        )
        self.assertEqual(record["active_variant"], "default")
        self.assertEqual(record["effective_source"], "FACTORY_DEFAULT")

    def test_03_custom_variant_switches_without_touching_factory(self) -> None:
        save_context_variant(
            "permission.denied",
            "custom",
            "CUSTOM {capability} / {tool_name}",
            description="Тестовый пользовательский вариант.",
            state_path=self.state_path,
        )
        set_active_variant(
            "permission.denied",
            "custom",
            state_path=self.state_path,
        )
        text = resolve_context_text(
            "permission.denied",
            {"capability": "WRITE", "tool_name": "replace_text"},
            state_path=self.state_path,
        )
        self.assertEqual(text, "CUSTOM WRITE / replace_text")

        record = get_context_record(
            "permission.denied",
            state_path=self.state_path,
        )
        self.assertEqual(record["active_variant"], "custom")
        self.assertEqual(record["factory_text"].startswith("Capability "), True)

    def test_04_default_can_be_edited_as_data(self) -> None:
        save_context_variant(
            "task.stage",
            "default",
            "НОВЫЙ DEFAULT TASK STAGE",
            description="Рабочий default, изменённый через storage.",
            state_path=self.state_path,
        )
        text = resolve_context_text(
            "task.stage",
            state_path=self.state_path,
        )
        self.assertEqual(text, "НОВЫЙ DEFAULT TASK STAGE")
        record = get_context_record(
            "task.stage",
            state_path=self.state_path,
        )
        self.assertTrue(record["has_default_override"])
        self.assertNotEqual(record["factory_text"], record["default_text"])

    def test_05_unknown_placeholder_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            save_context_variant(
                "permission.denied",
                "custom",
                "BROKEN {unknown}",
                description="Некорректный тест.",
                state_path=self.state_path,
            )

    def test_06_delete_active_custom_returns_to_default(self) -> None:
        save_context_variant(
            "tool.error",
            "custom",
            "CUSTOM {tool_name}: {error_type}: {error_message}",
            description="Кастомное сообщение tool error.",
            state_path=self.state_path,
        )
        set_active_variant(
            "tool.error",
            "custom",
            state_path=self.state_path,
        )
        delete_context_variant(
            "tool.error",
            "custom",
            state_path=self.state_path,
        )
        record = get_context_record(
            "tool.error",
            state_path=self.state_path,
        )
        self.assertEqual(record["active_variant"], "default")

    def test_07_planner_base_and_each_mode_resolve(self) -> None:
        base = resolve_context_text("planner.base", state_path=self.state_path)
        initial = resolve_context_text(
            "planner.initial", {"plan_format": "INITIAL_FORMAT"},
            state_path=self.state_path,
        )
        readiness = resolve_context_text(
            "planner.readiness", state_path=self.state_path,
        )
        replan = resolve_context_text(
            "planner.replan", {"plan_format": "REPLAN_FORMAT"},
            state_path=self.state_path,
        )

        self.assertIn("separate tool-free Task Planner", base)
        self.assertIn("INITIAL_FORMAT", initial)
        self.assertIn("open_persistence_obligations", readiness)
        self.assertIn("REPLAN_FORMAT", replan)

    def test_08_planner_switches_default_and_custom_without_restart(self) -> None:
        factory_default = resolve_context_text(
            "planner.base", state_path=self.state_path,
        )
        save_context_variant(
            "planner.base",
            "custom",
            "CUSTOM PLANNER BASE",
            description="Тестовый Planner context.",
            state_path=self.state_path,
        )
        set_active_variant(
            "planner.base", "custom", state_path=self.state_path,
        )
        self.assertEqual(
            resolve_context_text("planner.base", state_path=self.state_path),
            "CUSTOM PLANNER BASE",
        )

        set_active_variant(
            "planner.base", "default", state_path=self.state_path,
        )
        self.assertEqual(
            resolve_context_text("planner.base", state_path=self.state_path),
            factory_default,
        )


if __name__ == "__main__":
    unittest.main()
