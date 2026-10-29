"""Independent reverse check of the card changes (does not import tools/task_slot_rotate.py).

From the final Claude and Codex cards it undoes exactly what this task did and compares the result with the card hashes
seen before any edit:
  Claude: BLOCK 1.1 copy -> back to BLOCK 1, previous BLOCK 1.1 text (evidence/previous_block11.json) -> back to 1.1,
          the four marker lines and the added instruction paragraph removed;
  Codex:  the four marker lines and the added instruction paragraph removed.
If the hashes match, nothing else in the cards changed. Writes evidence/reverse_check.json.
"""
import hashlib
import json
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
REPO = PACKAGE.parents[1]
BEFORE = {  # first dry run / first check output, before any edit of the cards in this task
    "000_Задачи Claude.md": "166beba53757d405134184805ca28c9a03d384bd3d4fc4c43dd810a93d154657",
    "000_Задачи Codex.md": "e910cb1273650c05a10dc949c7fd1a27d249c0d89019622ed24c3547c43b18da",
}
PARAGRAPH_START = "**Скрипт и маркеры слотов (служебное поручение координатора 2026-10-29"
WAITING = "**ОЖИДАНИЕ НОВОЙ ЗАДАЧИ.**"


def lines_of(data: bytes):
    parts = data.split(b"\n")
    return [p + b"\n" for p in parts[:-1]] + ([parts[-1]] if parts[-1] else [])


def text(line: bytes) -> str:
    return line.rstrip(b"\n").rstrip(b"\r").decode("utf-8")


def drop_paragraph(lines):
    start = [i for i, x in enumerate(lines) if text(x).startswith(PARAGRAPH_START)]
    assert len(start) == 1, "instruction paragraph not found exactly once"
    end = start[0]
    while text(lines[end]).strip():
        end += 1
    return lines[:start[0]] + lines[end + 1:], end + 1 - start[0]


def main():
    result = {}
    for name, expected in BEFORE.items():
        data = (REPO / "Документация" / name).read_bytes()
        lines, removed = drop_paragraph(lines_of(data))
        marker_at = [i for i, x in enumerate(lines) if "TASK-SLOT:BLOCK-" in text(x)]
        assert len(marker_at) == 4, marker_at
        b1b, b1e, b11b, b11e = marker_at
        row = {"instruction_lines_removed": removed, "marker_lines": 4}
        if name.endswith("Claude.md"):
            assert [text(x) for x in lines[b1b + 1:b1e]] == [WAITING], "BLOCK 1 is not the waiting line"
            slot = lines[b11b + 1:b11e]
            assert text(slot[0]).startswith("**SUBMITTED / REVIEW PENDING** · TASK ID `") and not text(slot[1])
            copy = slot[2:]
            previous = json.loads((PACKAGE / "evidence" / "previous_block11.json").read_text(encoding="utf-8"))["text"]
            eol = b"\r\n" if lines[0].endswith(b"\r\n") else b"\n"
            restored11 = lines_of(previous.replace("\r\n", "\n").encode("utf-8").replace(b"\n", eol))
            lines = lines[:b1b + 1] + copy + lines[b1e:b11b + 1] + restored11 + lines[b11e:]
            row["copy_lines_moved_back"] = len(copy)
        original = b"".join(x for x in lines if "TASK-SLOT:BLOCK-" not in text(x))
        got = hashlib.sha256(original).hexdigest()
        row.update(expected_sha256=expected, reconstructed_sha256=got, match=got == expected,
                   reconstructed_sha256_lf=hashlib.sha256(original.replace(b"\r\n", b"\n")).hexdigest(),
                   final_card_sha256=hashlib.sha256(data).hexdigest())
        result[name] = row
    record = {"purpose": "prove that the cards changed only by the instruction paragraph, the markers and the rotation",
              "imports_rotation_script": False, "cards": result,
              "verdict": "PASS" if all(r["match"] for r in result.values()) else "FAIL"}
    (PACKAGE / "evidence" / "reverse_check.json").write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n",
                                                             encoding="utf-8", newline="\n")
    print(json.dumps({n: r["match"] for n, r in result.items()}, ensure_ascii=False), record["verdict"])


if __name__ == "__main__":
    main()
