#!/usr/bin/env python3
"""Mechanical rotation BLOCK 1 -> BLOCK 1.1 of a personal task card (Claude 008, Codex 007).

Rule: Документация/18 -> DOC-BLOCK1-SLOT-01@2 (USER GO 2026-11-04). The script moves bytes; it never shortens or
rephrases task text. It produces only two fixed lines: the waiting line of BLOCK 1 and the status line of BLOCK 1.1.

Commands (a dry run unless --apply is given):
  finish           --card CARD --task-id ID --no-chat-amendment [--apply] [--monitor | --headless]
                   one process: check -> dry-run -> apply -> readback
  watch            --card CARD [--headless] (read-only; window refreshes local state, never uses Git)
  check            --card CARD
  assign           --card CARD --task-file FILE --expected-card-sha256 SHA [--apply]
                   user action: assign new Markdown only to a verified WAITING block
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
MIN_TASK_CHARS = 100


def task_chars(text):
    """Whitespace padding does not turn an accidental short note into a task."""
    return sum(not char.isspace() for char in text)
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
    if task_id and task_chars("\n".join(texts)) < MIN_TASK_CHARS:
        problems.append(problem("TASK_TOO_SHORT", f"fewer than {MIN_TASK_CHARS} non-whitespace characters"))
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
    if task_chars(copy.decode("utf-8")) < MIN_TASK_CHARS:
        result["problems"].append(problem("PREVIOUS_TASK_TOO_SHORT", f"fewer than {MIN_TASK_CHARS} non-whitespace characters"))
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


MAX_SNAPSHOT_BYTES = 4 * 1024 * 1024


def snapshot_path(repo, value):
    """Only one addressed handoff file under reports; no recursive discovery."""
    path = Path(os.path.abspath(repo / Path(value)))
    reports = repo / "reports"
    if not path.is_relative_to(reports) or path.name != "handoff_task.md":
        raise Refused([problem("UNSAFE_SNAPSHOT_PATH", "expected reports/.../handoff_task.md")])
    for node in (path, *path.parents):
        if node == repo:
            break
        if node.exists() or node.is_symlink():
            st = node.lstat()
            if node.is_symlink() or getattr(st, "st_file_attributes", 0) & 0x400:
                raise Refused([problem("UNSAFE_SNAPSHOT_PATH", "link/reparse point")])
    return path


def bounded_bytes(path):
    if not path.exists():
        return None
    if not path.is_file() or path.stat().st_size > MAX_SNAPSHOT_BYTES:
        raise Refused([problem("ARCHIVE_SIZE_OR_TYPE", path.name)])
    return path.read_bytes()


def preserve_previous(slot, args, repo, card_path):
    """Plan preservation. A local archive is not an assertion of publication."""
    previous = {"state": slot["state"]}
    if slot["state"] != "FILLED":
        previous["archived"] = "NOT_NEEDED"
        return previous, []
    previous.update(task_id=slot["task_id"], copy_sha256=slot["copy_sha256"],
                    publication="NOT VERIFIED")
    # The exact snapshot reference is already in the slot. Explicit paths are overrides.
    raw = args.previous_archive or slot["meta"]["snap"]
    path = snapshot_path(repo, raw)
    data = bounded_bytes(path)
    expected_amends = 0 if slot["meta"]["amend"] == "нет" else int(slot["meta"]["amend"].split()[0])
    copy = slot["copy"].replace(b"\r\n", b"\n")
    if data is not None:
        parts = snapshot_parts(data)
        if not parts or parts[0] != copy or len(parts[1]) != expected_amends:
            raise Refused([problem("PREVIOUS_SNAPSHOT_CONFLICT", rel(path, repo))])
        previous.update(archived="IN_SNAPSHOT", action="REUSED", locator=rel(path, repo),
                        archive_sha256=sha256(data))
        if args.previous_archive_ref:
            previous["reference"] = args.previous_archive_ref  # caller-supplied, not independently verified
        return previous, [(path, data, data)]
    # An explicit historical archive is an addressed fallback, never a whole-repo search.
    if args.archive_001 and not expected_amends:
        archive = Path(args.archive_001).resolve()
        historical = bounded_bytes(archive)
        if historical is not None and copy in historical.replace(b"\r\n", b"\n"):
            previous.update(archived="IN_001", action="REUSED", locator=rel(archive, repo),
                            archive_sha256=sha256(historical))
            return previous, [(archive, historical, historical)]
    if expected_amends:
        raise Refused([problem("PREVIOUS_AMENDMENTS_MISSING", "cannot reconstruct chat amendments from the card")])
    data = snapshot_bytes(slot["task_id"], rel(card_path, repo), slot["meta"]["date"],
                          copy, [], slot["meta"]["report"])
    previous.update(archived="IN_SNAPSHOT", action="WILL_CREATE", locator=rel(path, repo),
                    archive_sha256=sha256(data))
    return previous, [(path, None, data)]


def create_snapshot(path, data):
    """Publish a new immutable snapshot without replacing a concurrently created file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".slot-", suffix=".tmp", dir=path.parent, delete=False) as out:
            tmp = Path(out.name)
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        os.link(tmp, path)  # atomic no-replace publication; same volume, fails closed if unsupported
    except OSError as error:
        raise Refused([problem("ARCHIVE_CREATE_FAILED", f"{path.name}: {type(error).__name__}")])
    finally:
        if tmp is not None:
            with contextlib.suppress(OSError):
                tmp.unlink()


