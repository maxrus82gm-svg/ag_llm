"""Final state before the hand-in of CLAUDE-WUA-CHAT-S2-SHARED-STORAGE-001 (matrix item 10 and the slot guard):
- the launcher is in STANDARD (launch_config.json, load_launch()) and its three files are byte-identical to the
  pre-start record - no TEST switch was made by this task;
- the card slot check (tools/task_slot_rotate.py check) before the rotation;
- the Python sources of the write scope compile in memory (no .pyc written).
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
SOURCES = ("context_storage.py", "ultra_ui.py", "web_alarm/ultra_chat.py", "web_alarm/server.py", "web_alarm/ui.py",
           "test_ultra_chat_storage.py", "test_web_alarm_ultra_chat_storage.py")


def main():
    prestart = json.loads((REPO / "reports/CLAUDE-WUA-CHAT-S2-SHARED-STORAGE-001/evidence/prestart.json").read_text(encoding="utf-8"))
    launcher_files = {rel: hashlib.sha256((REPO / rel).read_bytes()).hexdigest() == prestart["files"][rel]["sha256"]
                      for rel in ("Start_WebAlarm.bat", "web_alarm/launcher.py", "web_alarm/launch_config.json")}
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
        "task": "CLAUDE-WUA-CHAT-S2-SHARED-STORAGE-001", "purpose": "final state before the hand-in",
        "launcher": {"config_active": config["active"], "load_launch_standard": launch.standard, "name": launch.name,
                     "files_identical_to_prestart": launcher_files, "test_switch_made": False},
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
