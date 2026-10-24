"""Card rotation for CLAUDE-WA4-R-FT1-ARCHIVE-RETRY-001 (card rules: 001 first, readback, BLOCKS 2-3, then BLOCK 1).

precheck  read-only: card markers and line ends; BLOCK 1 holds this TASK; 5/5 entries in BLOCKS 2-3; hashes of Rules
          and BLOCK 4; read back exactly the previous own 001 record by its receipt and the last two bytes of 001 -
          no other archive content is read or searched.
A         append the record (BLOCK 1 statement verbatim, factual result, locators, the evicted BLOCK 2-3 lines) to
          001; read back exactly the appended byte range; prove the earlier archive bytes unchanged.
B         re-verify; BLOCK 2/3: new line on top, oldest line evicted (it is in the A record); BLOCK 1 -> WAITING;
          Rules and BLOCK 4 byte-identical; the archive unchanged since A.
Usage: rotate_task.py precheck <state.json> | A <closeout.md> <state.json> | B <state.json>
"""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[4]
DOCS = ROOT / "Документация"
CARD = DOCS / "000_Задачи Claude.md"
ARCHIVE = DOCS / "001_История выполненных задач Claude.md"
TASK = "CLAUDE-WA4-R-FT1-ARCHIVE-RETRY-001"
REPORT = f"Alarm/ALARM_TASK_SESSION/TASK_{TASK}/report.md"
PREVIOUS = ROOT / "Alarm" / "ALARM_TASK_SESSION" / "TASK_CLAUDE-CARD-ROTATION-RECOVERY-001" / "rotation.json"
H1 = "---\n# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА\n---\n\n"
H2 = "---\n# БЛОК 2 — ПЯТЬ ПОСЛЕДНИХ ЗАДАЧ (КОМПАКТНО)\n"
H3 = "# БЛОК 3 — КРАТКИЕ ФАКТИЧЕСКИЕ ИТОГИ\n"
H4 = "# БЛОК 4 — НЕЗАВИСИМАЯ ПРИЁМКА / VERIFIER\n"
WAITING = "Статус: ОЖИДАНИЕ НОВОЙ ЗАДАЧИ\nTASK: —\n\n"
LINE2 = (f"- **2026-10-24 / {TASK}** — устранение ложных срабатываний guard тестового runner (F-T1) и проверка полноты "
         "forensic-архива при повторном восстановлении (`_proven_attempts`). Статус: RESULT READY / AWAITING "
         "INDEPENDENT VERIFICATION.")
LINE3 = (f"- **{TASK}** — F-T1: `Path.resolve()` оставлял префикс расширенного пути при гонке создания каталога "
         "(ошибка 3→2) и разрешал удаляемый каталог в `$Extend\\$Deleted` → guard снимает только свой префикс и "
         "переразрешает `$Deleted`, явные выходы по-прежнему отвергаются; Archive Retry: `tail.bin` и квитанция не "
         "проверялись → проверяются, повреждение → REFUSED без записи, отсутствие квитанции допустимо. Мутанты 6/6 + "
         f"9/9. Полный источник: запись в `001` и `{REPORT}`.")
sha = lambda data: hashlib.sha256(data).hexdigest()


def load_card():
    data = CARD.read_bytes()
    crlf = data.count(b"\r\n")
    assert data.count(b"\r") == crlf and (crlf == 0 or data.count(b"\n") == crlf), "mixed line endings: STOP"
    eol = "\r\n" if crlf else "\n"
    text = data.decode("utf-8").replace("\r\n", "\n")
    for marker in (H1, H2, H3, H4):
        assert text.count(marker) == 1, f"marker not unique: {marker!r}"
    assert text.index(H1) < text.index(H2) < text.index(H3) < text.index(H4), "marker order: STOP"
    return data, text, eol


def regions(text):
    return (text[:text.index(H1)], text[text.index(H1) + len(H1):text.index(H2)],
            text[text.index(H2):text.index(H3)], text[text.index(H3):text.index(H4)], text[text.index(H4):])


def entries(block):
    return [line for line in block.split("\n") if line.startswith("- **")]


def read_range(offset, length):
    with open(ARCHIVE, "rb") as handle:
        handle.seek(offset)
        return handle.read(length)


def rotate(block, line):
    old = entries(block)
    lines = block.split("\n")
    first = lines.index(old[0])
    kept = [line] + old[:4]
    rest = [x for x in lines[first:] if x not in old]
    return "\n".join(lines[:first] + kept + rest), old[4]


