#!/usr/bin/env python3
"""Mechanical rotation BLOCK 1 -> BLOCK 1.1 of a personal task card (Claude 008, Codex 007).

Rule: Документация/18 -> DOC-BLOCK1-SLOT-01@1 (commit #460). The script moves bytes; it never writes, shortens or
rephrases task text. It produces only two fixed lines: the waiting line of BLOCK 1 and the status line of BLOCK 1.1.

Commands (a dry run unless --apply is given):
  check            --card CARD
  install-markers  --card CARD [--apply]
  rotate           --card CARD --task-id ID (--no-chat-amendment | --chat-amendment FILE [...])
                   [--report-dir DIR] [--archive-001 FILE] [--previous-archive FILE --previous-archive-ref TEXT]
                   [--date YYYY-MM-DD] [--repo DIR] [--apply]

Exit codes: 0 OK; 3 NO ROTATE / REFUSED / INVALID (nothing was changed); 2 usage error; 1 unexpected error.
Output: one JSON protocol on stdout. Paths in it are relative to the repository.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import hashlib
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

H1 = "# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА"
H11 = "# БЛОК 1.1 — ПОСЛЕДНЯЯ СДАННАЯ ЗАДАЧА"
H2_PREFIX = "# БЛОК 2 — "
TOKEN = "TASK-SLOT:BLOCK-"
B1_BEGIN = "###### ▼ НАЧАЛО ЗАДАЧИ — строку-маркер не удалять · TASK-SLOT:BLOCK-1:BEGIN"
B1_END = "###### ▲ КОНЕЦ ЗАДАЧИ — строку-маркер не удалять · TASK-SLOT:BLOCK-1:END"
B11_BEGIN = "###### ▼ НАЧАЛО КОПИИ СДАННОЙ ЗАДАЧИ — заполняет только скрипт · TASK-SLOT:BLOCK-1.1:BEGIN"
B11_END = "###### ▲ КОНЕЦ КОПИИ СДАННОЙ ЗАДАЧИ — заполняет только скрипт · TASK-SLOT:BLOCK-1.1:END"
MARKERS = (B1_BEGIN, B1_END, B11_BEGIN, B11_END)
SLOT_NAMES = ("b1b", "b1e", "b11b", "b11e")
WAITING = "**ОЖИДАНИЕ НОВОЙ ЗАДАЧИ.**"
PLACEHOLDERS = (
    "**НЕ ЗАПОЛНЕН — ПЕРВЫЙ ПЕРЕНОС ЕЩЁ НЕ ВЫПОЛНЕН.** После первого безопасного переноса здесь хранится ровно одна "
    "последняя дословная постановка из БЛОКА 1 с TASK ID и меткой `SUBMITTED / REVIEW PENDING`. Это не авторский отчёт "
    "и не решение о приёмке. Предыдущая запись заменяется только после подтверждённого постоянного архивирования.",
)
STATUS = "SUBMITTED / REVIEW PENDING"
META = ("**" + STATUS + "** · TASK ID `{task}` · перенесено {date} · SHA-256 копии `{sha}` · "
        "CHAT-ONLY AMENDMENT: {amend} · снимок `{snap}` · отчёт `{report}`")
ID = r"[A-Z0-9]+(?:-[A-Z0-9]+)+"
TASK_ID_RE = re.compile(ID)
META_RE = re.compile(r"\*\*SUBMITTED / REVIEW PENDING\*\* · TASK ID `(?P<task>" + ID + r")` · "
                     r"перенесено (?P<date>\d{4}-\d{2}-\d{2}) · SHA-256 копии `(?P<sha>[0-9a-f]{64})` · "
                     r"CHAT-ONLY AMENDMENT: (?P<amend>нет|\d+ в снимке) · снимок `(?P<snap>[^`]+)` · "
                     r"отчёт `(?P<report>[^`]+)`")
DECL_RE = re.compile(r"(?:\*\*)?TASK ID:?(?:\*\*)?:?[ \t]+`(?:\*\*)?(" + ID + r")(?:\*\*)?`")
AMEND_RE = re.compile(r"AMENDMENT(?:\*\*)?\s+(?:к|для|to|for)(?:\*\*)?\s*`(?:\*\*)?(" + ID + r")(?:\*\*)?`")
SNAP_BEGIN = "<!-- TASK-SNAPSHOT:BEGIN -->"
SNAP_END = "<!-- TASK-SNAPSHOT:END -->"
REPORT_NOT_FINAL = ("DRAFT", "ТЕСТЫ НЕ ЗАВЕРШЕНЫ", "TESTS RUNNING", "NOT FINAL")

_BEFORE_CARD_WRITE = None  # test hook: called right before the final re-read of the card


class Refused(Exception):
    def __init__(self, problems):
        super().__init__(problems)
        self.problems = problems


def problem(code, detail="", line=None):
    out = {"code": code}
    if detail:
        out["detail"] = detail
    if line is not None:
        out["line"] = line + 1
    return out


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_lf(data: bytes) -> str:
    return sha256(data.replace(b"\r\n", b"\n"))


def split_lines(data: bytes) -> list:
    """Lines with their own line ending. Only LF ends a line (U+2028, U+0085 and lone CR stay inside)."""
    parts = data.split(b"\n")
    lines = [part + b"\n" for part in parts[:-1]]
    if parts[-1]:
        lines.append(parts[-1])
    return lines


def line_text(line: bytes) -> str:
    if line.endswith(b"\n"):
        line = line[:-1]
    if line.endswith(b"\r"):
        line = line[:-1]
    return line.decode("utf-8")


@dataclass
class Card:
    data: bytes
    lines: list = field(default_factory=list)
    texts: list = field(default_factory=list)
    eol: bytes = b"\n"
    idx: dict = field(default_factory=dict)
    problems: list = field(default_factory=list)

    def body(self, begin, end):
        return self.lines[self.idx[begin] + 1:self.idx[end]], self.texts[self.idx[begin] + 1:self.idx[end]], self.idx[begin] + 1


def parse(data: bytes, markers: bool = True) -> Card:
    card = Card(data)
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        card.problems.append(problem("INVALID_UTF8"))
        return card
    card.lines = split_lines(data)
    card.texts = [line_text(line) for line in card.lines]
    if card.texts:
        card.texts[0] = card.texts[0].removeprefix("﻿")
    crlf = sum(1 for line in card.lines if line.endswith(b"\r\n"))
    lf = sum(1 for line in card.lines if line.endswith(b"\n")) - crlf
    if crlf and lf:
        card.problems.append(problem("MIXED_EOL", f"CRLF {crlf}, LF {lf}"))
    card.eol = b"\r\n" if crlf else b"\n"
    heads = {"h1": [i for i, t in enumerate(card.texts) if t == H1],
             "h11": [i for i, t in enumerate(card.texts) if t == H11],
             "h2": [i for i, t in enumerate(card.texts) if t.startswith(H2_PREFIX)]}
    for name, found in heads.items():
        if len(found) == 1:
            card.idx[name] = found[0]
        else:
            card.problems.append(problem("HEADING_COUNT", f"{name}: {len(found)}"))
    if markers:
        for name, marker in zip(SLOT_NAMES, MARKERS):
            found = [i for i, t in enumerate(card.texts) if t == marker]
            if not found:
                card.problems.append(problem("MARKER_MISSING", name))
            elif len(found) > 1:
                card.problems.append(problem("MARKER_DUPLICATED", name, found[1]))
            else:
                card.idx[name] = found[0]
        for i, t in enumerate(card.texts):
            if TOKEN in t and t not in MARKERS:
                card.problems.append(problem("MARKER_DAMAGED", "", i))
        order = ("h1", "b1b", "b1e", "h11", "b11b", "b11e", "h2")
    else:
        for i, t in enumerate(card.texts):
            if TOKEN in t:
                card.problems.append(problem("MARKER_ALREADY_PRESENT", "", i))
        order = ("h1", "h11", "h2")
    if card.problems:
        return card
    positions = [card.idx[name] for name in order]
    if positions != sorted(positions):
        card.problems.append(problem("ORDER", " < ".join(order)))
        return card
    if markers:
        for begin, end in (("h1", "b1b"), ("b1e", "h11"), ("h11", "b11b"), ("b11e", "h2")):
            for i in range(card.idx[begin] + 1, card.idx[end]):
                if card.texts[i].strip() not in ("", "---"):
                    card.problems.append(problem("TEXT_OUTSIDE_MARKERS", "", i))
    return card


def declarations(texts):
    found = []
    for i, text in enumerate(texts):
        stripped = text.lstrip()
        for prefix in ("- ", "> "):
            stripped = stripped.removeprefix(prefix)
        match = DECL_RE.match(stripped)
        if match:
            found.append((i, match.group(1)))
    return found


def classify_block1(texts, base):
    nonblank = [t for t in texts if t.strip()]
    if not nonblank:
        return {"state": "EMPTY", "problems": []}
    if [t.strip() for t in nonblank] == [WAITING]:
        return {"state": "WAITING", "problems": []}
    problems = []
    decls = declarations(texts)
    ids = sorted({task for _, task in decls})
    task_id = ids[0] if len(ids) == 1 else None
    if not decls:
        problems.append(problem("NO_TASK_ID"))
    elif len(ids) > 1:
        problems.append(problem("MULTIPLE_TASK_IDS", ", ".join(ids)))
    elif len(decls) > 1 and sum(1 for t in texts if t == nonblank[0]) > 1:
        problems.append(problem("DUPLICATE_PASTE", "the task title and TASK ID repeat", base + decls[1][0]))
    for i, text in enumerate(texts):
        if text.startswith("# БЛОК "):
            problems.append(problem("CARD_STRUCTURE_IN_TASK", "", base + i))
        if META_RE.fullmatch(text):
            problems.append(problem("SLOT_COPY_IN_TASK", "", base + i))
        if text.strip() == WAITING:
            problems.append(problem("WAITING_LINE_LEFT_IN_TASK", "", base + i))
        if text.strip() in PLACEHOLDERS:
            problems.append(problem("PLACEHOLDER_IN_TASK", "", base + i))
        if text in (SNAP_BEGIN, SNAP_END):
            problems.append(problem("SNAPSHOT_MARKER_IN_TASK", "", base + i))
        for match in AMEND_RE.finditer(text):
            if task_id and match.group(1) != task_id:
                problems.append(problem("AMENDMENT_FOR_OTHER_TASK", match.group(1), base + i))
    return {"state": "INVALID" if problems else "TASK", "task_id": task_id, "problems": problems}


def classify_block11(lines, texts, base):
    nonblank = [t for t in texts if t.strip()]
    if not nonblank:
        return {"state": "EMPTY", "problems": []}
    if len(nonblank) == 1 and nonblank[0] in PLACEHOLDERS:
        return {"state": "PLACEHOLDER", "problems": []}
    match = META_RE.fullmatch(texts[0])
    if not match or len(texts) < 3 or texts[1] != "":
        return {"state": "INVALID", "problems": [problem("SLOT_1_1_DAMAGED", "status line or layout", base)]}
    copy = b"".join(lines[2:])
    result = {"state": "FILLED", "task_id": match["task"], "copy": copy, "copy_sha256": sha_lf(copy),
              "meta": match.groupdict(), "problems": []}
    if result["copy_sha256"] != match["sha"]:
        result["problems"].append(problem("SLOT_1_1_COPY_CHANGED", "the copy does not match its SHA-256", base + 2))
    if {task for _, task in declarations(texts[2:])} != {match["task"]}:
        result["problems"].append(problem("SLOT_1_1_TASK_ID_MISMATCH", match["task"], base))
    if result["problems"]:
        result["state"] = "INVALID"
    return result


def public(slot):
    return {key: value for key, value in slot.items() if key not in ("copy", "meta")}


def repo_root(card_path: Path, repo) -> Path:
    if repo:
        return Path(repo).resolve()
    return card_path.parent.parent if card_path.parent.name == "Документация" else card_path.parent


def rel(path: Path, repo: Path) -> str:
    try:
        return path.resolve().relative_to(repo).as_posix()
    except ValueError:
        return path.name


def package_problems(folder: Path):
    found = []
    report, manifest = folder / "report.md", folder / "manifest.json"
    if not report.is_file():
        found.append(problem("REPORT_MISSING"))
    else:
        head = "\n".join(report.read_text(encoding="utf-8", errors="replace").splitlines()[:12]).upper()
        found += [problem("REPORT_NOT_FINAL", mark) for mark in REPORT_NOT_FINAL if mark in head]
    if not manifest.is_file():
        found.append(problem("MANIFEST_MISSING"))
    else:
        try:
            value = json.loads(manifest.read_text(encoding="utf-8"))
        except (ValueError, UnicodeDecodeError):
            found.append(problem("MANIFEST_UNREADABLE"))
        else:
            status = str(value.get("status", "")).upper() if isinstance(value, dict) else ""
            found += [problem("MANIFEST_NOT_FINAL", mark) for mark in ("DRAFT", "RUNNING", "NOT FINAL") if mark in status]
    return found


def find_001(card_path: Path):
    agent = card_path.stem.removeprefix("000_Задачи ").strip()
    found = sorted(p for p in card_path.parent.glob("001_История*.md") if p.stem.endswith(" " + agent))
    return found[0] if len(found) == 1 else None


def archived_at(copy: bytes, path: Path):
    if not path or not path.is_file():
        return None
    data = path.read_bytes().replace(b"\r\n", b"\n")
    at = data.find(copy.replace(b"\r\n", b"\n"))
    return None if at < 0 else data[:at].count(b"\n") + 1


def snapshot_parts(data: bytes):
    lines = split_lines(data.replace(b"\r\n", b"\n"))
    texts = [line.rstrip(b"\n").decode("utf-8", "replace") for line in lines]
    try:
        begin = texts.index(SNAP_BEGIN)
        end = texts.index(SNAP_END, begin + 1)
    except ValueError:
        return None
    amendments, number = [], 1
    while True:
        try:
            a_begin = texts.index(f"<!-- TASK-SNAPSHOT:AMENDMENT-{number}:BEGIN -->", end)
            a_end = texts.index(f"<!-- TASK-SNAPSHOT:AMENDMENT-{number}:END -->", a_begin + 1)
        except ValueError:
            break
        amendments.append(b"".join(lines[a_begin + 1:a_end]))
        number += 1
    return b"".join(lines[begin + 1:end]), amendments


def snapshot_bytes(task, card_rel, date, copy_lf, amendments, report_rel):
    amend = "нет (заявлено исполнителем)" if not amendments else f"{len(amendments)}, ниже"
    head = [f"# Снимок постановки `{task}` — перенос БЛОК 1 → БЛОК 1.1", "",
            "| Поле | Значение |", "|---|---|",
            f"| TASK ID | `{task}` |",
            f"| Карточка | `{card_rel}` |",
            f"| Дата переноса | {date} |",
            f"| Статус | `{STATUS}` — сдано исполнителем; независимая приёмка не выполнена |",
            f"| SHA-256 постановки (UTF-8, концы строк LF) | `{sha256(copy_lf)}` |",
            f"| Строк постановки | {len(split_lines(copy_lf))} |",
            f"| CHAT-ONLY AMENDMENT | {amend} |",
            f"| Отчёт | `{report_rel}` |",
            "| Инструмент | `tools/task_slot_rotate.py` — побайтовое копирование без пересказа |", "",
            "Текст между строками-маркерами ниже — побайтовая копия содержимого БЛОКА 1 (концы строк приведены к LF).", "",
            SNAP_BEGIN]
    out = ("\n".join(head) + "\n").encode("utf-8") + copy_lf + (SNAP_END + "\n").encode("utf-8")
    for number, text in enumerate(amendments, 1):
        out += (f"\n## CHAT-ONLY AMENDMENT {number} — SHA-256 `{sha256(text)}`\n\n"
                f"<!-- TASK-SNAPSHOT:AMENDMENT-{number}:BEGIN -->\n").encode("utf-8")
        out += text + f"<!-- TASK-SNAPSHOT:AMENDMENT-{number}:END -->\n".encode("utf-8")
    return out


def atomic_write(path: Path, data: bytes):
    tmp = path.with_name("." + path.name + ".rotate-tmp")
    try:
        with open(tmp, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except OSError as error:
        with contextlib.suppress(OSError):
            tmp.unlink()
        raise Refused([problem("WRITE_FAILED", f"{path.name}: {type(error).__name__}")])


@contextlib.contextmanager
def card_lock(path: Path):
    lock = Path(tempfile.gettempdir()) / ("task_slot_rotate-" + sha256(str(path).lower().encode("utf-8"))[:16] + ".lock")
    try:
        handle = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise Refused([problem("LOCKED", "another rotation holds the lock; remove a stale lock only if none runs")])
    try:
        os.write(handle, str(os.getpid()).encode("ascii"))
        os.close(handle)
        yield
    finally:
        with contextlib.suppress(OSError):
            lock.unlink()


def same_segments(old: Card, new: Card) -> bool:
    o, n = old.idx, new.idx
    return (old.lines[:o["b1b"] + 1] == new.lines[:n["b1b"] + 1]
            and old.lines[o["b1e"]:o["b11b"] + 1] == new.lines[n["b1e"]:n["b11b"] + 1]
            and old.lines[o["b11e"]:] == new.lines[n["b11e"]:])


def cmd_check(args, proto):
    card_path = Path(args.card).resolve()
    card = parse(card_path.read_bytes())
    proto.update({"card_sha256": sha256(card.data), "eol": "CRLF" if card.eol == b"\r\n" else "LF"})
    problems = list(card.problems)
    if not problems:
        proto["marker_lines"] = {name: card.idx[name] + 1 for name in SLOT_NAMES}
        lines1, texts1, base1 = card.body("b1b", "b1e")
        lines11, texts11, base11 = card.body("b11b", "b11e")
        block1, block11 = classify_block1(texts1, base1), classify_block11(lines11, texts11, base11)
        proto["block1"] = {**public(block1), "lines": len(texts1)}
        proto["block1_1"] = public(block11)
        problems += block1["problems"] + block11["problems"]
    proto["problems"] = problems
    proto["result"] = "INVALID" if problems else "OK"
    return proto, 3 if problems else 0


def cmd_install(args, proto):
    card_path = Path(args.card).resolve()
    data = card_path.read_bytes()
    proto.update({"mode": "apply" if args.apply else "dry-run", "old_card_sha256": sha256(data)})
    card = parse(data, markers=False)
    if card.problems:
        raise Refused(card.problems)
    spans = []
    for begin, end in (("h1", "h11"), ("h11", "h2")):
        inner = [i for i in range(card.idx[begin] + 1, card.idx[end]) if card.texts[i].strip() not in ("", "---")]
        spans.append((inner[0], inner[-1] + 1) if inner else (card.idx[begin] + 1, card.idx[begin] + 1))
    (s1, e1), (s11, e11) = spans
    eol, lines = card.eol, card.lines
    marker = [(m + "\n").encode("utf-8").replace(b"\n", eol) for m in MARKERS]
    new = b"".join(lines[:s1] + [marker[0]] + lines[s1:e1] + [marker[1]] + lines[e1:s11] + [marker[2]]
                   + lines[s11:e11] + [marker[3]] + lines[e11:])
    check = parse(new)
    restored = b"".join(line for line in split_lines(new) if line_text(line) not in MARKERS)
    problems = list(check.problems)
    if restored != data:
        problems.append(problem("INSTALL_CHANGED_TEXT"))
    if not problems:
        lines1, texts1, base1 = check.body("b1b", "b1e")
        lines11, texts11, base11 = check.body("b11b", "b11e")
        block1, block11 = classify_block1(texts1, base1), classify_block11(lines11, texts11, base11)
        if block11["state"] not in ("EMPTY", "PLACEHOLDER", "FILLED"):
            problems += block11["problems"] or [problem("SLOT_1_1_UNKNOWN_CONTENT")]
        proto.update({"block1": public(block1), "block1_1": public(block11),
                      "marker_lines_after_install": [check.idx[name] + 1 for name in SLOT_NAMES],
                      "left_outside": [{"line": i + 1, "text": check.texts[i]} for i in range(len(check.texts))
                                       if check.texts[i].strip() == "---" and
                                       (check.idx["h1"] < i < check.idx["b1b"] or check.idx["b1e"] < i < check.idx["h11"]
                                        or check.idx["h11"] < i < check.idx["b11b"] or check.idx["b11e"] < i < check.idx["h2"])]})
    if problems:
        raise Refused(problems)
    proto.update({"new_card_sha256": sha256(new), "only_marker_lines_added": True, "eol": "CRLF" if eol == b"\r\n" else "LF"})
    if not args.apply:
        proto["result"] = "DRY RUN OK"
        return proto, 0
    with card_lock(card_path):
        if card_path.read_bytes() != data:
            raise Refused([problem("CARD_CHANGED", "the card changed after it was read")])
        atomic_write(card_path, new)
        if card_path.read_bytes() != new:
            atomic_write(card_path, data)
            raise Refused([problem("READBACK_MISMATCH_ROLLED_BACK")])
    proto["result"] = "MARKERS INSTALLED"
    return proto, 0


def cmd_rotate(args, proto):
    card_path = Path(args.card).resolve()
    repo = repo_root(card_path, args.repo)
    task = args.task_id or ""
    proto.update({"mode": "apply" if args.apply else "dry-run", "task_id": task, "status": STATUS})
    if len(task) > 120 or not TASK_ID_RE.fullmatch(task):
        raise Refused([problem("TASK_ID_FORMAT", "expected letters A-Z, digits and dashes")])
    try:
        date = dt.date.fromisoformat(args.date).isoformat() if args.date else dt.date.today().isoformat()
    except ValueError:
        raise Refused([problem("DATE_FORMAT")])
    data = card_path.read_bytes()
    proto["old_card_sha256"] = sha256(data)
    card = parse(data)
    if card.problems:
        raise Refused(card.problems)
    problems = []
    lines1, texts1, base1 = card.body("b1b", "b1e")
    lines11, texts11, base11 = card.body("b11b", "b11e")
    block1, block11 = classify_block1(texts1, base1), classify_block11(lines11, texts11, base11)
    if block1["state"] in ("EMPTY", "WAITING"):
        problems.append(problem("NOTHING_TO_ROTATE", f"BLOCK 1 is {block1['state']}"))
    problems += block1["problems"]
    if block1.get("task_id") and block1["task_id"] != task:
        problems.append(problem("TASK_ID_MISMATCH", f"BLOCK 1 holds {block1['task_id']}"))
    if args.no_chat_amendment and args.chat_amendment:
        problems.append(problem("CHAT_AMENDMENT_CONFLICT"))
    elif not args.no_chat_amendment and not args.chat_amendment:
        problems.append(problem("CHAT_AMENDMENT_UNDECLARED", "pass --no-chat-amendment or --chat-amendment FILE"))
    amendments = []
    for name in args.chat_amendment or []:
        try:
            text = Path(name).read_bytes().replace(b"\r\n", b"\n")
            text.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            problems.append(problem("CHAT_AMENDMENT_UNREADABLE", Path(name).name))
            continue
        if not text.strip():
            problems.append(problem("CHAT_AMENDMENT_EMPTY", Path(name).name))
            continue
        amendments.append(text if text.endswith(b"\n") else text + b"\n")
    previous = {"state": block11["state"]}
    if block11["state"] == "INVALID":
        problems += block11["problems"]
    elif block11["state"] == "FILLED":
        previous.update(task_id=block11["task_id"], copy_sha256=block11["copy_sha256"])
        if block11["task_id"] == task:
            problems.append(problem("ALREADY_ROTATED", "BLOCK 1.1 already holds this TASK"))
        else:
            archive = Path(args.archive_001).resolve() if args.archive_001 else find_001(card_path)
            line = archived_at(block11["copy"], archive)
            if line:
                previous.update(archived="IN_001", locator=f"{rel(archive, repo)}:{line}",
                                archive_sha256=sha256(archive.read_bytes()))
            elif args.previous_archive:
                snap = Path(args.previous_archive).resolve()
                line = archived_at(block11["copy"], snap)
                if not args.previous_archive_ref:
                    problems.append(problem("PREVIOUS_ARCHIVE_REF_MISSING", "name the published commit/locator"))
                elif line:
                    previous.update(archived="IN_SNAPSHOT", locator=f"{rel(snap, repo)}:{line}",
                                    archive_sha256=sha256(snap.read_bytes()), reference=args.previous_archive_ref)
                else:
                    problems.append(problem("PREVIOUS_SLOT_NOT_ARCHIVED", block11["task_id"]))
            else:
                problems.append(problem("PREVIOUS_SLOT_NOT_ARCHIVED", block11["task_id"]))
    else:
        previous["archived"] = "NOT_NEEDED"
    proto["previous_slot"] = previous
    report_dir = Path(args.report_dir).resolve() if args.report_dir else repo / "reports" / task
    problems += package_problems(report_dir)
    copy = b"".join(lines1)
    copy_lf = copy.replace(b"\r\n", b"\n")
    snap_path = report_dir / "handoff_task.md"
    reuse = False
    if snap_path.exists():
        parts = snapshot_parts(snap_path.read_bytes())
        if parts == (copy_lf, amendments):
            reuse = True
        else:
            problems.append(problem("SNAPSHOT_CONFLICT", "handoff_task.md exists with another text"))
    if problems:
        raise Refused(problems)
    snap_rel, report_rel = rel(snap_path, repo), rel(report_dir / "report.md", repo)
    amend = "нет" if not amendments else f"{len(amendments)} в снимке"
    meta = META.format(task=task, date=date, sha=sha256(copy_lf), amend=amend, snap=snap_rel, report=report_rel)
    eol, idx = card.eol, card.idx
    new = b"".join(card.lines[:idx["b1b"] + 1] + [WAITING.encode("utf-8") + eol] + card.lines[idx["b1e"]:idx["b11b"] + 1]
                   + [meta.encode("utf-8") + eol, eol] + lines1 + card.lines[idx["b11e"]:])
    after = parse(new)
    if after.problems:
        raise Refused([problem("PLAN_INVALID", json.dumps(after.problems, ensure_ascii=False))])
    after1 = classify_block1(after.body("b1b", "b1e")[1], 0)
    after11 = classify_block11(*after.body("b11b", "b11e"))
    copied_exact = after11["state"] == "FILLED" and after11["copy"] == copy and after11["task_id"] == task
    if after1["state"] != "WAITING" or not copied_exact or not same_segments(card, after):
        raise Refused([problem("PLAN_INVALID", "the planned card fails its own readback")])
    snapshot = snapshot_bytes(task, rel(card_path, repo), date, copy_lf, amendments, report_rel)
    proto.update({"new_card_sha256": sha256(new), "copy_sha256_lf": sha256(copy_lf), "copy_lines": len(lines1),
                  "copied_exact": True, "outside_slots_unchanged": True, "block1_after": "WAITING",
                  "eol": "CRLF" if eol == b"\r\n" else "LF", "snapshot": snap_rel,
                  "snapshot_state": "EXISTS_IDENTICAL" if reuse else "NEW", "chat_amendments": len(amendments)})
    if not args.apply:
        proto["result"] = "DRY RUN OK"
        return proto, 0
    with card_lock(card_path):
        if card_path.read_bytes() != data:
            raise Refused([problem("CARD_CHANGED", "the card changed after it was read")])
        if not reuse:
            atomic_write(snap_path, snapshot)
            if snapshot_parts(snap_path.read_bytes()) != (copy_lf, amendments):
                raise Refused([problem("SNAPSHOT_READBACK", "the card was not changed")])
        if _BEFORE_CARD_WRITE:
            _BEFORE_CARD_WRITE(card_path)
        if card_path.read_bytes() != data:
            raise Refused([problem("CARD_CHANGED", "the card changed after it was read")])
        atomic_write(card_path, new)
        if card_path.read_bytes() != new:
            atomic_write(card_path, data)
            raise Refused([problem("READBACK_MISMATCH_ROLLED_BACK")])
    proto["snapshot_sha256"] = sha256(snap_path.read_bytes())
    proto["result"] = "ROTATED"
    return proto, 0


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="validate markers, TASK IDs and the BLOCK 1.1 copy")
    install = sub.add_parser("install-markers", help="one-time insertion of the four slot markers")
    rotate = sub.add_parser("rotate", help="move BLOCK 1 to BLOCK 1.1 and set BLOCK 1 to waiting")
    for item in (check, install, rotate):
        item.add_argument("--card", required=True)
        item.add_argument("--repo", help="repository root (default: the folder above Документация)")
    for item in (install, rotate):
        item.add_argument("--apply", action="store_true", help="write the change (default: dry run)")
    rotate.add_argument("--task-id", required=True, help="the TASK ID that the executor hands in")
    rotate.add_argument("--no-chat-amendment", action="store_true", help="the TASK had no chat-only AMENDMENT")
    rotate.add_argument("--chat-amendment", action="append", metavar="FILE", help="exact text of a chat-only AMENDMENT")
    rotate.add_argument("--report-dir", help="final package folder (default: reports/<TASK-ID>)")
    rotate.add_argument("--archive-001", help="personal archive №001 (default: found next to the card)")
    rotate.add_argument("--previous-archive", help="published snapshot holding the previous BLOCK 1.1 copy")
    rotate.add_argument("--previous-archive-ref", help="commit/locator of that published snapshot")
    rotate.add_argument("--date", help="transfer date YYYY-MM-DD (default: today)")
    return parser


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    handler = {"check": cmd_check, "install-markers": cmd_install, "rotate": cmd_rotate}[args.command]
    card_path = Path(args.card).resolve()
    proto = {"command": args.command, "card": rel(card_path, repo_root(card_path, args.repo))}
    try:
        proto, code = handler(args, proto)
    except (Refused, FileNotFoundError) as error:
        problems = error.problems if isinstance(error, Refused) else [
            problem("FILE_NOT_FOUND", Path(error.filename or "").name)]
        proto.update({"result": "NO ROTATE" if args.command == "rotate" else "REFUSED", "problems": problems,
                      "card_unchanged": True})
        code = 3
    print(json.dumps(proto, ensure_ascii=False, indent=1))
    return code


if __name__ == "__main__":
    sys.exit(main())
