"""Six intentional inner RED controls; patches affect disposable process RAM only."""
import json
import os
from pathlib import Path
import textwrap
import unittest
from unittest import mock

import test_web_alarm_wa4r006_local_gate as local
import test_web_alarm_wa4r002_diagnostics as diagnostic
import web_alarm.task_store as tasks
import web_alarm.event_checkpoint_store as events
import web_alarm.operation_store as operations


def old_method(name, module):
    entry = json.loads(Path(__file__).with_name("control-inputs.json").read_text(encoding="utf-8"))[name]
    namespace = dict(vars(module))
    exec(compile(textwrap.dedent(entry["code"]), "frozen-before:" + entry["file"] + ":" + name, "exec"), namespace)
    return namespace[name]


class Sensitivity(unittest.TestCase):
    def run_broken(self, selector, patch, expected):
        test = local.LocalGateTests(selector)
        result = unittest.TestResult()
        with patch:
            test.run(result)
        self.facts = [{"selector": test.id(), "inner_tests": result.testsRun,
                       "inner_failures": len(result.failures), "inner_errors": len(result.errors),
                       "inner_skips": len(result.skipped), "inner_facts": test.facts,
                       "failure": result.failures[0][1] if result.failures else None}]
        self.assertEqual((result.testsRun, len(result.failures), len(result.errors), len(result.skipped)), (1, 1, 0, 0))
        self.assertIn(expected, result.failures[0][1])

    def test_old_task_loader_exposes_false_completed(self):
        self.run_broken("test_task_identity_mismatch_blocks_gated_and_direct_completion",
                        mock.patch.object(tasks.TaskStore, "_load_task_from", old_method("_load_task_from", tasks)),
                        "mismatched TASK identity accepted completion")

    def test_old_plan_loader_exposes_foreign_plan_completion(self):
        self.run_broken("test_plan_identity_mismatch_blocks_gated_completion",
                        mock.patch.object(tasks.TaskStore, "_load_plan_from", old_method("_load_plan_from", tasks)),
                        "foreign plan accepted by closeout")

    def test_old_microtask_loader_exposes_foreign_parent_apply(self):
        actual = diagnostic.RaceEvidenceTests.run_actor

        def parent_actor(harness, name, action, mode="normal", exit_code=0):
            if name != "foreign_micro":
                return actual(harness, name, action, mode, exit_code)
            outcome = local.MutationExecutor(harness.storage).execute(
                local.TASK, "m1", "op_diag", "write", "data.bin", payload=local.POST)
            selected = {key: outcome.get(key) for key in ("result", "result_code", "receipt", "claim_release")}
            harness.facts.append({"worker": name, "pid": os.getpid(), "exit": 0,
                                  "stdout": json.dumps(selected), "stderr": "",
                                  "control_execution": "same production API in parent to inherit RAM mutant"})
            return selected

        with mock.patch.object(diagnostic.RaceEvidenceTests, "run_actor", parent_actor):
            self.run_broken("test_foreign_microtask_parent_refuses_before_intent_and_apply",
                            mock.patch.object(tasks.TaskStore, "_load_microtask_from", old_method("_load_microtask_from", tasks)),
                            "EXECUTED")

    def test_old_event_reader_accepts_missing_delimiter(self):
        self.run_broken("test_unterminated_event_read_and_append_fail_without_modifying_prefix",
                        mock.patch.object(events.EventCheckpointStore, "read_events", old_method("read_events", events)),
                        "unterminated event accepted as durable history")

    def test_old_event_appender_splices_json_records(self):
        self.run_broken("test_unterminated_event_read_and_append_fail_without_modifying_prefix",
                        mock.patch.object(events.EventCheckpointStore, "append_event", old_method("append_event", events)),
                        "append joined onto an unterminated JSON record")

    def test_old_public_lock_creates_before_validating_identity(self):
        self.run_broken("test_invalid_closeout_and_public_lock_identity_create_no_lock_files",
                        mock.patch.object(operations.OperationStore, "_serialized", old_method("_serialized", operations)),
                        "invalid task lock acquired")