def progress(args, step, message, color="blue"):
    if getattr(args, "progress", False):
        print(json.dumps({"step": step, "message": message, "color": color}, ensure_ascii=False),
              file=sys.stderr, flush=True)


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
            if any(t.startswith(f"<!-- TASK-SNAPSHOT:AMENDMENT-{number}:") for t in texts[end + 1:]):
                return None
            break
        content = b"".join(lines[a_begin + 1:a_end])
        header = f"## CHAT-ONLY AMENDMENT {number} — SHA-256 `{sha256(content)}`"
        if header not in texts[end + 1:a_begin]:
            return None
        amendments.append(content)
        number += 1
    markers = [t for t in texts[end + 1:] if t.startswith("<!-- TASK-SNAPSHOT:AMENDMENT-")]
    if len(markers) != 2 * len(amendments):
        return None
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
        if block1.get("task_id"):
            title = next((t.removeprefix("**Название:**").strip() for t in texts1 if t.startswith("**Название:**")), "")
            if not title:
                title = next((t.lstrip("# ").strip() for t in texts1 if t.startswith("# ")), "")
            block1["title"] = title[:500]
        proto["block1"] = {**public(block1), "lines": len(texts1)}
        proto["block1_1"] = public(block11)
        problems += block1["problems"] + block11["problems"]
    proto["problems"] = problems
    proto["result"] = "INVALID" if problems else "OK"
    return proto, 3 if problems else 0


def new_task_bytes(raw, eol=b"\n"):
    """Validate user Markdown; only normalize CRLF, an initial BOM and final LF."""
    if len(raw) > MAX_SNAPSHOT_BYTES:
        raise Refused([problem("TASK_TOO_LARGE", "maximum 4 MiB")])
    try:
        text = raw.decode("utf-8-sig").replace("\r\n", "\n")
    except UnicodeDecodeError:
        raise Refused([problem("TASK_INVALID_UTF8")])
    if "\x00" in text:
        raise Refused([problem("TASK_INVALID_CHARACTER", "NUL")])
    slot = classify_block1(text.split("\n"), 0)
    if slot["state"] != "TASK":
        raise Refused(slot["problems"] or [problem("NEW_TASK_REQUIRED", "paste a complete task, not the waiting line")])
    if any(TOKEN in line for line in text.split("\n")):
        raise Refused([problem("CARD_STRUCTURE_IN_TASK", "paste only the task, without card markers")])
    if not text.endswith("\n"):
        text += "\n"
    return text.encode("utf-8").replace(b"\n", eol), slot["task_id"]


