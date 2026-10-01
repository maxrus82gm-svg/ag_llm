from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import server
from context_storage import new_task_block_id
from run_store import get_run_index_entry, load_run_summary


class ProviderAuthFailureRunStoreTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_credentials_closes_run_as_failed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            workspace = base / "workspace"
            workspace.mkdir()
            runtime_root = base / "runtime"
            runtime_paths = {
                "backup_dir": str(runtime_root / "backup"),
                "log_dir": str(runtime_root / "logs"),
            }
            permissions = {
                "allow_read": True,
                "allow_write": False,
                "allow_delete": False,
                "allow_verify": True,
                "allow_guard_p1": True,
                "read_scope": ".",
                "write_scope": ".",
                "delete_scope": ".",
                "tool_limit": 20,
                "auto_backup": False,
            }
            task_block_id = new_task_block_id()
            events = []

            with (
                patch.object(
                    server,
                    "get_access_token",
                    AsyncMock(
                        side_effect=RuntimeError(
                            "Не найдена переменная среды GIGACHAT_CREDENTIALS."
                        )
                    ),
                ),
                patch.object(
                    server,
                    "load_agent_global_context",
                    return_value="ROLE",
                ),
                patch.object(
                    server,
                    "ensure_workspace_runtime_dirs",
                    return_value=runtime_paths,
                ),
            ):
                with self.assertRaisesRegex(
                    RuntimeError,
                    "Не удалось получить токен GigaChat",
                ):
                    await server.run_agent_task(
                        "AUTH FAILURE PROBE",
                        str(workspace),
                        permissions=permissions,
                        task_block_id=task_block_id,
                        planner_enabled=True,
                        final_audit_enabled=True,
                        on_event=events.append,
                    )

            started = next(
                event for event in events if event["event"] == "run_started"
            )
            failed = next(
                event for event in events if event["event"] == "run_failed"
            )
            run_id = started["run_id"]

            self.assertEqual(failed["reason"], "provider_auth_error")
            self.assertEqual(failed["api_requests"], 0)
            self.assertEqual(failed["tool_calls"], 0)

            summary = load_run_summary(workspace, run_id)
            self.assertIsNotNone(summary)
            self.assertEqual(summary["run_status"], "FAILED")
            self.assertEqual(summary["final_audit"], "NOT_RUN")
            self.assertEqual(summary["usage"]["total"]["calls"], 0)
            self.assertEqual(summary["provider_accounting"]["started_ids"], [])
            self.assertEqual(summary["provider_accounting"]["terminal_ids"], [])
            self.assertTrue(summary["provider_accounting"]["complete"])

            index_entry = get_run_index_entry(workspace, run_id)
            self.assertIsNotNone(index_entry)
            self.assertEqual(index_entry["run_status"], "FAILED")
            self.assertEqual(index_entry["final_audit"], "NOT_RUN")


if __name__ == "__main__":
    unittest.main()
