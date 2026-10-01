from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import context_storage as cs


class ChatCreateAtomicityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name) / "workspace"
        self.workspace.mkdir()
        self.info = cs.ensure_workspace_storage(self.workspace)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    @property
    def chats_dir(self) -> Path:
        return self.workspace / cs.ULTRA_DIRNAME / "chats"

    @property
    def staging_root(self) -> Path:
        return self.workspace / cs.ULTRA_DIRNAME / "chat_staging"

    def visible_chat_dirs(self) -> list[Path]:
        return sorted(
            item
            for item in self.chats_dir.iterdir()
            if item.is_dir() and item.name.startswith("chat_")
        )

    def test_create_chat_publishes_complete_directory_atomically(self) -> None:
        chat = cs.create_chat(self.workspace, "Atomic Chat")
        chat_dir = self.chats_dir / chat["chat_id"]

        self.assertTrue((chat_dir / "metadata.json").is_file())
        self.assertTrue((chat_dir / "messages").is_dir())
        self.assertTrue((chat_dir / "summaries").is_dir())
        self.assertFalse(self.staging_root.exists())
        listed = cs.list_existing_chats(
            self.workspace,
            expected_workspace_id=self.info["workspace_id"],
        )
        self.assertEqual([item["chat_id"] for item in listed], [chat["chat_id"]])

    def test_metadata_failure_does_not_leave_visible_or_staging_orphan(self) -> None:
        with patch.object(
            cs,
            "_atomic_write_json",
            side_effect=RuntimeError("metadata write failed"),
        ):
            with self.assertRaisesRegex(RuntimeError, "metadata write failed"):
                cs.create_chat(self.workspace, "Broken Metadata")

        self.assertEqual(self.visible_chat_dirs(), [])
        self.assertFalse(self.staging_root.exists())
        self.assertEqual(
            cs.list_existing_chats(
                self.workspace,
                expected_workspace_id=self.info["workspace_id"],
            ),
            [],
        )

    def test_publish_failure_does_not_leave_visible_or_staging_orphan(self) -> None:
        with patch.object(
            cs,
            "_publish_chat_directory",
            side_effect=PermissionError("publish locked"),
        ):
            with self.assertRaisesRegex(PermissionError, "publish locked"):
                cs.create_chat(self.workspace, "Broken Publish")

        self.assertEqual(self.visible_chat_dirs(), [])
        self.assertFalse(self.staging_root.exists())

    def test_legacy_directory_without_metadata_is_not_a_visible_chat(self) -> None:
        orphan = self.chats_dir / ("chat_" + "a" * 32)
        orphan.mkdir()
        (orphan / "messages").mkdir()
        (orphan / "summaries").mkdir()

        self.assertEqual(
            cs.list_existing_chats(
                self.workspace,
                expected_workspace_id=self.info["workspace_id"],
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()
