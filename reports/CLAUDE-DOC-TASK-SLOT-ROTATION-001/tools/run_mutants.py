"""Mutation check of tools/task_slot_rotate.py: each mutant disables one guard; the test file must fail on it.
A mutant copy lives in a temporary folder; the tests load it through TASK_SLOT_ROTATE_UNDER_TEST. The real script and
the real cards are not changed (the tests only read the cards). Writes evidence/mutants.json.
"""
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_tests import PACKAGE, REPO, run  # noqa: E402

SCRIPT = REPO / "tools" / "task_slot_rotate.py"
# (id, guard, old text, new text, occurrence)
MUTANTS = [
    ("M01", "damaged marker line is not reported", "if TOKEN in t and t not in MARKERS:", "if False:", 1),
    ("M02", "duplicated marker is not reported", "elif len(found) > 1:", "elif False:", 1),
    ("M03", "text outside the markers is accepted", 'if card.texts[i].strip() not in ("", "---"):', "if False:", 1),
    ("M04", "mixed line endings are accepted", "if crlf and lf:", "if False:", 1),
    ("M05", "TASK ID of BLOCK 1 is not compared with --task-id",
     'if block1.get("task_id") and block1["task_id"] != task:', "if False:", 1),
    ("M06", "TASK ID format (path safety) is not checked", "if len(task) > 120 or not TASK_ID_RE.fullmatch(task):",
     "if False:", 1),
    ("M07", "two different TASK IDs in BLOCK 1 are accepted", "elif len(ids) > 1:", "elif False:", 1),
    ("M08", "the same task pasted twice is accepted",
     "elif len(decls) > 1 and sum(1 for t in texts if t == nonblank[0]) > 1:", "elif False:", 1),
    ("M09", "AMENDMENT for another TASK is accepted", "if task_id and match.group(1) != task_id:", "if False:", 1),
    ("M10", "the previous BLOCK 1.1 counts as archived without proof",
     "return None if at < 0 else data[:at].count(b\"\\n\") + 1", "return 1", 1),
    ("M11", "an edited BLOCK 1.1 copy is accepted", 'if result["copy_sha256"] != match["sha"]:', "if False:", 1),
    ("M12", "the same TASK can be rotated twice", 'if block11["task_id"] == task:', "if False:", 1),
    ("M13", "an unfinished report package is accepted", "problems += package_problems(report_dir)", "pass", 1),
    ("M14", "chat AMENDMENT status may stay undeclared",
     "elif not args.no_chat_amendment and not args.chat_amendment:", "elif False:", 1),
    ("M15", "an existing different snapshot is overwritten", "if parts == (copy_lf, amendments):", "if True:", 1),
    ("M16", "the card is not re-read right before the write",
     "_BEFORE_CARD_WRITE(card_path)\n        if card_path.read_bytes() != data:",
     "_BEFORE_CARD_WRITE(card_path)\n        if False:", 1),
    ("M17", "the lock does not exclude a second rotation", "os.O_CREAT | os.O_EXCL | os.O_WRONLY",
     "os.O_CREAT | os.O_WRONLY", 1),
    ("M18", "dry run of rotate writes", 'if not args.apply:\n        proto["result"] = "DRY RUN OK"\n        return proto, 0\n'
     '    with card_lock(card_path):\n        if card_path.read_bytes() != data:\n            raise Refused([problem("CARD_CHANGED", '
     '"the card changed after it was read")])\n        if not reuse:',
     'if False:\n        pass\n    with card_lock(card_path):\n        if card_path.read_bytes() != data:\n            raise '
     'Refused([problem("CARD_CHANGED", "the card changed after it was read")])\n        if not reuse:', 1),
    ("M19", "lines are split on Unicode separators too",
     '    parts = data.split(b"\\n")\n    lines = [part + b"\\n" for part in parts[:-1]]\n    if parts[-1]:\n'
     '        lines.append(parts[-1])\n    return lines', "    return data.splitlines(keepends=True)", 1),
    ("M20", "the copy is normalised to LF inside a CRLF card", "+ [meta.encode(\"utf-8\") + eol, eol] + lines1 +",
     "+ [meta.encode(\"utf-8\") + eol, eol] + [x.replace(b\"\\r\\n\", b\"\\n\") for x in lines1] +", 1),
    ("M21", "the waiting line differs from the regulation", 'WAITING = "**ОЖИДАНИЕ НОВОЙ ЗАДАЧИ.**"',
     'WAITING = "ОЖИДАНИЕ НОВОЙ ЗАДАЧИ"', 1),
    ("M22", "a failed write leaves the temporary file", "        with contextlib.suppress(OSError):\n            tmp.unlink()\n"
     "        raise Refused", "        raise Refused", 1),
    ("M23", "a whole card pasted into BLOCK 1 is accepted when markers stay unique",
     'if text.startswith("# БЛОК "):', "if False:", 1),
    ("M24", "install-markers changes text, not only adds marker lines",
     "lines[:s1] + [marker[0]] + lines[s1:e1]", "lines[:s1] + [marker[0]] + lines[s1 + 1:e1]", 1),
]


def mutate(source: str, old: str, new: str, occurrence: int) -> str:
    assert occurrence == 1 and source.count(old) == 1, f"pattern must occur exactly once: {old[:60]}"
    return source.replace(old, new)


def main():
    source = SCRIPT.read_text(encoding="utf-8")
    cards = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (REPO / "Документация").glob("000_Задачи *.md")}
    work = Path(tempfile.mkdtemp(prefix="task-slot-mutants-"))
    rows = []
    try:
        control = run()
        for mid, guard, old, new, occurrence in MUTANTS:
            path = work / f"{mid}.py"
            path.write_text(mutate(source, old, new, occurrence), encoding="utf-8", newline="\n")
            result = run({"TASK_SLOT_ROTATE_UNDER_TEST": str(path)})
            failed = sorted(k for k, v in result["per_test"].items() if v in ("FAIL", "ERROR"))
            rows.append({"id": mid, "guard": guard, "killed": result["exit"] != 0 and bool(failed),
                         "failing_tests": failed, "tests_run": result["tests_run"]})
            print(mid, "killed" if rows[-1]["killed"] else "SURVIVED", len(failed))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (REPO / "Документация").glob("000_Задачи *.md")}
    record = {"purpose": "each mutant disables one guard of tools/task_slot_rotate.py; the tests must fail",
              "control": {k: control[k] for k in ("exit", "tests_run", "pass", "fail", "errors", "skips")},
              "mutants": len(rows), "killed": sum(r["killed"] for r in rows), "rows": rows,
              "script_sha256": hashlib.sha256(SCRIPT.read_bytes()).hexdigest(),
              "real_cards_unchanged": cards == after}
    (PACKAGE / "evidence" / "mutants.json").write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n",
                                                       encoding="utf-8", newline="\n")
    print(json.dumps({k: record[k] for k in ("control", "mutants", "killed", "real_cards_unchanged")}))


if __name__ == "__main__":
    main()
