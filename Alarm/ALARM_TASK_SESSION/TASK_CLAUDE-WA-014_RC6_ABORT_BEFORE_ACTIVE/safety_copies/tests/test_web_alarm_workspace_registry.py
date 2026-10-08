import json
import tempfile
import unittest
from pathlib import Path

from web_alarm.workspace_registry import (
    WorkspaceRegistry,
    WorkspaceRegistryError,
)


class WorkspaceRegistryTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.storage = self.root / "state"
        self.project_a = self.root / "project_a"
        self.project_b = self.root / "project_b"
        self.project_a.mkdir()
        self.project_b.mkdir()
        (self.project_a / "marker.txt").write_text("A", encoding="utf-8")
        (self.project_b / "marker.txt").write_text("B", encoding="utf-8")

    def tearDown(self):
        self.tempdir.cleanup()

    def test_registers_two_external_workspaces_without_copying_projects(self):
        registry = WorkspaceRegistry(self.storage)
        a = registry.register("Project A", self.project_a)
        b = registry.register("Project B", self.project_b)

        self.assertNotEqual(a.workspace_id, b.workspace_id)
        self.assertEqual(Path(a.workspace_root), self.project_a.resolve())
        self.assertEqual(Path(b.workspace_root), self.project_b.resolve())
        self.assertTrue(
            (self.storage / "workspaces" / f"{a.workspace_id}.json").is_file()
        )
        self.assertTrue(
            (self.storage / "workspaces" / f"{b.workspace_id}.json").is_file()
        )
        self.assertFalse((self.storage / "marker.txt").exists())
        self.assertEqual(len(registry.list()), 2)

    def test_registration_survives_new_registry_instance(self):
        first = WorkspaceRegistry(self.storage)
        saved = first.register("Project A", self.project_a)

        reopened = WorkspaceRegistry(self.storage)
        loaded = reopened.get(saved.workspace_id)

        self.assertEqual(loaded.workspace_id, saved.workspace_id)
        self.assertEqual(loaded.display_name, "Project A")
        self.assertEqual(loaded.workspace_root, str(self.project_a.resolve()))
        self.assertEqual(loaded.created_at, saved.created_at)

    def test_same_root_reuses_existing_identity(self):
        registry = WorkspaceRegistry(self.storage)
        first = registry.register("Project A", self.project_a)
        second = registry.register("Project A", self.project_a)

        self.assertEqual(second.workspace_id, first.workspace_id)
        self.assertEqual(len(registry.list()), 1)

    def test_find_by_root_returns_persisted_registration(self):
        registry = WorkspaceRegistry(self.storage)
        saved = registry.register("Project A", self.project_a)

        found = WorkspaceRegistry(self.storage).find_by_root(self.project_a)

        self.assertIsNotNone(found)
        self.assertEqual(found.workspace_id, saved.workspace_id)

    def test_missing_or_file_root_fails_closed(self):
        registry = WorkspaceRegistry(self.storage)
        file_root = self.root / "not_a_directory.txt"
        file_root.write_text("x", encoding="utf-8")

        with self.assertRaises(WorkspaceRegistryError):
            registry.register("Missing", self.root / "missing")
        with self.assertRaises(WorkspaceRegistryError):
            registry.register("File", file_root)

    def test_unsafe_explicit_workspace_id_is_rejected(self):
        registry = WorkspaceRegistry(self.storage)

        with self.assertRaises(WorkspaceRegistryError):
            registry.register(
                "Project A",
                self.project_a,
                workspace_id="../escape",
            )

    def test_duplicate_root_cannot_be_claimed_by_another_explicit_id(self):
        registry = WorkspaceRegistry(self.storage)
        registry.register("Project A", self.project_a, workspace_id="ws_a")

        with self.assertRaises(WorkspaceRegistryError):
            registry.register("Project A", self.project_a, workspace_id="ws_b")

    def test_unknown_schema_version_fails_closed(self):
        registry = WorkspaceRegistry(self.storage)
        saved = registry.register("Project A", self.project_a)
        path = self.storage / "workspaces" / f"{saved.workspace_id}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["schema_version"] = 999
        path.write_text(json.dumps(payload), encoding="utf-8")

        with self.assertRaises(WorkspaceRegistryError):
            WorkspaceRegistry(self.storage).get(saved.workspace_id)


if __name__ == "__main__":
    unittest.main()
