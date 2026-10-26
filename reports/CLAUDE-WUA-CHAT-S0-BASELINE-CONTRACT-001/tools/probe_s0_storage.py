"""Stage 0 isolated probes: what the existing Ultra storage, Run Store and lock primitives really do today.

Each test builds synthetic Workspaces in its own TEMP folder, calls the existing production functions unchanged and
asserts the OBSERVED behaviour (a characterisation, not a fix). A failing assertion means the source does not behave
as the stage-0 analysis expects. No user data, no network, no credentials; run under the guarded Web Alarm runner so
that any write outside TEMP is an isolation violation. Observed facts are appended as one JSON line per test to the
file named by S0_FACTS_PATH (it must lie inside TEMP; the guard refuses writes anywhere else).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

import context_storage as cs
import run_store
from web_alarm.store_lock import InterProcessLock, StoreLockTimeout

ROOT = Path(cs.__file__).resolve().parent


def tree(root: Path) -> list[str]:
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*"))


class Fixture(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix="wa_s0_")).resolve()
        self.addCleanup(self._cleanup, self.base)
        self.facts = [{"task": "CLAUDE-WUA-CHAT-S0-BASELINE-CONTRACT-001", "test": self.id()}]
        self.addCleanup(self._dump_facts)

    def _dump_facts(self):
        target = os.environ.get("S0_FACTS_PATH")
        if target:
            with open(target, "a", encoding="utf-8", newline="\n") as stream:
                stream.write(json.dumps(self.facts, ensure_ascii=False) + "\n")

    @staticmethod
    def _cleanup(base: Path):
        for path in base.rglob("*"):
            if path.is_junction():
                os.rmdir(path)
        shutil.rmtree(base, ignore_errors=True)

    def workspace(self, name: str) -> tuple[Path, str, str]:
        root = self.base / name
        root.mkdir()
        info = cs.ensure_workspace_storage(root)
        chat = cs.create_chat(root, "Chat")
        return root, info["workspace_id"], chat["chat_id"]

    @staticmethod
    def msg_path(root: Path, chat_id: str, message_id: str) -> Path:
        return root / ".ultra" / "chats" / chat_id / "messages" / f"{message_id}.json"


class ReadPathTests(Fixture):
    def test_p1_one_damaged_chat_hides_every_chat_and_workspace_id_of_a_chat_is_not_checked(self):
        root, ws, chat = self.workspace("w")
        second = cs.create_chat(root, "Second")["chat_id"]
        meta = root / ".ultra" / "chats" / second / "metadata.json"
        data = json.loads(meta.read_text(encoding="utf-8"))
        data["workspace_id"] = "ws_" + "f" * 32  # a chat claiming another Workspace
        meta.write_text(json.dumps(data), encoding="utf-8")
        listed = [c["chat_id"] for c in cs.list_existing_chats(root, expected_workspace_id=ws)]
        self.facts.append({"foreign_workspace_chat_listed": second in listed})
        self.assertIn(second, listed, "list_existing_chats now checks chat.workspace_id")
        meta.write_text("{broken", encoding="utf-8")
        with self.assertRaises(RuntimeError):
            cs.list_existing_chats(root, expected_workspace_id=ws)
        self.facts.append({"one_damaged_chat_breaks_listing": True})

    def test_p2_file_name_and_message_id_are_not_compared_and_duplicates_are_returned(self):
        root, _, chat = self.workspace("w")
        first = cs.append_raw_message(root, chat, "user", "hello")
        copy = self.msg_path(root, chat, "msg_" + "a" * 32)
        copy.write_bytes(self.msg_path(root, chat, first["message_id"]).read_bytes())  # same message_id, other name
        messages = cs.load_chat_messages(root, chat)
        ids = [m["message_id"] for m in messages]
        self.facts.append({"display_messages": len(ids), "distinct_ids": len(set(ids))})
        self.assertEqual((len(ids), len(set(ids))), (2, 1), "load_chat_messages now rejects name/id mismatch")
        working = cs.load_chat_working_messages(root, chat)
        self.facts.append({"working_messages": len(working), "same_text_twice": len({w["content"] for w in working}) == 1})
        self.assertEqual(len(working), 2, "the duplicate would reach a model prompt twice")

    def test_p3_display_path_accepts_a_foreign_workspace_message_that_the_by_id_path_refuses(self):
        root, _, chat = self.workspace("w")
        stored = cs.append_raw_message(root, chat, "assistant", "answer")
        path = self.msg_path(root, chat, stored["message_id"])
        data = json.loads(path.read_text(encoding="utf-8"))
        data["workspace_id"] = "ws_" + "e" * 32
        path.write_text(json.dumps(data), encoding="utf-8")
        self.assertEqual(len(cs.load_chat_messages(root, chat)), 1)
        with self.assertRaises(RuntimeError):
            cs.load_raw_message(root, chat, stored["message_id"])
        with self.assertRaises(RuntimeError):
            cs.load_chat_working_messages(root, chat)
        self.facts.append({"display_accepts_foreign_workspace": True, "by_id_refuses": True, "working_refuses": True})

    def test_p4_reading_has_no_size_bound(self):
        root, ws, chat = self.workspace("w")
        big = "x" * (8 * 1024 * 1024)
        path = self.msg_path(root, chat, "msg_" + "b" * 32)
        path.write_text(json.dumps({"schema_version": 1, "workspace_id": ws, "chat_id": chat, "message_id": "msg_" + "b" * 32,
                                    "role": "user", "created_at": "2026-01-01T00:00:00+00:00", "original_text": big}),
                        encoding="utf-8")
        loaded = cs.load_chat_messages(root, chat)
        self.facts.append({"read_bytes_of_one_raw": path.stat().st_size, "append_limit": cs.MAX_MESSAGE_BYTES})
        self.assertEqual(len(loaded[0]["original_text"]), len(big), "load_chat_messages now bounds a single record")
        with self.assertRaises(ValueError):
            cs.append_raw_message(root, chat, "user", big)

    def test_p5_which_functions_create_storage_when_they_only_look(self):
        bare = self.base / "bare"
        bare.mkdir()
        results = {}
        for name, call in (("probe_existing_workspace", lambda: cs.probe_existing_workspace(bare)),
                           ("list_existing_chats", lambda: cs.list_existing_chats(bare)),
                           ("load_existing_project_context", lambda: cs.load_existing_project_context(bare)),
                           ("list_chats", lambda: cs.list_chats(bare))):
            before = tree(bare)
            try:
                call()
                outcome = "returned"
            except Exception as exc:  # noqa: BLE001 - recorded
                outcome = type(exc).__name__
            results[name] = {"outcome": outcome, "created": sorted(set(tree(bare)) - set(before))[:4]}
        self.facts.append({"bare_folder": results})
        self.assertEqual(results["probe_existing_workspace"]["created"], [])
        self.assertEqual(results["list_existing_chats"]["created"], [])
        self.assertEqual(results["load_existing_project_context"]["created"], [])
        self.assertTrue(results["list_chats"]["created"], "list_chats no longer creates storage")

    def test_p6_reader_follows_a_junction_inside_the_chats_folder(self):
        victim, _, foreign_chat = self.workspace("other")
        cs.append_raw_message(victim, foreign_chat, "user", "private text of another Workspace")
        root, ws, _ = self.workspace("w")
        import _winapi
        _winapi.CreateJunction(str(victim / ".ultra" / "chats" / foreign_chat), str(root / ".ultra" / "chats" / foreign_chat))
        listed = [c["chat_id"] for c in cs.list_existing_chats(root, expected_workspace_id=ws)]
        shown = cs.load_chat_messages(root, foreign_chat)
        self.facts.append({"foreign_chat_listed": foreign_chat in listed, "foreign_messages_read": len(shown)})
        self.assertIn(foreign_chat, listed)
        self.assertEqual(len(shown), 1, "display path no longer follows the junction")
        with self.assertRaises(RuntimeError):
            cs.load_raw_message(root, foreign_chat, shown[0]["message_id"])  # workspace identity stops the by-id path


class WritePathTests(Fixture):
    def test_p7_repeating_append_after_a_lost_answer_creates_a_second_message(self):
        root, _, chat = self.workspace("w")
        cs.append_raw_message(root, chat, "user", "same request")
        cs.append_raw_message(root, chat, "user", "same request")  # what a naive retry does
        ids = [m["message_id"] for m in cs.load_chat_messages(root, chat)]
        self.facts.append({"messages_after_retry": len(ids)})
        self.assertEqual(len(ids), 2)

    def test_p8_tk_style_failure_is_stored_as_an_assistant_answer_and_is_classifiable_by_its_run(self):
        root, ws, chat = self.workspace("w")
        tb = cs.new_task_block_id()
        cs.append_raw_message(root, chat, "user", "do something", task_block_id=tb)
        run_store.create_run_summary(root, ws, chat, tb, "20260101_000000_abcdef")
        run_store.update_run_summary_index(root, "20260101_000000_abcdef", {"run_status": "FAILED"})
        cs.append_raw_message(root, chat, "assistant", "RUN STATUS: FAILED\nRuntimeError: boom", task_block_id=tb)
        working = cs.load_chat_working_messages(root, chat)
        self.assertEqual([w["role"] for w in working], ["user", "assistant"], "failure text reaches the working history")
        index = run_store.load_workspace_run_index(root)
        runs = index["tasks"][tb]["runs"]
        statuses = [index["runs"][r]["run_status"] for r in runs]
        self.facts.append({"legacy_failure_in_working_history": True, "classified_by_task_block_runs": statuses})
        self.assertEqual(statuses, ["FAILED"])

    def test_p9_concurrent_new_runs_lose_entries_of_the_shared_workspace_index(self):
        root, ws, chat = self.workspace("w")
        child = (
            "import sys, time, pathlib\n"
            "sys.path.insert(0, sys.argv[1])\n"
            "import run_store\n"
            "root, tag, flag = sys.argv[2], sys.argv[3], pathlib.Path(sys.argv[4])\n"
            "while not flag.exists(): time.sleep(0.001)\n"
            "for i in range(40):\n"
            "    tb = 'tb_' + ('%s%031d' % (tag, i))[:32]\n"
            "    run_store.ensure_run_index_entry(root, 'r_' + tag + '_' + str(i), tb, 'chat_x')\n"
        )
        flag = self.base / "go"
        procs = [subprocess.Popen([sys.executable, "-B", "-c", child, str(ROOT), str(root), tag, str(flag)],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE) for tag in ("a", "b")]
        time.sleep(0.3)
        flag.write_text("1")
        errors = []
        for proc in procs:
            _, err = proc.communicate(timeout=120)
            if proc.returncode:
                errors.append(err.decode(errors="replace").strip().splitlines()[-1][:160])
        index = run_store.load_workspace_run_index(root)
        runs = [r for r in index["runs"] if r.startswith("r_")]
        numbers = [index["runs"][r]["display_id"] for r in runs]
        self.facts.append({"expected_runs": 80, "persisted_runs": len(runs), "duplicate_display_ids": len(numbers) - len(set(numbers)),
                           "child_errors": errors})
        self.assertLess(len(runs), 80, "no lost update observed in this run (the race was not hit; repeat before concluding)")


class SharingTests(Fixture):
    """A reader in another shell must not break the Tk writer: Windows refuses to replace a file opened without
    FILE_SHARE_DELETE (the default of Python's open()), and context_storage replaces without a retry."""

    def test_p11_plain_open_reader_makes_a_tk_metadata_replace_fail_and_leaves_no_temp(self):
        root, _, chat = self.workspace("w")
        meta = root / ".ultra" / "chats" / chat / "metadata.json"
        before = meta.read_bytes()
        with open(meta, "rb") as reader:
            reader.read(1)
            with self.assertRaises(PermissionError):
                cs.rename_chat(root, chat, "Renamed by Tk")
        leftovers = [p.name for p in meta.parent.iterdir() if p.name.endswith(".tmp")]
        self.facts.append({"replace_refused_while_plain_reader_open": True, "metadata_unchanged": meta.read_bytes() == before,
                           "temp_leftovers": len(leftovers)})
        self.assertEqual((meta.read_bytes() == before, leftovers), (True, []))

    def test_p12_even_a_share_delete_reader_blocks_the_replace_on_this_host_but_a_retry_after_close_succeeds(self):
        import _winapi
        import msvcrt
        root, _, chat = self.workspace("w")
        meta = root / ".ultra" / "chats" / chat / "metadata.json"
        before = meta.read_bytes()
        handle = _winapi.CreateFile(str(meta), 0x80000000, 0x1 | 0x2 | 0x4, 0, 3, 0x80, 0)  # read; share r/w/delete
        with open(msvcrt.open_osfhandle(handle, os.O_RDONLY), "rb") as reader:
            reader.read(1)
            try:
                cs.rename_chat(root, chat, "Renamed by Tk")
                outcome = "replaced"
            except OSError as exc:
                outcome = type(exc).__name__
        unchanged = meta.read_bytes() == before
        cs.rename_chat(root, chat, "Renamed by Tk")  # the same write once the reader has closed its handle
        renamed = json.loads(meta.read_text(encoding="utf-8"))["title"]
        self.facts.append({"replace_with_share_delete_reader_open": outcome, "metadata_unchanged_meanwhile": unchanged,
                           "retry_after_reader_closed": renamed})
        self.assertEqual((outcome, unchanged, renamed), ("PermissionError", True, "Renamed by Tk"))


class LockTests(Fixture):
    def test_p10_store_lock_is_exclusive_between_threads_and_processes_and_freed_by_process_death(self):
        path = self.base / "locks" / "w.lock"
        holder = InterProcessLock(path, timeout=1)
        holder.acquire()
        other = InterProcessLock(path, timeout=0.2)
        blocked_in_thread = []

        def contender():
            try:
                other.acquire()
                other.release()
                blocked_in_thread.append(False)
            except StoreLockTimeout:
                blocked_in_thread.append(True)
        t = threading.Thread(target=contender)
        t.start()
        t.join(5)
        holder.release()
        child = ("import sys, os, time\nsys.path.insert(0, sys.argv[1])\n"
                 "from web_alarm.store_lock import InterProcessLock\n"
                 "lock = InterProcessLock(sys.argv[2], timeout=5)\nlock.acquire()\n"
                 "print('held', flush=True)\ntime.sleep(60)\n")  # keep a reference: a collected lock closes its handle
        proc = subprocess.Popen([sys.executable, "-B", "-c", child, str(ROOT), str(path)], stdout=subprocess.PIPE)
        self.assertEqual(proc.stdout.readline().strip(), b"held")
        blocked_by_process = False
        try:
            InterProcessLock(path, timeout=0.3).acquire()
        except StoreLockTimeout:
            blocked_by_process = True
        proc.kill()
        proc.wait(10)
        after_death = InterProcessLock(path, timeout=5)
        after_death.acquire()
        after_death.release()
        self.facts.append({"exclusive_between_threads": blocked_in_thread == [True],
                           "exclusive_between_processes": blocked_by_process, "released_on_process_death": True})
        self.assertEqual((blocked_in_thread, blocked_by_process), ([True], True))


if __name__ == "__main__":
    unittest.main()
