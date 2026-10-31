"""Pre-start record of CLAUDE-WUA-CHAT-S2-CONTEXT-PATH-REPAIR-001, taken before the first edit (no Git):
- the card slot check (tools/task_slot_rotate.py check);
- the launcher (launch_config.json active, load_launch() standard) and its three files against the launcher package;
- every new/changed engineering file of the Stage2 package (published as No.473, base No.474 of this repair) against
  that package's manifest, by content (LF/CRLF-normalised: the user's sync may change line endings);
- the other published Ultra/EVM files against their last package pins.
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
    s2 = manifest("CLAUDE-WUA-CHAT-S2-SHARED-STORAGE-001")
    stage2 = {rel: {"sha256_now": sha((REPO / rel).read_bytes()), "same_content_as_stage2_package": same(rel, row["sha256"])}
              for group in ("changed_files", "new_files") for rel, row in s2[group].items()}
    pins = {}
    for task, key in (("CLAUDE-WUA-CHAT-LAUNCHER-001", "new_files"), ("CLAUDE-WUA-CHAT-S1-READONLY-UI-001", "changed_files"),
                      ("CLAUDE-WUA-EVM-PINNED-MULTIWINDOW-001", "changed_files")):
        pins.update({rel: row["sha256"] for rel, row in manifest(task)[key].items()})
    others = {rel: same(rel, pin) for rel, pin in sorted(pins.items()) if rel not in stage2}
    config = json.loads((REPO / "web_alarm/launch_config.json").read_text(encoding="utf-8"))
    launch = load_launch()
    record = {
        "task": "CLAUDE-WUA-CHAT-S2-CONTEXT-PATH-REPAIR-001", "purpose": "pre-start state before the first edit",
        "base": "main@254e48166407d3aabf6484c8627da86acf8b05df (No.474); engineering bytes = Stage2 package (No.473), checked by content",
        "card_check": {"exit": check.returncode, "result": protocol["result"], "card_sha256": protocol["card_sha256"],
                       "block1": protocol["block1"], "block1_1": protocol["block1_1"]},
        "launcher": {"config_active": config["active"], "load_launch_standard": launch.standard,
                     "launcher_files_same_as_package": {rel: others.get(rel) for rel in ("Start_WebAlarm.bat", "web_alarm/launcher.py",
                                                                                         "web_alarm/launch_config.json")}},
        "stage2_files": stage2,
        "other_published_files_same": others,
        "no_drift": all(v["same_content_as_stage2_package"] for v in stage2.values()) and all(others.values()),
        "parallel_work": "Direction B has no active TASK on these files (No.34/No.40); the Stage2 package is closed REVISE",
        "git_used": False,
    }
    Path(sys.argv[1]).write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"check": protocol["result"], "block1": protocol["block1"].get("task_id"), "launcher": config["active"],
                      "no_drift": record["no_drift"], "stage2": {k: v["same_content_as_stage2_package"] for k, v in stage2.items()}}))


if __name__ == "__main__":
    main()
