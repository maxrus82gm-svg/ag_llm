"""Tests for tools/task_slot_rotate.py (BLOCK 1 -> BLOCK 1.1 rotation, DOC-BLOCK1-SLOT-01@1).

Every test works on synthetic cards in its own temporary folder; the real cards are only read (test_real_cards_*).
Run: python -B -m unittest tools/test_task_slot_rotate.py   (TASK_SLOT_ROTATE_UNDER_TEST=<file> tests a mutant).
"""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
SCRIPT = Path(os.environ.get("TASK_SLOT_ROTATE_UNDER_TEST") or HERE / "task_slot_rotate.py")
_spec = importlib.util.spec_from_file_location("task_slot_rotate_under_test", SCRIPT)
tsr = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = tsr  # dataclasses look the module up while the class is built
_spec.loader.exec_module(tsr)

REPO = HERE.parent
TASK = "CLAUDE-TEST-SLOT-001"
TASK2 = "CLAUDE-TEST-SLOT-002"
# Fixed by the regulation (№18 DOC-BLOCK1-SLOT-01@1), written here literally on purpose.
WAITING_LITERAL = "**ОЖИДАНИЕ НОВОЙ ЗАДАЧИ.**"
H1_LITERAL = "# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА"
H11_LITERAL = "# БЛОК 1.1 — ПОСЛЕДНЯЯ СДАННАЯ ЗАДАЧА"
DATE = "2026-10-29"


def task_text(task_id=TASK, title="проверочная постановка", extra=""):
    return (f"# 🟨 Задача: {title}\n\n**TASK ID:** `{task_id}`  \n\n"
            "Текст с `кодом`, хвостовыми пробелами   \n"
            "Разделители внутри строки: LS, PS,\u0085NEL и одиночный\rCR.\n\n"
            "---\n\n## 2. Пункт\n\n- пункт а\n    \n- пункт б\n" + extra +
            f"\n**AMENDMENT к** `**{task_id}**`**:**\n\nОстальное без изменений.\n")


def make_card(b1=None, b11=None, markers=True, eol="\n", bom=False):
    b1 = task_text() if b1 is None else b1
    b11 = tsr.PLACEHOLDERS[0] + "\n" if b11 is None else b11

    def m(marker):
        return marker + "\n" if markers else ""
    text = ("# Рабочая карточка исполнителя — Test\n\n## Рабочий порядок\n\nПравила карточки.\n\n"
            f"{H1_LITERAL}\n---\n\n{m(tsr.B1_BEGIN)}{b1}{m(tsr.B1_END)}\n---\n\n"
            f"{H11_LITERAL}\n\n{m(tsr.B11_BEGIN)}{b11}{m(tsr.B11_END)}\n"
            "# БЛОК 2 — ПЯТЬ ПОСЛЕДНИХ ЗАДАЧ (КОМПАКТНО)\n\n- старая запись\n\n---\n\n"
            "# БЛОК 4 — НЕЗАВИСИМАЯ ПРИЁМКА\n\nТекст verdict.\n\n**NEXT:** ждать.\n")
    data = text.replace("\n", eol).encode("utf-8")
    return (b"\xef\xbb\xbf" + data) if bom else data


def lines_between(data, begin, end):
    lines = tsr.split_lines(data)
    texts = [tsr.line_text(x) for x in lines]
    i, j = texts.index(begin), texts.index(end)
    return b"".join(lines[i + 1:j])


class Workspace:
    def __init__(self, root):
        self.root = Path(root) / "ag_llm"
        (self.root / "Документация").mkdir(parents=True)
        self.card_path = self.root / "Документация" / "000_Задачи Test.md"

    def card(self, data):
        self.card_path.write_bytes(data)
        return self.card_path

    def package(self, task=TASK, status="RESULT READY / AWAITING INDEPENDENT VERIFICATION",
                head="# Отчёт\n\n**Статус: RESULT READY / AWAITING INDEPENDENT VERIFICATION.**\n"):
        folder = self.root / "reports" / task
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "report.md").write_text(head, encoding="utf-8")
        (folder / "manifest.json").write_text(json.dumps({"status": status}), encoding="utf-8")
        return folder

    def archive(self, data=b"# Archive\n"):
        path = self.root / "Документация" / "001_История выполненных задач Test.md"
        path.write_bytes(data)
        return path


