"""Compare my independent attempts with the R-006 originals (IDs, statuses, source map) — read-only.
Usage: compare_runs.py <my results.json> <R-006 attempt member, e.g. attempts/full-release/results.json>"""
import hashlib
import json
import sys
import zipfile
from collections import Counter
from pathlib import Path

PKG = Path(r"M:\GitHub\ag_llm\reports\CODEX-WA4-R-006-WINDOWS-F1F2F3-LOCAL-GATE")
mine_path, member = Path(sys.argv[1]), sys.argv[2]
mine_bytes = mine_path.read_bytes()
mine = json.loads(mine_bytes)
with zipfile.ZipFile(PKG / "evidence.zip") as zf:
    orig = json.loads(zf.read(member))
checks = json.loads((PKG / "checks.json").read_bytes())
pins = checks["final_full_source_sha256"]
m_status = {t["test"]: t["status"] for t in mine["tests"]}
o_status = {t["test"]: t["status"] for t in orig["tests"]}
only_mine, only_orig = sorted(set(m_status) - set(o_status)), sorted(set(o_status) - set(m_status))
differ = sorted((k, o_status[k], m_status[k]) for k in set(m_status) & set(o_status) if m_status[k] != o_status[k])
src = mine["source_sha256"]
src_diff = sorted(k for k in set(src) | set(pins) if src.get(k) != pins.get(k))
focused = checks["focused_within_full"]["test_ids"]
print(json.dumps({
    "my_results_sha256": hashlib.sha256(mine_bytes).hexdigest(),
    "mine": {k: mine[k] for k in ("tests_run", "passed", "failures", "errors", "skips", "elapsed_seconds", "python")},
    "mine_status_counts": Counter(m_status.values()),
    "orig": {k: orig[k] for k in ("tests_run", "passed", "failures", "errors", "skips", "elapsed_seconds")},
    "isolation_violations_mine": len(mine["isolation_violations"]),
    "ids_only_in_mine": only_mine[:20], "ids_only_in_orig": only_orig[:20],
    "same_id_different_status": differ[:40],
    "my_source_map_vs_R006_pins_diff": src_diff,
    "focused_103_in_mine": sum(i in m_status for i in focused),
    "focused_103_pass_in_mine": sum(m_status.get(i) == "PASS" for i in focused),
    "non_pass_mine": [(t["test"], t["status"], (t.get("reason") or t.get("error") or "")[-400:])
                      for t in mine["tests"] if t["status"] != "PASS"],
}, ensure_ascii=False, indent=1, default=dict))
