"""TEST-QA for the launcher: each mutant weakens one rule in a TEMP mirror and test_web_alarm_launcher must kill it.

Mirror = top-level *.py / *.js / *.bat plus web_alarm/*.py and web_alarm/*.json of the working tree. Runs through
run_gate.py with CLAUDE_RUNNER_ROOT (guarded runner, TEMP isolation). Path-free JSON record.
Usage: run_mutants.py <python> <out.json>
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
L, C = "web_alarm/launcher.py", "web_alarm/launch_config.json"
MUTANTS = {
    "M01 test profile may use the standard storage": (L, '    if raw.get("storage") != "temp":', "    if False:"),
    "M02 test profile may use the standard port": (L, "    if port == standard_port():", "    if False:"),
    "M03 test page not marked": (L, '    return page.replace("<body>", "<body>" + frame + badge, 1)', "    return page"),
    "M04 no warning pause before the browser": (L, "            for left in range(TEST_WARNING_SECONDS, 0, -1):\n                out.write(f\"Браузер",
                                                 "            for left in range(0):\n                out.write(f\"Браузер"),
    "M05 listening server on the port not detected": (L, "        if bind_port and (claim is None or _port_in_use(bind_port)):",
                                                      "        if bind_port and claim is None:"),
    "M06 port claim never refuses": (L, "    except StoreLockTimeout:\n        return None", "    except StoreLockTimeout:\n        return lock"),
    "M07 reuse ignores the storage": (L, "    same_storage = isinstance(storage, str) and (", "    same_storage = True or isinstance(storage, str) and ("),
    "M08 shipped configuration left in test mode": (C, '"active": "standard"', '"active": "isolated-empty"'),
    "M09 standard banner painted red": (L, "paint(STANDARD_TEXT, 42, colors)", "paint(STANDARD_TEXT, 41, colors)"),
    "M10 test storage not removed": (L, "        shutil.rmtree(storage_root, ignore_errors=True)", "        pass"),
    "M11 break and close signals ignored": (L, "                signal.signal(getattr(signal, name), raise_interrupt)", "                pass"),
    "M12 normal stop keeps the test storage": (L, '        _remove_temp_storage(storage_root)\n        out.write("Сервер остановлен.',
                                                '        out.write("Сервер остановлен.'),
    "M13 refused launch keeps the test storage": (L, '        _remove_temp_storage(storage_root)\n        url = f"http',
                                                   '        url = f"http'),
    "M14 self-test keeps the test storage": (L, "            _remove_temp_storage(storage_root)\n    _stop_on_break()", "    _stop_on_break()"),
}


def mirror(file_name=None, old=None, new=None) -> Path:
    dest = Path(tempfile.mkdtemp(prefix="claude-launch-mirror-"))
    for pattern in ("*.py", "*.js", "*.bat"):
        for path in REPO.glob(pattern):
            shutil.copy2(path, dest / path.name)
    (dest / "web_alarm").mkdir()
    for path in (REPO / "web_alarm").iterdir():
        if path.suffix in {".py", ".json"}:
            shutil.copy2(path, dest / "web_alarm" / path.name)
    config = json.loads((REPO / "web_alarm" / "launch_config.json").read_text(encoding="utf-8"))
    for profile in config["test_profiles"].values():  # scripts named by the shipped profiles
        if profile.get("script"):
            (dest / profile["script"]).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO / profile["script"], dest / profile["script"])
    if file_name:
        target = dest / file_name
        text = target.read_text(encoding="utf-8")
        if text.count(old) != 1:
            shutil.rmtree(dest)
            sys.exit(f"pattern occurs {text.count(old)} times in {file_name}: {old[:60]!r}")
        target.write_bytes(text.replace(old, new).encode("utf-8"))
    return dest


def test_storages() -> set:
    return set(Path(tempfile.gettempdir()).glob("wa-test-launch-*"))


def run(python, dest):
    """Returns (exit, failing tests, isolation violations, test storages the mutant left behind and this tool removed).
    M10/M11 disable the launcher's own cleanup on purpose, so the tool cleans up after them."""
    before = test_storages()
    env = dict(os.environ, CLAUDE_RUN_PREFIX="claude-launch", CLAUDE_TASK_LABEL="CLAUDE-WUA-CHAT-LAUNCHER-001",
               CLAUDE_RUNNER_ROOT=str(dest), PYTHONIOENCODING="utf-8")
    env.pop("CLAUDE_EXTRA_PATH", None)
    try:
        done = subprocess.run([python, str(GATE), python, "mutant", "test_web_alarm_launcher"], cwd=dest, env=env,
                              capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    finally:
        left = test_storages() - before
        for path in left:
            shutil.rmtree(path, ignore_errors=True)
    summary = json.loads(done.stdout)
    if summary.get("results") == "MISSING":
        return summary["exit"], ["<module import failed>"], None, len(left)
    failed = sorted({t[0].split(".")[-1].split(" ")[0] for t in summary.get("non_pass", []) if t[1] != "SKIP"})
    return summary["exit"], failed, summary.get("isolation_violations"), len(left)


python, target = sys.argv[1], Path(sys.argv[2])
dest = mirror()
try:
    code, failed, isolation, left = run(python, dest)
finally:
    shutil.rmtree(dest, ignore_errors=True)
control = {"exit": code, "failing": failed, "isolation_violations": isolation, "test_storages_left": left,
           "verdict": "PASS" if code == 0 and not failed and not left else "FAIL"}
print(json.dumps({"control": control["verdict"]}), flush=True)
rows = []
for name, (file_name, old, new) in MUTANTS.items():
    dest = mirror(file_name, old, new)
    try:
        code, failed, isolation, left = run(python, dest)
    finally:
        shutil.rmtree(dest, ignore_errors=True)
    verdict = ("INVALID (mutant does not import)" if failed == ["<module import failed>"]
               else "KILLED" if code != 0 and failed else "SURVIVED")
    rows.append({"mutant": name, "file": file_name, "exit": code, "failing_tests": failed,
                 "isolation_violations": isolation, "test_storages_left_removed_by_tool": left, "verdict": verdict})
    print(json.dumps({"mutant": name, "verdict": verdict, "failing": failed}, ensure_ascii=False), flush=True)
record = {"task": "CLAUDE-WUA-CHAT-LAUNCHER-001", "control": control, "results": rows,
          "killed": sum(r["verdict"] == "KILLED" for r in rows), "mutants": len(rows)}
target.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