def run(*argv, hook=None):
    out = io.StringIO()
    old_hook = tsr._BEFORE_CARD_WRITE
    tsr._BEFORE_CARD_WRITE = hook
    try:
        with contextlib.redirect_stdout(out):
            code = tsr.main([str(a) for a in argv])
    finally:
        tsr._BEFORE_CARD_WRITE = old_hook
    return code, json.loads(out.getvalue())


def codes(proto):
    return {p["code"] for p in proto.get("problems", [])}


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="task-slot-test-")
        self.ws = Workspace(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def rotate(self, *extra, task=TASK, apply=True, amend=("--no-chat-amendment",), hook=None):
        args = ["rotate", "--card", self.ws.card_path, "--task-id", task, "--date", DATE, *amend, *extra]
        return run(*(args + (["--apply"] if apply else [])), hook=hook)

    def assert_refused(self, expected, *extra, task=TASK, amend=("--no-chat-amendment",)):
        before = self.ws.card_path.read_bytes()
        for apply in (False, True):
            code, proto = self.rotate(*extra, task=task, apply=apply, amend=amend)
            self.assertEqual(code, 3, proto)
            self.assertEqual(proto["result"], "NO ROTATE")
            self.assertIn(expected, codes(proto), proto)
            self.assertEqual(self.ws.card_path.read_bytes(), before, "the card must stay byte-identical")
        return proto


class Rotation(Base):
    def check_rotated(self, before, eol=b"\n"):
        after = self.ws.card_path.read_bytes()
        body1 = lines_between(after, tsr.B1_BEGIN, tsr.B1_END)
        self.assertEqual(body1, WAITING_LITERAL.encode() + eol, "BLOCK 1 must be exactly the waiting line")
        old_body = lines_between(before, tsr.B1_BEGIN, tsr.B1_END)
        slot = tsr.split_lines(lines_between(after, tsr.B11_BEGIN, tsr.B11_END))
        self.assertRegex(tsr.line_text(slot[0]), r"^\*\*SUBMITTED / REVIEW PENDING\*\* · TASK ID `" + TASK + "`")
        self.assertEqual(slot[1], eol)
        self.assertEqual(b"".join(slot[2:]), old_body, "BLOCK 1.1 must hold the old BLOCK 1 byte for byte")
        # Everything outside the two slot bodies is unchanged.
        cut = lambda d: (d[:d.index(tsr.B1_BEGIN.encode())], d[d.index(tsr.B1_END.encode()):d.index(tsr.B11_BEGIN.encode())],
                         d[d.index(tsr.B11_END.encode()):])
        self.assertEqual(cut(after), cut(before))
        return after

    def test_r01_rotate_lf_card_verbatim(self):
        before = self.ws.card(make_card()).read_bytes()
        self.ws.package()
        code, proto = self.rotate()
        self.assertEqual((code, proto["result"]), (0, "ROTATED"), proto)
        self.check_rotated(before)
        self.assertTrue(proto["copied_exact"] and proto["outside_slots_unchanged"])
        self.assertEqual(proto["old_card_sha256"], hashlib.sha256(before).hexdigest())
        self.assertEqual(proto["new_card_sha256"], hashlib.sha256(self.ws.card_path.read_bytes()).hexdigest())
        self.assertEqual(proto["previous_slot"], {"state": "PLACEHOLDER", "archived": "NOT_NEEDED"})
        snap = (self.ws.root / "reports" / TASK / "handoff_task.md").read_bytes()
        self.assertEqual(tsr.snapshot_parts(snap), (lines_between(before, tsr.B1_BEGIN, tsr.B1_END), []))
        self.assertNotIn(b"\r\n", snap)
        code, check = run("check", "--card", self.ws.card_path)
        self.assertEqual((code, check["block1"]["state"], check["block1_1"]["state"]), (0, "WAITING", "FILLED"), check)

    def test_r02_crlf_card_stays_crlf(self):
        before = self.ws.card(make_card(eol="\r\n")).read_bytes()
        self.ws.package()
        code, proto = self.rotate()
        self.assertEqual(code, 0, proto)
        after = self.check_rotated(before, eol=b"\r\n")
        self.assertEqual(after.count(b"\n"), after.count(b"\r\n"), "no bare LF may appear in a CRLF card")
        lf_sha = hashlib.sha256(lines_between(make_card(), tsr.B1_BEGIN, tsr.B1_END)).hexdigest()
        self.assertEqual(proto["copy_sha256_lf"], lf_sha, "the copy hash does not depend on line endings")

    def test_r03_bom_and_unicode_separators_kept(self):
        before = self.ws.card(make_card(bom=True)).read_bytes()
        self.ws.package()
        code, proto = self.rotate()
        self.assertEqual(code, 0, proto)
        body = lines_between(before, tsr.B1_BEGIN, tsr.B1_END)
        self.assertEqual(proto["copy_lines"], body.count(b"\n"), "only LF ends a line (not LS/PS/NEL or a lone CR)")
        after = self.check_rotated(before)
        self.assertTrue(after.startswith(b"\xef\xbb\xbf"))
        slot = lines_between(after, tsr.B11_BEGIN, tsr.B11_END).decode("utf-8")
        for char in (" ", " ", "\u0085", "\r", "пробелами   \n", "\n    \n"):
            self.assertIn(char, slot)

    def test_r04_dry_run_writes_nothing(self):
        path = self.ws.card(make_card())
        package = self.ws.package()
        stat, before = path.stat(), path.read_bytes()
        code, proto = self.rotate(apply=False)
        self.assertEqual((code, proto["result"], proto["mode"]), (0, "DRY RUN OK", "dry-run"), proto)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(path.stat().st_mtime_ns, stat.st_mtime_ns)
        self.assertFalse((package / "handoff_task.md").exists())
        self.assertEqual(sorted(p.name for p in path.parent.iterdir()), [path.name])

    def test_r05_two_rotations_need_the_archive(self):
        self.ws.card(make_card())
        self.ws.package()
        self.assertEqual(self.rotate()[0], 0)
        first = self.ws.card_path.read_bytes()
        old_copy = lines_between(first, tsr.B11_BEGIN, tsr.B11_END).split(b"\n", 2)[2]
        # The user pastes the next task in place of the waiting line.
        self.ws.card(first.replace(WAITING_LITERAL.encode() + b"\n", task_text(TASK2, "вторая").encode()))
        self.ws.package(TASK2)
        proto = self.assert_refused("PREVIOUS_SLOT_NOT_ARCHIVED", task=TASK2)
        self.assertEqual(proto["previous_slot"]["task_id"], TASK)
        # Archived with one changed character: still refused.
        self.ws.archive(b"# Archive\n\n" + old_copy.replace("Пункт".encode(), "Пукнт".encode()))
        self.assert_refused("PREVIOUS_SLOT_NOT_ARCHIVED", task=TASK2)
        # Exact copy in №001 (the coordinator archived it, CRLF there): rotation goes on.
        self.ws.archive((b"# Archive\n\n## " + TASK.encode() + b"\n\n" + old_copy).replace(b"\n", b"\r\n"))
        before = self.ws.card_path.read_bytes()
        code, proto = self.rotate(task=TASK2)
        self.assertEqual(code, 0, proto)
        self.assertEqual(proto["previous_slot"]["archived"], "IN_001")
        self.assertTrue(proto["previous_slot"]["locator"].endswith(":5"), proto)
        slot = lines_between(self.ws.card_path.read_bytes(), tsr.B11_BEGIN, tsr.B11_END)
        self.assertIn(TASK2.encode(), slot.split(b"\n", 1)[0])
        self.assertEqual(slot.split(b"\n", 2)[2], lines_between(before, tsr.B1_BEGIN, tsr.B1_END))

    def test_r06_previous_archive_snapshot_needs_reference(self):
        self.ws.card(make_card())
        self.ws.package()
        self.rotate()
        first = self.ws.card_path.read_bytes()
        self.ws.card(first.replace(WAITING_LITERAL.encode() + b"\n", task_text(TASK2, "вторая").encode()))
        self.ws.package(TASK2)
        snapshot = self.ws.root / "reports" / TASK / "handoff_task.md"
        self.assert_refused("PREVIOUS_ARCHIVE_REF_MISSING", "--previous-archive", snapshot, task=TASK2)
        code, proto = self.rotate("--previous-archive", snapshot, "--previous-archive-ref", "main@abc #1", task=TASK2)
        self.assertEqual(code, 0, proto)
        self.assertEqual((proto["previous_slot"]["archived"], proto["previous_slot"]["reference"]),
                         ("IN_SNAPSHOT", "main@abc #1"))

    def test_r07_chat_amendment_kept_in_snapshot(self):
        self.ws.card(make_card())
        package = self.ws.package()
        note = Path(self._tmp.name) / "amend.txt"
        note.write_bytes("Поправка из чата:\r\n  точный текст без правки".encode("utf-8"))
        code, proto = self.rotate(amend=("--chat-amendment", note))
        self.assertEqual((code, proto["chat_amendments"]), (0, 1), proto)
        parts = tsr.snapshot_parts((package / "handoff_task.md").read_bytes())
        self.assertEqual(parts[1], ["Поправка из чата:\n  точный текст без правки\n".encode("utf-8")])
        meta = lines_between(self.ws.card_path.read_bytes(), tsr.B11_BEGIN, tsr.B11_END).split(b"\n", 1)[0]
        self.assertIn("CHAT-ONLY AMENDMENT: 1 в снимке".encode(), meta)

    def test_r08_existing_identical_snapshot_is_reused(self):
        self.ws.card(make_card())
        package = self.ws.package()
        self.assertEqual(self.rotate(apply=True, hook=lambda p: (_ for _ in ()).throw(tsr.Refused([]))
                                     )[0], 3)  # snapshot written, card left alone
        self.assertTrue((package / "handoff_task.md").exists())
        code, proto = self.rotate()
        self.assertEqual((code, proto["snapshot_state"]), (0, "EXISTS_IDENTICAL"), proto)


class Refusals(Base):
    def setUp(self):
        super().setUp()
        self.ws.package()

    def test_n01_marker_missing(self):
        self.ws.card(make_card().replace((tsr.B1_END + "\n").encode(), b""))
        self.assert_refused("MARKER_MISSING")

    def test_n02_whole_card_pasted_into_block1(self):
        whole = make_card().decode("utf-8")
        self.ws.card(make_card(b1=whole))
        proto = self.assert_refused("MARKER_DUPLICATED")
        self.assertIn("HEADING_COUNT", codes(proto))

    def test_n03_damaged_marker(self):
        self.ws.card(make_card().replace(tsr.B1_BEGIN.encode(), tsr.B1_BEGIN.removeprefix("###### ").encode()))
        proto = self.assert_refused("MARKER_DAMAGED")
        self.assertIn("MARKER_MISSING", codes(proto))

    def test_n04_markers_swapped(self):
        data = make_card().replace(tsr.B1_BEGIN.encode(), b"@@").replace(tsr.B1_END.encode(), tsr.B1_BEGIN.encode())
        self.ws.card(data.replace(b"@@", tsr.B1_END.encode()))
        self.assert_refused("ORDER")

    def test_n05_task_pasted_above_the_marker(self):
        data = make_card()
        self.ws.card(data.replace((tsr.B1_BEGIN + "\n").encode(), ("Новая задача\n" + tsr.B1_BEGIN + "\n").encode()))
        self.assert_refused("TEXT_OUTSIDE_MARKERS")

    def test_n06_new_task_already_in_block1(self):
        self.ws.card(make_card(b1=task_text(TASK2)))
        proto = self.assert_refused("TASK_ID_MISMATCH")
        self.assertIn(TASK2, json.dumps(proto["problems"]))

    def test_n07_no_task_id(self):
        self.ws.card(make_card(b1="# Задача без идентификатора\n\nТекст.\n"))
        self.assert_refused("NO_TASK_ID")

    def test_n08_two_tasks_mixed(self):
        self.ws.card(make_card(b1=task_text() + task_text(TASK2)))
        self.assert_refused("MULTIPLE_TASK_IDS")

    def test_n09_same_task_pasted_twice(self):
        self.ws.card(make_card(b1=task_text() + "\n" + task_text()))
        self.assert_refused("DUPLICATE_PASTE")

    def test_n10_amendment_for_another_task(self):
        self.ws.card(make_card(b1=task_text(extra=f"\n**AMENDMENT к** `{TASK2}`**:** чужая поправка.\n")))
        self.assert_refused("AMENDMENT_FOR_OTHER_TASK")

    def test_n11_waiting_line_left_in_task(self):
        self.ws.card(make_card(b1=WAITING_LITERAL + "\n" + task_text()))
        self.assert_refused("WAITING_LINE_LEFT_IN_TASK")

    def test_n12_card_structure_in_task(self):
        self.ws.card(make_card(b1=task_text(extra="\n# БЛОК 3 — КРАТКИЕ ФАКТИЧЕСКИЕ ИТОГИ\n")))
        self.assert_refused("CARD_STRUCTURE_IN_TASK")

    def test_n13_block1_waiting_or_empty(self):
        self.ws.card(make_card(b1=WAITING_LITERAL + "\n"))
        self.assert_refused("NOTHING_TO_ROTATE")
        self.ws.card(make_card(b1="\n"))
        self.assert_refused("NOTHING_TO_ROTATE")

    def test_n14_block11_copy_edited(self):
        self.ws.card(make_card())
        self.rotate()
        data = self.ws.card_path.read_bytes()
        slot_start = data.index(tsr.B11_BEGIN.encode())
        edited = data[:slot_start] + data[slot_start:].replace("Пункт".encode(), "Пунктик".encode(), 1)
        self.ws.card(edited.replace(WAITING_LITERAL.encode() + b"\n", task_text(TASK2).encode()))
        self.ws.package(TASK2)
        self.assert_refused("SLOT_1_1_COPY_CHANGED", task=TASK2)
        self.assertEqual(run("check", "--card", self.ws.card_path)[0], 3)

    def test_n15_same_task_rotated_twice(self):
        self.ws.card(make_card())
        self.rotate()
        data = self.ws.card_path.read_bytes()
        self.ws.card(data.replace(WAITING_LITERAL.encode() + b"\n", task_text().encode()))
        self.assert_refused("ALREADY_ROTATED")

    def test_n16_report_package_not_final(self):
        self.ws.card(make_card())
        package = self.ws.root / "reports" / TASK
        (package / "manifest.json").unlink()
        self.assert_refused("MANIFEST_MISSING")
        self.ws.package(head="# 🔴 ТЕСТЫ НЕ ЗАВЕРШЕНЫ — ЗАДАЧА В РАБОТЕ — ОТЧЁТ ПРЕДВАРИТЕЛЬНЫЙ\n\nDRAFT\n")
        self.assert_refused("REPORT_NOT_FINAL")
        self.ws.package(status="TESTS RUNNING / NOT FINAL")
        self.assert_refused("MANIFEST_NOT_FINAL")
        (package / "report.md").unlink()
        self.assert_refused("REPORT_MISSING")

    def test_n17_chat_amendment_must_be_declared(self):
        self.ws.card(make_card())
        self.assert_refused("CHAT_AMENDMENT_UNDECLARED", amend=())
        note = Path(self._tmp.name) / "a.txt"
        note.write_text("x", encoding="utf-8")
        self.assert_refused("CHAT_AMENDMENT_CONFLICT", amend=("--no-chat-amendment", "--chat-amendment", note))
        note.write_text("  \n", encoding="utf-8")
        self.assert_refused("CHAT_AMENDMENT_EMPTY", amend=("--chat-amendment", note))

    def test_n18_snapshot_conflict(self):
        self.ws.card(make_card())
        snap = self.ws.root / "reports" / TASK / "handoff_task.md"
        snap.write_bytes(tsr.snapshot_bytes(TASK, "c", DATE, b"another text\n", [], "r"))
        self.assert_refused("SNAPSHOT_CONFLICT")
        self.assertEqual(tsr.snapshot_parts(snap.read_bytes())[0], b"another text\n")

    def test_n19_concurrent_edit_is_not_overwritten(self):
        self.ws.card(make_card())
        edited = make_card(b1=task_text(title="правка пользователя"))
        code, proto = self.rotate(hook=lambda path: path.write_bytes(edited))
        self.assertEqual((code, codes(proto)), (3, {"CARD_CHANGED"}), proto)
        self.assertEqual(self.ws.card_path.read_bytes(), edited)

    def test_n20_lock_held(self):
        path = self.ws.card(make_card())
        lock = Path(tempfile.gettempdir()) / (
            "task_slot_rotate-" + hashlib.sha256(str(path.resolve()).lower().encode()).hexdigest()[:16] + ".lock")
        lock.write_text("1")
        try:
            before = path.read_bytes()
            code, proto = self.rotate()
            self.assertEqual((code, codes(proto)), (3, {"LOCKED"}), proto)
            self.assertEqual(path.read_bytes(), before)
        finally:
            lock.unlink()

    def test_n21_mixed_line_endings(self):
        data = make_card()
        self.ws.card(data.replace(b"\n", b"\r\n", 3))
        self.assert_refused("MIXED_EOL")

    def test_n22_task_id_cannot_be_a_path(self):
        self.ws.card(make_card())
        for bad in ("../" + TASK, "claude-lower-001", "NODASH", TASK + "/x", "A-" + "B" * 130):
            self.assert_refused("TASK_ID_FORMAT", task=bad)

    def test_n23_heading_missing_and_bad_utf8(self):
        self.ws.card(make_card().replace(H11_LITERAL.encode(), b"# BLOCK 1.1"))
        self.assert_refused("HEADING_COUNT")
        self.ws.card(make_card() + b"\xff\xfe")
        self.assert_refused("INVALID_UTF8")

    def test_n24_block11_unknown_text(self):
        self.ws.card(make_card(b11="Ручная запись координатора без статуса.\n"))
        self.assert_refused("SLOT_1_1_DAMAGED")

    def test_n25_failed_write_leaves_card_and_no_temp_file(self):
        path = self.ws.card(make_card())
        before = path.read_bytes()
        real_replace = os.replace

        def replace(src, dst):
            if Path(dst).name == path.name:
                raise PermissionError("busy")
            return real_replace(src, dst)
        with unittest.mock.patch.object(tsr.os, "replace", side_effect=replace):
            code, proto = self.rotate()
        self.assertEqual((code, codes(proto)), (3, {"WRITE_FAILED"}), proto)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(sorted(p.name for p in path.parent.iterdir()), [path.name])

    def test_n27_wrong_text_inside_task(self):
        cases = {
            "SLOT_COPY_IN_TASK": tsr.META.format(task=TASK, date=DATE, sha="0" * 64, amend="нет", snap="s", report="r"),
            "PLACEHOLDER_IN_TASK": tsr.PLACEHOLDERS[0],
            "SNAPSHOT_MARKER_IN_TASK": tsr.SNAP_END,
        }
        for code, line in cases.items():
            with self.subTest(code=code):
                self.ws.card(make_card(b1=task_text(extra="\n" + line + "\n")))
                self.assert_refused(code)

    def test_n28_bad_arguments_and_files(self):
        self.ws.card(make_card())
        self.assert_refused("DATE_FORMAT", "--date", "29.10.2026")
        self.assert_refused("CHAT_AMENDMENT_UNREADABLE", amend=("--chat-amendment", Path(self._tmp.name) / "absent.txt"))
        (self.ws.root / "reports" / TASK / "manifest.json").write_text("{broken", encoding="utf-8")
        self.assert_refused("MANIFEST_UNREADABLE")
        code, proto = run("check", "--card", self.ws.root / "Документация" / "absent.md")
        self.assertEqual((code, codes(proto)), (3, {"FILE_NOT_FOUND"}), proto)

    def test_n29_block11_holds_another_task_than_its_status_line(self):
        copy = task_text(TASK2)
        meta = tsr.META.format(task=TASK2.replace("002", "003"), date=DATE, amend="нет", snap="s", report="r",
                               sha=hashlib.sha256(copy.encode("utf-8")).hexdigest())
        self.ws.card(make_card(b11=meta + "\n\n" + copy))
        self.assert_refused("SLOT_1_1_TASK_ID_MISMATCH")
        self.assertEqual(run("check", "--card", self.ws.card_path)[0], 3)

    def test_n30_readback_failures_keep_the_card(self):
        path = self.ws.card(make_card())
        before = path.read_bytes()
        real = tsr.atomic_write

        def broken_card(target, data):
            real(target, data + b"x" if target.name == path.name and data != before else data)
        with unittest.mock.patch.object(tsr, "atomic_write", side_effect=broken_card):
            code, proto = self.rotate()
        self.assertEqual((code, codes(proto)), (3, {"READBACK_MISMATCH_ROLLED_BACK"}), proto)
        self.assertEqual(path.read_bytes(), before, "the card is rolled back")
        (self.ws.root / "reports" / TASK / "handoff_task.md").unlink()

        def broken_snapshot(target, data):
            real(target, b"garbage\n" if target.name == "handoff_task.md" else data)
        with unittest.mock.patch.object(tsr, "atomic_write", side_effect=broken_snapshot):
            code, proto = self.rotate()
        self.assertEqual((code, codes(proto)), (3, {"SNAPSHOT_READBACK"}), proto)
        self.assertEqual(path.read_bytes(), before, "the card is not written after a bad snapshot")

    def test_n26_waiting_line_with_trailing_spaces_is_waiting(self):
        self.ws.card(make_card(b1=WAITING_LITERAL + "  \n\n"))
        proto = self.assert_refused("NOTHING_TO_ROTATE")
        self.assertEqual(codes(proto), {"NOTHING_TO_ROTATE"})
        self.assertEqual(run("check", "--card", self.ws.card_path)[1]["block1"]["state"], "WAITING")


class Markers(Base):
    def test_m01_install_only_adds_four_lines(self):
        for eol in ("\n", "\r\n"):
            legacy = make_card(markers=False, eol=eol)
            path = self.ws.card(legacy)
            code, proto = run("install-markers", "--card", path)
            self.assertEqual((code, proto["result"]), (0, "DRY RUN OK"), proto)
            self.assertEqual(path.read_bytes(), legacy)
            code, proto = run("install-markers", "--card", path, "--apply")
            self.assertEqual((code, proto["result"]), (0, "MARKERS INSTALLED"), proto)
            new = path.read_bytes()
            self.assertEqual(new, make_card(eol=eol), "markers go around the slot text, not around the separators")
            stripped = b"".join(x for x in tsr.split_lines(new) if tsr.line_text(x) not in tsr.MARKERS)
            self.assertEqual(stripped, legacy)
            self.assertEqual((proto["block1"]["state"], proto["block1_1"]["state"]), ("TASK", "PLACEHOLDER"))
            code, proto = run("install-markers", "--card", path)
            self.assertEqual((code, codes(proto)), (3, {"MARKER_ALREADY_PRESENT"}))

    def test_m02_install_refuses_unknown_block11(self):
        path = self.ws.card(make_card(markers=False, b11="Чужой текст в слоте.\n"))
        before = path.read_bytes()
        code, proto = run("install-markers", "--card", path, "--apply")
        self.assertEqual((code, codes(proto)), (3, {"SLOT_1_1_DAMAGED"}), proto)
        self.assertEqual(path.read_bytes(), before)

    def test_m03_marker_text_is_valid_markdown_heading(self):
        for marker in tsr.MARKERS:
            self.assertTrue(marker.startswith("###### "))
            self.assertIn(tsr.TOKEN, marker)
            self.assertEqual(marker, marker.strip())
        self.assertEqual(len(set(tsr.MARKERS)), 4)


class Cli(Base):
    def test_c01_process_exit_codes_and_no_absolute_paths(self):
        path = self.ws.card(make_card())
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        ok = subprocess.run([sys.executable, "-B", str(SCRIPT), "check", "--card", str(path)],
                            capture_output=True, env=env)
        self.assertEqual(ok.returncode, 0, ok.stderr)
        proto = json.loads(ok.stdout.decode("utf-8"))
        self.assertEqual(proto["card"], "Документация/000_Задачи Test.md")
        self.assertNotIn(Path(self._tmp.name).name.encode(), ok.stdout)
        self.assertNotRegex(ok.stdout.decode("utf-8"), r"[A-Za-z]:\\\\")
        refused = subprocess.run([sys.executable, "-B", str(SCRIPT), "rotate", "--card", str(path), "--task-id", TASK2,
                                  "--no-chat-amendment", "--apply"], capture_output=True, env=env)
        self.assertEqual(refused.returncode, 3)
        self.assertEqual(json.loads(refused.stdout.decode("utf-8"))["result"], "NO ROTATE")
        usage = subprocess.run([sys.executable, "-B", str(SCRIPT), "rotate", "--card", str(path)],
                               capture_output=True, env=env)
        self.assertEqual(usage.returncode, 2)
        self.assertEqual(path.read_bytes(), make_card())


class RealCards(unittest.TestCase):
    """The live cards keep a valid structure (read only)."""

    def test_real_cards_are_valid(self):
        for name in ("000_Задачи Claude.md", "000_Задачи Codex.md"):
            path = REPO / "Документация" / name
            if not path.is_file():
                self.skipTest(f"{name} is absent")
            code, proto = run("check", "--card", path)
            self.assertEqual(code, 0, proto)


if __name__ == "__main__":
    unittest.main()