def cmd_assign(args, proto):
    """User-initiated assignment: replace WAITING only; never touch block 1.1."""
    path = Path(args.card).resolve()
    data = path.read_bytes()
    check, code = cmd_check(args, {"command": "check"})
    proto.update(mode="apply" if args.apply else "dry-run", steps=[check], old_card_sha256=sha256(data))
    if code:
        raise Refused(check["problems"])
    if check["card_sha256"] != sha256(data) or args.expected_card_sha256 != sha256(data):
        raise Refused([problem("CARD_CHANGED", "card changed since the new-task form was opened")])
    if check["block1"]["state"] != "WAITING":
        raise Refused([problem("BLOCK1_NOT_WAITING", "finish the current task before assigning another")])
    source = Path(args.task_file)
    if not source.is_file() or source.stat().st_size > MAX_SNAPSHOT_BYTES:
        raise Refused([problem("TASK_FILE_SIZE_OR_TYPE")])
    card = parse(data)
    payload, task = new_task_bytes(source.read_bytes(), card.eol)
    if check["block1_1"].get("task_id") == task:
        raise Refused([problem("TASK_ALREADY_SUBMITTED", "this TASK ID is already in block 1.1")])
    new = b"".join(card.lines[:card.idx["b1b"] + 1] + [payload] + card.lines[card.idx["b1e"]:])
    plan = parse(new)
    if plan.problems:
        raise Refused(plan.problems)
    after = classify_block1(plan.body("b1b", "b1e")[1], 0)
    unchanged = (card.lines[:card.idx["b1b"] + 1] == plan.lines[:plan.idx["b1b"] + 1]
                 and card.lines[card.idx["b1e"]:] == plan.lines[plan.idx["b1e"]:])
    if after["state"] != "TASK" or after["task_id"] != task or not unchanged:
        raise Refused([problem("PLAN_INVALID")])
    proto.update(task_id=task, new_card_sha256=sha256(new), task_sha256_lf=sha_lf(payload),
                 block1_1_and_history_unchanged=True, only_block1_changed=True)
    if not args.apply:
        proto.update(result="DRY RUN OK", card_unchanged=True)
        return proto, 0
    progress(args, "assign", "Записываем новую задачу в ожидающий БЛОК 1", "green")
    with card_lock(path):
        if path.read_bytes() != data:
            raise Refused([problem("CARD_CHANGED")])
        if _BEFORE_CARD_WRITE:
            _BEFORE_CARD_WRITE(path)
        if path.read_bytes() != data:
            raise Refused([problem("CARD_CHANGED")])
        atomic_write(path, new)
        if path.read_bytes() != new:
            atomic_write(path, data)
            raise Refused([problem("READBACK_MISMATCH_ROLLED_BACK")])
        readback, code = cmd_check(args, {"command": "readback"})
        if code or readback["card_sha256"] != sha256(new):
            raise Refused([problem("ASSIGN_READBACK_CONFLICT", "inspect the card; concurrent changes were not overwritten")])
    proto["steps"].append(readback)
    proto.update(result="ASSIGNED", card_unchanged=False)
    progress(args, "done", "Задача записана в БЛОК 1; история сохранена", "green")
    return proto, 0


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
    already = block1["state"] in ("EMPTY", "WAITING") and block11.get("task_id") == task
    duplicate = block1.get("task_id") == task and block11.get("task_id") == task
    if block1["state"] in ("EMPTY", "WAITING") and not already:
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
    if block11["state"] == "INVALID":
        problems += block11["problems"]
    if duplicate and b"".join(lines1).replace(b"\r\n", b"\n") != block11["copy"].replace(b"\r\n", b"\n"):
        problems.append(problem("SAME_TASK_DIFFERENT_TEXT", "both slots name the same TASK but the texts differ"))
    if problems:
        raise Refused(problems)
    previous, artifacts = preserve_previous(block11, args, repo, card_path)
    proto["previous_slot"] = previous
    progress(args, "archive", "БЛОК 1.1: " + (block11.get("task_id") or block11["state"]) +
             (" · точная копия уже есть: " if previous.get("action") == "REUSED" else
              " · сначала сохраняем копию: " if previous.get("action") == "WILL_CREATE" else " · архивирование не требуется") +
             previous.get("locator", ""))
    report_dir = Path(args.report_dir).resolve() if args.report_dir else repo / "reports" / task
    problems += package_problems(report_dir)
    copy = block11["copy"] if already else b"".join(lines1)
    copy_lf = copy.replace(b"\r\n", b"\n")
    snap_path = snapshot_path(repo, report_dir / "handoff_task.md")
    reuse = False
    initial_snapshot = bounded_bytes(snap_path)
    if initial_snapshot is not None:
        parts = snapshot_parts(initial_snapshot)
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
    new_slot = lines11 if duplicate or already else [meta.encode("utf-8") + eol, eol] + lines1
    new = b"".join(card.lines[:idx["b1b"] + 1] + [WAITING.encode("utf-8") + eol] + card.lines[idx["b1e"]:idx["b11b"] + 1]
                   + new_slot + card.lines[idx["b11e"]:])
    if already and block1["state"] == "WAITING":
        new = data  # even whitespace/mtime remain unchanged on a verified repeat
    after = parse(new)
    if after.problems:
        raise Refused([problem("PLAN_INVALID", json.dumps(after.problems, ensure_ascii=False))])
    after1 = classify_block1(after.body("b1b", "b1e")[1], 0)
    after11 = classify_block11(*after.body("b11b", "b11e"))
    copied_exact = after11["state"] == "FILLED" and after11["copy"] == copy and after11["task_id"] == task
    if after1["state"] != "WAITING" or not copied_exact or not same_segments(card, after):
        raise Refused([problem("PLAN_INVALID", "the planned card fails its own readback")])
    snapshot = snapshot_bytes(task, rel(card_path, repo), date, copy_lf, amendments, report_rel)
    # If the current task is already in 1.1, its snapshot may be planned by preserve_previous.
    by_path = {p: (old, payload) for p, old, payload in artifacts}
    if snap_path in by_path:
        old, payload = by_path[snap_path]
        if snapshot_parts(payload) != (copy_lf, amendments):
            raise Refused([problem("SNAPSHOT_CONFLICT", "amendments or task text differ")])
    else:
        artifacts.append((snap_path, initial_snapshot, initial_snapshot if reuse else snapshot))
    artifacts = list({p: (p, old, payload) for p, old, payload in artifacts}.values())
    proto.update({"new_card_sha256": sha256(new), "copy_sha256_lf": sha256(copy_lf), "copy_lines": len(lines1),
                  "copied_exact": True, "outside_slots_unchanged": True, "block1_after": "WAITING",
                  "eol": "CRLF" if eol == b"\r\n" else "LF", "snapshot": snap_rel,
                  "snapshot_state": "EXISTS_IDENTICAL" if reuse else "NEW", "chat_amendments": len(amendments)})
    if not args.apply:
        proto["result"] = "DRY RUN OK"
        proto["planned_action"] = "ALREADY_ROTATED" if already else "CLEARED_DUPLICATE_BLOCK1" if duplicate else "ROTATED"
        return proto, 0
    with card_lock(card_path):
        if card_path.read_bytes() != data:
            raise Refused([problem("CARD_CHANGED", "the card changed after it was read")])
        if getattr(args, "checked_sha256", sha256(data)) != sha256(data):
            raise Refused([problem("CARD_CHANGED", "card changed since workflow check")])
        for p, old, payload in artifacts:
            if bounded_bytes(p) != old:
                raise Refused([problem("ARCHIVE_CHANGED", rel(p, repo))])
        for p, old, payload in artifacts:
            if old is None:
                snapshot_path(repo, p)  # recheck addressed parents before creating anything
                create_snapshot(p, payload)
            if False:
                raise Refused([problem("SNAPSHOT_READBACK", "the card was not changed")])
        if _BEFORE_CARD_WRITE:
            _BEFORE_CARD_WRITE(card_path)
        if card_path.read_bytes() != data:
            raise Refused([problem("CARD_CHANGED", "the card changed after it was read")])
        for p, old, payload in artifacts:
            if False:
                raise Refused([problem("ARCHIVE_CHANGED", rel(p, repo))])
        if new != data:
            atomic_write(card_path, new)
        if card_path.read_bytes() != new:
            atomic_write(card_path, data)
            raise Refused([problem("READBACK_MISMATCH_ROLLED_BACK")])
    proto["snapshot_sha256"] = sha256(snap_path.read_bytes())
    if previous.get("action") == "WILL_CREATE":
        previous["action"] = "CREATED"
    proto["result"] = "ALREADY_ROTATED" if already else "CLEARED_DUPLICATE_BLOCK1" if duplicate else "ROTATED"
    proto["card_unchanged"] = new == data
    return proto, 0


