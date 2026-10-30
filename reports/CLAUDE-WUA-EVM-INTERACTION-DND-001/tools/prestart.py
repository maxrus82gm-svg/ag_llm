"""Pre-start record of CLAUDE-WUA-EVM-INTERACTION-DND-001, taken before the first edit:
- the slot check of the Claude card (tools/task_slot_rotate.py check);
- the launcher mode (launch_config.json and load_launch(): STANDARD, nothing switched);
- the files of the task scope compared with the published EVM package #457 (its manifest), allowing the CRLF
  that the user's synchronisation gives (no Git is used or read).
Only hashes, states and counters are written, never a path outside the repository.
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
SCOPE = ("web_alarm/ui.py", "web_alarm/server.py", "web_alarm/model_cards.py", "test_web_alarm_model_cards.py",
         "test_web_alarm_evm_ui.js")
sha = lambda data: hashlib.sha256(data).hexdigest()


def main():
    check = subprocess.run([sys.executable, "-B", "tools/task_slot_rotate.py", "check", "--card", CARD], cwd=REPO,
                           capture_output=True, text=True, encoding="utf-8")
    protocol = json.loads(check.stdout)
    config = json.loads((REPO / "web_alarm/launch_config.json").read_text(encoding="utf-8"))
    launch = load_launch()
    evm = json.loads((REPO / "reports/CLAUDE-WUA-EVM-COMPACT-LAYOUT-001/manifest.json").read_text(encoding="utf-8"))
    scope = {}
    for rel in SCOPE:
        data = (REPO / rel).read_bytes()
        lf = data.replace(b"\r\n", b"\n")
        pin = evm["changed_files"][rel]["sha256"]
        scope[rel] = {"sha256": sha(data), "eol": "CRLF" if b"\r\n" in data else "LF",
                      "same_content_as_published_457": pin in {sha(data), sha(lf), sha(lf.replace(b"\n", b"\r\n"))}}
    record = {
        "task": "CLAUDE-WUA-EVM-INTERACTION-DND-001", "purpose": "pre-start state before the first edit",
        "card_check": {"exit": check.returncode, "result": protocol["result"], "card_sha256": protocol["card_sha256"],
                       "eol": protocol["eol"], "block1": protocol["block1"], "block1_1": protocol["block1_1"]},
        "launcher": {"config_active": config["active"], "load_launch": {"name": launch.name, "standard": launch.standard,
                                                                         "port": launch.port, "storage": launch.storage,
                                                                         "kind": launch.kind}},
        "scope_vs_published_457": scope,
        "no_conflicting_changes": all(r["same_content_as_published_457"] for r in scope.values()),
        "git_used": False,
    }
    Path(sys.argv[1]).write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"check": protocol["result"], "launcher": config["active"], "standard": launch.standard,
                      "no_conflicting_changes": record["no_conflicting_changes"]}))


if __name__ == "__main__":
    main()