phase = sys.argv[1]
state_path = Path(sys.argv[-1])
data, text, eol = load_card()
rules, block1, block2, block3, block4 = regions(text)
if phase == "precheck":
    prev = json.loads(PREVIOUS.read_text(encoding="utf-8"))
    prev_ok = sha(read_range(prev["archive_offset"], prev["archive_appended_bytes"])) == prev["archive_record_sha256"]
    size = ARCHIVE.stat().st_size
    state = {"phase": "precheck", "card_sha256": sha(data), "card_bytes": len(data),
             "card_eol": "CRLF" if eol == "\r\n" else "LF", "block1_is_this_task": f"# {TASK}\n" in block1,
             "rules_sha256": sha(rules.encode()), "block4_sha256": sha(block4.encode()),
             "block2_entries": len(entries(block2)), "block3_entries": len(entries(block3)),
             "previous_record_readback": prev_ok,
             "previous_record_ends_archive": prev["archive_offset"] + prev["archive_appended_bytes"] == size,
             "archive_size": size, "archive_sha256": sha(ARCHIVE.read_bytes()),
             "archive_eol": "CRLF" if read_range(size - 2, 2) == b"\r\n" else "OTHER",
             "already_archived": TASK in read_range(prev["archive_offset"], prev["archive_appended_bytes"]).decode(),
             "archive_read": "previous own record range (by receipt) + last 2 bytes; whole-file hash only"}
    ok = (state["block1_is_this_task"] and state["block2_entries"] == 5 and state["block3_entries"] == 5 and prev_ok
          and state["previous_record_ends_archive"] and state["archive_eol"] == "CRLF")
    state["result"] = "OK" if ok else "STOP"
elif phase == "A":
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["phase"] == "precheck" and state["result"] == "OK" and state["card_sha256"] == sha(data), "drift"
    before = ARCHIVE.read_bytes()
    assert len(before) == state["archive_size"] and sha(before) == state["archive_sha256"], "archive changed: STOP"
    statement = "\n".join(line.rstrip() for line in block1.strip("\n").split("\n"))
    assert "````" not in statement
    fence = "````" if "```" in statement else "```"
    closeout = Path(sys.argv[2]).read_text(encoding="utf-8").replace("\r\n", "\n").strip("\n")
    evicted2, evicted3 = entries(block2)[4], entries(block3)[4]
    record = (
        f"\n---\n\n## 2026-10-24 — {TASK} — 🟨 Устранение нестабильности guard тестового runner (F-T1) и проверка "
        "полноты forensic-архива при повторном восстановлении\n\n"
        "**НЕПРОВЕРЕННАЯ АРХИВНАЯ СЕКЦИЯ** (факт исполнителя; независимая приёмка — БЛОК 4 / 06). **AMENDMENT:** не "
        f"было. **Исходный статус:** RESULT READY / AWAITING INDEPENDENT VERIFICATION. **Отчёт:** `{REPORT}`; "
        f"manifest — `Alarm/ALARM_TASK_SESSION/TASK_{TASK}/manifest.json`.\n\n"
        f"### Постановка — БЛОК 1 дословно (хвостовые пробелы сняты)\n\n{fence}text\n{statement}\n{fence}\n\n"
        f"### Фактический результат\n\n{closeout}\n\n"
        f"### Вытеснено этой ротацией из окна пяти задач (строки БЛОКОВ 2–3 дословно)\n\n"
        f"- БЛОК 2: {evicted2[2:]}\n- БЛОК 3: {evicted3[2:]}\n"
    )
    payload = record.replace("\n", "\r\n").encode("utf-8")
    with open(ARCHIVE, "ab") as handle:
        handle.write(payload)
    after = ARCHIVE.read_bytes()
    assert read_range(len(before), len(payload)) == payload and after[:len(before)] == before, \
        "archive readback mismatch: CARD ROTATION BLOCKED"
    state.update(phase="A", archive_offset=len(before), archive_appended_bytes=len(payload),
                 archive_record_sha256=sha(payload), archive_size_after=len(after), archive_sha256_after=sha(after),
                 readback="MATCH", earlier_bytes_unchanged=True, evicted_block2=evicted2, evicted_block3=evicted3)
elif phase == "B":
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["phase"] == "A" and state["card_sha256"] == sha(data), "card changed since precheck: STOP"
    assert sha(ARCHIVE.read_bytes()) == state["archive_sha256_after"], "archive changed since A: STOP"
    new2, out2 = rotate(block2, LINE2)
    new3, out3 = rotate(block3, LINE3)
    assert (out2, out3) == (state["evicted_block2"], state["evicted_block3"]), "eviction differs from the record"
    CARD.write_bytes((rules + H1 + WAITING + new2 + new3 + block4).replace("\n", eol).encode("utf-8"))
    disk, disk_text, disk_eol = load_card()
    d_rules, d_block1, d_block2, d_block3, d_block4 = regions(disk_text)
    assert disk_eol == eol and d_block1 == WAITING
    assert entries(d_block2)[0] == LINE2 and entries(d_block3)[0] == LINE3
    assert len(entries(d_block2)) == 5 and len(entries(d_block3)) == 5
    assert out2 not in d_block2 and out3 not in d_block3
    assert (sha(d_rules.encode()), sha(d_block4.encode())) == (state["rules_sha256"], state["block4_sha256"])
    assert sha(ARCHIVE.read_bytes()) == state["archive_sha256_after"]
    state.update(phase="B", card_after_sha256=sha(disk), card_after_bytes=len(disk), block1_now="WAITING",
                 block2_entries_after=5, block3_entries_after=5, rules_unchanged=True,
                 block4_sha256_after=sha(d_block4.encode()), block4_unchanged=True, archive_unchanged_after_B=True)
else:
    raise SystemExit("phase must be precheck, A or B")
state_path.write_text(json.dumps(state, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({k: v for k, v in state.items() if not k.startswith("evicted")}, ensure_ascii=True, indent=1))
