import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import server


class FileEditingToolboxTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "workspace"
        self.root.mkdir()
        self.backup_dir = Path(self.temp.name) / "backup"
        self.backup_dir.mkdir()
        self.session = {
            "backup_dir": self.backup_dir,
            "backed_up_paths": set(),
            "delete_backed_up_paths": set(),
            "manifest": {"core_files": [], "changed_files": [], "new_files": [], "deleted_files": []},
        }
        self.policy = self.make_policy()

    def make_policy(self, **changes):
        values = {
            "allow_read": True, "allow_write": True, "allow_delete": True,
            "allow_verify": True, "allow_guard_p1": False,
            "read_scope": ".", "write_scope": ".", "delete_scope": ".",
            "tool_limit": 10,
        }
        values.update(changes)
        return server._prepare_policy_for_workspace(
            self.root, server._normalize_permissions(values)
        )

    def call(self, name, **arguments):
        return server._execute_agent_function(
            self.root, {"name": name, "arguments": arguments},
            self.policy, self.session,
        )

    def test_utf8_and_jsonl_write_read_share_logical_hash(self):
        for filename in ("plain.txt", "events.jsonl"):
            with self.subTest(filename=filename):
                written = self.call("write_file", path=filename, content="Привет\nnext\n")
                read = self.call("read_file", path=filename)
                self.assertEqual(read["content"], "Привет\nnext\n")
                self.assertEqual(written["content_sha256"], read["content_sha256"])
                raw = (self.root / filename).read_bytes()
                if filename.endswith(".jsonl"):
                    self.assertTrue(raw.startswith(b"\xff\xfe"))
                else:
                    self.assertEqual(raw, "Привет\nnext\n".encode("utf-8"))

    def test_find_text_zero_one_many_and_bounded_results(self):
        self.call("write_file", path="text.txt", content="alpha beta\nalpha alpha\n")
        zero = self.call("find_text", path="text.txt", text="missing")
        self.assertEqual(zero["count"], 0)
        one = self.call("find_text", path="text.txt", text="beta")
        self.assertEqual((one["count"], one["matches"][0]["line"], one["matches"][0]["column"]), (1, 1, 7))
        many = self.call("find_text", path="text.txt", text="alpha")
        self.assertEqual(many["count"], 3)
        self.assertEqual(many["matches"][2]["column"], 7)
        self.assertEqual(many["content_sha256"], one["content_sha256"])
        with patch.object(server, "MAX_FIND_TEXT_MATCHES", 1):
            limited = self.call("find_text", path="text.txt", text="alpha")
        self.assertEqual(len(limited["matches"]), 1)
        self.assertTrue(limited["truncated"])
        self.assertLessEqual(len(limited["matches"][0]["snippet"]), server.MAX_FIND_TEXT_SNIPPET_CHARS)

    def test_read_file_range_inclusive_and_strict_bounds(self):
        self.call("write_file", path="text.txt", content="one\ntwo\nthree\n")
        result = self.call("read_file_range", path="text.txt", start_line=2, end_line=3)
        self.assertEqual(result["content"], "two\nthree\n")
        self.assertEqual(result["total_lines"], 3)
        self.assertEqual(result["content_sha256"], self.call("read_file", path="text.txt")["content_sha256"])
        for start, end in ((0, 1), (2, 1), (1, 4), (True, 1), (1, 201)):
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                self.call("read_file_range", path="text.txt", start_line=start, end_line=end)

    def test_replace_unique_and_failed_edits_do_not_mutate(self):
        path = self.root / "text.txt"
        path.write_text("red blue green", encoding="utf-8")
        expected = self.call("find_text", path="text.txt", text="blue")["content_sha256"]
        result = self.call("replace_text", path="text.txt", old_text="blue", new_text="cyan", expected_content_sha256=expected)
        self.assertEqual(path.read_text(encoding="utf-8"), "red cyan green")
        self.assertEqual((result["removed_chars"], result["added_chars"]), (4, 4))
        self.assertNotIn("content", result)
        self.assertEqual(result["previous_content_sha256"], expected)
        self.assertEqual(result["content_sha256"], self.call("read_file", path="text.txt")["content_sha256"])
        current = path.read_bytes()
        for old, hash_value in (("absent", result["content_sha256"]), ("cyan", expected)):
            with self.subTest(old=old), self.assertRaises(ValueError):
                self.call("replace_text", path="text.txt", old_text=old, new_text="x", expected_content_sha256=hash_value)
            self.assertEqual(path.read_bytes(), current)
        path.write_text("same same", encoding="utf-8")
        duplicate_hash = self.call("read_file", path="text.txt")["content_sha256"]
        with self.assertRaises(ValueError):
            self.call("replace_text", path="text.txt", old_text="same", new_text="x", expected_content_sha256=duplicate_hash)
        self.assertEqual(path.read_text(encoding="utf-8"), "same same")

    def test_insert_before_after_and_ambiguous_marker(self):
        path = self.root / "text.txt"
        path.write_text("HEAD\nTAIL\n", encoding="utf-8")
        hash_value = self.call("read_file", path="text.txt")["content_sha256"]
        before = self.call("insert_before", path="text.txt", marker="TAIL", content="MIDDLE\n", expected_content_sha256=hash_value)
        self.assertEqual(path.read_text(encoding="utf-8"), "HEAD\nMIDDLE\nTAIL\n")
        after = self.call("insert_after", path="text.txt", marker="TAIL", content=" END", expected_content_sha256=before["content_sha256"])
        self.assertEqual(path.read_text(encoding="utf-8"), "HEAD\nMIDDLE\nTAIL END\n")
        duplicate = self.call("read_file", path="text.txt")["content_sha256"]
        with self.assertRaises(ValueError):
            self.call("insert_before", path="text.txt", marker="\n", content="X", expected_content_sha256=duplicate)
        self.assertEqual(path.read_text(encoding="utf-8"), "HEAD\nMIDDLE\nTAIL END\n")

    def test_stale_or_ambiguous_edit_never_starts_backup(self):
        path = self.root / "stable.txt"
        path.write_text("same same", encoding="utf-8")
        hash_value = self.call("read_file", path="stable.txt")["content_sha256"]
        with self.assertRaises(server.StaleFileStateError):
            self.call("replace_text", path="stable.txt", old_text="same", new_text="new", expected_content_sha256="0" * 64)
        with self.assertRaises(ValueError):
            self.call("insert_after", path="stable.txt", marker="same", content="!", expected_content_sha256=hash_value)
        self.assertEqual(path.read_text(encoding="utf-8"), "same same")
        self.assertEqual(self.session["manifest"]["changed_files"], [])
        self.assertFalse((self.backup_dir / "changed" / "stable.txt").exists())

    def test_jsonl_precise_edit_preserves_utf16(self):
        self.call("write_file", path="events.jsonl", content='{"event":"old"}\n')
        before = self.call("read_file", path="events.jsonl")
        result = self.call("replace_text", path="events.jsonl", old_text="old", new_text="new", expected_content_sha256=before["content_sha256"])
        self.assertEqual(self.call("read_file", path="events.jsonl")["content"], '{"event":"new"}\n')
        self.assertEqual(result["content_sha256"], self.call("read_file", path="events.jsonl")["content_sha256"])
        self.assertTrue((self.root / "events.jsonl").read_bytes().startswith(b"\xff\xfe"))

    def test_backup_is_created_before_precise_edit(self):
        path = self.root / "text.txt"
        path.write_text("old text", encoding="utf-8")
        hash_value = self.call("read_file", path="text.txt")["content_sha256"]
        original = server._write_logical_text

        def check_backup_then_write(target, content):
            self.assertEqual((self.backup_dir / "changed" / "text.txt").read_text(encoding="utf-8"), "old text")
            self.assertEqual(path.read_text(encoding="utf-8"), "old text")
            return original(target, content)

        with patch.object(server, "_write_logical_text", side_effect=check_backup_then_write):
            self.call("replace_text", path="text.txt", old_text="old", new_text="new", expected_content_sha256=hash_value)
        self.assertEqual(path.read_text(encoding="utf-8"), "new text")
        self.assertEqual(self.session["manifest"]["changed_files"], ["text.txt"])

    def test_mutation_bookkeeping_and_final_audit_evidence(self):
        (self.root / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
        expected = self.call("read_file", path="module.py")["content_sha256"]
        result = self.call("replace_text", path="module.py", old_text="1", new_text="2", expected_content_sha256=expected)
        state = {
            "write_revision": 0, "python_write_revision": None,
            "python_verified_revision": None, "python_verified_paths": [],
            "git_status_revision": 0, "git_diff_revision": 0,
            "ui_smoke_required": False, "ui_smoke_write_revision": None,
            "ui_smoke_verified_revision": None,
            "changed_python_paths": [], "deleted_python_paths": [],
        }
        owned = {}
        server._bookkeep_successful_mutation(
            function_name="replace_text", result=result,
            run_owned_state=owned, verification_state=state,
        )
        self.assertEqual(state["write_revision"], 1)
        self.assertEqual(state["changed_python_paths"], ["module.py"])
        self.assertIsNone(state["git_status_revision"])
        self.assertEqual(owned["module.py"]["content_sha256"], result["content_sha256"])
        self.assertEqual([entry["tool"] for entry in server._verification_missing_requirements(state)], ["python_compile"])
        context, metadata = server._collect_final_audit_evidence(
            root=self.root, candidate_final="Done", policy=self.policy,
            run_id="test", api_request_count=1, tool_call_count=1,
            verification_state=state, backup_session=self.session,
            run_owned_state=owned,
        )
        self.assertFalse(metadata["critical_for_success"])
        self.assertTrue(json.loads(context)["run_owned_filesystem_evidence"][0]["match"])
        for filename in ("server.py", "ultra_ui.py"):
            with self.subTest(filename=filename):
                local_state = dict(state, write_revision=0, changed_python_paths=[],
                                   ui_smoke_required=False)
                server._bookkeep_successful_mutation(
                    function_name="insert_after",
                    result={"path": filename, "content_sha256": result["content_sha256"]},
                    run_owned_state={}, verification_state=local_state,
                )
                self.assertTrue(local_state["ui_smoke_required"])
                self.assertEqual({item["tool"] for item in server._verification_missing_requirements(local_state)},
                                 {"python_compile", "ui_smoke_test"})

    def test_permission_scope_denial_and_tool_exposure(self):
        (self.root / "inside").mkdir()
        (self.root / "outside.txt").write_text("secret", encoding="utf-8")
        policy = self.make_policy(read_scope="inside", write_scope="inside", delete_scope="inside")
        with self.assertRaises(PermissionError):
            server._agent_find_text(self.root, "outside.txt", "secret", policy)
        with self.assertRaises(PermissionError):
            server._agent_read_file_range(self.root, "outside.txt", 1, 1, policy)
        with self.assertRaises(PermissionError):
            server._agent_precise_edit(self.root, "replace_text", "outside.txt", "secret", "x", "0" * 64, policy, self.session)
        self.assertEqual((self.root / "outside.txt").read_text(encoding="utf-8"), "secret")
        read_only = self.make_policy(allow_write=False, allow_delete=False)
        names = {item["name"] for item in server._functions_for_policy(read_only)}
        self.assertIn("find_text", names)
        self.assertNotIn("replace_text", names)
        for bad_path in ("../outside.txt", str(self.root / "outside.txt")):
            with self.assertRaises(ValueError):
                server._agent_find_text(self.root, bad_path, "secret", self.policy)


if __name__ == "__main__":
    unittest.main()
