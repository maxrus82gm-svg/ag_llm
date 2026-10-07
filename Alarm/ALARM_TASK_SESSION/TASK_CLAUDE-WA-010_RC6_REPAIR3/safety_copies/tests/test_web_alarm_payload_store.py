import hashlib
import tempfile
import unittest
from pathlib import Path

from web_alarm.file_state import (
    UTF8_BOM,
    eol_only_drift,
    observe_bytes,
    observe_path,
)
from web_alarm.payload_store import (
    PayloadIntegrityError,
    PayloadScopeError,
    PayloadStore,
)
from web_alarm.task_store import TaskStore
from web_alarm.workspace_registry import WorkspaceRegistry


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class FileStateTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_authority_is_exact_bytes_and_eol_bom_are_diagnostic(self):
        cases = {
            b"": "none",
            b"no newline": "none",
            b"a\nb\n": "lf",
            b"a\r\nb\r\n": "crlf",
            b"a\r\nb\n": "mixed",
            b"a\rb": "mixed",
        }
        for data, eol in cases.items():
            with self.subTest(data=data):
                state = observe_bytes(data)
                self.assertTrue(state.exists)
                self.assertEqual(state.size, len(data))
                self.assertEqual(state.sha256, sha256(data))
                self.assertEqual(state.eol, eol)
                self.assertFalse(state.bom)

    def test_normalized_hash_ignores_crlf_and_bom_but_authority_does_not(self):
        lf = observe_bytes(b"a\nb\n")
        crlf = observe_bytes(b"a\r\nb\r\n")
        bom = observe_bytes(UTF8_BOM + b"a\nb\n")

        self.assertNotEqual(lf.sha256, crlf.sha256)
        self.assertEqual(lf.normalized_sha256, crlf.normalized_sha256)
        self.assertEqual(lf.normalized_sha256, bom.normalized_sha256)
        self.assertTrue(bom.bom)
        self.assertTrue(eol_only_drift(lf, crlf))
        self.assertFalse(eol_only_drift(lf, observe_bytes(b"a\nc\n")))
        self.assertFalse(eol_only_drift(lf, lf))

    def test_streaming_read_keeps_crlf_pair_across_chunk_boundary(self):
        data = b"x" * (64 * 1024 - 1) + b"\r\n" + b"y" * 10
        path = self.root / "big.txt"
        path.write_bytes(data)

        state = observe_path(path)

        self.assertEqual(state, observe_bytes(data))
        self.assertEqual(state.eol, "crlf")
        self.assertEqual(state.normalized_sha256, sha256(data.replace(b"\r\n", b"\n")))

    def test_absent_path_has_no_file_metadata(self):
        state = observe_path(self.root / "missing.txt")

        self.assertFalse(state.exists)
        self.assertIsNone(state.size)
        self.assertIsNone(state.sha256)


class PayloadStoreTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.storage = self.root / "state"
        self.project = self.root / "project"
        self.project.mkdir()
        workspace = WorkspaceRegistry(self.storage).register(
            "Project", self.project, workspace_id="ws_payload"
        )
        TaskStore(self.storage).create_task(
            workspace.workspace_id,
            "Payload Task",
            "RAW TASK",
            "Store payloads",
            task_id="task_payload",
        )
        self.store = PayloadStore(self.storage, max_bytes=64)

    def tearDown(self):
        self.tempdir.cleanup()

    def blob_path(self, ref):
        return (
            self.storage / "tasks" / "active" / "task_payload" / "payloads"
            / f"{ref['sha256']}.bin"
        )

    def test_put_is_content_addressed_immutable_and_verified_on_read(self):
        data = b"line 1\r\nline 2\n"

        first = self.store.put("task_payload", data, forbidden_roots=[self.project])
        second = PayloadStore(self.storage, max_bytes=64).put("task_payload", data)

        self.assertEqual(first, second)
        self.assertEqual(first["sha256"], sha256(data))
        self.assertEqual(first["size"], len(data))
        self.assertEqual(self.blob_path(first).read_bytes(), data)
        self.assertEqual(PayloadStore(self.storage).read("task_payload", first), data)
        self.assertFalse(any(self.project.rglob("*")))

    def test_corrupted_missing_or_resized_blob_fails_closed(self):
        ref = self.store.put("task_payload", b"original")
        path = self.blob_path(ref)

        path.write_bytes(b"originaX")
        with self.assertRaises(PayloadIntegrityError):
            self.store.read("task_payload", ref)
        with self.assertRaises(PayloadIntegrityError):
            self.store.put("task_payload", b"original")
        self.assertEqual(path.read_bytes(), b"originaX")

        path.write_bytes(b"original+")
        with self.assertRaises(PayloadIntegrityError):
            self.store.read("task_payload", ref)

        path.unlink()
        with self.assertRaises(PayloadIntegrityError):
            self.store.read("task_payload", ref)

    def test_size_limit_and_workspace_location_fail_closed(self):
        with self.assertRaises(PayloadScopeError):
            self.store.put("task_payload", b"x" * 65)
        with self.assertRaises(PayloadScopeError):
            self.store.put(
                "task_payload",
                b"inside",
                forbidden_roots=[self.storage],
            )
        payload_dir = self.storage / "tasks" / "active" / "task_payload" / "payloads"
        self.assertFalse(payload_dir.exists() and any(payload_dir.iterdir()))


if __name__ == "__main__":
    unittest.main()
