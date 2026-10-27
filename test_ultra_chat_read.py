"""Bounded read-only access to the Ultra history for the web shell (programme No.37 stage 1).

Each fixture is a disposable Workspace in TEMP written by the existing Tk writers of context_storage. Where the old
display path is weak (stage-0 findings P1-P6) a test first pins that the old function still behaves as before - the
Tk path is deliberately unchanged - and then checks the new bounded function on the same bytes. Windows junctions
and hard links need no privilege and run here; file symlinks need one and are skipped honestly when missing.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import context_storage as cs

ROOT = Path(cs.__file__).resolve().parent
LIMITS = cs.DEFAULT_READ_LIMITS


def snapshot(base: Path) -> dict[str, tuple]:
    """Names, kinds, sizes, mtimes and content hashes, never descending into links or junctions.

    Times come from os.lstat (the object itself), not from DirEntry.stat: on NTFS the copy of a directory's
    times kept in its parent's index is refreshed lazily, so scandir can report a stale value that changes later
    without any write (first FAIL of this test, kept as evidence and classified as a harness defect).
    """
    result: dict[str, tuple] = {}
    stack = [base]
    while stack:
        folder = stack.pop()
        with os.scandir(folder) as entries:
            for entry in entries:
                st = os.lstat(entry.path)
                rel = Path(entry.path).relative_to(base).as_posix()
                if cs._is_link_or_reparse(st):
                    result[rel] = ("link", st.st_mtime_ns)
                elif entry.is_dir(follow_symlinks=False):
                    result[rel] = ("dir", st.st_mtime_ns)
                    stack.append(Path(entry.path))
                else:
                    data = Path(entry.path).read_bytes()
                    result[rel] = ("file", st.st_size, st.st_mtime_ns, hashlib.sha256(data).hexdigest())
    return result


class Base(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix="wa_s1_read_")).resolve()
        self.junctions: list[Path] = []
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        for link in reversed(self.junctions):
            try:
                os.rmdir(link)
            except OSError:
                pass
        shutil.rmtree(self.base, ignore_errors=True)

    def junction(self, target: Path, link: Path) -> None:
        import _winapi
        _winapi.CreateJunction(str(target), str(link))
        self.junctions.append(link)

    def workspace(self, name: str = "w", title: str = "Диалог") -> tuple[Path, str, str]:
        root = self.base / name
        root.mkdir()
        workspace_id = cs.ensure_workspace_storage(root)["workspace_id"]
        chat = cs.create_chat(root, title)["chat_id"]
        return root, workspace_id, chat

    @staticmethod
    def messages_dir(root: Path, chat: str) -> Path:
        return root / ".ultra" / "chats" / chat / "messages"

    def write_raw(self, root: Path, chat: str, message_id: str, **fields) -> Path:
        record = {"schema_version": 1, "workspace_id": cs.read_workspace_identity_bounded(root)["workspace_id"],
                  "chat_id": chat, "message_id": message_id, "role": "user",
                  "created_at": "2026-01-01T00:00:00+00:00", "original_text": "text"}
        record.update(fields)
        path = self.messages_dir(root, chat) / f"{message_id}.json"
        path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        return path


def mid(n: int) -> str:
    return "msg_" + f"{n:032x}"


class WorkspaceIdentityTests(Base):
    def test_bare_folder_has_no_history_and_nothing_is_created(self):
        bare = self.base / "bare"
        bare.mkdir()
        self.assertEqual(cs.read_workspace_identity_bounded(bare), {"status": "missing_history"})
        with self.assertRaises(cs.StorageReadError) as caught:
            cs.list_chats_bounded(bare)
        self.assertEqual(caught.exception.code, "missing_history")
        self.assertEqual(list(bare.iterdir()), [])

    def test_missing_relative_file_and_damaged_roots_are_named_not_raised(self):
        root, workspace_id, _ = self.workspace()
        a_file = self.base / "file.txt"
        a_file.write_text("x")
        cases = {"missing_path": [self.base / "absent", Path("relative")], "not_directory": [a_file]}
        for status, paths in cases.items():
            for path in paths:
                with self.subTest(status=status):
                    self.assertEqual(cs.read_workspace_identity_bounded(path)["status"], status)
        meta = root / ".ultra" / "workspace.json"
        original = meta.read_bytes()
        for label, payload, status in (("broken", b"{", "invalid_metadata"), ("array", b"[]", "invalid_metadata"),
                                       ("bad id", json.dumps({"schema_version": 1, "workspace_id": "x"}).encode(), "invalid_metadata"),
                                       ("newer", json.dumps({"schema_version": 2, "workspace_id": workspace_id}).encode(), "unsupported_version"),
                                       ("huge", b" " * (LIMITS.max_workspace_metadata_bytes + 1), "invalid_metadata")):
            with self.subTest(case=label):
                meta.write_bytes(payload)
                self.assertEqual(cs.read_workspace_identity_bounded(root)["status"], status)
        meta.write_bytes(original)
        self.assertEqual(cs.read_workspace_identity_bounded(root), {"status": "ok", "workspace_id": workspace_id,
                                                                    "display_name": "w"})

    def test_ultra_folder_replaced_by_a_junction_is_refused(self):
        other, _, _ = self.workspace("other")
        root = self.base / "w"
        root.mkdir()
        self.junction(other / ".ultra", root / ".ultra")
        self.assertEqual(cs.read_workspace_identity_bounded(root)["status"], "unsafe_storage_link")


class ChatListingTests(Base):
    def test_chats_are_listed_in_creation_order_with_titles(self):
        root, _, first = self.workspace()
        second = cs.create_chat(root, "Второй")["chat_id"]
        listing = cs.list_chats_bounded(root)
        self.assertEqual([(c["chat_id"], c["status"], c["title"]) for c in listing["chats"]],
                         [(first, "ok", "Диалог"), (second, "ok", "Второй")])
        self.assertEqual(listing["excluded"], {})

    def test_one_damaged_card_hides_nothing_else(self):
        root, _, good = self.workspace()
        bad = cs.create_chat(root, "Сломан")["chat_id"]
        (root / ".ultra" / "chats" / bad / "metadata.json").write_text("{", encoding="utf-8")
        with self.assertRaises(RuntimeError):  # characterization P1: the Tk listing still fails as a whole
            cs.list_existing_chats(root)
        statuses = {c["chat_id"]: c["status"] for c in cs.list_chats_bounded(root)["chats"]}
        self.assertEqual(statuses, {good: "ok", bad: "damaged"})

    def test_chat_of_another_workspace_is_excluded_and_counted(self):
        root, _, good = self.workspace()
        foreign = cs.create_chat(root, "Чужой")["chat_id"]
        meta = root / ".ultra" / "chats" / foreign / "metadata.json"
        data = json.loads(meta.read_text(encoding="utf-8"))
        data["workspace_id"] = "ws_" + "f" * 32
        meta.write_text(json.dumps(data), encoding="utf-8")
        self.assertIn(foreign, [c["chat_id"] for c in cs.list_existing_chats(root)])  # characterization P1
        listing = cs.list_chats_bounded(root)
        self.assertEqual([c["chat_id"] for c in listing["chats"]], [good])
        self.assertEqual(listing["excluded"], {"foreign_identity": 1})

    def test_folder_name_must_match_chat_id_and_odd_entries_are_ignored(self):
        root, _, good = self.workspace()
        moved = cs.create_chat(root, "Переименован")["chat_id"]
        renamed = "chat_" + "e" * 32
        os.rename(root / ".ultra" / "chats" / moved, root / ".ultra" / "chats" / renamed)
        (root / ".ultra" / "chats" / "notes.txt").write_text("x")
        (root / ".ultra" / "chats" / "not_a_chat").mkdir()
        listing = cs.list_chats_bounded(root)
        self.assertEqual({c["chat_id"]: c["status"] for c in listing["chats"]}, {good: "ok", renamed: "damaged"})
        self.assertEqual(listing["excluded"], {"unexpected_entry": 2})

    def test_chat_folder_junction_is_reported_and_never_read(self):
        other, _, foreign_chat = self.workspace("other")
        cs.append_raw_message(other, foreign_chat, "user", "FOREIGN-PRIVATE-TEXT")
        root, _, good = self.workspace()
        self.junction(other / ".ultra" / "chats" / foreign_chat, root / ".ultra" / "chats" / foreign_chat)
        self.assertEqual(len(cs.load_chat_messages(root, foreign_chat)), 1)  # characterization P6
        listing = cs.list_chats_bounded(root)
        self.assertEqual({c["chat_id"]: c["status"] for c in listing["chats"]},
                         {good: "ok", foreign_chat: "unsafe_storage_link"})
        with self.assertRaises(cs.StorageReadError) as caught:
            cs.read_chat_history_bounded(root, foreign_chat)
        self.assertEqual(caught.exception.code, "unsafe_storage_link")

    def test_chats_folder_junction_refuses_the_listing(self):
        other, _, _ = self.workspace("other")
        root = self.base / "w"
        root.mkdir()
        cs.ensure_workspace_storage(root)
        os.rmdir(root / ".ultra" / "chats")
        self.junction(other / ".ultra" / "chats", root / ".ultra" / "chats")
        with self.assertRaises(cs.StorageReadError) as caught:
            cs.list_chats_bounded(root)
        self.assertEqual(caught.exception.code, "unsafe_storage_link")

    def test_missing_chats_folder_is_an_empty_list_and_too_many_entries_are_refused(self):
        root = self.base / "w"
        root.mkdir()
        cs.ensure_workspace_storage(root)
        os.rmdir(root / ".ultra" / "chats")
        self.assertEqual(cs.list_chats_bounded(root)["chats"], [])
        cs.ensure_workspace_storage(root)
        for _ in range(4):
            cs.create_chat(root, "x")
        with self.assertRaises(cs.StorageReadError) as caught:
            cs.list_chats_bounded(root, limits=cs.ReadLimits(max_chat_entries=3))
        self.assertEqual(caught.exception.code, "chats_listing_too_large")
        with self.assertRaises(cs.StorageReadError) as caught:
            cs.list_chats_bounded(root, limits=cs.ReadLimits(max_chats=3))
        self.assertEqual(caught.exception.code, "chats_listing_too_large")


class HistoryTests(Base):
    def test_order_identity_and_legacy_records(self):
        root, _, chat = self.workspace()
        tb = cs.new_task_block_id()
        first = cs.append_raw_message(root, chat, "user", "вопрос <b>", task_block_id=tb)
        producer = {"kind": "llm", "role_id": "main_chat", "run_id": "r1", "model_id": "m", "model_display_name": "M",
                    "provider": "p", "provider_model_id": "P"}
        second = cs.append_raw_message(root, chat, "assistant", "ответ", producer=producer, task_block_id=tb)
        legacy = self.write_raw(root, chat, mid(1), created_at="2000-01-01T00:00:00+00:00")
        data = json.loads(legacy.read_text(encoding="utf-8"))
        data.pop("schema_version")
        legacy.write_text(json.dumps(data), encoding="utf-8")
        history = cs.read_chat_history_bounded(root, chat)
        self.assertEqual([m["message_id"] for m in history["messages"]], [mid(1), first["message_id"], second["message_id"]])
        self.assertEqual(history["messages"][1]["text"], "вопрос <b>")
        self.assertEqual(history["messages"][2]["producer"], {"kind": "llm", "run_id": "r1", "model_id": "m",
                                                              "model_display_name": "M"})
        self.assertNotIn("task_block_id", history["messages"][0])
        self.assertEqual((history["excluded"], history["chat"]["title"]), ({}, "Диалог"))

    def test_copy_under_another_name_is_excluded_once_and_shown_once(self):
        root, _, chat = self.workspace()
        original = cs.append_raw_message(root, chat, "user", "один раз")
        copy = self.messages_dir(root, chat) / f"{mid(7)}.json"
        copy.write_bytes(Path(original["path"]).read_bytes())
        self.assertEqual(len(cs.load_chat_working_messages(root, chat)), 2)  # characterization P2
        history = cs.read_chat_history_bounded(root, chat)
        self.assertEqual([m["message_id"] for m in history["messages"]], [original["message_id"]])
        self.assertEqual((history["excluded"], history["excluded_ids"]), ({"name_mismatch": 1}, [mid(7)]))

    def test_message_of_another_workspace_or_chat_is_excluded(self):
        root, _, chat = self.workspace()
        self.write_raw(root, chat, mid(1), workspace_id="ws_" + "e" * 32)
        self.assertEqual(len(cs.load_chat_messages(root, chat)), 1)  # characterization P3: foreign workspace accepted
        self.write_raw(root, chat, mid(2), chat_id="chat_" + "d" * 32)
        history = cs.read_chat_history_bounded(root, chat)
        self.assertEqual((history["messages"], history["excluded"]), ([], {"foreign_identity": 2}))

    def test_every_kind_of_damage_is_counted_while_good_messages_stay(self):
        root, _, chat = self.workspace()
        good = cs.append_raw_message(root, chat, "user", "хорошее")
        folder = self.messages_dir(root, chat)
        (folder / f"{mid(1)}.json").write_text("{", encoding="utf-8")
        (folder / f"{mid(2)}.json").write_text("[]", encoding="utf-8")
        self.write_raw(root, chat, mid(3), original_text=5)
        self.write_raw(root, chat, mid(4), role="hacker")
        self.write_raw(root, chat, mid(5), producer={"kind": "llm"})
        self.write_raw(root, chat, mid(6), task_block_id="tb_bad")
        self.write_raw(root, chat, mid(7), schema_version=2)
        self.write_raw(root, chat, mid(8), created_at=None)
        (folder / f"{mid(9)}.json").write_bytes(b"\xff\xfe\x00bad")
        (folder / f"{mid(10)}.json").mkdir()
        (folder / "notes.json").write_text("{}", encoding="utf-8")
        (folder / f".{good['message_id']}.json.0123.tmp").write_text("writer in progress", encoding="utf-8")
        history = cs.read_chat_history_bounded(root, chat)
        self.assertEqual([m["message_id"] for m in history["messages"]], [good["message_id"]])
        self.assertEqual(history["excluded"], {"damaged": 9, "unsupported_version": 1, "name_mismatch": 1})

    def test_chat_level_states(self):
        root, _, chat = self.workspace()
        shutil.rmtree(self.messages_dir(root, chat))
        self.assertEqual(cs.read_chat_history_bounded(root, chat)["messages"], [])
        for chat_id, code in (("chat_" + "a" * 32, "chat_not_found"), ("../x", "invalid_chat_id"), ("", "invalid_chat_id")):
            with self.subTest(code=code):
                with self.assertRaises(cs.StorageReadError) as caught:
                    cs.read_chat_history_bounded(root, chat_id)
                self.assertEqual(caught.exception.code, code)
        meta = root / ".ultra" / "chats" / chat / "metadata.json"
        data = json.loads(meta.read_text(encoding="utf-8"))
        for payload, code in ((json.dumps({**data, "workspace_id": "ws_" + "b" * 32}), "foreign_identity"),
                              ("{", "chat_damaged"), (json.dumps({**data, "title": ""}), "chat_damaged")):
            with self.subTest(code=code):
                meta.write_text(payload, encoding="utf-8")
                with self.assertRaises(cs.StorageReadError) as caught:
                    cs.read_chat_history_bounded(root, chat)
                self.assertEqual(caught.exception.code, code)


class LimitTests(Base):
    def counting(self):
        """Count the bytes physically read from message files through the bounded reader."""
        stats = {"message_bytes": 0, "message_reads": []}
        original_read, original_file = os.read, cs._read_file_bounded

        def file_wrapper(anchor, parts, limit):
            if "messages" in parts:
                stats["message_reads"].append(parts[-1])
            return original_file(anchor, parts, limit)

        def read_wrapper(fd, n):
            data = original_read(fd, n)
            stats["message_bytes"] += len(data)
            return data
        return stats, file_wrapper, read_wrapper

    def test_default_limits_follow_the_stage0_contract(self):
        self.assertEqual((LIMITS.max_message_bytes, LIMITS.max_message_files, LIMITS.max_history_bytes,
                          LIMITS.max_chat_entries, LIMITS.max_chats),
                         (4 * 1024 * 1024, 2000, 64 * 1024 * 1024, 2000, 500))

    def test_oversized_message_is_excluded_without_reading_its_content(self):
        root, _, chat = self.workspace()
        small = cs.append_raw_message(root, chat, "user", "short")
        self.write_raw(root, chat, mid(1), original_text="x" * 5000)
        stats, file_wrapper, read_wrapper = self.counting()
        with patch.object(cs, "_read_file_bounded", file_wrapper):
            history = cs.read_chat_history_bounded(root, chat, limits=cs.ReadLimits(max_message_bytes=4096))
        self.assertEqual([m["message_id"] for m in history["messages"]], [small["message_id"]])
        self.assertEqual((history["excluded"], history["excluded_ids"]), ({"too_large": 1}, [mid(1)]))
        self.assertNotIn(f"{mid(1)}.json", stats["message_reads"])

    def test_a_file_larger_than_its_stat_is_cut_at_the_limit(self):
        root, _, chat = self.workspace()
        self.write_raw(root, chat, mid(1), original_text="y" * 20000)
        real_fstat, original_read = os.fstat, os.read
        physical = []

        def lying_fstat(fd):
            st = real_fstat(fd)
            fields = {name: getattr(st, name) for name in dir(st) if name.startswith("st_")}
            return types.SimpleNamespace(**{**fields, "st_size": 10})

        def counting_read(fd, n):
            data = original_read(fd, n)
            physical.append(len(data))
            return data
        limits = cs.ReadLimits(max_message_bytes=4096)
        anchor = cs._StorageAnchor(root)
        parts = (".ultra", "chats", chat, "messages", f"{mid(1)}.json")
        with patch.object(cs.os, "fstat", lying_fstat), patch.object(cs.os, "read", counting_read):
            with self.assertRaises(cs.StorageReadError) as caught:
                cs._read_file_bounded(anchor, parts, limits.max_message_bytes)
        self.assertEqual(caught.exception.code, "too_large")
        self.assertLessEqual(sum(physical), limits.max_message_bytes + 1)

    def test_too_many_files_or_bytes_refuse_the_history_before_any_message_is_read(self):
        root, _, chat = self.workspace()
        for n in range(6):
            self.write_raw(root, chat, mid(n), original_text="z" * 300)
        for limits in (cs.ReadLimits(max_message_files=5), cs.ReadLimits(max_history_bytes=1000)):
            stats, file_wrapper, _ = self.counting()
            with self.subTest(limits=limits.max_message_files):
                with patch.object(cs, "_read_file_bounded", file_wrapper):
                    with self.assertRaises(cs.StorageReadError) as caught:
                        cs.read_chat_history_bounded(root, chat, limits=limits)
                self.assertEqual(caught.exception.code, "history_too_large")
                self.assertEqual(stats["message_reads"], [])

    def test_budget_holds_when_files_grow_after_the_listing(self):
        root, _, chat = self.workspace()
        for n in range(4):
            self.write_raw(root, chat, mid(n), original_text="g" * 400)
        original_scan = cs._scan_directory

        def understated(anchor, parts, max_entries):
            return [(name, kind, 1) for name, kind, _size in original_scan(anchor, parts, max_entries)]
        stats, file_wrapper, read_wrapper = self.counting()
        with patch.object(cs, "_scan_directory", understated), patch.object(cs, "_read_file_bounded", file_wrapper):
            with self.assertRaises(cs.StorageReadError) as caught:
                cs.read_chat_history_bounded(root, chat, limits=cs.ReadLimits(max_history_bytes=1200))
        self.assertEqual(caught.exception.code, "history_too_large")
        self.assertLess(len(stats["message_reads"]), 4)


class PathSafetyTests(Base):
    def forged_copy(self, root: Path, chat: str, marker: str) -> Path:
        """A folder elsewhere holding files with the same names and the same identity, but other text."""
        forged = self.base / "forged"
        forged.mkdir()
        for path in self.messages_dir(root, chat).iterdir():
            record = json.loads(path.read_text(encoding="utf-8"))
            record["original_text"] = marker
            (forged / path.name).write_text(json.dumps(record), encoding="utf-8")
        return forged

    def test_messages_folder_junction_is_refused(self):
        other, _, foreign_chat = self.workspace("other")
        cs.append_raw_message(other, foreign_chat, "user", "FOREIGN-PRIVATE-TEXT")
        root, _, chat = self.workspace()
        shutil.rmtree(self.messages_dir(root, chat))
        self.junction(self.messages_dir(other, foreign_chat), self.messages_dir(root, chat))
        with self.assertRaises(cs.StorageReadError) as caught:
            cs.read_chat_history_bounded(root, chat)
        self.assertEqual(caught.exception.code, "unsafe_storage_link")

    def test_folder_swapped_for_a_junction_after_its_check_is_caught_at_open(self):
        root, _, chat = self.workspace()
        for n in range(3):
            cs.append_raw_message(root, chat, "user", f"own {n}")
        forged = self.forged_copy(root, chat, "FORGED-SAME-IDENTITY")
        folder = self.messages_dir(root, chat)
        original_verify = cs._verify_directory
        swapped = []

        def verify_then_swap(anchor, parts):
            original_verify(anchor, parts)
            if parts[-1] == "messages" and not swapped:
                os.rename(folder, folder.with_name("messages_aside"))
                self.junction(forged, folder)
                swapped.append(True)
        with patch.object(cs, "_verify_directory", verify_then_swap):
            history = cs.read_chat_history_bounded(root, chat)
        self.assertEqual(swapped, [True])
        self.assertEqual(history["messages"], [])
        self.assertEqual(history["excluded"], {"unsafe_storage_link": 3})
        self.assertNotIn("FORGED", json.dumps(history, ensure_ascii=False))

    def test_folder_swapped_between_listing_and_open_is_caught(self):
        root, _, chat = self.workspace()
        cs.append_raw_message(root, chat, "user", "own")
        forged = self.forged_copy(root, chat, "FORGED-SAME-IDENTITY")
        folder = self.messages_dir(root, chat)
        original_open = cs._open_file_no_follow

        def swap_then_open(path):
            # Only once the listing is done: the first open of a message file.
            if "messages" in Path(path).parts and not folder.is_junction():
                os.rename(folder, folder.with_name("messages_aside"))
                self.junction(forged, folder)
            return original_open(path)
        with patch.object(cs, "_open_file_no_follow", swap_then_open):
            history = cs.read_chat_history_bounded(root, chat)
        self.assertEqual((history["messages"], history["excluded"]), ([], {"unsafe_storage_link": 1}))

    def test_hard_link_to_a_file_elsewhere_is_refused(self):
        root, _, chat = self.workspace()
        outside = self.base / "outside.json"
        own = cs.append_raw_message(root, chat, "user", "own")
        record = json.loads(Path(own["path"]).read_text(encoding="utf-8"))
        record.update(message_id=mid(5), original_text="LINKED-OUTSIDE")
        outside.write_text(json.dumps(record), encoding="utf-8")
        os.link(outside, self.messages_dir(root, chat) / f"{mid(5)}.json")
        history = cs.read_chat_history_bounded(root, chat)
        self.assertEqual([m["message_id"] for m in history["messages"]], [own["message_id"]])
        self.assertEqual(history["excluded"], {"unsafe_storage_link": 1})

    def test_file_symlink_is_refused_when_the_platform_allows_creating_one(self):
        root, _, chat = self.workspace()
        target = self.base / "target.json"
        target.write_text("{}", encoding="utf-8")
        try:
            os.symlink(target, self.messages_dir(root, chat) / f"{mid(3)}.json")
        except OSError:
            self.skipTest("symlink creation needs a privilege this host does not grant (NOT RUN, junctions covered)")
        history = cs.read_chat_history_bounded(root, chat)
        self.assertEqual(history["excluded"], {"unsafe_storage_link": 1})

    def test_generic_storage_reader_refuses_traversal_names(self):
        root, _, _ = self.workspace()
        for parts in ((), ("..", "x"), ("a/b",), (".",), ("audit", "")):
            with self.subTest(parts=len(parts)):
                with self.assertRaises(cs.StorageReadError) as caught:
                    cs.read_ultra_json_bounded(root, parts, max_bytes=10)
                self.assertEqual(caught.exception.code, "invalid_path")


class ReadOnlyTests(Base):
    def test_every_read_leaves_every_byte_name_and_time_unchanged(self):
        other, _, foreign_chat = self.workspace("other")
        cs.append_raw_message(other, foreign_chat, "user", "foreign")
        root, _, chat = self.workspace()
        cs.append_raw_message(root, chat, "user", "own")
        broken = cs.create_chat(root, "broken")["chat_id"]
        (root / ".ultra" / "chats" / broken / "metadata.json").write_text("{", encoding="utf-8")
        self.junction(other / ".ultra" / "chats" / foreign_chat, root / ".ultra" / "chats" / foreign_chat)
        (self.base / "bare").mkdir()
        before = snapshot(self.base)
        time.sleep(0.05)
        for path in (root, other, self.base / "bare", self.base / "absent"):
            cs.read_workspace_identity_bounded(path)
        for call in (lambda: cs.list_chats_bounded(root), lambda: cs.list_chats_bounded(self.base / "bare"),
                     lambda: cs.read_chat_history_bounded(root, chat), lambda: cs.read_chat_history_bounded(root, broken),
                     lambda: cs.read_chat_history_bounded(root, foreign_chat),
                     lambda: cs.read_ultra_json_bounded(root, ("audit", "index.json"), max_bytes=100),
                     lambda: cs.list_ultra_files_bounded(root, ("audit", "index_generations"), max_entries=10)):
            try:
                call()
            except cs.StorageReadError:
                pass
        self.assertEqual(snapshot(self.base), before)


class ConcurrencyTests(Base):
    def test_reading_while_the_tk_writer_appends_and_renames_in_another_process(self):
        root, _, chat = self.workspace()
        child = (
            "import json, sys\n"
            "sys.path.insert(0, sys.argv[1])\n"
            "import context_storage as cs\n"
            "root, chat = sys.argv[2], sys.argv[3]\n"
            "ok = fail = renamed = rename_fail = 0\n"
            "for n in range(80):\n"
            "    try:\n"
            "        cs.append_raw_message(root, chat, 'user', 'written %d' % n); ok += 1\n"
            "    except PermissionError:\n"
            "        fail += 1\n"
            "    if n % 8 == 0:\n"
            "        try:\n"
            "            cs.rename_chat(root, chat, 'title %d' % n); renamed += 1\n"
            "        except PermissionError:\n"
            "            rename_fail += 1\n"
            "print(json.dumps({'ok': ok, 'fail': fail, 'renamed': renamed, 'rename_fail': rename_fail}))\n"
        )
        writer = subprocess.Popen([sys.executable, "-B", "-c", child, str(ROOT), str(root), chat],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        reads, unexpected = 0, []
        while writer.poll() is None:
            try:
                history = cs.read_chat_history_bounded(root, chat)
                listing = cs.list_chats_bounded(root)
                reads += 1
                if history["excluded"] or [c["status"] for c in listing["chats"]] != ["ok"]:
                    unexpected.append((history["excluded"], [c["status"] for c in listing["chats"]]))
            except cs.StorageReadError as exc:
                unexpected.append(exc.code)
        out, err = writer.communicate(timeout=120)
        self.assertEqual(writer.returncode, 0, err[-500:])
        counts = json.loads(out.strip().splitlines()[-1])
        final = cs.read_chat_history_bounded(root, chat)
        self.assertGreater(reads, 0)
        self.assertEqual(unexpected, [], "the reader saw damage that a correct writer never produces")
        self.assertEqual(len(final["messages"]), counts["ok"])
        self.assertEqual(counts["ok"] + counts["fail"], 80)
        print("S1-CONCURRENCY " + json.dumps({"reads": reads, **counts}), file=sys.stderr)


if __name__ == "__main__":
    unittest.main()
