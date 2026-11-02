"""TEST-QA of P9 (CLAUDE-WUA-CHAT-RUNSTORE-P9-001): each mutant removes one part of the index protection in a
disposable TEMP mirror (top-level *.py / *.json and web_alarm/*.py / *.json; no Git metadata, no data); the final
test_run_store_v2.py must kill it. The unmodified mirror is the control and must pass. Tests run through
tools/run_pytest.py with P9_CODE_ROOT pointing at the mirror. Analysed in advance: M05 (create_run_summary without
its own lock) is expected to be equivalent for the index, because both inner steps lock themselves.
Usage: run_mutants.py <out.json> [mutant-name ...]
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parents[2]
RS = "run_store.py"

MUTANTS = {
    "M01 ensure_task_index_entry without the lock": [(
        "    with _index_lock(workspace_root):  # read, number and publish as one step (P9)\n",
        "    with contextlib.nullcontext():  # read, number and publish as one step (P9)\n"),
        ("            _save_index(workspace_root, index)\n        elif entry.get(\"chat_id\") != chat_id:",
         "            _save_index_unlocked(workspace_root, index)\n        elif entry.get(\"chat_id\") != chat_id:")],
    "M02 ensure_run_index_entry without its own lock": [(
        "    with _index_lock(workspace_root):  # the task and its run in one step; the nested task call re-enters (P9)\n",
        "    with contextlib.nullcontext():  # the task and its run in one step; the nested task call re-enters (P9)\n"),
        ("            if run_id not in task_entry[\"runs\"]:\n                task_entry[\"runs\"].append(run_id)\n"
         "            _save_index(workspace_root, index)\n",
         "            if run_id not in task_entry[\"runs\"]:\n                task_entry[\"runs\"].append(run_id)\n"
         "            _save_index_unlocked(workspace_root, index)\n")],
    "M03 update_run_summary_index without the lock": [(
        "    with _index_lock(workspace_root):  # the summary and the index status read and written as one step (P9)\n",
        "    with contextlib.nullcontext():  # the summary and the index status read and written as one step (P9)\n"),
        ("        if index_changed:\n            _save_index(workspace_root, index)\n",
         "        if index_changed:\n            _save_index_unlocked(workspace_root, index)\n")],
    "M04 the publication guard removed": [(
        "    _require_index_lock(workspace_root)\n    snapshot = copy.deepcopy(index)\n",
        "    snapshot = copy.deepcopy(index)\n")],
    "M05 create_run_summary without its own lock (expected equivalent)": [(
        "    with _index_lock(workspace_root):  # index entries and the summary they point to as one step (P9)\n",
        "    with contextlib.nullcontext():  # index entries and the summary they point to as one step (P9)\n")],
    "M06 a lock that does not exclude other processes": [(
        "    with _ultra_core._workspace_writer_lock(_ultra_core._write_anchor(root)):\n        yield\n",
        "    held = _ultra_core._held_writer_locks()\n"
        "    key = _ultra_core._write_anchor(root).expected((_ultra_core.ULTRA_DIRNAME, _ultra_core.LOCKS_DIRNAME, _ultra_core.WRITER_LOCK_NAME))\n"
        "    held[key] = held.get(key, 0) + 1\n    try:\n        yield\n    finally:\n        held[key] -= 1\n"
        "        if not held[key]:\n            del held[key]\n")],
    "M07 a reader crashes on a compacted generation": [(
        "        try:\n            value = _load_index_file(path)\n        except FileNotFoundError:\n",
        "        try:\n            value = _load_index_file(path)\n        except ZeroDivisionError:\n")],
}
# M01-M03 also need a save that skips the guard (otherwise the guard alone would kill them):
UNLOCKED_SAVE = ("\n\ndef _save_index_unlocked(workspace_root, index):\n"
                 "    held = _ultra_core._held_writer_locks()\n"
                 "    key = _ultra_core._write_anchor(Path(workspace_root).resolve()).expected("
                 "(_ultra_core.ULTRA_DIRNAME, _ultra_core.LOCKS_DIRNAME, _ultra_core.WRITER_LOCK_NAME))\n"
                 "    held[key] = held.get(key, 0) + 1\n    try:\n        _save_index(workspace_root, index)\n"
                 "    finally:\n        held[key] -= 1\n        if not held[key]:\n            del held[key]\n")


def mirror(edits) -> Path:
    dest = Path(tempfile.mkdtemp(prefix="p9-mut-mirror-"))
    for pattern in ("*.py", "*.json"):
        for path in REPO.glob(pattern):
            shutil.copy2(path, dest / path.name)
    (dest / "web_alarm").mkdir()
    for pattern in ("*.py", "*.json"):
        for path in (REPO / "web_alarm").glob(pattern):
            shutil.copy2(path, dest / "web_alarm" / path.name)
    if edits:
        target = dest / RS
        text = target.read_bytes().decode("utf-8")
        for old, new in edits:
            if text.count(old) != 1:
                shutil.rmtree(dest)
                sys.exit(f"pattern occurs {text.count(old)} times: {old[:60]!r}")
            text = text.replace(old, new)
        if "_save_index_unlocked(" in text:
            text = text.rstrip("\n") + UNLOCKED_SAVE
        compile(text, RS, "exec")  # a mutant must stay valid Python (no false kill)
        target.write_bytes(text.encode("utf-8"))
    return dest


def run(dest):
    out = Path(tempfile.mkdtemp(prefix="p9-mut-out-")) / "r.json"
    env = dict(os.environ, P9_CODE_ROOT=str(dest), PYTHONIOENCODING="utf-8")
    subprocess.run([sys.executable, "-B", str(TOOLS / "run_pytest.py"), "mutant", str(out), "test_run_store_v2.py"],
                   env=env, capture_output=True, text=True, encoding="utf-8", timeout=1800)
    record = json.loads(out.read_text(encoding="utf-8"))
    shutil.rmtree(out.parent, ignore_errors=True)
    failed = sorted(t["test"].split(".")[-1] for t in record["tests"] if t["status"] in {"FAIL", "ERROR"})
    return record["exit"], record["tests_run"], failed


def leftovers():
    temp = Path(tempfile.gettempdir())
    return sorted(p.name for pattern in ("p9-*", "wa_p9_*", "pytest-of-*") for p in temp.glob(pattern))


def main():
    target = Path(sys.argv[1])
    chosen = sys.argv[2:] or list(MUTANTS)
    text = (REPO / RS).read_bytes().decode("utf-8")
    for name in chosen:  # every pattern must occur exactly once before anything runs
        for old, _new in MUTANTS[name]:
            if text.count(old) != 1:
                sys.exit(f"{name}: pattern occurs {text.count(old)} times")
    before = set(leftovers())
    dest = mirror([])
    try:
        code, run_count, failed = run(dest)
    finally:
        shutil.rmtree(dest, ignore_errors=True)
    control = {"exit": code, "tests_run": run_count, "failing": failed, "verdict": "PASS" if code == 0 and not failed else "FAIL"}
    print(json.dumps({"control": control["verdict"], "tests_run": run_count}), flush=True)
    rows = []
    for name in chosen:
        dest = mirror(MUTANTS[name])
        try:
            code, run_count, failed = run(dest)
        finally:
            shutil.rmtree(dest, ignore_errors=True)
        verdict = "KILLED" if code != 0 and failed else "SURVIVED"
        rows.append({"mutant": name, "exit": code, "tests_run": run_count, "failing_tests": failed, "verdict": verdict})
        print(json.dumps({"mutant": name, "verdict": verdict, "failing": failed}, ensure_ascii=False), flush=True)
    record = {"task": "CLAUDE-WUA-CHAT-RUNSTORE-P9-001", "purpose": "mutation gate of the P9 index protection (TEST-QA)",
              "targets": ["test_run_store_v2.py"], "control": control, "results": rows, "mutants": len(rows),
              "killed": sum(r["verdict"] == "KILLED" for r in rows), "temp_leftovers_new": sorted(set(leftovers()) - before)}
    target.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"mutants": record["mutants"], "killed": record["killed"], "control": control["verdict"],
                      "leftovers": record["temp_leftovers_new"]}))


if __name__ == "__main__":
    main()
