import ast
import os
import runpy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import ultra_ui


class SingleInstanceTests(unittest.TestCase):
    def test_lock_path_uses_local_appdata_and_home_fallback(self) -> None:
        expected = (
            Path(os.getenv("LOCALAPPDATA") or Path.home())
            / "GigaChatUltra"
            / "runtime"
            / "ultra_ui.lock"
        )
        self.assertEqual(ultra_ui._INSTANCE_LOCK_PATH, expected)

        fallback_home = Path("C:/fallback-home")
        with patch.dict(os.environ, {"LOCALAPPDATA": ""}), \
             patch.object(Path, "home", return_value=fallback_home):
            namespace = runpy.run_path(ultra_ui.__file__)
        self.assertEqual(
            namespace["_INSTANCE_LOCK_PATH"],
            fallback_home / "GigaChatUltra" / "runtime" / "ultra_ui.lock",
        )

    def test_acquire_creates_directory_holds_handle_and_writes_pid(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "runtime" / "ultra_ui.lock"
            instance_lock = ultra_ui._SingleInstanceLock(path)
            with patch.object(ultra_ui.msvcrt, "locking") as locking:
                self.assertTrue(instance_lock.acquire())
                handle = instance_lock._handle
                self.assertTrue(path.parent.is_dir())
                self.assertIsNotNone(handle)
                self.assertFalse(handle.closed)
                self.assertEqual(path.read_text(encoding="ascii"), str(os.getpid()))
                locking.assert_called_once_with(
                    handle.fileno(),
                    ultra_ui.msvcrt.LK_NBLCK,
                    1,
                )
                instance_lock.release()

    def test_release_unlocks_closes_handle_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ultra_ui.lock"
            instance_lock = ultra_ui._SingleInstanceLock(path)
            with patch.object(ultra_ui.msvcrt, "locking") as locking:
                self.assertTrue(instance_lock.acquire())
                handle = instance_lock._handle
                instance_lock.release()
                instance_lock.release()
            self.assertTrue(handle.closed)
            self.assertIsNone(instance_lock._handle)
            self.assertEqual(locking.call_count, 2)
            self.assertEqual(locking.call_args.args[1:], (ultra_ui.msvcrt.LK_UNLCK, 1))
            self.assertTrue(path.exists())

    def test_failed_nonblocking_lock_closes_handle_and_returns_false(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ultra_ui.lock"
            instance_lock = ultra_ui._SingleInstanceLock(path)
            real_open = Path.open
            opened = []

            def capture_open(target, *args, **kwargs):
                handle = real_open(target, *args, **kwargs)
                opened.append(handle)
                return handle

            with patch.object(Path, "open", capture_open), \
                 patch.object(
                     ultra_ui.msvcrt,
                     "locking",
                     side_effect=OSError("already locked"),
                 ):
                self.assertFalse(instance_lock.acquire())

            self.assertEqual(len(opened), 1)
            self.assertTrue(opened[0].closed)
            self.assertIsNone(instance_lock._handle)

    def test_entrypoint_releases_lock_in_finally(self) -> None:
        source = Path(ultra_ui.__file__).read_text(encoding="utf-8")
        module = ast.parse(source)
        main_if = next(
            node
            for node in module.body
            if isinstance(node, ast.If)
            and ast.unparse(node.test) == "__name__ == '__main__'"
        )
        guarded_branch = next(node for node in main_if.body if isinstance(node, ast.If))
        try_node = next(node for node in guarded_branch.orelse if isinstance(node, ast.Try))
        self.assertEqual(
            [ast.unparse(node) for node in try_node.finalbody],
            ["instance_lock.release()"],
        )

        entrypoint = compile(
            ast.fix_missing_locations(ast.Module(body=[main_if], type_ignores=[])),
            ultra_ui.__file__,
            "exec",
        )

        for failure_point in ("constructor", "mainloop"):
            with self.subTest(failure_point=failure_point):
                released = []

                class FakeLock:
                    def acquire(self):
                        return True

                    def release(self):
                        released.append(True)

                class FakeApp:
                    def __init__(self):
                        if failure_point == "constructor":
                            raise RuntimeError("constructor failed")

                    def mainloop(self):
                        raise RuntimeError("mainloop failed")

                namespace = {
                    "__name__": "__main__",
                    "_SingleInstanceLock": lambda _path: FakeLock(),
                    "_INSTANCE_LOCK_PATH": Path("unused"),
                    "_show_already_running_message": lambda: None,
                    "UltraApp": FakeApp,
                }
                with self.assertRaises(RuntimeError):
                    exec(entrypoint, namespace)
                self.assertEqual(released, [True])


if __name__ == "__main__":
    unittest.main()
