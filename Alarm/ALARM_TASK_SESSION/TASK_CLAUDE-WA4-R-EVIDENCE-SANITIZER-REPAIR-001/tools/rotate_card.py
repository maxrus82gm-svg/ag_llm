"""Rotation of Документация/000_Задачи Claude.md under the 2026-10-23 card rules, with an append-only 001 record.

precheck  read-only: card markers, BLOCK 1 = this TASK, BLOCK 2/3 windows, hashes of the Rules and BLOCK 4 regions;
          of 001 only its size and last two bytes are read (to append with the same line ending) - the archive's
          older records are never read or searched (BLOCK 1 section 2 / 10).
A         append this TASK's record to 001: full BLOCK 1 statement (no AMENDMENT), factual result (block3-closeout),
          status, locators, and - verbatim - the BLOCK 2/3 window lines this rotation will evict, so that the evicted
          lines are provably archived without reading older archive records; then read back exactly the appended
          byte range.
B         re-verify the appended range and the unchanged card, then: new entry on top of BLOCK 2 and 3, the oldest
          beyond five evicted (only lines contained in the read-back record), BLOCK 1 -> waiting slot; Rules and
          BLOCK 4 must stay byte-identical (BLOCK 4 is the verifier's, read-only).
Usage: rotate_card.py precheck <state.json> | A <block3.md> <state.json> | B <state.json>
"""
import hashlib
import json
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parents[4] / "Документация"
CARD = DOCS / "000_Задачи Claude.md"
ARCHIVE = DOCS / "001_История выполненных задач Claude.md"
TASK = "CLAUDE-WA4-R-EVIDENCE-SANITIZER-REPAIR-001"
DATE = "2026-10-23"
TITLE = "Исправление fail-open ошибок механизма безопасной публикации диагностических отчётов"
REPORT = f"Alarm/ALARM_TASK_SESSION/TASK_{TASK}/report.md"
MANIFEST = f"Alarm/ALARM_TASK_SESSION/TASK_{TASK}/manifest.json"
H1 = "---\n# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА\n---\n\n"
H2 = "---\n# БЛОК 2 — ПЯТЬ ПОСЛЕДНИХ ЗАДАЧ (КОМПАКТНО)\n"
H3 = "# БЛОК 3 — КРАТКИЕ ФАКТИЧЕСКИЕ ИТОГИ\n"
H4 = "# БЛОК 4 — НЕЗАВИСИМАЯ ПРИЁМКА / VERIFIER\n"
WAITING = "Статус: ОЖИДАНИЕ НОВОЙ ЗАДАЧИ\nTASK: —\n\n"
LINE2 = (f"- **{DATE} / {TASK}** — исправление fail-open F-ES-01 / F-ES-02 механизма публикации evidence. "
         "Статус: RESULT READY / AWAITING INDEPENDENT VERIFICATION.")
sha = lambda data: hashlib.sha256(data).hexdigest()


def load_card():
    data = CARD.read_bytes()
    crlf = data.count(b"\r\n")
    assert data.count(b"\r") == crlf and (crlf == 0 or data.count(b"\n") == crlf), "mixed line endings: STOP"
    eol = "\r\n" if crlf else "\n"
    text = data.decode("utf-8").replace("\r\n", "\n")
    for marker in (H1, H2, H3, H4):
        assert text.count(marker) == 1, f"marker not unique: {marker!r}"
    assert text.index(H1) < text.index(H2) < text.index(H3) < text.index(H4)
    return data, text, eol


def regions(text):
    rules = text[:text.index(H1)]
    block1 = text[text.index(H1) + len(H1):text.index(H2)]
    block2 = text[text.index(H2):text.index(H3)]
    block3 = text[text.index(H3):text.index(H4)]
    block4 = text[text.index(H4):]
    return rules, block1, block2, block3, block4


def entries(block):
    return [line for line in block.split("\n") if line.startswith("- **")]


def line3(closeout: str) -> str:
    return (f"- **{TASK}** — F-ES-01 (manifest SHA-256/размер) и F-ES-02 (полнота комплекта) закрыты fail-closed; "
            f"verify доказывает набор против пакета или внешнего хеша карты, иначе REFUSED. Полный источник: запись "
            f"в `001` и `{REPORT}`.")


def archive_tail():
    size = ARCHIVE.stat().st_size
    with open(ARCHIVE, "rb") as handle:
        handle.seek(max(0, size - 2))
        tail = handle.read()
    eol = "\r\n" if tail.endswith(b"\r\n") else "\n"
    return size, tail, eol


def body_of(block1):
    return "\n".join(line.rstrip() for line in block1.rstrip("\n").split("\n"))


phase = sys.argv[1]
data, text, eol = load_card()
rules, block1, block2, block3, block4 = regions(text)
state_path = Path(sys.argv[-1])
if phase == "precheck":
    size, tail, archive_eol = archive_tail()
    state = {"phase": "precheck", "card_sha256": sha(data), "card_eol": "CRLF" if eol == "\r\n" else "LF",
             "block1_is_task": f"**TASK ID:** `{TASK}`" in block1, "block2_entries": len(entries(block2)),
             "block3_entries": len(entries(block3)), "rules_sha256": sha(rules.encode()),
             "block4_sha256": sha(block4.encode()), "archive_size": size, "archive_ends_with_newline": tail[-1:] == b"\n",
             "archive_eol": "CRLF" if archive_eol == "\r\n" else "LF",
             "archive_read": "last 2 bytes only (no older record read or searched)"}
    state["result"] = "OK" if state["block1_is_task"] and state["block2_entries"] and state["block3_entries"] else "STOP"
