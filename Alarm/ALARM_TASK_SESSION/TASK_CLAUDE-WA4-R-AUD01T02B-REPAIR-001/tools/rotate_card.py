"""Two-phase safe rotation of Документация/000_Задачи Claude.md (LF only, all other bytes kept).

phase A: copy the full BLOCK 1 statement (trailing spaces stripped) to the TOP of BLOCK 2 as a fenced
         text block with a status line, and put the closeout (from <block3.md>) at the TOP of BLOCK 3.
         BLOCK 1 is not touched. Verifies: old BLOCK 2/3 content kept byte-exact after the new entries.
phase B: only if phase A is proved on disk (both new entries present, statement identical), replace the
         BLOCK 1 statement with the waiting slot.
Usage: rotate_card.py A <block3.md> <out.json> | rotate_card.py B <out.json>
"""
import hashlib
import json
import sys
from pathlib import Path

CARD = Path(r"M:\GitHub\ag_llm\Документация\000_Задачи Claude.md")
TASK = "CLAUDE-WA4-R-AUD01T02B-REPAIR-001"
H1 = "---\n# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА\n---\n\n"
H2 = "---\n# БЛОК 2 — ПОСЛЕДНЯЯ ВЫПОЛНЕННАЯ ЗАДАЧА — ПОСТАНОВКА\n---\n\n"
H3 = "# БЛОК 3 — РЕЗУЛЬТАТ ПОСЛЕДНЕЙ ВЫПОЛНЕННОЙ ЗАДАЧИ\n---\n\n"
WAITING = "Статус: ОЖИДАНИЕ НОВОЙ ЗАДАЧИ\nTASK: —\n\n"
TITLE = f"### {TASK} — Web Alarm Reliability: Global Transport History & Microtask Transition Integrity"
sha = lambda b: hashlib.sha256(b).hexdigest()


def load():
    data = CARD.read_bytes()
    assert b"\r" not in data, "card is not LF-only"
    text = data.decode("utf-8")
    for marker in (H1, H2, H3):
        assert text.count(marker) == 1, f"marker not unique: {marker!r}"
    return data, text


def statement(text):
    start = text.index(H1) + len(H1)
    end = text.index(H2)
    return text[start:end]


phase = sys.argv[1]
data, text = load()
report = {"phase": phase, "before_sha256": sha(data), "before_bytes": len(data)}
if phase == "A":
    block1 = statement(text)
    assert f"**TASK ID:** `{TASK}`" in block1, "BLOCK 1 is not this TASK"
    assert "```" not in block1
    body = "\n".join(line.rstrip() for line in block1.rstrip("\n").removesuffix("---").rstrip("\n").split("\n"))
    entry2 = (f"{TITLE}\n\n**Статус постановки:** БЛОК 1 (USER-DIRECTED, размещён пользователем). Назначение — "
              "стартовое сообщение пользователя в чат 2026-10-16; выполнена агентом 008 (Claude) 2026-10-16; "
              "AMENDMENT во время работы не было; результат — в БЛОКЕ 3. Полная постановка из БЛОКА 1 дословно "
              "(хвостовые пробелы сняты):\n\n```text\n" + body + "\n```\n\n")
    entry3 = Path(sys.argv[2]).read_text(encoding="utf-8").rstrip("\n") + "\n\n---\n\n"
    assert "\r" not in entry3
    i2 = text.index(H2) + len(H2)
    text = text[:i2] + entry2 + text[i2:]
    i3 = text.index(H3) + len(H3)
    text = text[:i3] + entry3 + text[i3:]
    new = text.encode("utf-8")
    CARD.write_bytes(new)
    # proof on disk
    disk = CARD.read_bytes().decode("utf-8")
    assert disk == text
    assert statement(disk) == block1, "BLOCK 1 changed in phase A"
    old_rest2 = data.decode("utf-8")
    old2 = old_rest2[old_rest2.index(H2) + len(H2):old_rest2.index(H3)]
    new2 = disk[disk.index(H2) + len(H2) + len(entry2):disk.index(H3)]
    old3 = old_rest2[old_rest2.index(H3) + len(H3):]
    new3 = disk[disk.index(H3) + len(H3) + len(entry3):]
    report.update(entry2_bytes=len(entry2.encode()), entry3_bytes=len(entry3.encode()),
                  old_block2_kept=old2 == new2, old_block3_kept=old3 == new3,
                  block1_sha256=sha(block1.encode()), after_sha256=sha(CARD.read_bytes()),
                  after_bytes=len(CARD.read_bytes()))
    assert report["old_block2_kept"] and report["old_block3_kept"]
    out = Path(sys.argv[3])
elif phase == "B":
    out = Path(sys.argv[2])
    previous = json.loads(out.read_text(encoding="utf-8"))
    assert previous["phase"] == "A" and previous["after_sha256"] == sha(data), "card changed since phase A"
    block1 = statement(text)
    assert sha(block1.encode()) == previous["block1_sha256"]
    after2 = text[text.index(H2) + len(H2):]
    after3 = text[text.index(H3) + len(H3):]
    assert after2.startswith(TITLE) and after3.startswith(f"### {TASK}"), "phase A entries not on top"
    body = "\n".join(line.rstrip() for line in block1.rstrip("\n").removesuffix("---").rstrip("\n").split("\n"))
    assert body in after2, "BLOCK 2 does not hold the full statement"
    start = text.index(H1) + len(H1)
    end = text.index(H2)
    text = text[:start] + WAITING + text[end:]
    CARD.write_bytes(text.encode("utf-8"))
    disk = CARD.read_bytes().decode("utf-8")
    assert statement(disk) == WAITING
    report = dict(previous, phase="B", phase_a_after_sha256=previous["after_sha256"],
                  after_sha256=sha(CARD.read_bytes()), after_bytes=len(CARD.read_bytes()), block1_now="WAITING")
else:
    raise SystemExit("phase must be A or B")
out.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=1))
