"""Record the finalization of this TASK (BLOCK 1 task of 2026-10-24 without its own TASK ID) - BLOCK 1 is NOT changed.

The user instruction for this finalization: results go to BLOCKS 2 and 3 by the current rules, BLOCK 1 stays as it is.
precheck  read-only: card markers; BLOCK 1 holds the finalization task; this TASK's lines in BLOCK 2/3; hashes of the
          Rules / BLOCK 1 / BLOCK 4 regions; read back this TASK's two earlier 001 records (receipts in the folder)
          and the last two bytes of 001 - no other archive content is read or searched.
A         append the FINALIZE record (BLOCK 1 statement verbatim, factual result, locators) to 001; read back exactly
          the appended byte range.
B         re-verify, then replace this TASK's line in BLOCK 2 and in BLOCK 3 in place; Rules, BLOCK 1 and BLOCK 4 must
          stay byte-identical.
Usage: rotate_finalize.py precheck <state.json> | A <closeout.md> <state.json> | B <state.json>
"""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
DOCS = Path(__file__).resolve().parents[4] / "Документация"
CARD = DOCS / "000_Задачи Claude.md"
ARCHIVE = DOCS / "001_История выполненных задач Claude.md"
TASK = "CLAUDE-WA4-R-EVIDENCE-SANITIZER-REPAIR-001"
REPORT = f"Alarm/ALARM_TASK_SESSION/TASK_{TASK}/report.md"
H1 = "---\n# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА\n---\n\n"
H2 = "---\n# БЛОК 2 — ПЯТЬ ПОСЛЕДНИХ ЗАДАЧ (КОМПАКТНО)\n"
H3 = "# БЛОК 3 — КРАТКИЕ ФАКТИЧЕСКИЕ ИТОГИ\n"
H4 = "# БЛОК 4 — НЕЗАВИСИМАЯ ПРИЁМКА / VERIFIER\n"
BLOCK1_MARK = "Завершение локального пакета проверки Evidence Sanitizer после F-ES-03"
PREFIX2 = f"- **2026-10-23 / {TASK}**"
PREFIX3 = f"- **{TASK}**"
LINE2 = (f"{PREFIX2} — исправление fail-open F-ES-01 / F-ES-02 + REVISE F-ES-03 (2026-10-24) + локальное завершение "
         "пакета (SHA-256/manifest/mapping, 2026-10-24). Статус: RESULT READY / AWAITING INDEPENDENT VERIFICATION.")
LINE3 = (f"{PREFIX3} — F-ES-01/F-ES-02 закрыты fail-closed; REVISE F-ES-03: `--package` = комплект, внутри или вокруг "
         "него, через ссылку или жёсткие ссылки → `package-not-independent`, REFUSED; завершение: 201 CRLF-копия прогона "
         "не сверялась бы с опубликованным блобом → копии в LF, manifest отказывает при CR, `evidence.json` исправлен, "
         f"`tools/check_package.py` CONSISTENT. Полный источник: записи в `001` и `{REPORT}`.")
sha = lambda data: hashlib.sha256(data).hexdigest()


def load_card():
    data = CARD.read_bytes()
    crlf = data.count(b"\r\n")
    assert data.count(b"\r") == crlf and (crlf == 0 or data.count(b"\n") == crlf), "mixed line endings: STOP"
    eol = "\r\n" if crlf else "\n"
    text = data.decode("utf-8").replace("\r\n", "\n")
    for marker in (H1, H2, H3, H4):
        assert text.count(marker) == 1, f"marker not unique: {marker!r}"
    return data, text, eol


def regions(text):
    return (text[:text.index(H1)], text[text.index(H1) + len(H1):text.index(H2)],
            text[text.index(H2):text.index(H3)], text[text.index(H3):text.index(H4)], text[text.index(H4):])


def own_line(block, prefix):
    lines = [line for line in block.split("\n") if line.startswith(prefix)]
    assert len(lines) == 1, f"expected exactly one line for this TASK: {prefix}"
    return lines[0]


def read_range(offset, length):
    with open(ARCHIVE, "rb") as handle:
        handle.seek(offset)
        return handle.read(length)


