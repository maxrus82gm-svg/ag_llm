"""Two-phase safe rotation of Документация/000_Задачи Claude.md, preserving the card's current line endings.

The working copy of the card is CRLF throughout (converted outside this TASK; history proven intact, see
card_precheck.json). Work happens on the LF-normalized text and is written back with the same EOL, so no
line ending of existing content changes. Phase A puts the full BLOCK 1 statement on top of BLOCK 2 (fenced,
trailing spaces stripped) and the closeout on top of BLOCK 3; BLOCK 1 untouched; old BLOCK 2/3 must be kept
exactly. Phase B (only if A is proved on disk) replaces BLOCK 1 with the waiting slot.
Usage: rotate_card.py precheck <out.json> | A <block3.md> <out.json> | B <out.json>
"""
import hashlib
import json
import sys
from pathlib import Path

CARD = Path(r"M:\GitHub\ag_llm\Документация\000_Задачи Claude.md")
TASK = "CLAUDE-WA4-R-TRANSPORT-TAIL-RECOVERY-001"
PREVIOUS_ROTATION_AFTER = "01c20408ce33648523dba1c291c772272ff57f9d78ae7867a78631594b38cd58"  # LF, prior task
H1 = "---\n# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА\n---\n\n"
H2 = "---\n# БЛОК 2 — ПОСЛЕДНЯЯ ВЫПОЛНЕННАЯ ЗАДАЧА — ПОСТАНОВКА\n---\n\n"
H3 = "# БЛОК 3 — РЕЗУЛЬТАТ ПОСЛЕДНЕЙ ВЫПОЛНЕННОЙ ЗАДАЧИ\n---\n\n"
WAITING = "Статус: ОЖИДАНИЕ НОВОЙ ЗАДАЧИ\nTASK: —\n\n"
TITLE = (f"### {TASK} — 🟨 Безопасное ручное восстановление повреждённого транспортного журнала "
         "после аварии (AUD-01T-R)")
sha = lambda b: hashlib.sha256(b).hexdigest()


def load():
    data = CARD.read_bytes()
    crlf = data.count(b"\r\n")
    bare_lf = data.count(b"\n") - crlf
    assert data.count(b"\r") == crlf, "stray CR in the card"
    assert crlf == 0 or bare_lf == 0, "mixed line endings in the card: STOP"
    eol = "\r\n" if crlf else "\n"
    text = data.decode("utf-8").replace("\r\n", "\n")
    for marker in (H1, H2, H3):
        assert text.count(marker) == 1, f"marker not unique: {marker!r}"
    return data, text, eol


def statement(text):
    return text[text.index(H1) + len(H1):text.index(H2)]


def encode(text, eol):
    return text.replace("\n", eol).encode("utf-8")


def body_of(block1):
    return "\n".join(line.rstrip() for line in block1.rstrip("\n").removesuffix("---").rstrip("\n").split("\n"))


phase = sys.argv[1]
data, text, eol = load()
report = {"phase": phase, "before_sha256": sha(data), "before_bytes": len(data), "eol": "CRLF" if eol == "\r\n" else "LF"}
if phase == "precheck":
    i, j = text.index(H1) + len(H1), text.index(H2)
    rebuilt = text[:i] + WAITING + text[j:]
    report.update(method="LF-normalized card with BLOCK 1 replaced by the waiting slot must equal the previous "
                         "rotation result", expected_sha256=PREVIOUS_ROTATION_AFTER,
                  reconstructed_sha256=sha(rebuilt.encode("utf-8")))
    report["result"] = "MATCH" if report["reconstructed_sha256"] == PREVIOUS_ROTATION_AFTER else "MISMATCH: STOP"
    out = Path(sys.argv[2])
elif phase == "A":
    block1 = statement(text)
    assert f"**TASK ID:** `{TASK}`" in block1, "BLOCK 1 is not this TASK"
    body = body_of(block1)
    fence = "````" if "```" in body else "```"
    assert fence + "`" not in body and (fence == "```" or "````" not in body)
    entry2 = (f"{TITLE}\n\n**Статус постановки:** БЛОК 1 (USER APPROVED, размещён пользователем/координатором LLM12). "
              "Запуск — короткое сообщение пользователя 2026-10-20; выполнена агентом 008 (Claude) 2026-10-20; "
              "AMENDMENT во время работы не было; результат — в БЛОКЕ 3. Полная постановка из БЛОКА 1 дословно "
              f"(хвостовые пробелы сняты):\n\n{fence}text\n" + body + f"\n{fence}\n\n")
    entry3 = Path(sys.argv[2]).read_text(encoding="utf-8").replace("\r\n", "\n").rstrip("\n") + "\n\n---\n\n"
    i2 = text.index(H2) + len(H2)
    new_text = text[:i2] + entry2 + text[i2:]
    i3 = new_text.index(H3) + len(H3)
    new_text = new_text[:i3] + entry3 + new_text[i3:]
    CARD.write_bytes(encode(new_text, eol))
    disk, disk_text, disk_eol = load()
    assert disk_eol == eol and disk_text == new_text and statement(disk_text) == block1
    old2 = text[text.index(H2) + len(H2):text.index(H3)]
    new2 = disk_text[disk_text.index(H2) + len(H2) + len(entry2):disk_text.index(H3)]
    old3 = text[text.index(H3) + len(H3):]
    new3 = disk_text[disk_text.index(H3) + len(H3) + len(entry3):]
    report.update(entry2_bytes=len(encode(entry2, eol)), entry3_bytes=len(encode(entry3, eol)),
                  old_block2_kept=old2 == new2, old_block3_kept=old3 == new3, fence=fence,
                  block1_sha256=sha(block1.encode("utf-8")), after_sha256=sha(disk), after_bytes=len(disk))
    assert report["old_block2_kept"] and report["old_block3_kept"]
    out = Path(sys.argv[3])
elif phase == "B":
    out = Path(sys.argv[2])
    previous = json.loads(out.read_text(encoding="utf-8"))
    assert previous["phase"] == "A" and previous["after_sha256"] == sha(data), "card changed since phase A"
    block1 = statement(text)
    assert sha(block1.encode("utf-8")) == previous["block1_sha256"]
    after2 = text[text.index(H2) + len(H2):]
    after3 = text[text.index(H3) + len(H3):]
    assert after2.startswith(TITLE) and after3.startswith(f"### {TASK}"), "phase A entries not on top"
    assert body_of(block1) in after2, "BLOCK 2 does not hold the full statement"
    new_text = text[:text.index(H1) + len(H1)] + WAITING + text[text.index(H2):]
    CARD.write_bytes(encode(new_text, eol))
    disk, disk_text, disk_eol = load()
    assert disk_eol == eol and statement(disk_text) == WAITING
    report = dict(previous, phase="B", phase_a_after_sha256=previous["after_sha256"], after_sha256=sha(disk),
                  after_bytes=len(disk), block1_now="WAITING")
else:
    raise SystemExit("phase must be precheck, A or B")
out.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print(json.dumps(report, ensure_ascii=False, indent=1))