elif phase == "A":
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["phase"] == "precheck" and state["result"] == "OK" and state["card_sha256"] == sha(data), "card drift"
    size, tail, archive_eol = archive_tail()
    assert size == state["archive_size"], "archive changed since precheck"
    closeout = Path(sys.argv[2]).read_text(encoding="utf-8").replace("\r\n", "\n").strip("\n")
    old2, old3 = entries(block2), entries(block3)
    evict2, evict3 = old2[4:], old3[4:]
    statement = body_of(block1)
    assert "````" not in statement, "statement contains a four-backtick fence: STOP"
    fence = "````" if "```" in statement else "```"
    record = (
        f"\n---\n\n## {DATE} — {TASK} — 🟨 {TITLE}\n\n"
        "**НЕПРОВЕРЕННАЯ АРХИВНАЯ СЕКЦИЯ** (фактический результат исполнителя; независимая приёмка — БЛОК 4 / 06). "
        "**Исходный статус:** RESULT READY / AWAITING INDEPENDENT VERIFICATION. **AMENDMENT:** не было. "
        f"**Отчёт:** `{REPORT}`. **Manifest:** `{MANIFEST}`.\n\n"
        "### Постановка — БЛОК 1 дословно (хвостовые пробелы сняты; в карточке текст обрывается в §11)\n\n"
        f"{fence}text\n{statement}\n{fence}\n\n### Фактический результат\n\n{closeout}\n\n"
        "### Вытеснено этой ротацией из окна пяти задач (строки БЛОКОВ 2–3 дословно)\n\n"
        + "".join(f"- БЛОК 2: {line[2:]}\n" for line in evict2)
        + "".join(f"- БЛОК 3: {line[2:]}\n" for line in evict3)
    )
    prefix = "" if tail.endswith(b"\n") or size == 0 else "\n"
    payload = (prefix + record).replace("\n", archive_eol).encode("utf-8")
    with open(ARCHIVE, "ab") as handle:
        handle.write(payload)
    with open(ARCHIVE, "rb") as handle:  # read back exactly the appended range
        handle.seek(size)
        back = handle.read()
    assert back == payload, "archive readback mismatch: CARD ROTATION BLOCKED"
    state.update(phase="A", archive_offset=size, archive_appended_bytes=len(payload),
                 archive_record_sha256=sha(payload), archive_size_after=size + len(payload),
                 evicted_block2=evict2, evicted_block3=evict3, line3=line3(closeout), readback="MATCH")
elif phase == "B":
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["phase"] == "A" and state["card_sha256"] == sha(data), "card changed since precheck"
    with open(ARCHIVE, "rb") as handle:
        handle.seek(state["archive_offset"])
        back = handle.read(state["archive_appended_bytes"])
    assert sha(back) == state["archive_record_sha256"], "archive record changed: CARD ROTATION BLOCKED"
    record_text = back.decode("utf-8").replace("\r\n", "\n")
    for line in state["evicted_block2"] + state["evicted_block3"]:
        assert line[2:] in record_text, "an evicted line is not in the read-back record: STOP"
    assert body_of(block1) in record_text, "the full statement is not in the read-back record: STOP"
    old2, old3 = entries(block2), entries(block3)
    new2 = [LINE2] + old2[:4]
    new3 = [state["line3"]] + old3[:4]
    out2, out3 = block2, block3
    for old, new, name in ((old2, new2, "2"), (old3, new3, "3")):
        target = out2 if name == "2" else out3
        first = target.index(old[0])
        last = target.index(old[-1]) + len(old[-1])
        target = target[:first] + "\n".join(new) + target[last:]
        if name == "2":
            out2 = target
        else:
            out3 = target
    new_text = rules + H1 + WAITING + out2 + out3 + block4
    CARD.write_bytes(new_text.replace("\n", eol).encode("utf-8"))
    disk, disk_text, disk_eol = load_card()
    d_rules, d_block1, d_block2, d_block3, d_block4 = regions(disk_text)
    assert disk_eol == eol and d_block1 == WAITING and entries(d_block2) == new2 and entries(d_block3) == new3
    assert sha(d_rules.encode()) == state["rules_sha256"] and sha(d_block4.encode()) == state["block4_sha256"]
    state.update(phase="B", card_after_sha256=sha(disk), card_after_bytes=len(disk), block1_now="WAITING",
                 block2_entries_after=len(new2), block3_entries_after=len(new3), rules_unchanged=True,
                 block4_unchanged=True)
else:
    raise SystemExit("phase must be precheck, A or B")
state_path.write_text(json.dumps(state, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({k: v for k, v in state.items() if k not in ("evicted_block2", "evicted_block3", "line3")},
                 ensure_ascii=True, indent=1))