phase = sys.argv[1]
data, text, eol = load_card()
rules, block1, block2, block3, block4 = regions(text)
state_path = Path(sys.argv[-1])
if phase == "precheck":
    earlier = [json.loads((HERE / name).read_text(encoding="utf-8")) for name in ("card-rotation.json",
                                                                                  "amendment-rotation.json")]
    readbacks = [sha(read_range(r["archive_offset"], r["archive_appended_bytes"])) == r["archive_record_sha256"]
                 for r in earlier]
    size = ARCHIVE.stat().st_size
    tail = read_range(max(0, size - 2), 2)
    state = {"phase": "precheck", "card_sha256": sha(data), "block1_is_finalize_task": BLOCK1_MARK in block1,
             "rules_sha256": sha(rules.encode()), "block1_sha256": sha(block1.encode()),
             "block4_sha256": sha(block4.encode()), "line2_before": own_line(block2, PREFIX2),
             "line3_before": own_line(block3, PREFIX3), "earlier_records_readback": readbacks,
             "archive_size": size, "archive_eol": "CRLF" if tail.endswith(b"\r\n") else "LF",
             "archive_read": "own earlier record ranges + last 2 bytes only"}
    state["result"] = "OK" if state["block1_is_finalize_task"] and all(readbacks) else "STOP"
elif phase == "A":
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["phase"] == "precheck" and state["result"] == "OK" and state["card_sha256"] == sha(data), "drift"
    size = ARCHIVE.stat().st_size
    assert size == state["archive_size"], "archive changed since precheck"
    archive_eol = "\r\n" if state["archive_eol"] == "CRLF" else "\n"
    statement = "\n".join(line.rstrip() for line in block1.strip("\n").split("\n"))
    assert "````" not in statement
    fence = "````" if "```" in statement else "```"
    closeout = Path(sys.argv[2]).read_text(encoding="utf-8").replace("\r\n", "\n").strip("\n")
    record = (
        f"\n---\n\n## 2026-10-24 — {TASK} — ЛОКАЛЬНОЕ ЗАВЕРШЕНИЕ ПАКЕТА ПОСЛЕ F-ES-03\n\n"
        "**НЕПРОВЕРЕННАЯ АРХИВНАЯ СЕКЦИЯ** (дополнение к записям этой TASK от 2026-10-23 и 2026-10-24; факт "
        "исполнителя, независимая приёмка — БЛОК 4 / 06). Постановка — БЛОК 1 без собственного TASK ID; по указанию "
        "пользователя БЛОК 1 не изменялся. **Исходный статус:** RESULT READY / AWAITING INDEPENDENT VERIFICATION. "
        f"**Отчёт:** `{REPORT}` (раздел 13).\n\n### Постановка — БЛОК 1 дословно (хвостовые пробелы сняты)\n\n"
        f"{fence}text\n{statement}\n{fence}\n\n### Фактический результат\n\n{closeout}\n"
    )
    prefix = "" if read_range(max(0, size - 1), 1) == b"\n" else "\n"
    payload = (prefix + record).replace("\n", archive_eol).encode("utf-8")
    with open(ARCHIVE, "ab") as handle:
        handle.write(payload)
    back = read_range(size, len(payload))
    assert back == payload, "archive readback mismatch: CARD ROTATION BLOCKED"
    state.update(phase="A", archive_offset=size, archive_appended_bytes=len(payload),
                 archive_record_sha256=sha(payload), archive_size_after=size + len(payload), readback="MATCH")
elif phase == "B":
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["phase"] == "A" and state["card_sha256"] == sha(data), "card changed since precheck"
    assert sha(read_range(state["archive_offset"], state["archive_appended_bytes"])) == state["archive_record_sha256"]
    new_text = rules + H1 + block1 + block2.replace(state["line2_before"], LINE2) \
        + block3.replace(state["line3_before"], LINE3) + block4
    CARD.write_bytes(new_text.replace("\n", eol).encode("utf-8"))
    disk, disk_text, disk_eol = load_card()
    d_rules, d_block1, d_block2, d_block3, d_block4 = regions(disk_text)
    assert disk_eol == eol and own_line(d_block2, PREFIX2) == LINE2 and own_line(d_block3, PREFIX3) == LINE3
    assert (sha(d_rules.encode()), sha(d_block1.encode()), sha(d_block4.encode())) == \
        (state["rules_sha256"], state["block1_sha256"], state["block4_sha256"])
    state.update(phase="B", card_after_sha256=sha(disk), card_after_bytes=len(disk),
                 rules_block1_block4_unchanged=True)
else:
    raise SystemExit("phase must be precheck, A or B")
state_path.write_text(json.dumps(state, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({k: v for k, v in state.items() if not k.startswith("line")}, ensure_ascii=True, indent=1))
