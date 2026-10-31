"""Final state before the hand-in of CLAUDE-WUA-CHAT-S2-CONTEXT-PATH-REPAIR-001 (test item 10 and the slot guard):
- the launcher is STANDARD (launch_config.json, load_launch()) and its three files have the content of the launcher
  package, as at the pre-start - no TEST switch was made;
- the card slot check (tools/task_slot_rotate.py check) before the rotation;
- the changed Python files compile in memory (no .pyc written).
Usage: final_state.py <out.json>
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from web_alarm.launcher import load_launch  # noqa: E402

CARD = "Документация/000_Задачи Claude.md"
SOURCES = ("context_storage.py", "test_ultra_chat_storage.py")
sha = lambda data: hashlib.sha256(data).hexdigest()


def main():
    package = json.loads((REPO / "reports/CLAUDE-WUA-CHAT-LAUNCHER-001/manifest.json").read_text(encoding="utf-8"))["new_files"]
    launcher_files = {}
    for rel in ("Start_WebAlarm.bat", "web_alarm/launcher.py", "web_alarm/launch_config.json"):
        data = (REPO / rel).read_bytes()
        lf = data.replace(b"\r\n", b"\n")
        launcher_files[rel] = package[rel]["sha256"] in {sha(data), sha(lf), sha(lf.replace(b"\n", b"\r\n"))}
    config = json.loads((REPO / "web_alarm/launch_config.json").read_text(encoding="utf-8"))
    launch = load_launch()
    check = subprocess.run([sys.executable, "-B", "tools/task_slot_rotate.py", "check", "--card", CARD], cwd=REPO,
                           capture_output=True, text=True, encoding="utf-8")
    protocol = json.loads(check.stdout)
    compiled = {}
    for rel in SOURCES:
        try:
            compile((REPO / rel).read_bytes().decode("utf-8"), rel, "exec")
            compiled[rel] = "OK"
        except SyntaxError as exc:
            compiled[rel] = f"SyntaxError line {exc.lineno}"
    record = {
        "task": "CLAUDE-WUA-CHAT-S2-CONTEXT-PATH-REPAIR-001", "purpose": "final state before the hand-in",
        "launcher": {"config_active": config["active"], "load_launch_standard": launch.standard, "name": launch.name,
                     "files_same_as_launcher_package": launcher_files, "test_switch_made": False},
        "card_check": {"exit": check.returncode, "result": protocol["result"], "block1": protocol["block1"],
                       "block1_1": protocol["block1_1"]},
        "python_compile_in_memory": compiled,
        "git_used": False,
    }
    Path(sys.argv[1]).write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"launcher": config["active"], "standard": launch.standard, "files": launcher_files,
                      "check": protocol["result"], "compile": compiled}, ensure_ascii=False))


if __name__ == "__main__":
    main()
