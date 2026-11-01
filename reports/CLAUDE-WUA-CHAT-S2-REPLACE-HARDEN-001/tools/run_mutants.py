"""TEST-QA of CLAUDE-WUA-CHAT-S2-REPLACE-HARDEN-001: each mutant puts back one old write path or removes one part of the
verified replacement in a disposable TEMP mirror of the code; the tests must kill it. The unmodified mirror is the
control and must pass. Mirror = top-level *.py / *.js / *.json and web_alarm/*.py / *.json (no Git metadata, no data).
Targets run through run_gate.py with CLAUDE_RUNNER_ROOT pointing at the mirror (guarded runner, TEMP isolation).
Usage: run_mutants.py <absolute python> <out.json> [mutant-name ...]
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
GATE = REPO / "Alarm" / "ALARM_TASK_SESSION" / "TASK_CLAUDE-WA4-R-AUD010205-REPAIR-001" / "tools" / "run_gate.py"
CS = "context_storage.py"
TARGETS = ("test_ultra_chat_storage", "test_message_context")

MUTANTS = {
    "H01 rename_workspace by the old unchecked replace": [(
        "        _replace_verified(writer.anchor, (ULTRA_DIRNAME, WORKSPACE_METADATA_NAME), _json_bytes(metadata))\n",
        "        _atomic_write_json(writer.anchor.path((ULTRA_DIRNAME, WORKSPACE_METADATA_NAME)), metadata)\n")],
    "H02 rename_chat by the old replace plus read-back": [(
        "        _replace_verified(writer.anchor, parts + (\"metadata.json\",), _json_bytes(updated))\n",
        "        _atomic_write_json(writer.anchor.path(parts + (\"metadata.json\",)), updated)\n"
        "        _verify_published(writer.anchor, parts + (\"metadata.json\",), _json_bytes(updated))\n")],
    "H03 project_context.md by the old unchecked replace": [(
        "        _replace_verified(writer.anchor, context_parts, text.encode(\"utf-8\"))\n",
        "        _atomic_write_text(writer.anchor.path(context_parts), text)\n")],
    "H04 the old text read by following links": [(
        "        old_text = _read_project_context_for_write(writer.anchor, context_parts)\n",
        "        old_text = path.read_text(encoding=\"utf-8-sig\") if path.exists() else \"\"\n")],
    "H05 a revision written by replace (may overwrite)": [(
        "            _publish_new_file(anchor, history + (name,), payload)\n",
        "            _atomic_write_text(anchor.path(history + (name,)), old_text)\n")],
    "H06 verified replace without the temporary-file location check": [(
        "        try:\n            if os.path.normcase(_final_path_of_fd(fd)) != anchor.expected(parts[:-1] + (temp.name,)):\n",
        "        try:\n            if False:\n")],
    "H07 verified replace without the read-back": [(
        "        _replace_with_retry(temp, target)\n    finally:\n        try:\n            os.unlink(temp)\n"
        "        except FileNotFoundError:\n            pass\n    _verify_published(anchor, parts, payload)\n",
        "        _replace_with_retry(temp, target)\n    finally:\n        try:\n            os.unlink(temp)\n"
        "        except FileNotFoundError:\n            pass\n")],
    "H08 a linked Project Context reported as merely unreadable": [(
        "        if exc.code == \"unsafe_storage_link\":\n            raise _write_refusal(exc) from None\n"
        "        raise StorageWriteError(\n            \"project_context_unreadable\",",
        "        raise StorageWriteError(\n            \"project_context_unreadable\",")],
    "H09 the old text not seen as Path.read_text saw it (newlines)": [(
        "    return text.replace(\"\\r\\n\", \"\\n\").replace(\"\\r\", \"\\n\")  # the universal-newline view of Path.read_text\n",
        "    return text\n")],
}


def mirror(edits) -> Path:
    dest = Path(tempfile.mkdtemp(prefix="claude-s2h-mirror-"))
    for pattern in ("*.py", "*.js", "*.json"):
        for path in REPO.glob(pattern):
            shutil.copy2(path, dest / path.name)
    (dest / "web_alarm").mkdir()
    for pattern in ("*.py", "*.json"):
        for path in (REPO / "web_alarm").glob(pattern):
            shutil.copy2(path, dest / "web_alarm" / path.name)
    if edits:
        target = dest / CS
        text = target.read_bytes().decode("utf-8")
        for old, new in edits:
            if text.count(old) != 1:
                shutil.rmtree(dest)
                sys.exit(f"pattern occurs {text.count(old)} times: {old[:60]!r}")
            text = text.replace(old, new)
        compile(text, CS, "exec")  # a mutant must stay valid Python (no false kill)
        target.write_bytes(text.encode("utf-8"))
    return dest


def run(python, dest):
    env = dict(os.environ, CLAUDE_RUN_PREFIX="claude-s2h", CLAUDE_TASK_LABEL="CLAUDE-WUA-CHAT-S2-REPLACE-HARDEN-001",
               CLAUDE_RUNNER_ROOT=str(dest), PYTHONIOENCODING="utf-8")
    env.pop("CLAUDE_EXTRA_PATH", None)
    done = subprocess.run([python, str(GATE), python, "mutant", *TARGETS], cwd=dest, env=env, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=1800)
    summary = json.loads(done.stdout)
    shutil.rmtree(summary["base"], ignore_errors=True)  # the runner's own TEMP attempt folder
    failed = sorted({t[0].split(".")[-1].split(" ")[0] for t in summary.get("non_pass", []) if t[1] != "SKIP"})
    return summary["exit"], failed, summary.get("isolation_violations"), summary.get("tests_run")


def leftovers() -> list[str]:
    temp = Path(tempfile.gettempdir())
    return sorted(p.name for pattern in ("wa_s2_*", "claude-s2h-*") for p in temp.glob(pattern))


def main():
    python, target = sys.argv[1], Path(sys.argv[2])
    chosen = sys.argv[3:] or list(MUTANTS)
    text = (REPO / CS).read_bytes().decode("utf-8")
    for name in chosen:  # every pattern must occur exactly once before anything runs
        for old, _new in MUTANTS[name]:
            if text.count(old) != 1:
                sys.exit(f"{name}: pattern occurs {text.count(old)} times")
    before = set(leftovers())
    dest = mirror([])
    try:
        code, failed, isolation, run_count = run(python, dest)
    finally:
        shutil.rmtree(dest, ignore_errors=True)
    control = {"targets": list(TARGETS), "exit": code, "tests_run": run_count, "failing": failed,
               "isolation_violations": isolation, "verdict": "PASS" if code == 0 and not failed else "FAIL"}
    print(json.dumps({"control": control["verdict"], "tests_run": run_count}), flush=True)
    rows = []
    for name in chosen:
        dest = mirror(MUTANTS[name])
        try:
            code, failed, isolation, run_count = run(python, dest)
        finally:
            shutil.rmtree(dest, ignore_errors=True)
        verdict = "KILLED" if code != 0 and failed else "SURVIVED"
        rows.append({"mutant": name, "exit": code, "failing_tests": failed, "isolation_violations": isolation, "verdict": verdict})
        print(json.dumps({"mutant": name, "verdict": verdict, "failing": failed}, ensure_ascii=False), flush=True)
    record = {"task": "CLAUDE-WUA-CHAT-S2-REPLACE-HARDEN-001",
              "purpose": "mutation gate of the verified replacement of workspace.json, project_context.md (+history) and the Chat card",
              "targets": list(TARGETS), "control": control, "results": rows, "mutants": len(rows),
              "killed": sum(r["verdict"] == "KILLED" for r in rows), "temp_leftovers_new": sorted(set(leftovers()) - before)}
    target.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"mutants": record["mutants"], "killed": record["killed"], "control": control["verdict"],
                      "leftovers": record["temp_leftovers_new"]}))


if __name__ == "__main__":
    main()
