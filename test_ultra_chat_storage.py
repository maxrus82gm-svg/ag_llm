"""Shared writer contract of the Ultra storage (CLAUDE-WUA-CHAT-S2-SHARED-STORAGE-001, programme No.37 stage 2).

Every fixture is a disposable Workspace in TEMP. Oracles are independent of the code under test: raw bytes and
hashes of the files on disk, directory listings by os.scandir/os.lstat, JSON parsed here, and real child processes
(two writers, a lock holder that is killed, a writer that dies in the middle of a publication). Windows junctions
need no privilege and run here; a file symlink needs one and is skipped honestly when missing.
"""
from __future__ import annotations

import hashlib
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
from unittest.mock import patch

import context_storage as cs

ROOT = Path(cs.__file__).resolve().parent
CHILD = "import sys, os, time, json\nsys.path.insert(0, sys.argv[1])\nimport context_storage as cs\nfrom pathlib import Path\n"


def snapshot(base: Path) -> dict[str, tuple]:
    """Names, kinds, sizes, lstat mtimes and content hashes; never descends into links or junctions."""
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
                    result[rel] = ("dir",)
                    stack.append(Path(entry.path))
                else:
                    result[rel] = ("file", st.st_size, st.st_mtime_ns, hashlib.sha256(Path(entry.path).read_bytes()).hexdigest())
    return result


def without_lock(snap: dict[str, tuple]) -> dict[str, tuple]:
    return {k: v for k, v in snap.items() if "/locks" not in "/" + k}


def mid(n: int) -> str:
    return "msg_" + f"{n:032x}"


def cid(n: int) -> str:
    return "chat_" + f"{n:032x}"


