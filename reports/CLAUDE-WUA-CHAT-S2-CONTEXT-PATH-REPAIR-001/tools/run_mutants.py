"""TEST-QA of the F-01 repair (CLAUDE-WUA-CHAT-S2-CONTEXT-PATH-REPAIR-001): each mutant removes or weakens one part of
the message-context write protection in a disposable TEMP mirror of the code; the tests must kill it. The unmodified
mirror is the control and must pass. R01c is analysed in advance as equivalent for writes (create stays protected by
the second check, which R02 removes) and is run to show it, not to be counted as a gap in the tests.
Mirror = top-level *.py / *.js / *.json and web_alarm/*.py / *.json (no Git metadata, no data). Targets run through
run_gate.py with CLAUDE_RUNNER_ROOT pointing at the mirror (guarded runner, TEMP isolation).
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
EARLY = "        _refuse_linked_message_context(writer, chat_id, message_id)\n"

MUTANTS = {
    "R01 no first check in any context writer": [(EARLY + "        return _activate_message_context_variant(\n",
                                                  "        return _activate_message_context_variant(\n"),
                                                 (EARLY + "        return _create_message_context_variant(\n",
                                                  "        return _create_message_context_variant(\n"),
                                                 (EARLY + "        return _restore_message_raw(workspace_root, chat_id, message_id)\n",
                                                  "        return _restore_message_raw(workspace_root, chat_id, message_id)\n")],
    "R01a no first check in activate": [(EARLY + "        return _activate_message_context_variant(\n",
                                         "        return _activate_message_context_variant(\n")],
    "R01b no first check in restore": [(EARLY + "        return _restore_message_raw(workspace_root, chat_id, message_id)\n",
                                        "        return _restore_message_raw(workspace_root, chat_id, message_id)\n")],
    "R01c no first check in create (expected equivalent for writes)": [(EARLY + "        return _create_message_context_variant(\n",
                                                                        "        return _create_message_context_variant(\n")],
    "R02 folders made by plain mkdir right before the write": [(
        "    folder = _message_context_parts(chat_id, message_id)\n    _ensure_write_directory(anchor, folder[:-1])\n"
        "    _ensure_write_directory(anchor, folder)\n    if variants:\n        folder = folder + (\"variants\",)\n"
        "        _ensure_write_directory(anchor, folder)\n",
        "    folder = _message_context_parts(chat_id, message_id)\n    if variants:\n        folder = folder + (\"variants\",)\n"
        "    anchor.path(folder).mkdir(parents=True, exist_ok=True)\n")],
    "R03 restore overwrites a newer state": [(
        "    if isinstance(version, int) and not isinstance(version, bool) and version > MESSAGE_CONTEXT_SCHEMA_VERSION:\n",
        "    if False:\n")],
    "R04 the kind of state.json not checked": [(
        "    if st is not None:\n        if _is_link_or_reparse(st):\n", "    if False:\n        if _is_link_or_reparse(st):\n")],
    "R05 the lock guard of the internal writers removed": [(
        "    if anchor.expected((ULTRA_DIRNAME, LOCKS_DIRNAME, WRITER_LOCK_NAME)) not in _held_writer_locks():\n"
        "        raise RuntimeError(\"Запись контекста сообщения вне блокировки Workspace запрещена.\")\n", "")],
    "R06 the parents of message_context not verified again": [(
        "    for parts in ((ULTRA_DIRNAME,), (ULTRA_DIRNAME, \"chats\"), (ULTRA_DIRNAME, \"chats\", chat_id)):\n"
        "        _verify_write_directory(anchor, parts)\n", "")],
}


def mirror(edits) -> Path:
    dest = Path(tempfile.mkdtemp(prefix="claude-s2r-mirror-"))
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
    env = dict(os.environ, CLAUDE_RUN_PREFIX="claude-s2r", CLAUDE_TASK_LABEL="CLAUDE-WUA-CHAT-S2-CONTEXT-PATH-REPAIR-001",
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
    return sorted(p.name for pattern in ("wa_s2_*", "claude-s2r-*") for p in temp.glob(pattern))


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
    record = {"task": "CLAUDE-WUA-CHAT-S2-CONTEXT-PATH-REPAIR-001",
              "purpose": "mutation gate of the message-context write protection (TEST-QA)",
              "targets": list(TARGETS), "control": control, "results": rows, "mutants": len(rows),
              "killed": sum(r["verdict"] == "KILLED" for r in rows), "temp_leftovers_new": sorted(set(leftovers()) - before)}
    target.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"mutants": record["mutants"], "killed": record["killed"], "control": control["verdict"],
                      "leftovers": record["temp_leftovers_new"]}))


if __name__ == "__main__":
    main()
