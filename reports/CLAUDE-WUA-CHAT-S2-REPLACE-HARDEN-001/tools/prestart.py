"""Pre-start record of CLAUDE-WUA-CHAT-S2-REPLACE-HARDEN-001, taken before the first edit (no Git):
- the card slot check (tools/task_slot_rotate.py check);
- the launcher (launch_config.json active, load_launch() standard) and its three files against the launcher package;
- the engineering bytes of the base No.477 by content: the two files of the F-01 repair package (No.475) and every
  other new/changed file of the Stage2 package (No.473), plus the published launcher / Stage1 / EVM pins;
- the F-01 repair present in context_storage.py (its helpers and the three guarded writers).
Usage: prestart.py <out.json>
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
sha = lambda data: hashlib.sha256(data).hexdigest()


def manifest(task: str) -> dict:
    return json.loads((REPO / "reports" / task / "manifest.json").read_text(encoding="utf-8"))


def same(rel: str, pin: str) -> bool:
    data = (REPO / rel).read_bytes()
    lf = data.replace(b"\r\n", b"\n")
    return pin in {sha(data), sha(lf), sha(lf.replace(b"\n", b"\r\n"))}


def main():
    check = subprocess.run([sys.executable, "-B", "tools/task_slot_rotate.py", "check", "--card", CARD], cwd=REPO,
                           capture_output=True, text=True, encoding="utf-8")
    protocol = json.loads(check.stdout)
    pins, source = {}, {}
    for task, groups in (("CLAUDE-WUA-CHAT-LAUNCHER-001", ("new_files",)), ("CLAUDE-WUA-CHAT-S1-READONLY-UI-001", ("changed_files",)),
                         ("CLAUDE-WUA-EVM-PINNED-MULTIWINDOW-001", ("changed_files",)),
                         ("CLAUDE-WUA-CHAT-S2-SHARED-STORAGE-001", ("changed_files", "new_files")),
                         ("CLAUDE-WUA-CHAT-S2-CONTEXT-PATH-REPAIR-001", ("changed_files",))):
        for group in groups:
            for rel, row in manifest(task)[group].items():
                pins[rel], source[rel] = row["sha256"], task  # later packages win
    files = {rel: {"pinned_by": source[rel], "same_content": same(rel, pin)} for rel, pin in sorted(pins.items())}
    text = (REPO / "context_storage.py").read_text(encoding="utf-8")
    f01 = {name: name in text for name in ("def _refuse_linked_message_context", "def _message_context_folder_for_write",
                                           "def _replace_verified", "def _write_message_context_state",
                                           "def _refuse_newer_message_context_state")}
    f01["three_writers_guarded"] = text.count("        _refuse_linked_message_context(writer, chat_id, message_id)\n") == 3
    config = json.loads((REPO / "web_alarm/launch_config.json").read_text(encoding="utf-8"))
    launch = load_launch()
    record = {
        "task": "CLAUDE-WUA-CHAT-S2-REPLACE-HARDEN-001", "purpose": "pre-start state before the first edit",
        "base": "main@ffeb5d192924172f9ae6558cee961731b49295ce (No.477) as published content; Git not used",
        "card_check": {"exit": check.returncode, "result": protocol["result"], "card_sha256": protocol["card_sha256"],
                       "block1": protocol["block1"], "block1_1": protocol["block1_1"]},
        "launcher": {"config_active": config["active"], "load_launch_standard": launch.standard},
        "files": files,
        "no_drift": all(v["same_content"] for v in files.values()),
        "f01_repair_present": f01,
        "parallel_work": "Direction B: no active TASK on these files (No.34/No.40)",
        "git_used": False,
    }
    Path(sys.argv[1]).write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"check": protocol["result"], "block1": protocol["block1"].get("task_id"), "launcher": config["active"],
                      "no_drift": record["no_drift"], "drift": [k for k, v in files.items() if not v["same_content"]],
                      "f01": all(f01.values())}))


if __name__ == "__main__":
    main()
