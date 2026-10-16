"""Negative controls for CLAUDE-WA4-R-AUD010205-REPAIR-001 (RAM only, no production file is touched).

Each control re-installs ONE pre-repair method, taken byte-exact from ../baseline/web_alarm/*.py
(AST slice), into the running process and runs ONE repair test. Outer PASS requires exactly
1 inner test with 1 FAIL / 0 ERROR / 0 SKIP and the expected message: the test catches that
specific regression.
"""
from __future__ import annotations

import ast
import textwrap
import unittest
from pathlib import Path
from unittest import mock

import test_web_alarm_aud010205_repair as repair
import web_alarm.event_checkpoint_store as events
import web_alarm.operation_store as operations
import web_alarm.projection as projection

BASELINE = Path(__file__).resolve().parent.parent / "baseline" / "web_alarm"


def method_source(text: str, class_name: str, method: str) -> str:
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == method:
                    lines = text.splitlines(keepends=True)
                    start = (item.decorator_list[0].lineno if item.decorator_list else item.lineno) - 1
                    return textwrap.dedent("".join(lines[start:item.end_lineno]))
    raise LookupError(f"{class_name}.{method}")


def pre_repair(module, class_name: str, method: str):
    old = method_source((BASELINE / (module.__name__.rsplit(".", 1)[1] + ".py")).read_text(encoding="utf-8"),
                        class_name, method)
    current = method_source(Path(module.__file__).read_text(encoding="utf-8"), class_name, method)
    assert old != current, f"{class_name}.{method} is not changed by the repair: no mutant"
    namespace = dict(vars(module))
    exec(compile(old, f"baseline:{class_name}.{method}", "exec"), namespace)
    return namespace[method]


class RepairSensitivity(unittest.TestCase):
    def run_broken(self, case, selector, patch, expected):
        test = case(selector)
        result = unittest.TestResult()
        with patch:
            test.run(result)
        self.facts = [{"selector": test.id(), "inner": [result.testsRun, len(result.failures), len(result.errors),
                                                         len(result.skipped)],
                       "failure_tail": result.failures[0][1][-400:] if result.failures else None,
                       "error_tail": result.errors[0][1][-400:] if result.errors else None,
                       "inner_facts": getattr(test, "facts", None)}]
        self.assertEqual((result.testsRun, len(result.failures), len(result.errors), len(result.skipped)),
                         (1, 1, 0, 0))
        self.assertIn(expected, result.failures[0][1])

    def test_pre_repair_reader_is_caught(self):
        self.run_broken(repair.EventFramingTests, "test_pre_repair_records_with_raw_separators_stay_readable",
                        mock.patch.object(events.EventCheckpointStore, "read_events",
                                          pre_repair(events, "EventCheckpointStore", "read_events")),
                        "a valid pre-repair record with a raw separator became unreadable")

    def test_pre_repair_writer_is_caught(self):
        self.run_broken(repair.EventFramingTests, "test_separator_characters_round_trip_and_are_escaped_on_write",
                        mock.patch.object(events.EventCheckpointStore, "append_event",
                                          pre_repair(events, "EventCheckpointStore", "append_event")),
                        "raw line separator written into the JSONL log")

    def test_pre_repair_admission_is_caught(self):
        self.run_broken(repair.AdmissionTests, "test_torn_history_refuses_new_operation_without_artifacts",
                        mock.patch.object(operations.OperationStore, "begin",
                                          pre_repair(operations, "OperationStore", "begin")),
                        "a refused admission left durable artifacts or changed bytes")

    def test_pre_repair_projection_is_caught(self):
        self.run_broken(repair.CloseoutHistoryTests, "test_torn_history_without_operations_blocks_closeout",
                        mock.patch.object(projection.ProjectionService, "build",
                                          pre_repair(projection, "ProjectionService", "build")),
                        "closeout completed a TASK with unreadable history")


if __name__ == "__main__":
    unittest.main()
