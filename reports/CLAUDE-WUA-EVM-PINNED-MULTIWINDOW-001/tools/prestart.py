"""Pre-start record of CLAUDE-WUA-EVM-PINNED-MULTIWINDOW-001, taken before the first edit:
- the slot check of the Claude card (tools/task_slot_rotate.py check);
- the launcher mode (launch_config.json, load_launch(): STANDARD, nothing switched) and Start_WebAlarm.bat content;
- the files of the task scope compared with the accepted #464 package (ui.py, EVM page tests) and the published #457
  package (server.py, model_cards.py, their tests), allowing the CRLF of the user's synchronisation (no Git is used).
Only hashes, states and counters are written.
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


def same(rel: str, pin: str) -> dict:
    data = (REPO / rel).read_bytes()
    lf = data.replace(b"\r\n", b"\n")
    return {"sha256": sha(data), "eol": "CRLF" if b"\r\n" in data else "LF",
            "same_content_as_pin": pin in {sha(data), sha(lf), sha(lf.replace(b"\n", b"\r\n"))}}


def manifest(task: str) -> dict:
    return json.loads((REPO / "reports" / task / "manifest.json").read_text(encoding="utf-8"))


def main():
    check = subprocess.run([sys.executable, "-B", "tools/task_slot_rotate.py", "check", "--card", CARD], cwd=REPO,
                           capture_output=True, text=True, encoding="utf-8")
    protocol = json.loads(check.stdout)
    config = json.loads((REPO / "web_alarm/launch_config.json").read_text(encoding="utf-8"))
    launch = load_launch()
    m464, m457, launcher = (manifest("CLAUDE-WUA-EVM-INTERACTION-DND-001"), manifest("CLAUDE-WUA-EVM-COMPACT-LAYOUT-001"),
                            manifest("CLAUDE-WUA-CHAT-LAUNCHER-001"))
    scope = {rel: {"pin": "#464", **same(rel, row["sha256"])} for rel, row in m464["changed_files"].items()}
    for rel in ("web_alarm/server.py", "web_alarm/model_cards.py", "test_web_alarm_model_cards.py"):
        scope[rel] = {"pin": "#457", **same(rel, m457["changed_files"][rel]["sha256"])}
    bat = {rel: same(rel, row["sha256"]) for rel, row in launcher["new_files"].items() if rel.endswith(".bat") or rel.endswith("launcher.py")}
    record = {
        "task": "CLAUDE-WUA-EVM-PINNED-MULTIWINDOW-001", "purpose": "pre-start state before the first edit",
        "card_check": {"exit": check.returncode, "result": protocol["result"], "card_sha256": protocol["card_sha256"],
                       "eol": protocol["eol"], "block1": protocol["block1"], "block1_1": protocol["block1_1"]},
        "card_check_first": "INVALID (WAITING_LINE_LEFT_IN_TASK, line 46) before the user's fix; reported, not fixed by the executor",
        "launcher": {"config_active": config["active"], "load_launch": {"name": launch.name, "standard": launch.standard,
                                                                         "port": launch.port, "storage": launch.storage}},
        "launcher_files_vs_published": bat,
        "scope_vs_published": scope,
        "no_conflicting_changes": all(r["same_content_as_pin"] for r in scope.values()),
        "direction_b_active_files": "none (No.40, section B)",
        "git_used": False,
    }
    Path(sys.argv[1]).write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"check": protocol["result"], "launcher": config["active"], "no_conflicting_changes": record["no_conflicting_changes"],
                      "bat_ok": all(v["same_content_as_pin"] for v in bat.values())}))


if __name__ == "__main__":
    main()