class Base(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix="wa_s2_store_")).resolve()
        self.junctions: list[Path] = []
        self.children: list[subprocess.Popen] = []
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        for child in self.children:
            if child.poll() is None:
                child.kill()
            child.communicate(timeout=30)
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

    def spawn(self, code: str, *args) -> subprocess.Popen:
        child = subprocess.Popen([sys.executable, "-B", "-c", CHILD + code, str(ROOT), *map(str, args)],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
        self.children.append(child)
        return child

    def finish(self, child: subprocess.Popen, timeout: float = 120) -> str:
        out, err = child.communicate(timeout=timeout)
        self.assertEqual(child.returncode, 0, err[-800:])
        return out

    def wait_for(self, path: Path, timeout: float = 60) -> None:
        deadline = time.monotonic() + timeout
        while not path.exists():
            if time.monotonic() > deadline:
                self.fail("a child process did not reach its step")
            time.sleep(0.01)

    @staticmethod
    def messages(root: Path, chat: str) -> dict[str, dict]:
        folder = root / ".ultra" / "chats" / chat / "messages"
        return {p.name: json.loads(p.read_text(encoding="utf-8")) for p in folder.iterdir() if p.name.endswith(".json")}

    @staticmethod
    def card(root: Path, chat: str) -> dict:
        return json.loads((root / ".ultra" / "chats" / chat / "metadata.json").read_text(encoding="utf-8"))

    @staticmethod
    def leftovers(root: Path) -> list[str]:
        return sorted(str(p.relative_to(root)) for p in (root / ".ultra").rglob("*") if p.name.endswith(".tmp"))


class FormatTests(Base):
    def test_append_keeps_the_exact_stored_format(self):
        root, workspace_id, chat = self.workspace()
        tb = cs.new_task_block_id()
        producer = {"kind": "llm", "role_id": "main_chat", "run_id": "r1", "model_id": "m", "model_display_name": "M",
                    "provider": "p", "provider_model_id": "P"}
        result = cs.append_raw_message(root, chat, " Assistant ", "ответ\n<b>", producer=producer, task_block_id=tb)
        self.assertNotIn("created", result)
        path = root / ".ultra" / "chats" / chat / "messages" / f"{result['message_id']}.json"
        raw = path.read_bytes()
        stored = json.loads(raw)
        self.assertEqual(list(stored), ["schema_version", "workspace_id", "chat_id", "message_id", "role", "created_at",
                                        "original_text", "producer", "task_block_id"])
        self.assertEqual((stored["schema_version"], stored["workspace_id"], stored["chat_id"], stored["role"],
                          stored["original_text"], stored["producer"], stored["task_block_id"]),
                         (1, workspace_id, chat, "assistant", "ответ\n<b>", producer, tb))
        self.assertEqual(raw, (json.dumps(stored, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        self.assertEqual({k: v for k, v in result.items() if k != "path"}, stored)
        self.assertEqual(Path(result["path"]), path)

    def test_old_records_and_unknown_fields_survive_every_writer(self):
        root, workspace_id, chat = self.workspace()
        card_path = root / ".ultra" / "chats" / chat / "metadata.json"
        card = json.loads(card_path.read_text(encoding="utf-8"))
        card["future_note"] = {"kept": True}
        card_path.write_text(json.dumps(card, ensure_ascii=False), encoding="utf-8")
        legacy = root / ".ultra" / "chats" / chat / "messages" / f"{mid(1)}.json"
        legacy.write_text(json.dumps({"schema_version": 1, "workspace_id": workspace_id, "chat_id": chat, "message_id": mid(1),
                                      "role": "user", "created_at": "2025-01-01T00:00:00+00:00", "original_text": "старое"},
                                     ensure_ascii=False), encoding="utf-8")
        legacy_bytes = legacy.read_bytes()
        meta = root / ".ultra" / "workspace.json"
        meta_bytes = meta.read_bytes()
        cs.append_raw_message(root, chat, "user", "новое")
        cs.commit_raw_message(root, chat, mid(2), "assistant", "ответ")
        cs.create_chat(root, "Второй", expected_workspace_id=workspace_id)
        renamed = cs.rename_chat(root, chat, "Переименован")
        self.assertEqual(legacy.read_bytes(), legacy_bytes, "an old RAW is never rewritten")
        self.assertEqual(meta.read_bytes(), meta_bytes, "chat writers never touch workspace.json")
        stored = json.loads(card_path.read_text(encoding="utf-8"))
        self.assertEqual(stored, {**card, "title": "Переименован"})
        self.assertEqual(renamed, stored)
        self.assertEqual([m["original_text"] for m in cs.load_chat_messages(root, chat)], ["старое", "новое", "ответ"])

    def test_newer_or_damaged_formats_are_refused_by_every_writer_without_any_change(self):
        root, workspace_id, chat = self.workspace()
        cs.commit_raw_message(root, chat, mid(1), "user", "текст")
        meta = root / ".ultra" / "workspace.json"
        original = meta.read_bytes()
        writers = {
            "append": lambda: cs.append_raw_message(root, chat, "user", "x"),
            "commit": lambda: cs.commit_raw_message(root, chat, mid(9), "user", "x"),
            "create": lambda: cs.create_chat(root, "x"),
            "create expected": lambda: cs.create_chat(root, "x", expected_workspace_id=workspace_id),
            "rename": lambda: cs.rename_chat(root, chat, "x"),
            "rename workspace": lambda: cs.rename_workspace(root, "x"),
            "project context": lambda: cs.save_project_context(root, "x"),
            "variant": lambda: cs.create_message_context_variant(root, chat, mid(1), "x", source="manual_edit"),
            "restore": lambda: cs.restore_message_raw(root, chat, mid(1)),
            "ensure chat": lambda: cs.ensure_chat(root),
        }
        for label, payload in (("newer", json.dumps({"schema_version": 2, "workspace_id": workspace_id})),
                               ("damaged", "{"), ("bad id", json.dumps({"schema_version": 1, "workspace_id": "x"}))):
            meta.write_text(payload, encoding="utf-8")
            before = snapshot(self.base)
            for name, call in writers.items():
                with self.subTest(case=label, writer=name):
                    with self.assertRaises((cs.StorageWriteError, RuntimeError)):
                        call()
                    self.assertEqual(snapshot(self.base), before)
        meta.write_bytes(original)
        card = root / ".ultra" / "chats" / chat / "metadata.json"
        data = json.loads(card.read_text(encoding="utf-8"))
        for version, code in ((2, "unsupported_version"), ("1", "chat_damaged")):
            card.write_text(json.dumps({**data, "schema_version": version}), encoding="utf-8")
            before = snapshot(self.base)
            for name, call in (("rename", lambda: cs.rename_chat(root, chat, "x")),
                               ("commit", lambda: cs.commit_raw_message(root, chat, mid(9), "user", "x")),
                               ("variant", lambda: cs.create_message_context_variant(root, chat, mid(1), "x", source="manual_edit"))):
                with self.subTest(chat_version=version, writer=name):
                    with self.assertRaises(cs.StorageWriteError) as caught:
                        call()
                    self.assertEqual(caught.exception.code, code)
                    self.assertEqual(snapshot(self.base), before)
        card.write_text(json.dumps({k: v for k, v in data.items() if k != "schema_version"}), encoding="utf-8")
        self.assertEqual(cs.rename_chat(root, chat, "Старый формат")["title"], "Старый формат",
                         "a card without schema_version is an old v1 card and stays writable")

    def test_no_writer_creates_a_workspace_or_chat_on_a_read_error(self):
        bare = self.base / "bare"
        bare.mkdir()
        root, workspace_id, chat = self.workspace()
        for name, call in (("create expected", lambda: cs.create_chat(bare, "x", expected_workspace_id=workspace_id)),
                           ("record", lambda: cs.create_chat_record(bare, "x", chat_id=cid(1), expected_workspace_id=workspace_id)),
                           ("commit", lambda: cs.commit_raw_message(bare, chat, mid(1), "user", "x")),
                           ("append", lambda: cs.append_raw_message(bare, chat, "user", "x")),
                           ("rename", lambda: cs.rename_chat(bare, chat, "x"))):
            with self.subTest(writer=name):
                with self.assertRaises(cs.StorageWriteError) as caught:
                    call()
                self.assertEqual(caught.exception.code, "missing_history")
                self.assertEqual(list(bare.iterdir()), [])
        # workspace.json lost next to an existing history: no new identity for the orphaned chats
        (root / ".ultra" / "workspace.json").unlink()
        before = snapshot(self.base)
        for name, call in (("ensure", lambda: cs.ensure_workspace_storage(root)), ("tk list", lambda: cs.list_chats(root)),
                           ("tk create", lambda: cs.create_chat(root)), ("ensure chat", lambda: cs.ensure_chat(root))):
            with self.subTest(orphan=name):
                with self.assertRaises(cs.StorageWriteError) as caught:
                    call()
                self.assertEqual(caught.exception.code, "missing_workspace_metadata")
                self.assertEqual(without_lock(snapshot(self.base)), without_lock(before))
        self.assertFalse((root / ".ultra" / "workspace.json").exists())

    def test_expected_identity_is_checked_again_under_the_lock(self):
        root, workspace_id, chat = self.workspace()
        other = "ws_" + "f" * 32
        before = snapshot(self.base)
        for name, call in (("create", lambda: cs.create_chat(root, "x", expected_workspace_id=other)),
                           ("rename", lambda: cs.rename_chat(root, chat, "x", expected_workspace_id=other)),
                           ("commit", lambda: cs.commit_raw_message(root, chat, mid(1), "user", "x", expected_workspace_id=other))):
            with self.subTest(writer=name):
                with self.assertRaises(cs.StorageWriteError) as caught:
                    call()
                self.assertEqual(caught.exception.code, "workspace_identity_changed")
        self.assertEqual(snapshot(self.base), before)
        # identity replaced while the writer waited for the lock: refused after the second look
        meta = root / ".ultra" / "workspace.json"
        real = cs._read_workspace_metadata_for_write
        calls = []

        def swap_after_first(anchor):
            value = real(anchor)
            calls.append(1)
            if len(calls) == 1:  # the first look passes; the folder changes while the writer waits for the lock
                meta.write_text(json.dumps({**value, "workspace_id": other}), encoding="utf-8")
            return value
        with patch.object(cs, "_read_workspace_metadata_for_write", side_effect=swap_after_first):
            with self.assertRaises(cs.StorageWriteError) as caught:
                cs.commit_raw_message(root, chat, mid(1), "user", "x", expected_workspace_id=workspace_id)
        self.assertEqual(caught.exception.code, "workspace_identity_changed")
        self.assertFalse((root / ".ultra" / "chats" / chat / "messages" / f"{mid(1)}.json").exists())


class RawIdempotencyTests(Base):
    def test_new_id_same_content_conflict_and_same_text_under_two_ids(self):
        root, workspace_id, chat = self.workspace()
        tb = cs.new_task_block_id()
        first = cs.commit_raw_message(root, chat, mid(1), "user", "вопрос", task_block_id=tb)
        path = root / ".ultra" / "chats" / chat / "messages" / f"{mid(1)}.json"
        raw, st = path.read_bytes(), os.lstat(path)
        self.assertTrue(first["created"])
        again = cs.commit_raw_message(root, chat, mid(1), "user", "вопрос", task_block_id=tb)
        self.assertFalse(again["created"])
        self.assertEqual(again["created_at"], first["created_at"], "the stored result, not a new one")
        self.assertEqual((path.read_bytes(), os.lstat(path).st_mtime_ns), (raw, st.st_mtime_ns), "nothing written")
        producer = {"kind": "llm", "role_id": "main_chat", "run_id": "r", "model_id": "m", "model_display_name": "M",
                    "provider": "p", "provider_model_id": "P"}
        for label, kwargs in (("text", {"original_text": "другой"}), ("role", {"role": "assistant"}),
                              ("task block", {"task_block_id": cs.new_task_block_id()}), ("no task block", {"task_block_id": None}),
                              ("producer", {"producer": producer}), ("whitespace", {"original_text": "вопрос "})):
            with self.subTest(differs=label):
                args = {"role": "user", "original_text": "вопрос", "task_block_id": tb, **kwargs}
                with self.assertRaises(cs.StorageWriteError) as caught:
                    cs.commit_raw_message(root, chat, mid(1), args.pop("role"), args.pop("original_text"), **args)
                self.assertEqual(caught.exception.code, "message_id_conflict")
                self.assertEqual(path.read_bytes(), raw)
        second = cs.commit_raw_message(root, chat, mid(2), "user", "вопрос", task_block_id=tb)
        self.assertTrue(second["created"])
        self.assertEqual(sorted(self.messages(root, chat)), [f"{mid(1)}.json", f"{mid(2)}.json"])
        self.assertEqual([m["message_id"] for m in cs.read_chat_history_bounded(root, chat)["messages"]], [mid(1), mid(2)])

    def test_a_foreign_or_damaged_record_under_the_name_is_a_conflict_never_overwritten(self):
        root, workspace_id, chat = self.workspace()
        folder = root / ".ultra" / "chats" / chat / "messages"
        record = {"schema_version": 1, "workspace_id": workspace_id, "chat_id": chat, "message_id": mid(1), "role": "user",
                  "created_at": "2026-01-01T00:00:00+00:00", "original_text": "текст"}
        cases = (("other workspace", json.dumps({**record, "workspace_id": "ws_" + "e" * 32}).encode(), "message_id_conflict"),
                 ("other chat", json.dumps({**record, "chat_id": cid(5)}).encode(), "message_id_conflict"),
                 ("other name", json.dumps({**record, "message_id": mid(7)}).encode(), "message_id_conflict"),
                 ("no schema", json.dumps({k: v for k, v in record.items() if k != "schema_version"}).encode(), "message_id_conflict"),
                 ("broken json", b"{", "existing_record_damaged"), ("array", b"[]", "existing_record_damaged"),
                 ("bad utf8", b"\xff\xfe", "existing_record_damaged"))
        for label, payload, code in cases:
            with self.subTest(case=label):
                (folder / f"{mid(1)}.json").write_bytes(payload)
                with self.assertRaises(cs.StorageWriteError) as caught:
                    cs.commit_raw_message(root, chat, mid(1), "user", "текст")
                self.assertEqual(caught.exception.code, code)
                self.assertEqual((folder / f"{mid(1)}.json").read_bytes(), payload)
        (folder / f"{mid(1)}.json").write_text(json.dumps(record), encoding="utf-8")
        same = cs.commit_raw_message(root, chat, mid(1), "user", "текст")
        self.assertEqual((same["created"], same["created_at"]), (False, record["created_at"]))
        (folder / f"{mid(2)}.json").mkdir()
        with self.assertRaises(cs.StorageWriteError) as caught:
            cs.commit_raw_message(root, chat, mid(2), "user", "текст")
        self.assertEqual(caught.exception.code, "existing_record_damaged")
        self.assertTrue((folder / f"{mid(2)}.json").is_dir())

    def test_input_is_validated_before_anything_is_touched(self):
        root, _, chat = self.workspace()
        before = snapshot(self.base)
        for label, call in (("message id", lambda: cs.commit_raw_message(root, chat, "msg_../x", "user", "x")),
                            ("empty", lambda: cs.commit_raw_message(root, chat, mid(1), "user", "  ")),
                            ("role", lambda: cs.commit_raw_message(root, chat, mid(1), "hacker", "x")),
                            ("too big", lambda: cs.commit_raw_message(root, chat, mid(1), "user", "x" * (cs.MAX_MESSAGE_BYTES + 1))),
                            ("producer", lambda: cs.commit_raw_message(root, chat, mid(1), "user", "x", producer={"kind": "llm"})),
                            ("task block", lambda: cs.commit_raw_message(root, chat, mid(1), "user", "x", task_block_id="tb_x")),
                            ("chat id", lambda: cs.commit_raw_message(root, "chat_..", mid(1), "user", "x"))):
            with self.subTest(case=label):
                with self.assertRaises((ValueError, TypeError)):
                    call()
        self.assertEqual(snapshot(self.base), before)
        with self.assertRaises(cs.ChatNotFoundError):
            cs.commit_raw_message(root, cid(3), mid(1), "user", "x")
        self.assertIsInstance(cs.ChatNotFoundError("x"), FileNotFoundError)

    def test_the_largest_allowed_text_round_trips_byte_exact(self):
        root, _, chat = self.workspace()
        text = ("\"\\\n" + "я") * ((cs.MAX_MESSAGE_BYTES - 16) // 5)
        self.assertLessEqual(len(text.encode("utf-8")), cs.MAX_MESSAGE_BYTES)
        cs.commit_raw_message(root, chat, mid(1), "user", text)
        self.assertFalse(cs.commit_raw_message(root, chat, mid(1), "user", text)["created"])
        self.assertEqual(self.messages(root, chat)[f"{mid(1)}.json"]["original_text"], text)

    def test_legacy_append_still_gives_every_call_its_own_message(self):
        root, _, chat = self.workspace()
        ids = {cs.append_raw_message(root, chat, "user", "одинаково")["message_id"] for _ in range(3)}
        self.assertEqual(len(ids), 3)
        self.assertEqual(len(self.messages(root, chat)), 3)


class ChatWriterTests(Base):
    def test_create_with_a_chosen_id_is_idempotent_and_conflicts_are_explicit(self):
        root, workspace_id, _ = self.workspace()
        made = cs.create_chat_record(root, "Веб", chat_id=cid(1), expected_workspace_id=workspace_id)
        card = root / ".ultra" / "chats" / cid(1) / "metadata.json"
        raw = card.read_bytes()
        for title in ("Веб", None, "  Веб  ", ""):
            with self.subTest(repeat=title):
                again = cs.create_chat_record(root, title, chat_id=cid(1), expected_workspace_id=workspace_id)
                self.assertEqual((again["created"], again["chat"]), (False, made["chat"]))
        with self.assertRaises(cs.StorageWriteError) as caught:
            cs.create_chat_record(root, "Другой", chat_id=cid(1), expected_workspace_id=workspace_id)
        self.assertEqual(caught.exception.code, "chat_id_conflict")
        self.assertEqual(card.read_bytes(), raw)
        (root / ".ultra" / "chats" / cid(2)).mkdir()
        with self.assertRaises(cs.StorageWriteError) as caught:
            cs.create_chat_record(root, "x", chat_id=cid(2), expected_workspace_id=workspace_id)
        self.assertEqual(caught.exception.code, "chat_id_conflict")
        self.assertEqual(list((root / ".ultra" / "chats" / cid(2)).iterdir()), [])
        self.assertEqual(json.loads(raw), {"schema_version": 1, "workspace_id": workspace_id, "chat_id": cid(1),
                                           "title": "Веб", "created_at": made["chat"]["created_at"]})

    def test_default_titles_ignore_damaged_cards_and_the_chat_limit_is_kept(self):
        root, _, first = self.workspace(title="Чат 1")
        broken = cs.create_chat(root)["chat_id"]
        (root / ".ultra" / "chats" / broken / "metadata.json").write_text("{", encoding="utf-8")
        third = cs.create_chat(root)
        self.assertEqual(third["title"], "Чат 2", "a damaged card no longer blocks a new chat (P1 on create)")
        with patch.object(cs, "MAX_CHATS_PER_WORKSPACE", 3):
            before = snapshot(self.base)
            with self.assertRaises(cs.StorageWriteError) as caught:
                cs.create_chat(root, "лишний")
            self.assertEqual(caught.exception.code, "chats_limit_reached")
            self.assertEqual(without_lock(snapshot(self.base)), without_lock(before))

    def test_rename_checks_the_seen_title_ownership_and_keeps_a_repeat_free(self):
        root, workspace_id, chat = self.workspace()
        card = root / ".ultra" / "chats" / chat / "metadata.json"
        cs.rename_chat(root, chat, "Первый", expected_title="Диалог")
        raw, st = card.read_bytes(), os.lstat(card)
        self.assertEqual(cs.rename_chat(root, chat, "Первый", expected_title="Диалог")["title"], "Первый")
        self.assertEqual((card.read_bytes(), os.lstat(card).st_mtime_ns), (raw, st.st_mtime_ns), "a repeat writes nothing")
        with self.assertRaises(cs.StorageWriteError) as caught:
            cs.rename_chat(root, chat, "Второй", expected_title="Диалог")
        self.assertEqual(caught.exception.code, "title_changed")
        self.assertEqual(card.read_bytes(), raw)
        data = json.loads(raw)
        card.write_text(json.dumps({**data, "workspace_id": "ws_" + "e" * 32}), encoding="utf-8")
        with self.assertRaises(cs.StorageWriteError) as caught:
            cs.rename_chat(root, chat, "Чужой")
        self.assertEqual(caught.exception.code, "foreign_identity")
        with self.assertRaises(cs.ChatNotFoundError):
            cs.rename_chat(root, cid(4), "x")

    def test_titles_are_validated_before_any_write(self):
        root, _, chat = self.workspace()
        before = snapshot(self.base)
        for label, title in (("empty", "  "), ("long", "я" * 201), ("newline", "a\nb"), ("tab", "a\tb"),
                             ("nul", "a\x00b"), ("line separator", "a" + chr(0x2028) + "b"), ("c1", "a" + chr(0x85) + "b")):
            with self.subTest(title=label):
                with self.assertRaises(ValueError):
                    cs.rename_chat(root, chat, title)
                if label != "empty":
                    with self.assertRaises(ValueError):
                        cs.create_chat(root, title)
        self.assertEqual(snapshot(self.base), before)
        self.assertEqual(cs.rename_chat(root, chat, "я" * 200)["title"], "я" * 200)


class LockTests(Base):
    HOLD = ("anchor = cs._write_anchor(Path(sys.argv[2]))\n"
            "with cs._workspace_writer_lock(anchor):\n"
            "    open(sys.argv[3], 'w').close()\n"
            "    time.sleep(float(sys.argv[4]))\n")

    def test_reads_take_no_lock_and_create_nothing(self):
        root, _, chat = self.workspace()
        shutil.rmtree(root / ".ultra" / "locks")
        cs.append_raw_message(root, chat, "user", "x")  # recreates the lock folder; reading must not
        shutil.rmtree(root / ".ultra" / "locks")
        before = snapshot(self.base)
        cs.ensure_workspace_storage(root)
        cs.list_chats(root)
        cs.list_existing_chats(root)
        cs.load_chat_messages(root, chat)
        cs.load_chat_working_messages(root, chat)
        cs.load_project_context(root)
        cs.list_chats_bounded(root)
        cs.read_chat_history_bounded(root, chat)
        cs.probe_existing_workspace(root)
        self.assertEqual(snapshot(self.base), before)

    def test_a_held_lock_makes_writers_wait_and_then_refuse_visibly(self):
        root, _, chat = self.workspace()
        held = self.base / "held"
        holder = self.spawn(self.HOLD, root, held, 30)
        self.wait_for(held)
        before = without_lock(snapshot(self.base))
        with patch.object(cs, "WRITER_LOCK_TIMEOUT_SECONDS", 0.4):
            for name, call in (("append", lambda: cs.append_raw_message(root, chat, "user", "x")),
                               ("create", lambda: cs.create_chat(root, "x")),
                               ("rename", lambda: cs.rename_chat(root, chat, "x")),
                               ("project context", lambda: cs.save_project_context(root, "x"))):
                with self.subTest(writer=name):
                    started = time.monotonic()
                    with self.assertRaises(cs.WorkspaceBusyError) as caught:
                        call()
                    self.assertGreaterEqual(time.monotonic() - started, 0.35)
                    self.assertEqual(caught.exception.code, "workspace_busy")
        self.assertEqual(without_lock(snapshot(self.base)), before)
        holder.kill()  # the holder dies with the lock: the OS releases it
        holder.communicate(timeout=30)
        with patch.object(cs, "WRITER_LOCK_TIMEOUT_SECONDS", 5):
            self.assertEqual(cs.rename_chat(root, chat, "После падения")["title"], "После падения")

    def test_a_workspace_can_be_read_and_copied_while_a_writer_holds_the_lock(self):
        root, workspace_id, chat = self.workspace()
        cs.append_raw_message(root, chat, "user", "x")
        held = self.base / "held"
        holder = self.spawn(self.HOLD, root, held, 30)
        self.wait_for(held)
        copy = self.base / "copy"
        shutil.copytree(root, copy)  # every file, the lock file included, stays readable
        self.assertEqual((root / ".ultra" / "locks" / "writer.lock").read_bytes(), b"")
        self.assertEqual(cs.read_chat_history_bounded(copy, chat)["workspace_id"], workspace_id)
        self.assertEqual(cs.commit_raw_message(copy, chat, mid(3), "user", "в копии")["created"], True,
                         "the copy has its own lock, free while the original is held")
        holder.kill()
        holder.communicate(timeout=30)

    def test_a_writer_waits_for_a_short_holder_and_then_succeeds(self):
        root, _, chat = self.workspace()
        held = self.base / "held"
        holder = self.spawn(self.HOLD, root, held, 0.6)
        self.wait_for(held)
        started = time.monotonic()
        cs.commit_raw_message(root, chat, mid(1), "user", "после ожидания")
        self.assertGreaterEqual(time.monotonic() - started, 0.2, "the writer did not wait for the holder")
        self.finish(holder)

    def test_nested_calls_reenter_and_other_threads_wait(self):
        root, _, chat = self.workspace()
        raw = cs.commit_raw_message(root, chat, mid(1), "user", "x")
        started = time.monotonic()
        variant = cs.create_message_context_variant(root, chat, raw["message_id"], "кратко", source="manual_edit")
        self.assertLess(time.monotonic() - started, 5, "a nested writer must not wait for its own lock")
        self.assertEqual(cs.get_message_context_state(root, chat, mid(1))["active_variant_id"], variant["context_variant_id"])
        anchor = cs._write_anchor(root)
        entered, results = threading.Event(), []
        with cs._workspace_writer_lock(anchor):
            with cs._workspace_writer_lock(anchor):  # reentrant in the same thread
                pass

            def other():
                entered.set()
                results.append(cs.commit_raw_message(root, chat, mid(2), "user", "из потока")["created"])
            thread = threading.Thread(target=other)
            thread.start()
            entered.wait(5)
            time.sleep(0.3)
            self.assertEqual(results, [], "another thread wrote while the lock was held")
        thread.join(15)
        self.assertEqual(results, [True])
        self.assertEqual(cs._held_writer_locks(), {})

    def test_the_lock_folder_is_never_a_junction(self):
        root, _, chat = self.workspace()
        other, _, _ = self.workspace("other")
        locks = root / ".ultra" / "locks"
        shutil.rmtree(locks)
        self.junction(other / ".ultra" / "locks", locks)
        before = snapshot(other)
        with self.assertRaises(cs.StorageWriteError) as caught:
            cs.append_raw_message(root, chat, "user", "x")
        self.assertEqual(caught.exception.code, "unsafe_storage_link")
        self.assertEqual(snapshot(other), before)

    def test_the_lock_file_is_never_a_symlink_when_the_platform_allows_creating_one(self):
        root, _, chat = self.workspace()
        other, _, _ = self.workspace("other")
        lock = root / ".ultra" / "locks" / "writer.lock"
        lock.unlink()
        try:
            os.symlink(other / ".ultra" / "locks" / "writer.lock", lock)
        except OSError:
            self.skipTest("symlink creation needs a privilege this host does not grant (NOT RUN, junctions covered)")
        with self.assertRaises(cs.StorageWriteError) as caught:
            cs.append_raw_message(root, chat, "user", "x")
        self.assertEqual(caught.exception.code, "unsafe_storage_link")


class ConcurrencyTests(Base):
    GO = ("ready, go = Path(sys.argv[3]), Path(sys.argv[4])\nready.write_text('1')\n"
          "while not go.exists():\n    time.sleep(0.002)\n")

    def start_together(self, code: str, count: int, *args) -> list[subprocess.Popen]:
        go = self.base / "go"
        children = []
        for n in range(count):
            ready = self.base / f"ready{n}"
            children.append(self.spawn(self.GO + code, args[0], ready, go, n, *args[1:]))
        for n in range(count):
            self.wait_for(self.base / f"ready{n}")
        go.write_text("1")
        return children

    def test_two_processes_write_raw_create_and_rename_without_losing_anything(self):
        root, _, chat = self.workspace()
        code = ("root, n = sys.argv[2], int(sys.argv[5])\nmade = []\n"
                "for k in range(25):\n"
                "    cs.append_raw_message(root, sys.argv[6], 'user', 'p%d-%d' % (n, k))\n"
                "    if k % 5 == 0:\n        made.append(cs.create_chat(root)['chat_id'])\n"
                "    if k % 3 == 0:\n        cs.rename_chat(root, sys.argv[6], 'p%d-%d' % (n, k))\n"
                "print(json.dumps(made))\n")
        children = self.start_together(code, 2, root, chat)
        made = [json.loads(self.finish(child)) for child in children]
        stored = self.messages(root, chat)
        self.assertEqual(len(stored), 50, "lost RAW")
        self.assertEqual(sorted(m["original_text"] for m in stored.values()),
                         sorted(f"p{n}-{k}" for n in range(2) for k in range(25)))
        self.assertTrue(all(name == m["message_id"] + ".json" for name, m in stored.items()))
        titles = [self.card(root, c)["title"] for group in made for c in group]
        self.assertEqual(len(titles), 10)
        self.assertEqual(len(set(titles)), 10, "two processes chose the same default title: the listing was not locked")
        self.assertIn(self.card(root, chat)["title"], {"p0-24", "p1-24"})
        self.assertEqual(self.leftovers(root), [])
        self.assertFalse((root / ".ultra" / "chat_staging").exists())

    def test_processes_that_initialise_one_folder_share_one_identity(self):
        root = self.base / "fresh"
        root.mkdir()
        code = "print(cs.ensure_workspace_storage(sys.argv[2])['workspace_id'])\n"
        children = self.start_together(code, 4, root)
        ids = {self.finish(child).strip() for child in children}
        on_disk = json.loads((root / ".ultra" / "workspace.json").read_text(encoding="utf-8"))["workspace_id"]
        self.assertEqual(ids, {on_disk}, "a process returned an identity that is not the stored one")
        self.assertEqual(self.leftovers(root), [])

    def test_two_processes_commit_one_message_id(self):
        root, _, chat = self.workspace()
        for label, texts in (("same", ("одно", "одно")), ("different", ("первый", "второй"))):
            with self.subTest(content=label):
                message_id = mid(len(label))
                code = ("try:\n    r = cs.commit_raw_message(sys.argv[2], sys.argv[6], sys.argv[7], 'user', sys.argv[8 + int(sys.argv[5])])\n"
                        "    print(json.dumps({'created': r['created'], 'text': r['original_text']}))\n"
                        "except cs.StorageWriteError as e:\n    print(json.dumps({'conflict': e.code}))\n")
                for leftover in self.base.glob("ready*"):
                    leftover.unlink()
                (self.base / "go").unlink(missing_ok=True)
                children = self.start_together(code, 2, root, chat, message_id, *texts)
                outcomes = [json.loads(self.finish(child)) for child in children]
                stored = self.messages(root, chat)[f"{message_id}.json"]["original_text"]
                if label == "same":
                    self.assertEqual(sorted(o["created"] for o in outcomes), [False, True])
                else:
                    winners = [o for o in outcomes if "created" in o]
                    self.assertEqual((len(winners), [o.get("conflict") for o in outcomes if "conflict" in o]),
                                     (1, ["message_id_conflict"]))
                    self.assertEqual(stored, winners[0]["text"])

    def test_two_renames_from_the_same_seen_title_never_lose_one_silently(self):
        root, _, chat = self.workspace()
        code = ("try:\n    cs.rename_chat(sys.argv[2], sys.argv[6], 'from-%s' % sys.argv[5], expected_title='Диалог')\n"
                "    print('ok')\nexcept cs.StorageWriteError as e:\n    print(e.code)\n")
        children = self.start_together(code, 2, root, chat)
        outcomes = sorted(self.finish(child).strip() for child in children)
        self.assertEqual(outcomes, ["ok", "title_changed"])
        self.assertIn(self.card(root, chat)["title"], {"from-0", "from-1"})

    def test_ensure_chat_from_two_processes_makes_one_chat(self):
        root = self.base / "w"
        root.mkdir()
        cs.ensure_workspace_storage(root)
        code = "print(cs.ensure_chat(sys.argv[2])['chat_id'])\n"
        children = self.start_together(code, 2, root)
        ids = {self.finish(child).strip() for child in children}
        self.assertEqual(len(ids), 1)
        self.assertEqual(len(list((root / ".ultra" / "chats").iterdir())), 1)


class CrashTests(Base):
    # A child dies (os._exit) at one step of a publication; a fresh process then repeats the operation.
    DIE_AT = ("real = getattr(os, sys.argv[3])\n"
              "def die(*a, **k):\n"
              "    if sys.argv[4] == 'after':\n        real(*a, **k)\n"
              "    os._exit(17)\n"
              "setattr(os, sys.argv[3], die)\n")

    def crash(self, code: str, root: Path, function: str, when: str, *args) -> None:
        child = self.spawn(self.DIE_AT + code, root, function, when, *args)
        child.communicate(timeout=120)
        self.assertEqual(child.returncode, 17, "the child did not die at the intended step")

    def test_crash_before_and_after_raw_publication_then_restart(self):
        root, _, chat = self.workspace()
        publish = "rename" if os.name == "nt" else "link"
        commit = "cs.commit_raw_message(sys.argv[2], sys.argv[5], sys.argv[6], 'user', 'после сбоя')\n"
        self.crash(commit, root, publish, "before", chat, mid(1))
        self.assertEqual(self.messages(root, chat), {}, "a half publication is visible")
        self.assertEqual(len(self.leftovers(root)), 1, "the hidden temporary file of the dead writer")
        self.assertEqual(cs.read_chat_history_bounded(root, chat)["messages"], [])
        self.assertEqual(cs.load_chat_messages(root, chat), [])
        self.assertTrue(cs.commit_raw_message(root, chat, mid(1), "user", "после сбоя")["created"])
        self.crash(commit, root, publish, "after", chat, mid(2))
        self.assertIn(f"{mid(2)}.json", self.messages(root, chat), "published before the crash")
        again = cs.commit_raw_message(root, chat, mid(2), "user", "после сбоя")
        self.assertFalse(again["created"], "the repeat after a restart must not write a second RAW")
        with self.assertRaises(cs.StorageWriteError):
            cs.commit_raw_message(root, chat, mid(2), "user", "иначе")
        self.assertEqual(len(self.messages(root, chat)), 2)
        self.assertEqual([m["text"] for m in cs.read_chat_history_bounded(root, chat)["messages"]], ["после сбоя"] * 2)

    def test_crash_while_a_chat_is_published_leaves_no_visible_half_chat(self):
        root, workspace_id, chat = self.workspace()
        create = "cs.create_chat(sys.argv[2], 'Новый', expected_workspace_id=sys.argv[5])\n"
        self.crash(create, root, "rename", "before", workspace_id)
        self.assertEqual([c["chat_id"] for c in cs.list_existing_chats(root)], [chat])
        self.assertEqual([c["chat_id"] for c in cs.list_chats_bounded(root)["chats"]], [chat])
        staged = list((root / ".ultra" / "chat_staging").iterdir())
        self.assertEqual(len(staged), 1, "the dead writer's staging stays outside the chat list")
        self.assertEqual(cs.create_chat(root, "Новый", expected_workspace_id=workspace_id)["title"], "Новый")
        self.assertEqual(len(cs.list_chats_bounded(root)["chats"]), 2)
        self.crash(create, root, "rename", "after", workspace_id)
        self.assertEqual(sorted(c["title"] for c in cs.list_chats_bounded(root)["chats"]), ["Диалог", "Новый", "Новый"])

    def test_crash_before_and_after_the_metadata_replacement(self):
        root, _, chat = self.workspace()
        rename = "cs.rename_chat(sys.argv[2], sys.argv[5], sys.argv[6])\n"
        self.crash(rename, root, "replace", "before", chat, "Не сохранено")
        self.assertEqual(self.card(root, chat)["title"], "Диалог", "the old card is intact")
        self.assertEqual(len(self.leftovers(root)), 1)
        self.crash(rename, root, "replace", "after", chat, "Сохранено")
        self.assertEqual(self.card(root, chat)["title"], "Сохранено")
        self.assertEqual(cs.rename_chat(root, chat, "Сохранено", expected_title="Диалог")["title"], "Сохранено",
                         "the repeat after a restart is a no-op")

    def test_replacement_blocked_by_an_open_reader_is_retried_then_refused_visibly(self):
        if os.name != "nt":
            self.skipTest("Windows sharing semantics (stage 0, P11/P12)")
        root, _, chat = self.workspace()
        card = root / ".ultra" / "chats" / chat / "metadata.json"
        handle = open(card, "rb")  # a reader that keeps the file open, as stage 0 measured
        timer = threading.Timer(0.25, handle.close)
        timer.start()
        self.assertEqual(cs.rename_chat(root, chat, "После читателя")["title"], "После читателя")
        timer.join()
        raw = card.read_bytes()
        with open(card, "rb"):
            with patch.object(cs, "_REPLACE_RETRY_DELAYS", (0.01, 0.01)):
                with self.assertRaises(PermissionError):
                    cs.rename_chat(root, chat, "Не пройдёт")
        self.assertEqual(card.read_bytes(), raw)
        self.assertEqual(self.leftovers(root), [])

    def test_a_chat_folder_that_cannot_move_yet_is_retried_then_refused_without_leftovers(self):
        root, workspace_id, _ = self.workspace()
        real = os.rename
        refusals = []

        def busy(source, target, limit):
            if Path(target).parent.name == "chats" and len(refusals) < limit:
                refusals.append(1)
                raise PermissionError(13, "a file in the folder is open")
            return real(source, target)
        with patch.object(cs.os, "rename", side_effect=lambda s, t: busy(s, t, 2)):
            made = cs.create_chat(root, "После повтора", expected_workspace_id=workspace_id)
        self.assertEqual((len(refusals), self.card(root, made["chat_id"])["title"]), (2, "После повтора"))
        refusals.clear()
        before = {c["chat_id"] for c in cs.list_chats_bounded(root)["chats"]}
        with patch.object(cs, "_REPLACE_RETRY_DELAYS", (0.01, 0.01)), \
                patch.object(cs.os, "rename", side_effect=lambda s, t: busy(s, t, 99)):
            with self.assertRaises(PermissionError):
                cs.create_chat(root, "Не выйдет", expected_workspace_id=workspace_id)
        self.assertEqual(len(refusals), 3)
        self.assertEqual({c["chat_id"] for c in cs.list_chats_bounded(root)["chats"]}, before)
        self.assertFalse((root / ".ultra" / "chat_staging").exists(), "the staging of the refused chat is removed")

    def test_write_failures_leave_no_record_and_no_temporary_file(self):
        root, _, chat = self.workspace()

        def full_disk(*_args):
            raise OSError(28, "No space left on device")
        with patch.object(cs.os, "write", side_effect=full_disk):
            with self.assertRaises(OSError):
                cs.commit_raw_message(root, chat, mid(1), "user", "x")
        with patch.object(cs.os, "fsync", side_effect=OSError(5, "I/O error")):
            with self.assertRaises(OSError):
                cs.rename_chat(root, chat, "x")
        self.assertEqual((self.messages(root, chat), self.leftovers(root), self.card(root, chat)["title"]), ({}, [], "Диалог"))
        self.assertTrue(cs.commit_raw_message(root, chat, mid(1), "user", "x")["created"])

    def test_a_record_published_by_a_writer_outside_the_lock_is_never_overwritten(self):
        root, workspace_id, chat = self.workspace()
        target = root / ".ultra" / "chats" / chat / "messages" / f"{mid(1)}.json"
        real = cs._read_existing_raw
        calls = []

        def racing_writer(writer, parts):
            calls.append(1)
            if len(calls) == 1:  # the name is free at the check, then a lockless old writer takes it
                target.write_text(json.dumps({"schema_version": 1, "workspace_id": workspace_id, "chat_id": chat,
                                              "message_id": mid(1), "role": "user", "created_at": "2026-01-01T00:00:00+00:00",
                                              "original_text": "чужой"}), encoding="utf-8")
                return None
            return real(writer, parts)
        with patch.object(cs, "_read_existing_raw", side_effect=racing_writer):
            with self.assertRaises(cs.StorageWriteError) as caught:
                cs.commit_raw_message(root, chat, mid(1), "user", "мой")
        self.assertEqual(caught.exception.code, "message_id_conflict")
        self.assertEqual(json.loads(target.read_text(encoding="utf-8"))["original_text"], "чужой")
        self.assertEqual(self.leftovers(root), [])


class PathSafetyTests(Base):
    def test_links_in_the_written_path_are_refused_and_the_target_stays_untouched(self):
        other, _, other_chat = self.workspace("other")
        cs.append_raw_message(other, other_chat, "user", "ЧУЖОЕ")
        writers_of = {"chats": ("commit", "append", "rename", "create", "variant"), "chat": ("commit", "append", "rename", "variant"),
                      "messages": ("commit", "append"), "ultra": ("commit", "append", "rename", "create", "variant")}
        for case, affected in writers_of.items():
            with self.subTest(link=case):
                root = self.base / f"w_{case}"
                root.mkdir()
                workspace_id = cs.ensure_workspace_storage(root)["workspace_id"]
                chat = cs.create_chat(root, "Свой")["chat_id"]
                if case == "chats":
                    shutil.rmtree(root / ".ultra" / "chats")
                    self.junction(other / ".ultra" / "chats", root / ".ultra" / "chats")
                    chat = other_chat
                elif case == "chat":
                    shutil.rmtree(root / ".ultra" / "chats" / chat)
                    chat = other_chat
                    self.junction(other / ".ultra" / "chats" / other_chat, root / ".ultra" / "chats" / chat)
                elif case == "messages":
                    shutil.rmtree(root / ".ultra" / "chats" / chat / "messages")
                    self.junction(other / ".ultra" / "chats" / other_chat / "messages", root / ".ultra" / "chats" / chat / "messages")
                else:
                    shutil.rmtree(root / ".ultra")
                    self.junction(other / ".ultra", root / ".ultra")
                    chat = other_chat
                before = snapshot(other)
                for name, call in (("commit", lambda: cs.commit_raw_message(root, chat, mid(1), "user", "x")),
                                   ("append", lambda: cs.append_raw_message(root, chat, "user", "x")),
                                   ("rename", lambda: cs.rename_chat(root, chat, "x")),
                                   ("create", lambda: cs.create_chat(root, "x", expected_workspace_id=workspace_id)),
                                   ("variant", lambda: cs.restore_message_raw(root, chat, mid(1)))):
                    if name not in affected:
                        continue
                    with self.subTest(link=case, writer=name):
                        with self.assertRaises(Exception) as caught:
                            call()
                        self.assertIn(getattr(caught.exception, "code", None),
                                      {"unsafe_storage_link", "workspace_identity_changed", "foreign_identity"}, repr(caught.exception))
                self.assertEqual(snapshot(other), before, "a write reached the other Workspace")

    def test_a_directory_swapped_after_its_check_is_refused_before_publication(self):
        other, _, other_chat = self.workspace("other")
        root, _, chat = self.workspace()
        messages = root / ".ultra" / "chats" / chat / "messages"
        real = cs._read_existing_raw
        before = snapshot(other)

        def swap(writer, parts):
            os.rmdir(messages)
            self.junction(other / ".ultra" / "chats" / other_chat / "messages", messages)
            return real(writer, parts)
        with patch.object(cs, "_read_existing_raw", side_effect=swap):
            with self.assertRaises(cs.StorageWriteError) as caught:
                cs.commit_raw_message(root, chat, mid(1), "user", "x")
        self.assertEqual(caught.exception.code, "unsafe_storage_link")
        self.assertEqual(snapshot(other), before, "nothing was published into the other Workspace")
        # A swap in the remaining window (after the temporary file is checked, before its rename) is still only
        # detected afterwards by the read-back; the stage 0 contract does not promise defence against another
        # program of the same user (section 9). Simulated here by swapping right before the rename:
        os.rmdir(messages)
        self.junctions.remove(messages)
        messages.mkdir()
        real_rename = os.rename

        def late_swap(source, target):
            if str(target).endswith(f"{mid(2)}.json"):
                shutil.move(str(source), str(other / ".ultra" / "chats" / other_chat / "messages" / Path(source).name))
                os.rmdir(messages)
                self.junction(other / ".ultra" / "chats" / other_chat / "messages", messages)
            return real_rename(source, target)
        if os.name == "nt":
            with patch.object(cs.os, "rename", side_effect=late_swap):
                with self.assertRaises(cs.StorageWriteError) as caught:
                    cs.commit_raw_message(root, chat, mid(2), "user", "x")
            self.assertEqual(caught.exception.code, "unsafe_storage_link", "the read-back must catch the late swap")


class PortabilityTests(Base):
    def test_a_copied_or_moved_workspace_keeps_identity_ids_and_history_and_writes_only_to_itself(self):
        root, workspace_id, chat = self.workspace()
        cs.commit_raw_message(root, chat, mid(1), "user", "до копии")
        cs.append_raw_message(root, chat, "assistant", "ответ")
        original = cs.read_chat_history_bounded(root, chat)
        copy = self.base / "copy" / "nested"
        shutil.copytree(root, copy)
        moved = self.base / "moved"
        shutil.copytree(root, self.base / "to_move")
        os.rename(self.base / "to_move", moved)
        for label, place in (("copy", copy), ("move", moved)):
            with self.subTest(place=label):
                history = cs.read_chat_history_bounded(place, chat)
                self.assertEqual((history["workspace_id"], history["chat"], history["messages"]),
                                 (workspace_id, original["chat"], original["messages"]))
                self.assertEqual([m["message_id"] for m in cs.load_chat_messages(place, chat)],
                                 [m["message_id"] for m in original["messages"]])
                self.assertEqual(cs.probe_existing_workspace(place, workspace_id)["status"], "ok")
        before = snapshot(root)
        anchor = cs._write_anchor(root)
        with cs._workspace_writer_lock(anchor):  # the original is locked: the copy has its own lock file
            box = []
            thread = threading.Thread(target=lambda: box.append(cs.commit_raw_message(copy, chat, mid(2), "user", "в копии")))
            thread.start()
            thread.join(15)
        self.assertEqual(box[0]["created"], True)
        self.assertFalse(box[0]["path"].startswith(str(root) + os.sep))
        cs.rename_chat(moved, chat, "Перемещён")
        self.assertEqual(snapshot(root), before, "a write to a copy changed the original")
        self.assertEqual(self.card(copy, chat)["title"], "Диалог")
        self.assertEqual(self.card(moved, chat)["title"], "Перемещён")


if __name__ == "__main__":
    unittest.main()
