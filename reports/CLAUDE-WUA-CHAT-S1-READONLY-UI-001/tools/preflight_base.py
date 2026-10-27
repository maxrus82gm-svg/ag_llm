"""Stage 1 source preflight without Git: compare the current local bytes with the stage-0 baseline record.

Stage 0 (`reports/CLAUDE-WUA-CHAT-S0-BASELINE-CONTRACT-001/evidence/baseline.json`, published in main@734cbfc9 and
accepted by WEB_14) holds byte length and SHA-256 of every source the read-only Ultra Chat touches. This tool hashes
the same files again, plus the files stage 1 needs that stage 0 did not list, and reports any drift. Read-only.
Usage: preflight_base.py <out.json>
"""
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
STAGE0 = REPO / "reports" / "CLAUDE-WUA-CHAT-S0-BASELINE-CONTRACT-001" / "evidence" / "baseline.json"
EXTRA = ("web_alarm/workspace_registry.py", "web_alarm/__init__.py", "web_alarm/__main__.py", "web_alarm/cli.py",
         "test_web_alarm_evm_ui.js", "test_web_alarm_folder_picker.py", "test_web_alarm_ultra_connections.py",
         "test_failed_run_terminal_message.py", "wa4o_ui_launcher.py", "wa4o_ui_demo.py")
PLANNED = ("context_storage.py", "web_alarm/server.py", "web_alarm/ui.py", "test_web_alarm_evm_ui.js")


def facts(rel):
    path = REPO / rel
    if not path.is_file():
        return {"exists": False}
    data = path.read_bytes()
    return {"exists": True, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "eol": "CRLF" if b"\r\n" in data else "LF"}


stage0 = json.loads(STAGE0.read_text(encoding="utf-8"))
reference = {rel: {"bytes": row["astra_bytes"], "sha256": row["astra_sha256"]} for rel, row in stage0["compared"].items()}
reference.update({rel: {"bytes": row["bytes"], "sha256": row["sha256"]}
                  for rel, row in stage0["additional_files"].items() if row.get("exists")})
compared, drift = {}, []
for rel, ref in sorted(reference.items()):
    now = facts(rel)
    same = now.get("exists") and now["bytes"] == ref["bytes"] and now["sha256"] == ref["sha256"]
    compared[rel] = {"stage0_sha256": ref["sha256"], **now, "unchanged_since_stage0": bool(same)}
    if not same:
        drift.append(rel)
result = {"reference": "stage-0 evidence/baseline.json (main@734cbfc9, WEB_14 PASS)", "compared": compared,
          "drift_since_stage0": drift, "new_base_files": {rel: facts(rel) for rel in EXTRA if rel not in reference},
          "planned_changes": {rel: {"in_stage0_reference": rel in reference, "unchanged": rel not in drift}
                              for rel in PLANNED}, "git_used": False}
Path(sys.argv[1]).write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({"compared": len(compared), "drift": drift, "planned": result["planned_changes"]}, ensure_ascii=False))