def cmd_finish(args, proto):
    """One process: check -> dry run -> apply -> readback; no manual edits."""
    proto["steps"] = []
    for phase in ("check", "dry-run", "apply", "readback"):
        if phase in ("apply", "readback") and not args.apply:
            break
        progress(args, phase, {"check": "Проверяем оба блока", "dry-run": "Проверяем архив и план переноса",
                              "apply": "Сохраняем снимки и выполняем перенос", "readback": "Сверяем результат после записи"}[phase], "green")
        step = {"command": phase}
        if phase in ("check", "readback"):
            step, code = cmd_check(args, step)
            if phase == "check" and code == 0:
                expected = getattr(args, "expected_card_sha256", None)
                if expected is not None and expected != step["card_sha256"]:
                    proto["steps"].append(step)
                    proto.update(result="NO ROTATE", problems=[problem("CARD_CHANGED", "card changed since manual confirmation")])
                    return proto, 3
                args.checked_sha256 = step["card_sha256"]
                for slot_name in ("block1", "block1_1"):
                    slot = step[slot_name]
                    progress(args, "slots", ("БЛОК 1" if slot_name == "block1" else "БЛОК 1.1") +
                             ": " + slot.get("task_id", slot["state"]))
        else:
            saved = args.apply
            args.apply = phase == "apply"
            try:
                step, code = cmd_rotate(args, step)
            finally:
                args.apply = saved
        proto["steps"].append(step)
        if code:
            proto.update(result="NO ROTATE", problems=step.get("problems", []))
            return proto, code
    final = proto["steps"][-2] if args.apply else proto["steps"][-1]
    proto["result"] = final["result"]
    proto["task_id"] = args.task_id
    if args.apply:
        readback = proto["steps"][-1]
        if readback["block1"]["state"] != "WAITING" or readback["block1_1"].get("task_id") != args.task_id:
            raise Refused([problem("FINAL_READBACK_MISMATCH")])
    progress(args, "done", "Уже перенесено: повторная запись не требуется" if proto["result"] == "ALREADY_ROTATED"
             else "Проверка завершена" if not args.apply else "БЛОК 1 освобождён; БЛОК 1.1 и снимок проверены",
             "blue" if proto["result"] == "ALREADY_ROTATED" else "green")
    return proto, 0


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="validate markers, TASK IDs and the BLOCK 1.1 copy")
    install = sub.add_parser("install-markers", help="one-time insertion of the four slot markers")
    rotate = sub.add_parser("rotate", help="move BLOCK 1 to BLOCK 1.1 and set BLOCK 1 to waiting")
    finish = sub.add_parser("finish", help="one workflow: check, dry run, optional apply, readback")
    watch = sub.add_parser("watch", help="read-only local card status window; never rotates or uses Git")
    assign = sub.add_parser("assign", help="user assigns Markdown to a WAITING block; never replaces an active task")
    assign.set_defaults(task_id="NEW-TASK", report_dir=None)
    assign.add_argument("--task-file", required=True, help="UTF-8 Markdown supplied by the user")
    assign.add_argument("--expected-card-sha256", required=True, help="hash of the card shown to the user")
    assign.add_argument("--progress", action="store_true")
    assign.add_argument("--headless", action="store_true")
    watch.set_defaults(task_id="STATUS-ONLY", apply=False, report_dir=None, progress=False)
    watch_display = watch.add_mutually_exclusive_group()
    watch_display.add_argument("--headless", action="store_true", help="return one check without opening a window")
    watch_display.add_argument("--new-task", action="store_true", help="open the user task editor only if BLOCK 1 is WAITING; no automatic submission")
    for item in (check, install, rotate, finish, watch, assign):
        item.add_argument("--card", required=True)
        item.add_argument("--repo", help="repository root (default: the folder above Документация)")
    for item in (install, rotate, finish, assign):
        item.add_argument("--apply", action="store_true", help="write the change (default: dry run)")
    for item in (rotate, finish):
        item.add_argument("--task-id", required=True, help="the TASK ID that the executor hands in")
        item.add_argument("--no-chat-amendment", action="store_true", help="the TASK had no chat-only AMENDMENT")
        item.add_argument("--chat-amendment", action="append", metavar="FILE", help="exact text of a chat-only AMENDMENT")
        item.add_argument("--report-dir", help="final package folder (default: reports/<TASK-ID>)")
        item.add_argument("--archive-001", help="explicit historical archive fallback (no automatic full-history scan)")
        item.add_argument("--previous-archive", help="override the exact snapshot path already stored in BLOCK 1.1")
        item.add_argument("--previous-archive-ref", help="optional caller-supplied publication locator; never verified by this tool")
        item.add_argument("--date", help="transfer date YYYY-MM-DD (default: today)")
    finish.add_argument("--progress", action="store_true", help="JSON progress events on stderr")
    finish.add_argument("--expected-card-sha256", help="refuse if the card changed since the user's observation")
    display = finish.add_mutually_exclusive_group()
    display.add_argument("--monitor", action="store_true", help="show debug window for this run")
    display.add_argument("--headless", action="store_true", help="suppress debug window for this run")
    return parser


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    handler = {"check": cmd_check, "install-markers": cmd_install, "rotate": cmd_rotate, "finish": cmd_finish,
               "watch": cmd_check, "assign": cmd_assign}[args.command]
    card_path = Path(args.card).resolve()
    proto = {"command": args.command, "card": rel(card_path, repo_root(card_path, args.repo))}
    initial_sha = sha256(card_path.read_bytes()) if card_path.is_file() else None
    try:
        proto, code = handler(args, proto)
    except (Refused, FileNotFoundError) as error:
        problems = error.problems if isinstance(error, Refused) else [
            problem("FILE_NOT_FOUND", Path(error.filename or "").name)]
        proto.update({"result": "NO ROTATE" if args.command == "rotate" else "REFUSED", "problems": problems,
                      "card_unchanged": card_path.is_file() and sha256(card_path.read_bytes()) == initial_sha})
        code = 3
        progress(args, "blocked", "; ".join(p["code"] for p in problems), "red")
    print(json.dumps(proto, ensure_ascii=False, indent=1))
    return code


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "watch" and "--headless" not in sys.argv:
        from task_slot_monitor import launch
        sys.exit(launch(sys.argv[1:]))
    if len(sys.argv) > 1 and sys.argv[1] == "finish" and "--headless" not in sys.argv:
        from task_slot_monitor import debug_settings, launch
        if "--monitor" in sys.argv or debug_settings()["enabled"]:
            sys.exit(launch(sys.argv[1:]))
    sys.exit(main())
