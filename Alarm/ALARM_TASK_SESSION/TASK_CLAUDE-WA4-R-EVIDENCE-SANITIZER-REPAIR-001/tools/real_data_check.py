"""Compatibility check of the repaired tool on the real published package (read-only; output only in TEMP).

1. stage TASK_CLAUDE-WA4-R-TRANSPORT-TAIL-RECOVERY-001 in manifest mode into a fresh TEMP directory;
2. verify with --package, without any anchor, and with --mapping-sha256 (the hash printed by stage);
3. scan the candidate with --manifest (its manifest must describe the sanitized bytes);
4. verify the previous TASK's private bundle (made by the pre-repair tool) against the package - expected REFUSED
   because its candidate manifest still carries the hashes of the originals.
Prints one JSON object with counts and verdicts only (no paths, no values).
Usage: real_data_check.py <python>
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
PACKAGE = "Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA4-R-TRANSPORT-TAIL-RECOVERY-001"
OLD_BUNDLE = "logs/test-evidence/web_alarm/CLAUDE-WA4-R-EVIDENCE-SANITIZATION-001/tail-recovery-stage-final"
python = sys.argv[1]
out = Path(tempfile.mkdtemp(prefix="claude-esrep-real-")) / "stage"


def tool(*args):
    proc = subprocess.run([python, "-B", "-X", "utf8", "-m", "web_alarm.evidence_sanitizer", "--repo-anchor", "ag_llm",
                           *map(str, args)], cwd=REPO, capture_output=True, text=True, encoding="utf-8")
    return proc.returncode, json.loads(proc.stdout)


report = {}
code, staged = tool("stage", PACKAGE, "--out", out, "--manifest")
report["stage"] = {"exit": code, **{k: staged[k] for k in ("files_total", "files_changed", "files_blocked", "verdict",
                                                            "replacements_total", "kept_total", "tool_sha256_lf")}}
mapping = json.loads((out / "mapping.json").read_text(encoding="utf-8"))
manifest_row = next(r for r in mapping["files"] if r["id"] == "manifest.json")
checks = {}
for row in mapping["files"]:
    checks[str(row.get("manifest_check"))] = checks.get(str(row.get("manifest_check")), 0) + 1
report["manifest_checks"] = checks
report["candidate_manifest"] = {"changed": manifest_row["changed"],
                                "rehashed_entries": manifest_row.get("manifest_rehashed_entries")}
for name, extra in (("with_package", ["--package", PACKAGE]), ("no_anchor", []),
                    ("mapping_sha256", ["--mapping-sha256", staged["mapping_sha256"]])):
    code, result = tool("verify", out, *extra)
    report["verify_" + name] = {"exit": code, **{k: result[k] for k in ("verdict", "completeness", "publication",
                                                                         "problems")}}
code, scanned = tool("scan", out / "sanitized", "--manifest")
report["scan_candidate"] = {"exit": code, "classes": scanned["classes"]}
if (REPO / OLD_BUNDLE / "mapping.json").is_file():
    code, result = tool("verify", OLD_BUNDLE, "--package", PACKAGE)
    report["verify_previous_bundle"] = {"exit": code, **{k: result[k] for k in ("verdict", "publication", "problems")}}
else:
    report["verify_previous_bundle"] = "NOT RUN (private bundle not present)"
print(json.dumps(report, ensure_ascii=True, indent=1))
