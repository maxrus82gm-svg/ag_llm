"""Phase/order and per-run source provenance from the original evidence.zip members (read-only)."""
import hashlib
import json
import zipfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO = Path(r"M:\GitHub\ag_llm")
PKG = REPO / "reports" / "CODEX-WA4-R-006-WINDOWS-F1F2F3-LOCAL-GATE"
KEY = ["web_alarm/task_store.py", "web_alarm/event_checkpoint_store.py", "web_alarm/operation_store.py",
       "test_web_alarm_wa4r006_local_gate.py"]
checks = json.loads((PKG / "checks.json").read_bytes())
versions = json.loads((PKG / "versions.json").read_bytes())
final = checks["final_full_source_sha256"]
initial = versions["initial_pins"]
tz = timezone(timedelta(hours=5))


def canon(v):
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


with zipfile.ZipFile(PKG / "evidence.zip") as zf:
    rows = []
    for run in checks["runs"]:
        res = json.loads(zf.read(run["member"]))
        src = res["source_sha256"]
        diff_final = sorted(k for k in set(src) | set(final) if src.get(k) != final.get(k))
        key_state = {}
        for k in KEY:
            v = src.get(k)
            key_state[k.split("/")[-1]] = ("FINAL" if v == final.get(k) else
                                           "INITIAL" if v == initial.get(k) else
                                           "ABSENT" if v is None else "OTHER:" + v[:12])
        rows.append((res["started_unix"], run["attempt"], res["started_unix"] + res["elapsed_seconds"],
                     len(src), hashlib.sha256(canon(src)).hexdigest() == run["source_map_canonical_sha256"],
                     diff_final, key_state, res.get("successful")))
    rows.sort()
    for start, att, end, n, mapok, diff, ks, ok in rows:
        print(f"{datetime.fromtimestamp(start, tz):%H:%M:%S}-{datetime.fromtimestamp(end, tz):%H:%M:%S} {att:<22} "
              f"src={n} map_ok={mapok} successful={ok} diff_vs_final={diff[:6]}{'…' if len(diff) > 6 else ''}")
        print("     ", ks)
    print("\nZIP members:")
    for info in zf.infolist():
        print(f"  {info.file_size:>9} {info.filename}")
print("\nversions.changes:")
for c in versions["changes"]:
    print(" ", json.dumps(c, ensure_ascii=False)[:400])
